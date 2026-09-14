import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.body_limit import RequestBodyLimitMiddleware
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token
from app.modules.media.models import MediaAsset
from app.modules.media.service import MediaService
from app.modules.users.schemas import UserPatch
from app.modules.users.service import UserService
from app.realtime.auth import authenticate_websocket_token
from app.realtime.manager import RealtimeManager
from app.realtime.protocol import build_event_message
from app.realtime.constants import WsEventType
from app.realtime.handlers.dispatcher import RealtimeMessageHandler
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService


async def upload(client, headers, content=b"small-test-image", kind="images"):
    return await client.post(f"/api/v1/media/{kind}", headers=headers,
                            files={"file": ("test.png", content, "image/png")})


@pytest.mark.parametrize("with_length", [True, False])
async def test_request_limit_rejects_before_parser_including_chunked(with_length):
    called = False
    async def app(scope, receive, send):
        nonlocal called
        called = True
    chunks = iter([{"type": "http.request", "body": b"1234", "more_body": True},
                   {"type": "http.request", "body": b"56789", "more_body": False}])
    async def receive():
        return next(chunks)
    sent = []
    async def send(message):
        sent.append(message)
    # An understated header cannot bypass the actual byte counter either.
    headers = [(b"content-length", b"1")] if with_length else []
    await RequestBodyLimitMiddleware(app, 8)({"type": "http", "headers": headers}, receive, send)
    assert not called
    assert sent[0]["status"] == 413


async def test_request_limit_replays_exact_boundary_body():
    received = bytearray()
    async def app(scope, receive, send):
        while True:
            chunk = await receive()
            received.extend(chunk["body"])
            if not chunk["more_body"]:
                break
    async def receive():
        return {"type": "http.request", "body": b"12345678", "more_body": False}
    async def send(message):
        pass
    await RequestBodyLimitMiddleware(app, 8)({"type": "http", "headers": []}, receive, send)
    assert received == b"12345678"


async def test_file_limit_and_quota_preserve_small_uploads(api_client, factories, auth_headers, monkeypatch):
    user = await factories.create_user()
    await factories.commit()
    headers = auth_headers(user)
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 8)
    monkeypatch.setattr(get_settings(), "user_media_quota_bytes", 9)
    assert (await upload(api_client, headers, b"123456789")).status_code == 413
    accepted = await upload(api_client, headers, b"12345678")
    assert accepted.status_code == 200
    # Public media remains public; content verification is intentionally deferred.
    assert (await api_client.get(accepted.json()["url"])).content == b"12345678"
    assert (await upload(api_client, headers, b"ab", "stickers")).status_code == 413
    # Deduplication allocates no new storage, including at the quota boundary.
    assert (await upload(api_client, headers, b"12345678")).json()["id"] == accepted.json()["id"]


async def test_concurrent_uploads_cannot_overspend_quota(api_client, factories, auth_headers, monkeypatch):
    user = await factories.create_user()
    await factories.commit()
    monkeypatch.setattr(get_settings(), "user_media_quota_bytes", 8)
    responses = await asyncio.gather(upload(api_client, auth_headers(user), b"12345678"),
                                     upload(api_client, auth_headers(user), b"abcdefgh"))
    assert sorted(r.status_code for r in responses) == [200, 413]


async def test_public_image_collection_respects_copy_quota(api_client, factories, auth_headers, monkeypatch):
    owner = await factories.create_user()
    collector = await factories.create_user()
    await factories.commit()
    source = await upload(api_client, auth_headers(owner), b"12345678")
    url = f"/api/v1/media/images/{source.json()['id']}/collect-as-sticker"
    monkeypatch.setattr(get_settings(), "user_media_quota_bytes", 7)
    assert (await api_client.post(url, headers=auth_headers(collector))).status_code == 413
    monkeypatch.setattr(get_settings(), "user_media_quota_bytes", 8)
    assert (await api_client.post(url, headers=auth_headers(collector))).status_code == 200


async def test_rollback_removes_uncommitted_feedback_files(db_session, factories):
    user = await factories.create_user()
    await factories.commit()
    service = MediaService()
    asset = await service.create_feedback_image_asset_in_tx(db_session, user=user,
        file=UploadFile(BytesIO(b"screenshot"), filename="shot.png", headers=Headers({"content-type": "image/png"})))
    path = service.storage.get_file_path(asset_type=asset.asset_type, storage_key=asset.storage_key)
    assert path.exists()
    await db_session.rollback()
    assert not path.exists()


async def test_lazy_expiry_cleanup_and_reupload_restore_real_file(api_client, db_session, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()
    headers = auth_headers(user)
    first = (await upload(api_client, headers)).json()
    asset = await db_session.get(MediaAsset, first["id"])
    asset.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()
    service = MediaService()
    path = service.storage.get_file_path(asset_type=asset.asset_type, storage_key=asset.storage_key)
    assert (await api_client.get(first["url"])).status_code == 404
    assert await service.cleanup_expired_images(db_session) == 1
    assert not path.exists()
    assert await service.cleanup_expired_images(db_session) == 0
    second = await upload(api_client, headers)
    assert second.status_code == 200
    assert (await api_client.get(second.json()["url"])).content == b"small-test-image"
    assert (await api_client.get(first["url"])).status_code == 404


async def test_sticker_library_defaults_and_all_contract(api_client, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()
    headers = auth_headers(user)
    response = await api_client.get("/api/v1/media/stickers/library", headers=headers)
    assert response.status_code == 200
    assert (response.json()["page"], response.json()["page_size"]) == (1, 20)
    assert (await api_client.get("/api/v1/media/stickers/library?all=true", headers=headers)).status_code == 200
    assert (await api_client.get("/api/v1/media/stickers/library?all=true&page=1", headers=headers)).status_code == 400


async def test_password_change_revokes_access_refresh_and_ws(api_client, db_session, factories, auth_headers):
    user = await factories.create_user()
    await factories.commit()
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    email = user.email
    headers = {"Authorization": f"Bearer {access}"}
    assert (await api_client.patch("/api/v1/users/me", headers=headers, json={"username": "renamed"})).status_code == 200
    assert (await api_client.get("/api/v1/users/me", headers=headers)).status_code == 200
    assert (await api_client.patch("/api/v1/users/me", headers=headers, json={"password": "new-password"})).status_code == 200
    assert (await api_client.get("/api/v1/users/me", headers=headers)).status_code == 401
    assert (await api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})).status_code == 401
    db_session.expire_all()
    with pytest.raises(UnauthorizedError):
        await authenticate_websocket_token(db_session, token=access)
    login = await api_client.post("/api/v1/auth/login", json={"email": email, "password": "new-password"})
    assert login.status_code == 200
    new_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert (await api_client.get("/api/v1/users/me", headers=new_headers)).status_code == 200
    # Another immediate password change also revokes, without second-resolution iat races.
    assert (await api_client.patch("/api/v1/users/me", headers=new_headers, json={"password": "third-password"})).status_code == 200
    assert (await api_client.post("/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})).status_code == 401


async def test_established_ws_cannot_receive_after_password_change(db_session, factories):
    user = await factories.create_user()
    await factories.commit()
    class Socket:
        closed = False
        sent = []
        async def close(self, **kwargs):
            self.closed = True
        async def send_json(self, message):
            self.sent.append(message)
    ws = Socket()
    manager = RealtimeManager()
    connection = await manager.register_connection(user_id=user.id, websocket=ws, token_version=user.token_version)
    await UserService().patch_me(db_session, user, UserPatch(password="changed"))
    await manager.send_to_connection(connection_id=connection.connection_id,
        message=build_event_message(event=WsEventType.NOTIFICATION))
    assert ws.closed
    assert not ws.sent


async def test_established_ws_cannot_send_commands_after_password_change(db_session, factories):
    user = await factories.create_user()
    await factories.commit()
    class Socket:
        closed = False
        sent = []
        async def close(self, **kwargs): self.closed = True
        async def send_json(self, message): self.sent.append(message)
    ws = Socket()
    manager = RealtimeManager()
    connection = await manager.register_connection(user_id=user.id, websocket=ws, token_version=user.token_version)
    await UserService().patch_me(db_session, user, UserPatch(password="changed"))
    handler = RealtimeMessageHandler(presence_service=RoomPresenceService(), video_runtime_service=RoomVideoRuntimeService())
    await handler.handle(db=db_session, manager=manager, publisher=RealtimePublisher(manager), websocket=ws,
                         connection=connection, raw_message={"v": 1, "type": "command", "payload": {
                             "request_id": "old-session", "action": "room_enter", "data": {"room_id": 1}}})
    assert ws.closed
    assert ws.sent[-1]["payload"]["reason"] == "session_revoked"


async def test_server_time_is_present_in_outbound_envelope():
    before = int(datetime.now(timezone.utc).timestamp() * 1000)
    message = build_event_message(event=WsEventType.NOTIFICATION).model_dump(mode="json")
    assert before <= message["server_ts_ms"] <= int(datetime.now(timezone.utc).timestamp() * 1000)
