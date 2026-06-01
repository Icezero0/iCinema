from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.feedback.models import Feedback, FeedbackScreenshot


class FeedbackRepository:
    def _with_relations(self):
        return (
            selectinload(Feedback.creator),
            selectinload(Feedback.handled_by),
            selectinload(Feedback.screenshots).selectinload(FeedbackScreenshot.asset),
        )

    async def create_feedback(
        self,
        db: AsyncSession,
        *,
        creator_id: int,
        feedback_type: str,
        page: str,
        title: str,
        description: str,
        screenshot_asset_ids: list[int] | None = None,
    ) -> Feedback:
        feedback = Feedback(
            creator_id=creator_id,
            feedback_type=feedback_type,
            page=page,
            title=title,
            description=description,
        )
        db.add(feedback)
        await db.flush()

        for index, asset_id in enumerate(screenshot_asset_ids or []):
            db.add(
                FeedbackScreenshot(
                    feedback_id=feedback.id,
                    asset_id=asset_id,
                    sort_order=index,
                )
            )

        if screenshot_asset_ids:
            await db.flush()

        await db.refresh(feedback)
        return feedback

    async def find_feedback_by_id(
        self,
        db: AsyncSession,
        feedback_id: int,
    ) -> Feedback | None:
        result = await db.execute(
            select(Feedback)
            .where(Feedback.id == feedback_id)
            .options(*self._with_relations())
        )
        return result.unique().scalar_one_or_none()

    async def find_feedback_by_screenshot_asset_id(
        self,
        db: AsyncSession,
        asset_id: int,
    ) -> Feedback | None:
        result = await db.execute(
            select(Feedback)
            .outerjoin(FeedbackScreenshot)
            .where(FeedbackScreenshot.asset_id == asset_id)
            .options(*self._with_relations())
        )
        return result.unique().scalar_one_or_none()

    async def get_feedbacks(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        creator_id: int | None = None,
        status: str | None = None,
        feedback_type: str | None = None,
        feedback_page: str | None = None,
    ) -> tuple[list[Feedback], int]:
        stmt = select(Feedback).options(*self._with_relations())
        count_stmt = select(func.count()).select_from(Feedback)

        filters = []
        if creator_id is not None:
            filters.append(Feedback.creator_id == creator_id)
        if status is not None:
            filters.append(Feedback.status == status)
        if feedback_type is not None:
            filters.append(Feedback.feedback_type == feedback_type)
        if feedback_page is not None:
            filters.append(Feedback.page == feedback_page)

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        stmt = (
            stmt.order_by(Feedback.created_at.desc(), Feedback.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())

        total = await db.scalar(count_stmt)
        return items, int(total or 0)

    async def save_feedback(
        self,
        db: AsyncSession,
        feedback: Feedback,
    ) -> Feedback:
        db.add(feedback)
        await db.flush()
        await db.refresh(feedback)
        return feedback
