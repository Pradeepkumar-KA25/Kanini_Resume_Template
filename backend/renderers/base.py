from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class RendererError(RuntimeError):
    """A controlled rendering failure safe to translate at an API boundary."""


class LatexUnavailableError(RendererError):
    """XeLaTeX is unavailable in the current runtime environment."""


@dataclass(frozen=True)
class RenderResult:
    template_id: str
    output_format: str
    path: Path | None = None
    content: str | None = None
    diagnostics: str = ""
    used_fallback: bool = False
    metadata: dict[str, str] = field(default_factory=dict)