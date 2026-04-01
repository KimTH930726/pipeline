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
    acted_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None
    id: int | None = None

    def approve(self, comment: str | None = None, acted_by: str | None = None) -> None:
        self.status = ReviewStatus.APPROVED
        self.comment = comment
        self.acted_by = acted_by
        self.reviewed_at = datetime.now(timezone.utc)

    def reject(self, comment: str | None = None, acted_by: str | None = None) -> None:
        self.status = ReviewStatus.REJECTED
        self.comment = comment
        self.acted_by = acted_by
        self.reviewed_at = datetime.now(timezone.utc)

    def reset(self) -> None:
        self.status = ReviewStatus.PENDING
        self.comment = None
        self.acted_by = None
        self.reviewed_at = None

    @property
    def is_approved(self) -> bool:
        return self.status == ReviewStatus.APPROVED
