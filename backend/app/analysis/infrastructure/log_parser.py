from __future__ import annotations

_ERROR_KEYWORDS = ("error", "exception", "fail", "traceback", "fatal")


def extract_error_context(build_log: str, context_lines: int = 20) -> str:
    """Extract meaningful error context from build log for LLM analysis."""
    lines = build_log.split("\n")
    error_indices = [
        i
        for i, line in enumerate(lines)
        if any(kw in line.lower() for kw in _ERROR_KEYWORDS)
    ]

    if not error_indices:
        return "\n".join(lines[-30:])

    selected: set[int] = set()
    for idx in error_indices:
        start = max(0, idx - context_lines)
        end = min(len(lines), idx + context_lines + 1)
        selected.update(range(start, end))

    return "\n".join(lines[i] for i in sorted(selected))
