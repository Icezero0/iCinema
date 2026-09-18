from unittest.mock import AsyncMock

import pytest
from app.core.exceptions import BadRequestError
from app.modules.catalog.schemas import ContentInput
from app.modules.catalog.service import CatalogService


def test_content_schema_does_not_restrict_categories_or_region_to_japan():
    content = ContentInput(title="Sample", category="documentary", region="US")
    assert content.category == "documentary" and content.region == "US"
    assert ContentInput(title="Unknown origin").region == ""


async def test_category_validation_uses_repository():
    service = CatalogService()
    service.repo.category_exists = AsyncMock(return_value=True)
    await service.require_category(None, "documentary")
    service.repo.category_exists.assert_awaited_once_with(None, "documentary")
    service.repo.category_exists.return_value = False
    with pytest.raises(BadRequestError) as error:
        await service.require_category(None, "missing")
    assert error.value.reason == "catalog_category_not_found"
