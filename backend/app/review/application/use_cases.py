from __future__ import annotations

from app.review.domain.entities import Review
from app.review.domain.repositories import ReviewRepositoryPort
from app.review.application.dtos import ReviewResponseDTO


def _to_dto(r: Review) -> ReviewResponseDTO:
    return ReviewResponseDTO(
        id=r.id, branch=r.branch, status=r.status.value,
        comment=r.comment, created_at=r.created_at, reviewed_at=r.reviewed_at,
    )


class RequestReview:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str) -> ReviewResponseDTO:
        existing = await self._repo.find_by_branch(branch)
        if existing:
            return _to_dto(existing)
        review = Review(branch=branch)
        review = await self._repo.save(review)
        return _to_dto(review)


class ApproveReview:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str, comment: str | None = None) -> ReviewResponseDTO:
        review = await self._repo.find_by_branch(branch)
        if not review:
            review = Review(branch=branch)
            review.approve(comment)
            review = await self._repo.save(review)
        else:
            review.approve(comment)
            await self._repo.update(review)
        return _to_dto(review)


class RejectReview:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str, comment: str | None = None) -> ReviewResponseDTO:
        review = await self._repo.find_by_branch(branch)
        if not review:
            review = Review(branch=branch)
            review.reject(comment)
            review = await self._repo.save(review)
        else:
            review.reject(comment)
            await self._repo.update(review)
        return _to_dto(review)


class GetReviewStatus:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, branch: str) -> ReviewResponseDTO | None:
        review = await self._repo.find_by_branch(branch)
        return _to_dto(review) if review else None


class ListApprovedReviews:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self) -> list[ReviewResponseDTO]:
        return [_to_dto(r) for r in await self._repo.find_approved()]


class ListAllReviews:
    def __init__(self, repo: ReviewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self) -> list[ReviewResponseDTO]:
        return [_to_dto(r) for r in await self._repo.find_all()]
