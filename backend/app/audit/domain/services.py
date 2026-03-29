from __future__ import annotations

import hashlib
import json


class AuditDomainService:
    """Pure domain logic for audit hash-chain integrity."""

    @staticmethod
    def compute_entry_hash(
        prev_hash: str | None,
        event_data: dict,
        timestamp: str,
    ) -> str:
        payload = json.dumps(
            {
                "prev_hash": prev_hash or "",
                "event_data": event_data,
                "timestamp": timestamp,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def verify_chain(entries: list) -> bool:
        """Verify hash-chain integrity across a list of AuditEntry."""
        for i, entry in enumerate(entries):
            expected_prev = entries[i - 1].entry_hash if i > 0 else None
            if entry.prev_hash != expected_prev:
                return False
        return True
