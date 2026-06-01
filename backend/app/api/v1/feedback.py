from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.feedback.constants import FeedbackPage, FeedbackStatus, FeedbackType
from app.modules.feedback.models import Feedback
from app.modules.feedback.schemas import (
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackUpdateRequest,
)
from app.modules.feedback.service import FeedbackService
from app.modules.media.storage import MediaStorageService
from app.modules.users.models import User

router = APIRouter(prefix="/feedback", tags=["feedback"])

feedback_service = FeedbackService()
media_storage = MediaStorageService()


def _build_feedback_response(feedback: Feedback) -> FeedbackResponse:
    screenshot_asset_ids = [item.asset_id for item in feedback.screenshots]

    response = FeedbackResponse.model_validate(feedback)
    response.screenshot_asset_ids = screenshot_asset_ids
    response.screenshot_urls = [
        f"/api/v1/feedback/assets/{asset_id}" for asset_id in screenshot_asset_ids
    ]
    return response


@router.post("", response_model=FeedbackResponse)
async def create_feedback(
    feedback_type: FeedbackType = Form(...),
    page: FeedbackPage = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    screenshots: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    feedback = await feedback_service.create_feedback(
        db,
        user=current_user,
        feedback_type=feedback_type,
        page=page,
        title=title,
        description=description,
        screenshots=screenshots,
    )
    return _build_feedback_response(feedback)


@router.get("", response_model=FeedbackListResponse)
async def get_my_feedbacks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: FeedbackStatus | None = Query(default=None),
    feedback_type: FeedbackType | None = Query(default=None),
    feedback_page: FeedbackPage | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackListResponse:
    data = await feedback_service.get_my_feedbacks(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        feedback_type=feedback_type,
        feedback_page=feedback_page,
    )
    return FeedbackListResponse(
        items=[_build_feedback_response(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/admin", response_model=FeedbackListResponse)
async def get_all_feedbacks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: FeedbackStatus | None = Query(default=None),
    feedback_type: FeedbackType | None = Query(default=None),
    feedback_page: FeedbackPage | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackListResponse:
    data = await feedback_service.get_all_feedbacks(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        feedback_type=feedback_type,
        feedback_page=feedback_page,
    )
    return FeedbackListResponse(
        items=[_build_feedback_response(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    feedback = await feedback_service.get_feedback(
        db,
        feedback_id=feedback_id,
        user=current_user,
    )
    return _build_feedback_response(feedback)


@router.patch("/admin/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    feedback = await feedback_service.update_feedback(
        db,
        feedback_id=feedback_id,
        payload=payload,
        user=current_user,
    )
    return _build_feedback_response(feedback)


@router.get("/assets/{asset_id}")
async def get_feedback_screenshot(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    asset = await feedback_service.get_feedback_screenshot_asset(
        db,
        asset_id=asset_id,
        user=current_user,
    )
    path = media_storage.get_file_path(
        asset_type=asset.asset_type,
        storage_key=asset.storage_key,
    )
    return FileResponse(path, media_type=asset.mime_type)
