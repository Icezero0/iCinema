import pytest

from app.modules.site.constants import SiteRole
from app.modules.catalog.models import CatalogCategory

BASE = "/api/v1/admin/catalog/contents"


@pytest.fixture(autouse=True)
async def catalog_categories(db_session):
    db_session.add(CatalogCategory(code="japanese_animation", name="日本动画"))
    await db_session.commit()


async def admin_headers(factories, auth_headers):
    admin = await factories.create_user(site_role=SiteRole.ADMIN)
    await factories.commit()
    return auth_headers(admin)


def edit_payload(item, **changes):
    fields = ("title", "aliases", "category", "region", "content_type", "year", "description",
              "version", "status", "disabled", "disabled_reason")
    return {**{key: item[key] for key in fields}, **changes}


async def test_catalog_lifecycle_and_audit(api_client, factories, auth_headers):
    headers = await admin_headers(factories, auth_headers)
    created = await api_client.post(BASE, headers=headers, json={"title": "  测试动画  ", "year": 2024})
    assert created.status_code == 200
    item = created.json()
    assert item["title"] == "测试动画"
    assert item["status"] == "draft" and not item["disabled"]
    assert item["category"] == "japanese_animation" and item["region"] == ""
    path = f"{BASE}/{item['id']}"
    published = await api_client.put(path, headers=headers, json=edit_payload(item, status="published", aliases="别名"))
    assert published.status_code == 200
    disabled = await api_client.put(path, headers=headers, json=edit_payload(published.json(), disabled=True, disabled_reason="测试禁用"))
    assert disabled.status_code == 200 and disabled.json()["status"] == "published"
    filtered = (await api_client.get(BASE, headers=headers, params={"disabled": "true", "q": "别名"})).json()
    assert filtered["total"] == 1
    restored = await api_client.put(path, headers=headers, json=edit_payload(disabled.json(), disabled=False))
    assert restored.status_code == 200 and restored.json()["disabled_reason"] == ""
    withdrawn = await api_client.put(path, headers=headers, json=edit_payload(restored.json(), status="withdrawn"))
    assert withdrawn.status_code == 200
    persisted = (await api_client.get(path, headers=headers)).json()
    assert persisted["status"] == "withdrawn" and persisted["version"] == 5
    records = (await api_client.get(path + "/audits", headers=headers, params={"page_size": 2})).json()
    assert records["total"] == 5 and records["total_pages"] == 3
    assert records["items"][0]["changes"]["status"] == {"before": "published", "after": "withdrawn"}
    # Saving an unchanged form must not fabricate another audit entry.
    assert (await api_client.put(path, headers=headers, json=edit_payload(persisted))).status_code == 200
    assert (await api_client.get(path + "/audits", headers=headers)).json()["total"] == 5


async def test_catalog_endpoints_require_admin(api_client, factories, auth_headers):
    admin = await admin_headers(factories, auth_headers)
    item = (await api_client.post(BASE, headers=admin, json={"title": "管理资源"})).json()
    user = await factories.create_user()
    await factories.commit()
    for headers, expected in [({}, 401), (auth_headers(user), 403)]:
        for method, path, payload in [
            ("GET", BASE, None), ("GET", "/api/v1/admin/catalog/categories", None), ("POST", BASE, {"title": "越权"}),
            ("GET", f"{BASE}/{item['id']}", None),
            ("PUT", f"{BASE}/{item['id']}", edit_payload(item, title="越权")),
            ("GET", f"{BASE}/{item['id']}/audits", None),
        ]:
            response = await api_client.request(method, path, headers=headers, **({"json": payload} if payload else {}))
            assert response.status_code == expected


@pytest.mark.parametrize("invalid", [
    {"title": "   "}, {"category": "bad code"}, {"region": "x" * 17},
    {"content_type": "drama"}, {"year": 1800}, {"year": 2024.5}, {"title": "a" * 256},
])
async def test_catalog_rejects_invalid_scope_and_values(api_client, factories, auth_headers, invalid):
    headers = await admin_headers(factories, auth_headers)
    response = await api_client.post(BASE, headers=headers, json={"title": "动画", **invalid})
    assert response.status_code == 422
    assert (await api_client.get(BASE, headers=headers)).json()["total"] == 0


async def test_catalog_conflict_validation_and_missing(api_client, factories, auth_headers):
    headers = await admin_headers(factories, auth_headers)
    item = (await api_client.post(BASE, headers=headers, json={"title": "原始标题"})).json()
    path = f"{BASE}/{item['id']}"
    assert (await api_client.put(path, headers=headers, json=edit_payload(item, disabled=True))).status_code == 422
    assert (await api_client.put(path, headers=headers, json=edit_payload(item, category="unknown"))).status_code == 400
    assert (await api_client.put(path, headers=headers, json=edit_payload(item, title="先保存"))).status_code == 200
    stale = await api_client.put(path, headers=headers, json=edit_payload(item, title="旧表单覆盖"))
    assert stale.status_code == 409
    assert (await api_client.get(path, headers=headers)).json()["title"] == "先保存"
    assert (await api_client.get(path + "/audits", headers=headers)).json()["total"] == 2
    for suffix in ("/999999", "/999999/audits"):
        assert (await api_client.get(BASE + suffix, headers=headers)).status_code == 404


async def test_catalog_literal_search_and_pagination(api_client, factories, auth_headers):
    headers = await admin_headers(factories, auth_headers)
    for title in ("100%动画", "普通动画", "另一个动画"):
        assert (await api_client.post(BASE, headers=headers, json={"title": title})).status_code == 200
    assert (await api_client.get(BASE, headers=headers, params={"q": "%"})).json()["total"] == 1
    page1 = (await api_client.get(BASE, headers=headers, params={"page_size": 2})).json()
    page2 = (await api_client.get(BASE, headers=headers, params={"page_size": 2, "page": 2})).json()
    assert page1["total"] == 3 and page1["total_pages"] == 2
    assert not ({x["id"] for x in page1["items"]} & {x["id"] for x in page2["items"]})
    assert (await api_client.get(BASE, headers=headers, params={"page": 0})).status_code == 422


async def test_categories_are_data_driven_and_region_is_independent(api_client, factories, auth_headers, db_session):
    headers = await admin_headers(factories, auth_headers)
    path = "/api/v1/admin/catalog/categories"
    assert (await api_client.get(path, headers=headers)).json() == [{"code": "japanese_animation", "name": "日本动画"}]
    db_session.add(CatalogCategory(code="documentary", name="纪录片", sort_order=1))
    await db_session.commit()
    assert len((await api_client.get(path, headers=headers)).json()) == 2
    added = await api_client.post(BASE, headers=headers, json={"title": "测试作品", "category": "documentary", "region": "US"})
    assert added.status_code == 200
    assert added.json()["region"] == "US"
    assert (await api_client.get(BASE, headers=headers, params={"category": "documentary"})).json()["total"] == 1
    assert (await api_client.get(BASE, headers=headers, params={"category": "japanese_animation"})).json()["total"] == 0
    assert (await api_client.post(BASE, headers=headers, json={"title": "未知分类", "category": "unknown"})).status_code == 400
    updated = await api_client.put(f"{BASE}/{added.json()['id']}", headers=headers,
                                  json=edit_payload(added.json(), category="japanese_animation", region=""))
    assert updated.status_code == 200 and updated.json()["region"] == ""
