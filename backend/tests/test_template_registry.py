import asyncio
import json

import pytest
from pydantic import ValidationError

from main import list_templates
from templates.registry import TemplateMetadata, TemplateNotFoundError, TemplateRegistry
from templates.registry.template_registry import TemplateRegistryError


def _metadata(template_id: str, aliases: list[str] | None = None, enabled: bool = True) -> TemplateMetadata:
    return TemplateMetadata(
        id=template_id,
        display_name=template_id,
        description="Test template",
        version="1.0",
        enabled=enabled,
        supported_outputs=["html", "docx", "pdf"],
        page_size="LETTER",
        aliases=aliases or [],
    )


def test_repository_manifests_load_with_stable_ids_and_aliases():
    registry = TemplateRegistry.discover()

    assert registry.resolve("template1") == "kanini-format-1"
    assert registry.resolve("template2") == "kanini-format-2"
    assert registry.get("kanini-format-1").page_size == "LETTER"
    assert registry.get("kanini-format-2").page_size == "A4"
    assert registry.supports_output("template1", "pdf")
    assert not registry.supports_output("template2", "txt")


def test_unknown_template_raises_controlled_error():
    with pytest.raises(TemplateNotFoundError, match="Unknown template"):
        TemplateRegistry.discover().get("unknown-template")


def test_duplicate_ids_and_aliases_are_rejected():
    with pytest.raises(TemplateRegistryError, match="Duplicate template id"):
        TemplateRegistry([_metadata("one"), _metadata("one")])
    with pytest.raises(TemplateRegistryError, match="Duplicate or conflicting template alias"):
        TemplateRegistry([_metadata("one", ["legacy"]), _metadata("two", ["legacy"])])


def test_disabled_templates_are_resolvable_but_not_listed():
    registry = TemplateRegistry([_metadata("active"), _metadata("hidden", enabled=False)])

    assert registry.get("hidden").id == "hidden"
    assert [template.id for template in registry.list_enabled()] == ["active"]


def test_invalid_supported_output_is_rejected():
    with pytest.raises(ValidationError):
        TemplateMetadata(
            id="invalid",
            display_name="Invalid",
            description="Test template",
            version="1.0",
            enabled=True,
            supported_outputs=["txt"],
            page_size="LETTER",
        )


def test_template_listing_endpoint_exposes_enabled_public_metadata():
    response = asyncio.run(list_templates())

    assert [template["id"] for template in response["templates"]] == ["kanini-format-1", "kanini-format-2"]
    assert all("aliases" not in template and "assets" not in template for template in response["templates"])