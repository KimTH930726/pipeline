from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class Review:
    branch: str
    status: ReviewStatus = ReviewStatus.PENDING
    comment: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None
    id: int | None = None

    def approve(self, comment: str | None = None) -> None:
        self.status = ReviewStatus.APPROVED
        self.comment = comment
        self.reviewed_at = datetime.now(timezone.utc)

    def reject(self, comment: str | None = None) -> None:
        self.status = ReviewStatus.REJECTED
        self.comment = comment
        self.reviewed_at = datetime.now(timezone.utc)

    @property
    def is_approved(self) -> bool:
        return self.status == ReviewStatus.APPROVED
