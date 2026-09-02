import asyncio
import json

import pytest

import main
from models.resume import ResumeData
from renderers.render_service import RendererFactory
from templates.registry import TemplateRegistry
from templates.registry.template_registry import TemplateRegistryError
from tests.test_template_generation import VALID_SPEC


def _write_user_template(root, template_id="user-modern", display_name="Modern Resume"):
    package = root / template_id
    package.mkdir(parents=True)
    manifest = {
        "id": template_id,
        "display_name": display_name,
        "description": "A professional generated template.",
        "version": "1.0",
        "enabled": True,
        "supported_outputs": ["html", "docx", "pdf"],
        "page_size": "A4",
        "aliases": [],
        "assets": {},
        "download_base_name": template_id,
        "user_created": True,
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (package / "template-spec.json").write_text(json.dumps(VALID_SPEC), encoding="utf-8")
    return package


def test_built_in_templates_remain_discovered_with_user_templates(tmp_path):
    _write_user_template(tmp_path)
    registry = TemplateRegistry.discover(user_templates_dir=tmp_path)
    assert registry.exists("kanini-format-1")
    assert registry.exists("kanini-format-2")
    assert registry.get("user-modern").user_created


def test_invalid_user_manifest_is_ignored(tmp_path):
    package = tmp_path / "invalid"
    package.mkdir()
    (package / "manifest.json").write_text("not json", encoding="utf-8")
    registry = TemplateRegistry.discover(user_templates_dir=tmp_path)
    assert not registry.exists("invalid")
    assert registry.exists("kanini-format-1")


def test_duplicate_user_template_id_is_rejected(tmp_path):
    _write_user_template(tmp_path, template_id="kanini-format-1")
    with pytest.raises(TemplateRegistryError, match="Duplicate template id"):
        TemplateRegistry.discover(user_templates_dir=tmp_path)


def test_registry_reload_discovers_new_user_template_without_restart(tmp_path):
    registry = TemplateRegistry.discover(user_templates_dir=tmp_path)
    _write_user_template(tmp_path)
    registry.reload()
    assert registry.exists("user-modern")


def test_api_listing_and_resume_render_support_user_templates(tmp_path, monkeypatch, normal_resume):
    _write_user_template(tmp_path)
    registry = TemplateRegistry.discover(user_templates_dir=tmp_path)
    monkeypatch.setattr(main, "TEMPLATE_REGISTRY", registry)
    monkeypatch.setattr(main, "RENDERER_FACTORY", RendererFactory(registry))
    session_id = "user-template-render"
    main.SESSIONS[session_id] = {"review_data": normal_resume, "resume_data": normal_resume, "files": {}, "filename": "resume.pdf"}
    try:
        listing = asyncio.run(main.list_templates())
        assert "user-modern" in [template["id"] for template in listing["templates"]]
        assert next(template for template in listing["templates"] if template["id"] == "user-modern")["user_created"] is True
        response = asyncio.run(main.render_reviewed_resume(session_id, main.RenderRequest(template_id="user-modern")))
        assert response["template_id"] == "user-modern"
        assert "generated-resume" in response["preview_html"]
    finally:
        main.SESSIONS.pop(session_id, None)