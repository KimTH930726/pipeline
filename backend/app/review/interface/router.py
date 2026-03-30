from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.database import get_db
from app.review.application.dtos import ReviewRequestDTO, ReviewResponseDTO
from app.review.application.use_cases import (
    RequestReview, ApproveReview, RejectReview,
    GetReviewStatus, ListApprovedReviews, ListAllReviews,
)
from app.review.infrastructure.sqlalchemy_repository import SQLAlchemyReviewRepository

router = APIRouter(prefix="/api/review", tags=["review"])


def _repo(db: AsyncSession = Depends(get_db)) -> SQLAlchemyReviewRepository:
    return SQLAlchemyReviewRepository(db)


@router.post("/request", response_model=ReviewResponseDTO)
async def request_review(body: ReviewRequestDTO, repo=Depends(_repo)):
    return await RequestReview(repo).execute(body.branch)


@router.post("/approve", response_model=ReviewResponseDTO)
async def approve(body: ReviewRequestDTO, repo=Depends(_repo)):
    return await ApproveReview(repo).execute(body.branch, body.comment)


@router.post("/reject", response_model=ReviewResponseDTO)
async def reject(body: ReviewRequestDTO, repo=Depends(_repo)):
    return await RejectReview(repo).execute(body.branch, body.comment)


@router.get("/status/{branch:path}", response_model=ReviewResponseDTO)
async def get_status(branch: str, repo=Depends(_repo)):
    result = await GetReviewStatus(repo).execute(branch)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found for this branch")
    return result


@router.get("/approved", response_model=list[ReviewResponseDTO])
async def list_approved(repo=Depends(_repo)):
    return await ListApprovedReviews(repo).execute()


@router.get("/list", response_model=list[ReviewResponseDTO])
async def list_all(repo=Depends(_repo)):
    return await ListAllReviews(repo).execute()
