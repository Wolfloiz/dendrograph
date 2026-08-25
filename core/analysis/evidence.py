"""Every claim points at what produced it.

Nothing inferred enters the graph without a pointer to the file or path it came
from (FR-010, SC-006). This is the shape that pointer takes.
"""

from __future__ import annotations

KIND_PATH = "path"
KIND_MANIFEST = "manifest"
KIND_FILE_EXTENSION = "file_extension"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


def evidence(kind: str, detail: str) -> dict:
    return {"kind": kind, "detail": detail}
