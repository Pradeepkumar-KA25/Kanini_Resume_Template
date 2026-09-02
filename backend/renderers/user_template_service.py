from __future__ import annotations

import json
from pathlib import Path

from models.resume import ResumeData
from services.template_validation_service import validate_template_spec
from templates.registry.metadata import TemplateMetadata

from .base import RenderResult, RendererError
from .template_draft_renderer import render_template_draft_preview
from .user_template_output_service import render_user_template_docx, render_user_template_pdf


class UserTemplateRenderService:
    """Render a saved user template through its validated, non-executable spec."""

    def __init__(self, template: TemplateMetadata, root: Path) -> None:
        self.template = template
        self.root = root

    def render_html(self, resume: ResumeData) -> RenderResult:
        spec = self._load_spec()
        return RenderResult(self.template.id, "html", content=render_template_draft_preview(resume, spec))

    def render_docx(self, resume: ResumeData, output_path: Path) -> RenderResult:
        result = render_user_template_docx(resume, self._load_spec(), output_path)
        return RenderResult(self.template.id, "docx", path=result.path)

    def render_pdf(self, resume: ResumeData, output_path: Path) -> RenderResult:
        pdf_path = output_path.with_suffix(".pdf")
        html = render_template_draft_preview(resume, self._load_spec())
        result = render_user_template_pdf(html, self._load_spec(), pdf_path)
        return RenderResult(self.template.id, "pdf", path=result.path)

    def _load_spec(self):
        try:
            payload = json.loads((self.root / "template-spec.json").read_text(encoding="utf-8"))
            return validate_template_spec(payload)
        except Exception as exc:
            raise RendererError("User template specification is invalid.") from exc