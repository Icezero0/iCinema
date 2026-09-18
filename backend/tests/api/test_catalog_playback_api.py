import pytest

from app.modules.catalog.models import CatalogCategory
from app.modules.site.constants import SiteRole

BASE = "/api/v1/admin/catalog/contents"


@pytest.fixture
async def setup_catalog(api_client, factories, auth_headers, db_session):
    db_session.add(CatalogCategory(code="japanese_animation", name="日本动画"))
    admin = await factories.create_user(site_role=SiteRole.ADMIN)
    await factories.commit()
    headers = auth_headers(admin)
    content = (await api_client.post(BASE, headers=headers, json={"title": "测试作品"})).json()
    return headers, content


async def mutate(client, headers, content_id, entity, values, item_id=None, version=None):
    path = f"{BASE}/{content_id}"
    if version is None:
        version = (await client.get(path, headers=headers)).json()["version"]
    return await client.request("POST" if item_id is None else "PUT",
        f"{path}/{entity}" + ("" if item_id is None else f"/{item_id}"),
        headers=headers, json={**values, "version": version})


async def populated(client, headers, content_id):
    for values in ({"title": "第1集", "number": 1}, {"title": "第2集", "number": 2}):
        assert (await mutate(client, headers, content_id, "episodes", values)).status_code == 200
    for key in ("a", "b"):
        assert (await mutate(client, headers, content_id, "lines", {"name": key, "source_key": "manual", "line_key": key})).status_code == 200
    graph = (await client.get(f"{BASE}/{content_id}/graph", headers=headers)).json()
    for line in graph["lines"]:
        response = await mutate(client, headers, content_id, "playbacks", {
            "episode_id": graph["episodes"][0]["id"], "line_id": line["id"],
            "url": "https://media.example.test/video.m3u8?token=a%2Fb", "media_type": "hls"})
        assert response.status_code == 200, response.text
    return response.json()


def editable(item):
    return {key: value for key, value in item.items() if key not in ("id", "content_id", "available_line_count", "display_name")}


async def test_graph_dynamic_lines_missing_episodes_audit_and_preview(api_client, setup_catalog):
    headers, content = setup_catalog
    path = f"{BASE}/{content['id']}"
    empty = (await api_client.get(path + "/graph", headers=headers)).json()
    assert empty["episodes"] == empty["lines"] == empty["playbacks"] == []
    graph = await populated(api_client, headers, content["id"])
    assert [episode["available_line_count"] for episode in graph["episodes"]] == [2, 0]
    assert graph["content"]["status"] == "draft" and graph["content"]["version"] == 7
    entry = graph["playbacks"][0]
    preview = await api_client.get(f"{path}/playbacks/{entry['id']}/preview", headers=headers)
    assert preview.status_code == 200 and preview.json()["url"] == entry["url"]
    audit = (await api_client.get(path + "/audits", headers=headers)).json()
    assert audit["total"] == 7
    assert audit["items"][0]["action"] == "playback_create"
    assert audit["items"][0]["changes"]["item_id"]["after"] == graph["playbacks"][-1]["id"]


@pytest.mark.parametrize("entity,remaining", [("episodes", 0), ("lines", 1), ("playbacks", 1)])
async def test_disable_is_scoped_and_restore_preserves_mappings(api_client, setup_catalog, entity, remaining):
    headers, content = setup_catalog
    graph = await populated(api_client, headers, content["id"])
    item = graph[entity][0]
    payload = {**editable(item), "disabled": True, "disabled_reason": "测试禁用"}
    result = await mutate(api_client, headers, content["id"], entity, payload, item["id"])
    assert result.status_code == 200, result.text
    assert result.json()["episodes"][0]["available_line_count"] == remaining
    assert len(result.json()["playbacks"]) == 2
    path = f"{BASE}/{content['id']}/playbacks"
    assert (await api_client.get(f"{path}/{graph['playbacks'][0]['id']}/preview", headers=headers)).status_code == 400
    other = await api_client.get(f"{path}/{graph['playbacks'][1]['id']}/preview", headers=headers)
    assert other.status_code == (400 if entity == "episodes" else 200)
    restored = await mutate(api_client, headers, content["id"], entity, {**payload, "disabled": False}, item["id"])
    assert restored.json()["episodes"][0]["available_line_count"] == 2
    assert restored.json()[entity][0]["disabled_reason"] == ""


async def test_duplicate_and_stale_updates_roll_back_version_and_audit(api_client, setup_catalog):
    headers, content = setup_catalog
    graph = await populated(api_client, headers, content["id"])
    version = graph["content"]["version"]
    for entity in ("episodes", "lines", "playbacks"):
        duplicate = await mutate(api_client, headers, content["id"], entity, editable(graph[entity][0]))
        assert duplicate.status_code == 409
    episode = graph["episodes"][0]
    # No-op does not create an audit record or invalidate other editors.
    unchanged = await mutate(api_client, headers, content["id"], "episodes", editable(episode), episode["id"])
    assert unchanged.json()["content"]["version"] == version
    changed = await mutate(api_client, headers, content["id"], "episodes", {**editable(episode), "title": "更新"}, episode["id"])
    assert changed.status_code == 200
    stale = await mutate(api_client, headers, content["id"], "lines", {**editable(graph["lines"][0]), "name": "覆盖"}, graph["lines"][0]["id"], version)
    assert stale.status_code == 409
    audit = (await api_client.get(f"{BASE}/{content['id']}/audits", headers=headers)).json()
    assert audit["total"] == 8


async def test_mapping_can_move_and_special_episode_is_distinct(api_client, setup_catalog):
    headers, content = setup_catalog
    graph = await populated(api_client, headers, content["id"])
    entry = graph["playbacks"][0]
    moved = await mutate(api_client, headers, content["id"], "playbacks", {**editable(entry), "episode_id": graph["episodes"][1]["id"]}, entry["id"])
    assert [x["available_line_count"] for x in moved.json()["episodes"]] == [1, 1]
    special = await mutate(api_client, headers, content["id"], "episodes", {"title": "特别篇", "kind": "special", "number": 1, "sort_order": 99})
    assert special.status_code == 200
    assert special.json()["episodes"][-1]["kind"] == "special"
    updated = await mutate(api_client, headers, content["id"], "lines", {**editable(graph["lines"][1]), "sort_order": 10}, graph["lines"][1]["id"])
    assert updated.json()["lines"][-1]["id"] == graph["lines"][1]["id"]


async def test_parent_disable_and_player_pages_are_not_previewable(api_client, setup_catalog):
    headers, content = setup_catalog
    graph = await populated(api_client, headers, content["id"])
    entry = graph["playbacks"][0]
    changed = await mutate(api_client, headers, content["id"], "playbacks", {**editable(entry), "media_type": "page"}, entry["id"])
    assert changed.json()["episodes"][0]["available_line_count"] == 1
    path = f"{BASE}/{content['id']}"
    assert (await api_client.get(f"{path}/playbacks/{entry['id']}/preview", headers=headers)).status_code == 400
    current = changed.json()["content"]
    payload = {k: v for k, v in current.items() if k not in ("id", "created_at", "updated_at")}
    assert (await api_client.put(path, headers=headers, json={**payload, "disabled": True, "disabled_reason": "作品禁用"})).status_code == 200
    assert (await api_client.get(path + "/graph", headers=headers)).json()["episodes"][0]["available_line_count"] == 0
    assert (await api_client.get(f"{path}/playbacks/{graph['playbacks'][1]['id']}/preview", headers=headers)).status_code == 400


async def test_admin_permissions_and_cross_work_ownership(api_client, setup_catalog, factories, auth_headers):
    headers, content = setup_catalog
    graph = await populated(api_client, headers, content["id"])
    second = (await api_client.post(BASE, headers=headers, json={"title": "另一作品"})).json()
    user = await factories.create_user()
    await factories.commit()
    path = f"{BASE}/{content['id']}"
    for credentials, status in [({}, 401), (auth_headers(user), 403)]:
        assert (await api_client.get(path + "/graph", headers=credentials)).status_code == status
        assert (await api_client.get(f"{path}/playbacks/{graph['playbacks'][0]['id']}/preview", headers=credentials)).status_code == status
        for entity in ("episodes", "lines", "playbacks"):
            item = graph[entity][0]
            for item_id in (None, item["id"]):
                response = await mutate(api_client, credentials, content["id"], entity, editable(item), item_id, graph["content"]["version"])
                assert response.status_code == status
    for entity in ("episodes", "lines", "playbacks"):
        item = graph[entity][0]
        assert (await mutate(api_client, headers, second["id"], entity, editable(item), item["id"])).status_code == 404
    assert (await mutate(api_client, headers, second["id"], "playbacks", editable(graph["playbacks"][0]))).status_code == 404
    assert (await api_client.get(f"{BASE}/{second['id']}/playbacks/{graph['playbacks'][0]['id']}/preview", headers=headers)).status_code == 404
    assert (await api_client.get(f"{BASE}/999999/graph", headers=headers)).status_code == 404


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///tmp/video", "https://user:password@example.test/a", "https://example.test/a\nX", "https://example.test\\evil/a"])
async def test_unsafe_url_rejected_without_mutation(api_client, setup_catalog, url):
    headers, content = setup_catalog
    response = await mutate(api_client, headers, content["id"], "playbacks", {"episode_id": 1, "line_id": 1, "url": url})
    assert response.status_code == 422
    assert (await api_client.get(f"{BASE}/{content['id']}", headers=headers)).json()["version"] == 1


async def test_invalid_numbers_and_disable_reason(api_client, setup_catalog):
    headers, content = setup_catalog
    for changes in ({"season": 1}, {"number": -0.5}, {"number": 100000}, {"number": "NaN"}, {"disabled": True}, {"kind": "invalid"}, {"title": "  "}):
        assert (await mutate(api_client, headers, content["id"], "episodes", {"title": "一集", **changes})).status_code == 422


async def test_named_seasons_are_separate_works_without_episode_season(api_client, setup_catalog):
    headers, _ = setup_catalog
    episode_ids = []
    for title in ("测试动画 第一季", "测试动画 第二季"):
        content = (await api_client.post(BASE, headers=headers, json={"title": title})).json()
        response = await mutate(api_client, headers, content["id"], "episodes", {"title": "第1集", "number": 1})
        assert response.status_code == 200
        graph = response.json()
        assert graph["content"]["title"] == title
        assert graph["episodes"][0]["number"] == 1
        assert "season" not in graph["episodes"][0]
        episode_ids.append(graph["episodes"][0]["id"])
    assert len(set(episode_ids)) == 2
