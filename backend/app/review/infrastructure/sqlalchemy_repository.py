from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.review.domain.entities import Review, ReviewStatus
from app.review.domain.repositories import ReviewRepositoryPort
from app.review.infrastructure.sqlalchemy_models import ReviewModel


class SQLAlchemyReviewRepository(ReviewRepositoryPort):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, review: Review) -> Review:
        model = ReviewModel(
            branch=review.branch,
            status=review.status.value,
            comment=review.comment,
            created_at=review.created_at,
            reviewed_at=review.reviewed_at,
        )
        self._db.add(model)
        await self._db.commit()
        await self._db.refresh(model)
        review.id = model.id
        return review

    async def update(self, review: Review) -> None:
        result = await self._db.execute(
            select(ReviewModel).where(ReviewModel.id == review.id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return
        model.status = review.status.value
        model.comment = review.comment
        model.reviewed_at = review.reviewed_at
        await self._db.commit()

    async def find_by_id(self, review_id: int) -> Review | None:
        result = await self._db.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_branch(self, branch: str) -> Review | None:
        result = await self._db.execute(
            select(ReviewModel).where(ReviewModel.branch == branch)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_approved(self) -> list[Review]:
        result = await self._db.execute(
            select(ReviewModel).where(ReviewModel.status == "APPROVED")
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_all(self) -> list[Review]:
        result = await self._db.execute(
            select(ReviewModel).order_by(ReviewModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: ReviewModel) -> Review:
        return Review(
            id=model.id,
            branch=model.branch,
            status=ReviewStatus(model.status),
            comment=model.comment,
            created_at=model.created_at,
            reviewed_at=model.reviewed_at,
        )
