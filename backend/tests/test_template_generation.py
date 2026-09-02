import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException

import ai_parser
import main
from models.template_spec import TemplateSpec
from services import template_generation_service
from services.template_validation_service import TemplateSpecValidationError, validate_template_spec


VALID_SPEC = {
    "page": {"size": "A4", "orientation": "portrait", "margin_inches": 0.65},
    "typography": {"font_family": "Calibri", "base_size_pt": 10, "heading_size_pt": 14},
    "colors": {"text": "#1F2937", "accent": "#0072B4", "muted": "#64748B"},
    "header": {"layout": "left", "contact_layout": "inline", "show_divider": True},
    "layout": {"columns": 1, "sidebar_position": "none", "section_alignment": "left"},
    "sections": ["summary", "skills", "experience", "education"],
    "spacing": {"section_gap_pt": 12, "line_height": 1.35, "divider_style": "accent", "skill_style": "tags"},
}


def test_valid_template_spec_is_accepted():
    assert isinstance(validate_template_spec(VALID_SPEC), TemplateSpec)


def test_unsafe_template_spec_is_rejected():
    unsafe = {**VALID_SPEC, "script": "alert(1)"}
    with pytest.raises(TemplateSpecValidationError):
        validate_template_spec(unsafe)


def test_unsafe_template_spec_boundaries_are_rejected():
    with pytest.raises(TemplateSpecValidationError):
        validate_template_spec({**VALID_SPEC, "page": {**VALID_SPEC["page"], "margin_inches": 2}})
    with pytest.raises(TemplateSpecValidationError):
        validate_template_spec({**VALID_SPEC, "typography": {**VALID_SPEC["typography"], "heading_size_pt": 10}})


def test_ollama_template_response_is_parsed(monkeypatch):
    class Response:
        def read(self): return json.dumps({"response": json.dumps(VALID_SPEC)}).encode()
        def __enter__(self): return self
        def __exit__(self, *args): return False

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setattr(template_generation_service.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert template_generation_service.generate_template_spec({"summary": "Sample"}) == VALID_SPEC


def test_invalid_ollama_json_is_handled(monkeypatch):
    class Response:
        def read(self): return b'{"response":"not json"}'
        def __enter__(self): return self
        def __exit__(self, *args): return False

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setattr(template_generation_service.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(template_generation_service.TemplateGenerationError):
        template_generation_service.generate_template_spec({})


def test_ollama_unavailable_is_handled(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    with pytest.raises(ai_parser.ProviderUnavailableError):
        template_generation_service.generate_template_spec({})


def test_generate_template_draft_persists_spec(tmp_path, monkeypatch, normal_resume):
    draft_id = str(uuid.uuid4())
    draft_dir = tmp_path / draft_id
    draft_dir.mkdir()
    (draft_dir / "extracted_data.json").write_text(json.dumps({"filename": "sample.pdf", "extracted_data": normal_resume}), encoding="utf-8")
    monkeypatch.setattr(main, "TEMPLATE_DRAFT_DIR", tmp_path)
    monkeypatch.setattr(main, "generate_template_spec", lambda _: VALID_SPEC)

    response = asyncio.run(main.generate_template_draft(draft_id))

    assert response["status"] == "generated"
    assert response["template_spec"] == VALID_SPEC
    assert (draft_dir / "template_spec.json").is_file()
    assert (draft_dir / "preview.html").is_file()


def test_generate_template_draft_rejects_unsafe_spec(tmp_path, monkeypatch, normal_resume):
    draft_id = str(uuid.uuid4())
    draft_dir = tmp_path / draft_id
    draft_dir.mkdir()
    (draft_dir / "extracted_data.json").write_text(json.dumps({"extracted_data": normal_resume}), encoding="utf-8")
    monkeypatch.setattr(main, "TEMPLATE_DRAFT_DIR", tmp_path)
    monkeypatch.setattr(main, "generate_template_spec", lambda _: {**VALID_SPEC, "html": "<script>alert(1)</script>"})

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.generate_template_draft(draft_id))

    assert exc.value.status_code == 422
