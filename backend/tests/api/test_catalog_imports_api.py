import time

import pytest
from sqlalchemy import select, func

from app.core.exceptions import BadRequestError, ConflictError
from app.modules.catalog import import_service, provider_client
from app.modules.catalog.import_models import CatalogProvider, CatalogSource, CatalogImportJob
from app.modules.catalog.models import CatalogCategory, CatalogContent, CatalogAudit, CatalogPlayback
from app.modules.site.constants import SiteRole

BASE = "/api/v1/admin"


@pytest.fixture
async def aggregate_setup(import_setup, db_session, monkeypatch):
    headers, state = import_setup
    db_session.add(CatalogProvider(id=2, code="second", name="Second site", endpoint="https://second.example.test/api",
        enabled=True, category="japanese_animation", upstream_category=97, play_from="second_hls"))
    await db_session.commit()
    state.update(second_title="测试动画 第二季", extra=False, broken=False)

    async def fake(pid, endpoint, params):
        state["calls"].append((pid, dict(params)))
        if pid == 2 and state["broken"]:
            raise BadRequestError("Unavailable", reason="catalog_provider_unavailable")
        title = state["title"] if pid == 1 else state["second_title"]
        category = 25 if pid == 1 else 97
        row = dict(vod_id=1, vod_name=title, type_id=category, vod_time="2026-09-17 10:00:00")
        if params["ac"] == "list":
            return dict(code=1, page=1, pagecount=1, total=1, list=[row])
        row.update(vod_year="2024", vod_area="日本", vod_play_from="jinyingm3u8" if pid == 1 else "second_hls",
                   vod_play_url=f"第1集$https://media.example.test/{pid}/1.m3u8")
        if state["extra"]:
            row["vod_play_url"] += f"#第2集$https://media.example.test/{pid}/2.m3u8"
        return dict(code=1, list=[row])
    monkeypatch.setattr(provider_client, "request_json", fake)
    return headers, state


async def discover(client, headers, expected_status="preview", **criteria):
    result = await client.post(BASE + "/imports/discover", headers=headers,
        json=dict(name="测试动画", category="japanese_animation", **criteria))
    assert result.status_code == 200, result.text
    job = (await client.get(f"{BASE}/imports/{result.json()['id']}", headers=headers)).json()
    assert job["status"] == expected_status, job
    return job


async def select_discovered(client, headers, job, keys=None):
    response = await client.post(f"{BASE}/imports/{job['id']}/select", headers=headers,
        json={"keys": keys if keys is not None else [i["key"] for i in job["items"]]})
    assert response.status_code == 200, response.text
    return (await client.get(f"{BASE}/imports/{job['id']}", headers=headers)).json()


async def test_aggregate_two_sites_create_once_and_update_weekly(api_client, aggregate_setup, db_session):
    headers, state = aggregate_setup
    job = await discover(api_client, headers, updated_from="2026-09-01", updated_to="2026-09-17")
    assert job["query"]["complete"] and len(job["items"]) == 1
    item = job["items"][0]
    assert item["line_count"] == 2 and item["episode_count"] == item["new_episodes"] == 1
    assert len(item["sources"]) == 2 and "fields" not in item["sources"][0]
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0
    result = await select_discovered(api_client, headers, job)
    assert result["status"] == "completed", result
    cid = result["items"][0]["content_id"]
    graph = (await api_client.get(f"{BASE}/catalog/contents/{cid}/graph", headers=headers)).json()
    assert len(graph["episodes"]) == 1 and len(graph["lines"]) == len(graph["playbacks"]) == 2
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1
    repeated = await discover(api_client, headers)
    assert repeated["items"][0]["content_id"] == cid and repeated["items"][0]["new_episodes"] == 0
    unchanged = await select_discovered(api_client, headers, repeated)
    assert unchanged["items"][0]["status"] == "unchanged", unchanged
    state["extra"] = True
    weekly = await discover(api_client, headers)
    assert weekly["items"][0]["new_episodes"] == 1
    updated = await select_discovered(api_client, headers, weekly)
    assert updated["items"][0]["status"] == "updated", updated
    graph = (await api_client.get(f"{BASE}/catalog/contents/{cid}/graph", headers=headers)).json()
    assert len(graph["episodes"]) == 2 and len(graph["playbacks"]) == 4


async def test_aggregate_seasons_selection_and_incomplete_scope(api_client, aggregate_setup, db_session):
    headers, state = aggregate_setup
    state["second_title"] = "测试动画 第三季"
    job = await discover(api_client, headers)
    assert len(job["items"]) == 2
    result = await select_discovered(api_client, headers, job, [job["items"][0]["key"]])
    assert result["status"] == "completed" and len(result["items"]) == 1
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1
    state["broken"] = True
    partial = await discover(api_client, headers, expected_status="failed")
    assert not partial["query"]["complete"] and partial["query"]["failures"][0]["name"] == "Second site"
    state["broken"] = False
    recovered = await run(api_client, headers, partial, "retry")
    assert recovered["status"] == "preview" and recovered["query"]["complete"]
    assert not recovered["query"]["failures"]
    state["broken"] = True
    empty = await discover(api_client, headers, expected_status="failed", updated_from="2026-09-18")
    assert not empty["items"]
    assert (await api_client.post(f"{BASE}/imports/{empty['id']}/select", headers=headers, json={"keys":[]})).status_code == 422


async def test_aggregate_rejects_changed_catalog_and_configuration(api_client, aggregate_setup, db_session):
    headers, _ = aggregate_setup
    first = await discover(api_client, headers)
    await select_discovered(api_client, headers, first)
    job = await discover(api_client, headers)
    item = await db_session.get(CatalogContent, job["items"][0]["content_id"])
    item.version += 1
    item.title = "人工修改标题"
    await db_session.commit()
    result = await select_discovered(api_client, headers, job)
    assert result["status"] == "failed" and result["items"][0]["reason"] == "catalog_version_conflict"
    job = await discover(api_client, headers)
    provider = await db_session.get(CatalogProvider, 2)
    provider.version += 1
    await db_session.commit()
    response = await api_client.post(f"{BASE}/imports/{job['id']}/select", headers=headers, json={"keys":[job['items'][0]['key']]})
    assert response.status_code == 409


async def test_aggregate_ambiguous_existing_records_and_disabled_are_not_selectable(api_client, aggregate_setup, db_session):
    headers, _ = aggregate_setup
    for _ in range(2):
        db_session.add(CatalogContent(title="测试动画 第二季", category="japanese_animation", year=2024, region="日本", content_type="tv"))
    await db_session.commit()
    job = await discover(api_client, headers)
    assert all(i["blocked"] and i["match"] == "ambiguous" for i in job["items"])
    response = await api_client.post(f"{BASE}/imports/{job['id']}/select", headers=headers,
                                     json={"keys":[job["items"][0]["key"]]})
    assert response.status_code == 400


async def test_aggregate_cancelled_worker_cannot_write_and_retry_search(api_client, aggregate_setup, db_session):
    from app.modules.catalog import discovery_service
    from app.modules.catalog.import_schemas import DiscoveryInput
    headers, _ = aggregate_setup
    job, token = await discovery_service.discover(db_session, DiscoveryInput(name="测试", category="japanese_animation"), None)
    jid = job.id
    await import_service.cancel_import(db_session, jid)
    await import_service.run_import(jid, token)
    job = (await api_client.get(f"{BASE}/imports/{jid}", headers=headers)).json()
    assert job["status"] == "cancelled" and not job["items"]
    retried = await run(api_client, headers, job, "retry")
    assert retried["status"] == "preview" and retried["items"][0]["line_count"] == 2
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0


async def test_aggregate_finds_existing_manual_catalog_without_overwriting_it(api_client, aggregate_setup, db_session):
    headers, _ = aggregate_setup
    content = CatalogContent(title="测试动画 第二季", category="japanese_animation", year=2024, region="日本",
                             content_type="tv", description="管理员简介", status="published")
    db_session.add(content)
    await db_session.commit()
    job = await discover(api_client, headers)
    assert job["items"][0]["content_id"] == content.id and not job["items"][0]["blocked"]
    result = await select_discovered(api_client, headers, job)
    assert result["status"] == "completed", result
    await db_session.refresh(content)
    assert content.description == "管理员简介" and content.status == "published"


async def test_discovery_range_validation_and_expired_preview(api_client, aggregate_setup, db_session):
    headers, _ = aggregate_setup
    response = await api_client.post(BASE + "/imports/discover", headers=headers,
        json=dict(category="japanese_animation", updated_from="2026-09-18", updated_to="2026-09-17"))
    assert response.status_code == 422
    job = await discover(api_client, headers)
    record = await db_session.get(CatalogImportJob, job["id"])
    record.query = {**record.query, "ready_at":"2020-01-01T00:00:00+00:00"}
    await db_session.commit()
    response = await api_client.post(f"{BASE}/imports/{job['id']}/select", headers=headers, json={"keys":[job['items'][0]['key']]})
    assert response.status_code == 409


async def test_new_site_joins_existing_source_after_manual_title_edit(api_client, aggregate_setup, db_session):
    headers, _ = aggregate_setup
    second = await db_session.get(CatalogProvider, 2)
    second.enabled = False
    await db_session.commit()
    initial = await select_discovered(api_client, headers, await discover(api_client, headers))
    content = await db_session.get(CatalogContent, initial["items"][0]["content_id"])
    content.title = "管理员显示名称"
    content.version += 1
    second.enabled = True
    await db_session.commit()
    previewed = await discover(api_client, headers)
    assert len(previewed["items"]) == 1 and previewed["items"][0]["line_count"] == 2
    result = await select_discovered(api_client, headers, previewed)
    assert result["status"] == "completed", result
    await db_session.refresh(content)
    assert content.title == "管理员显示名称"
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1


async def test_discovery_does_not_call_unknown_dates_complete(api_client, aggregate_setup, monkeypatch):
    headers, _ = aggregate_setup
    original = provider_client.request_json

    async def missing_date(pid, endpoint, params):
        data = await original(pid, endpoint, params)
        if params["ac"] == "list":
            data["list"][0].pop("vod_time")
        return data
    monkeypatch.setattr(provider_client, "request_json", missing_date)
    result = await discover(api_client, headers, expected_status="failed", updated_from="2026-09-01")
    assert not result["query"]["complete"] and len(result["query"]["failures"]) == 2
    assert result["query"]["failures"][0]["reason"] == "catalog_discovery_date"


async def test_aggregate_work_rolls_back_all_lines_if_one_source_fails(api_client, aggregate_setup, monkeypatch, db_session):
    from app.modules.catalog import discovery_service
    headers, _ = aggregate_setup
    job = await discover(api_client, headers)
    original = discovery_service.sync_work

    async def fail_second(db, provider, *args, **kwargs):
        if provider.id == 2:
            raise BadRequestError("Invalid source", reason="catalog_import_data")
        return await original(db, provider, *args, **kwargs)
    monkeypatch.setattr(discovery_service, "sync_work", fail_second)
    result = await select_discovered(api_client, headers, job)
    assert result["status"] == "failed"
    for model in (CatalogContent, CatalogSource, CatalogPlayback):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0
    monkeypatch.setattr(discovery_service, "sync_work", original)
    retried = await run(api_client, headers, result, "retry")
    assert retried["status"] == "completed"
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1


async def test_delete_resource_cleans_children_and_invalidates_old_imports(api_client, aggregate_setup, db_session):
    from app.modules.catalog.models import CatalogEpisode, CatalogLine
    from app.modules.catalog import discovery_service
    headers, _ = aggregate_setup
    completed = await select_discovered(api_client, headers, await discover(api_client, headers))
    cid = completed['items'][0]['content_id']
    pending = await discover(api_client, headers)
    queued, token = await discovery_service.select_import(db_session, pending['id'], [pending['items'][0]['key']], None)
    queued_id = queued.id
    content = (await api_client.get(f'{BASE}/catalog/contents/{cid}', headers=headers)).json()
    stale = await api_client.delete(f'{BASE}/catalog/contents/{cid}', headers=headers, params={'version':content['version'] + 1})
    assert stale.status_code == 409
    assert await db_session.scalar(select(func.count()).select_from(CatalogSource)) == 2
    result = await api_client.delete(f'{BASE}/catalog/contents/{cid}', headers=headers, params={'version':content['version']})
    assert result.status_code == 204, result.text
    await import_service.run_import(queued_id, token)
    for model in (CatalogContent, CatalogEpisode, CatalogLine, CatalogPlayback, CatalogSource, CatalogAudit):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0
    old = (await api_client.get(f'{BASE}/imports/{queued_id}', headers=headers)).json()
    assert old['status'] == 'cancelled' and old['items'][0]['content_id'] is None
    assert old['items'][0]['status'] == 'skipped'
    assert (await api_client.get(f'{BASE}/catalog/contents/{cid}', headers=headers)).status_code == 404
    repeated = await select_discovered(api_client, headers, await discover(api_client, headers))
    assert repeated['status'] == 'completed' and repeated['items'][0]['content_id'] != cid


async def test_delete_resource_requires_admin_and_current_version(api_client, aggregate_setup, factories, auth_headers):
    headers, _ = aggregate_setup
    created = await select_discovered(api_client, headers, await discover(api_client, headers))
    cid = created['items'][0]['content_id']
    user = await factories.create_user()
    await factories.commit()
    path = f'{BASE}/catalog/contents/{cid}'
    assert (await api_client.delete(path, params={'version':1})).status_code == 401
    assert (await api_client.delete(path, headers=auth_headers(user), params={'version':1})).status_code == 403
    assert (await api_client.delete(path, headers=headers)).status_code == 422
    assert (await api_client.get(path, headers=headers)).status_code == 200


async def test_fractional_recaps_persist_sort_and_expand_without_duplicates(api_client, import_setup):
    headers, state = import_setup
    state['play'] = '第12集$https://example.test/12.m3u8#总集篇$https://example.test/recap.m3u8#第13集$https://example.test/13.m3u8'
    first = await run(api_client, headers, await preview(api_client, headers))
    cid = first['items'][0]['content_id']
    path = f'{BASE}/catalog/contents/{cid}'
    graph = (await api_client.get(path + '/graph', headers=headers)).json()
    assert [e['number'] for e in graph['episodes']] == [12, 12.5, 13]
    recap_id = graph['episodes'][1]['id']
    state['play'] = state['play'].replace('#第13集', '#总集篇二$https://example.test/recap2.m3u8#第13集')
    updated = await run(api_client, headers, await preview(api_client, headers))
    assert updated['status'] == 'completed', updated
    graph = (await api_client.get(path + '/graph', headers=headers)).json()
    assert [e['number'] for e in graph['episodes']] == [12, 12.51, 12.52, 13]
    assert graph['episodes'][1]['id'] == recap_id and len(graph['playbacks']) == 4
    repeated = await run(api_client, headers, await preview(api_client, headers))
    assert repeated['items'][0]['status'] == 'unchanged'
    episode = graph['episodes'][1]
    payload = {key:value for key,value in episode.items() if key not in ('id','content_id','available_line_count')}
    payload.update(number=12.53, sort_order=12.53, version=graph['content']['version'])
    edited = await api_client.put(f'{path}/episodes/{recap_id}', headers=headers, json=payload)
    assert edited.status_code == 200, edited.text
    assert any(e['number'] == 12.53 for e in edited.json()['episodes'])


@pytest.fixture
async def import_setup(db_session, factories, auth_headers, monkeypatch):
    db_session.add(CatalogCategory(code="japanese_animation", name="日本动画"))
    await db_session.flush()
    db_session.add(CatalogProvider(id=1, code="jinying", name="金鹰", endpoint=provider_client.ENDPOINT,
                                   enabled=True, category="japanese_animation", upstream_category=25, play_from="jinyingm3u8"))
    admin = await factories.create_user(site_role=SiteRole.ADMIN)
    await factories.commit()
    state = {"calls": [], "fail": set(), "category": 25, "play": "第1集$https://media.example.test/1.m3u8#第3集$https://media.example.test/3.m3u8#特别篇$https://media.example.test/sp.m3u8", "title": "测试动画 第二季"}

    async def fake(provider_id, endpoint, params):
        state["calls"].append(dict(params))
        if params["ac"] == "list":
            page = params.get("pg", 1)
            return dict(code=1, page=str(page), pagecount=2, total=2, **{
                "class": [{"type_id": state["category"], "type_name": "日本动漫"}],
                "list": [dict(vod_id=page, vod_name=state["title"], type_id=state["category"])]})
        if params["ids"] in state["fail"]:
            raise BadRequestError("Timed out", reason="catalog_provider_unavailable")
        return dict(code=1, list=[dict(vod_id=params["ids"], vod_name=state["title"], type_id=state["category"],
            vod_year="2024", vod_area="日本", vod_sub="别名", vod_content="<p>简介</p>",
            vod_play_from=state.get("line", "jinyingm3u8"), vod_play_url=state["play"])])
    monkeypatch.setattr(provider_client, "request_json", fake)
    return auth_headers(admin), state


async def preview(client, headers, **changes):
    result = await client.post(BASE + "/providers/1/preview", headers=headers,
                              json={"start_page": 1, "page_count": 1, "max_items": 20, **changes})
    assert result.status_code == 200, result.text
    return result.json()


async def run(client, headers, job, action="start"):
    result = await client.post(f"{BASE}/imports/{job['id']}/{action}", headers=headers)
    assert result.status_code == 200, result.text
    return (await client.get(f"{BASE}/imports/{job['id']}", headers=headers)).json()


async def test_preview_confirmation_import_and_idempotent_sync(api_client, import_setup, db_session):
    headers, state = import_setup
    assert (await api_client.post(BASE + "/providers/1/check", headers=headers)).status_code == 200
    job = await preview(api_client, headers)
    assert job["status"] == "preview" and len(job["items"]) == 1
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0
    result = await run(api_client, headers, job)
    assert result["status"] == "completed", result
    assert result["items"][0]["status"] == "created"
    content_id = result["items"][0]["content_id"]
    graph = (await api_client.get(f"{BASE}/catalog/contents/{content_id}/graph", headers=headers)).json()
    assert graph["content"]["status"] == "draft" and graph["content"]["title"].endswith("第二季")
    assert sorted((x["kind"], x["number"]) for x in graph["episodes"]) == [("episode", 1), ("episode", 3), ("special", 1)]
    assert len(graph["lines"]) == 1 and len(graph["playbacks"]) == 3
    assert graph["lines"][0]["source_key"] == "jinying"
    repeated = await run(api_client, headers, await preview(api_client, headers))
    assert repeated["items"][0]["status"] == "unchanged", repeated
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1
    assert await db_session.scalar(select(func.count()).select_from(CatalogSource)) == 1
    assert await db_session.scalar(select(func.count()).select_from(CatalogAudit)) == 1
    assert (await api_client.get(f"{BASE}/catalog/contents/{content_id}", headers=headers)).json()["version"] == graph["content"]["version"]
    state["play"] += "#第4集$https://media.example.test/4.m3u8"
    updated = await run(api_client, headers, await preview(api_client, headers))
    assert updated["items"][0]["status"] == "updated"
    assert await db_session.scalar(select(func.count()).select_from(CatalogPlayback)) == 4


async def test_sync_preserves_manual_fields_disabled_and_missing_entries(api_client, import_setup):
    headers, state = import_setup
    result = await run(api_client, headers, await preview(api_client, headers))
    cid = result["items"][0]["content_id"]
    path = f"{BASE}/catalog/contents/{cid}"
    graph = (await api_client.get(path + "/graph", headers=headers)).json()
    content = graph["content"]
    payload = {k:v for k,v in content.items() if k not in ("id", "created_at", "updated_at")}
    assert (await api_client.put(path, headers=headers, json={**payload, "title": "管理员标题", "status": "published"})).status_code == 200
    item = graph["playbacks"][0]
    item_payload = {k:v for k,v in item.items() if k not in ("id", "content_id")}
    item_payload.update(version=content["version"]+1, disabled=True, disabled_reason="手动禁用", url="https://manual.example.test/video.m3u8")
    assert (await api_client.put(f"{path}/playbacks/{item['id']}", headers=headers, json=item_payload)).status_code == 200
    state["title"] = "上游新标题"
    state["play"] = "第1集$https://media.example.test/new.m3u8"
    await run(api_client, headers, await preview(api_client, headers))
    graph = (await api_client.get(path + "/graph", headers=headers)).json()
    assert graph["content"]["title"] == "管理员标题" and graph["content"]["status"] == "published"
    assert len(graph["playbacks"]) == 3  # Missing upstream episodes are not silently removed.
    assert graph["playbacks"][0]["disabled"] and graph["playbacks"][0]["url"] == item_payload["url"]
    payload.update(version=graph["content"]["version"], disabled=True, disabled_reason="作品禁用")
    assert (await api_client.put(path, headers=headers, json=payload)).status_code == 200
    skipped = await run(api_client, headers, await preview(api_client, headers))
    assert skipped["items"][0]["reason"] == "work_disabled"


async def test_partial_failure_retry_and_category_filter(api_client, import_setup):
    headers, state = import_setup
    state["fail"] = {2}
    result = await run(api_client, headers, await preview(api_client, headers, page_count=2))
    assert result["status"] == "partial"
    assert [x["status"] for x in result["items"]] == ["created", "failed"]
    state["fail"] = set()
    state["calls"].clear()
    retried = await run(api_client, headers, result, "retry")
    assert retried["status"] == "completed"
    assert state["calls"] == [{"ac": "detail", "ids": 2}]
    job = await preview(api_client, headers)
    state["category"] = 24
    skipped = await run(api_client, headers, job)
    assert skipped["items"][0]["reason"] == "category_filtered"
    assert (await api_client.post(BASE + "/providers/1/preview", headers=headers, json={})).status_code == 400


async def test_unknown_labels_use_link_order_and_invalid_urls_are_reported(api_client, import_setup):
    headers, state = import_setup
    state["play"] = "第1-2集$https://example.test/a.m3u8#花絮上$https://example.test/b.m3u8#第3集$javascript:alert(1)"
    result = await run(api_client, headers, await preview(api_client, headers))
    item = result["items"][0]
    assert item["entries"] == 2 and len(item["warnings"]) == 1
    graph = (await api_client.get(f"{BASE}/catalog/contents/{item['content_id']}/graph", headers=headers)).json()
    assert [e["number"] for e in graph["episodes"]] == [1, 2]
    assert len(graph["playbacks"]) == 2


async def test_config_conflict_limits_and_disable(api_client, import_setup):
    headers, _ = import_setup
    job = await preview(api_client, headers)
    provider = (await api_client.get(BASE + "/providers", headers=headers)).json()[0]
    payload = {k:v for k,v in provider.items() if k not in ("id", "code")}
    for changes in ({"endpoint":"http://127.0.0.1"}, {"upstream_category":0}, {"name":" "}):
        assert (await api_client.put(BASE + "/providers/1", headers=headers, json={**payload, **changes})).status_code == 422
    assert (await api_client.put(BASE + "/providers/1", headers=headers, json={**payload, "name":"New name"})).status_code == 200
    assert (await api_client.put(BASE + "/providers/1", headers=headers, json=payload)).status_code == 409
    assert (await api_client.post(f"{BASE}/imports/{job['id']}/start", headers=headers)).status_code == 409
    for changes in ({"page_count":4}, {"max_items":61}, {"start_page":0}):
        assert (await api_client.post(BASE + "/providers/1/preview", headers=headers, json=changes)).status_code == 422
    assert (await api_client.put(BASE + "/providers/1", headers=headers, json={**payload, "version":2,"enabled":False})).status_code == 200
    assert (await api_client.post(BASE + "/providers/1/check", headers=headers)).status_code == 400


async def test_all_import_endpoints_require_admin(api_client, import_setup, factories, auth_headers):
    _, _state = import_setup
    user = await factories.create_user()
    await factories.commit()
    for headers, status in [({},401),(auth_headers(user),403)]:
        for method,path,body in [("GET","/providers",None),("POST","/providers",{}),("PUT","/providers/1",{}),
             ("POST","/providers/1/check",None),("POST","/providers/1/preview",{}),
             ("GET","/imports",None),("GET","/imports/1",None),
             ("POST","/imports/discover",{}),("POST","/imports/1/select",{}),
             ("POST","/imports/1/start",None),("POST","/imports/1/retry",None),("POST","/imports/1/cancel",None)]:
            response = await api_client.request(method, BASE+path, headers=headers, **({"json":body} if body is not None else {}))
            assert response.status_code == status


async def test_job_claim_cancel_recovery_and_stale_worker(api_client, import_setup, db_session):
    headers, _ = import_setup
    one = await preview(api_client, headers)
    two = await preview(api_client, headers, start_page=2)
    first, token = await import_service.start_import(db_session, one["id"], None)
    with pytest.raises(ConflictError) as exc:
        await import_service.start_import(db_session, two["id"], None)
    assert getattr(exc.value, "reason", None) == "catalog_import_busy"
    await import_service.cancel_import(db_session, one["id"])
    await import_service.run_import(one["id"], token)
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0
    second, token = await import_service.start_import(db_session, two["id"], None)
    second.lease_until = time.time()-1
    await db_session.commit()
    await import_service.recover_expired(db_session)
    await db_session.refresh(second)
    assert second.status == "interrupted"
    await import_service.run_import(second.id, token)
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 0
    result = await run(api_client, headers, {"id":second.id}, "retry")
    assert result["status"] == "completed"


async def test_provider_is_an_instance_not_a_fixed_site(api_client, import_setup):
    headers, state = import_setup
    first = await run(api_client, headers, await preview(api_client, headers))
    payload = dict(code="another_site", name="Another site", endpoint="https://catalog.example.test/api/videos/",
                   enabled=True, category="japanese_animation", upstream_category=97, play_from="alternate_hls")
    response = await api_client.post(BASE + "/providers", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    site = response.json()
    assert site["id"] != 1 and site["play_from"] == "alternate_hls"
    assert (await api_client.post(BASE + "/providers", headers=headers, json=payload)).status_code == 409
    state["category"] = 97
    state["line"] = "alternate_hls"
    state["calls"].clear()
    assert (await api_client.post(f"{BASE}/providers/{site['id']}/check", headers=headers)).json()["upstream_category"] == 97
    preview_response = await api_client.post(f"{BASE}/providers/{site['id']}/preview", headers=headers, json={})
    assert preview_response.status_code == 200
    assert state["calls"][-1]["t"] == 97
    imported = await run(api_client, headers, preview_response.json())
    assert imported["status"] == "completed"
    cid = imported["items"][0]["content_id"]
    assert cid != first["items"][0]["content_id"]  # Same upstream ID belongs to different sites.
    graph = (await api_client.get(f"{BASE}/catalog/contents/{cid}/graph", headers=headers)).json()
    assert graph["lines"][0]["source_key"] == "another_site"
    assert graph["lines"][0]["line_key"] == "alternate_hls"
    assert len(graph["playbacks"]) == 3


async def test_provider_abbreviation_updates_existing_line_display(api_client, import_setup):
    headers, _ = import_setup
    imported = await run(api_client, headers, await preview(api_client, headers))
    cid = imported["items"][0]["content_id"]
    provider = (await api_client.get(BASE + "/providers", headers=headers)).json()[0]
    assert provider["abbreviation"] == ""

    async def save(abbreviation):
        nonlocal provider
        payload = {key: value for key, value in provider.items() if key not in ("id", "code")}
        payload["abbreviation"] = abbreviation
        response = await api_client.put(f"{BASE}/providers/{provider['id']}", headers=headers, json=payload)
        assert response.status_code == 200, response.text
        provider = response.json()
        return (await api_client.get(f"{BASE}/catalog/contents/{cid}/graph", headers=headers)).json()

    graph = await save("  JY  ")
    assert provider["abbreviation"] == "JY"
    assert all(line["display_name"] == "JY" for line in graph["lines"])
    assert all(line["name"] == provider["name"] for line in graph["lines"])
    graph = await save("   ")
    assert provider["abbreviation"] == ""
    assert all(line["display_name"] == provider["name"] for line in graph["lines"])


@pytest.mark.parametrize("cancelled", [False, True])
async def test_import_partial_search_results_preserves_search_and_accepts_later_sources(
        api_client, aggregate_setup, db_session, cancelled):
    from app.modules.catalog import discovery_service
    from app.modules.catalog.import_schemas import DiscoveryInput
    headers, _ = aggregate_setup
    job, token = await discovery_service.discover(db_session,
        DiscoveryInput(name="测试", category="japanese_animation"), None)
    assert await import_service.claim(db_session, job.id, token)
    await db_session.refresh(job)
    provider = await db_session.get(CatalogProvider, 1)
    detail = await provider_client.request_json(1, provider.endpoint, {"ac": "detail", "ids": 1})
    await discovery_service.add_candidate(db_session, job, provider, detail["list"][0], "2026-09-17")
    await db_session.commit()
    if cancelled:
        await import_service.cancel_import(db_session, job.id)
    response = await api_client.post(f"{BASE}/imports/{job.id}/select", headers=headers,
        json={"keys": [job.items[0]["key"]]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == ("cancelled" if cancelled else "running")
    assert result["query"]["phase"] == "search"
    assert result["items"][0]["status"] == "created"
    cid = result["items"][0]["content_id"]
    # Repeating the same selection updates the existing work, never duplicates it.
    response = await api_client.post(f"{BASE}/imports/{job.id}/select", headers=headers,
        json={"keys": [result["items"][0]["key"]]})
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["status"] == "unchanged"
    await import_service.run_import(job.id, token)
    current = (await api_client.get(f"{BASE}/imports/{job.id}", headers=headers)).json()
    if cancelled:
        assert current["status"] == "cancelled"
        assert current["items"][0]["line_count"] == 1
    else:
        assert current["status"] == "preview"
        assert current["items"][0]["line_count"] == 2
        assert current["items"][0]["status"] == "pending"
        imported = await select_discovered(api_client, headers, current)
        assert imported["status"] == "completed", imported
    graph = (await api_client.get(f"{BASE}/catalog/contents/{cid}/graph", headers=headers)).json()
    assert len(graph["lines"]) == (1 if cancelled else 2)
    assert await db_session.scalar(select(func.count()).select_from(CatalogContent)) == 1
