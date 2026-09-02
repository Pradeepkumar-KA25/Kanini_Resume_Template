from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from models.template_spec import TemplateSpec


class UserTemplateValidationError(ValueError):
    """Raised when user-provided template metadata is unsuitable for storage."""


_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,'&()_-]*$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_TEMPLATE_ID_RE = re.compile(r"^user-[a-f0-9]{32}$")


def validate_template_name(value: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise UserTemplateValidationError("Template name is required.")
    if len(name) > 80:
        raise UserTemplateValidationError("Template name must be 80 characters or fewer.")
    if not _NAME_RE.fullmatch(name):
        raise UserTemplateValidationError("Template name contains unsupported characters.")
    return name


def validate_template_description(value: str) -> str:
    description = str(value or "").strip()
    if not description:
        raise UserTemplateValidationError("Template description is required.")
    if len(description) > 240:
        raise UserTemplateValidationError("Template description must be 240 characters or fewer.")
    if _CONTROL_RE.search(description) or "<" in description or ">" in description:
        raise UserTemplateValidationError("Template description contains unsupported characters.")
    return description


def describe_template_spec(spec: TemplateSpec) -> str:
    columns = "Two-column" if spec.layout.columns == 2 else "Single-column"
    style = "accent-divided" if spec.spacing.divider_style == "accent" else "minimal" if spec.spacing.divider_style == "none" else "structured"
    section_names = ", ".join(section.replace("_", " ") for section in spec.sections[:3])
    return f"{columns} {spec.typography.font_family} resume template with a {style} visual style and organized {section_names} sections."


def _package(root: Path, template_id: str) -> Path:
    if not _TEMPLATE_ID_RE.fullmatch(str(template_id or "")):
        raise UserTemplateValidationError("User template was not found.")
    package = (root / template_id).resolve()
    if package.parent != root.resolve() or not package.is_dir():
        raise UserTemplateValidationError("User template was not found.")
    return package


def load_user_template(root: Path, template_id: str) -> tuple[dict, TemplateSpec, Path]:
    package = _package(root, template_id)
    try:
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        spec = TemplateSpec.model_validate(json.loads((package / "template-spec.json").read_text(encoding="utf-8")))
    except Exception as exc:
        raise UserTemplateValidationError("User template data is invalid.") from exc
    if manifest.get("id") != template_id or not manifest.get("user_created"):
        raise UserTemplateValidationError("User template data is invalid.")
    return manifest, spec, package


def update_user_template(root: Path, template_id: str, spec: TemplateSpec, display_name: str, description: str) -> dict[str, str]:
    manifest, _, package = load_user_template(root, template_id)
    manifest.update({"display_name": display_name, "description": description, "page_size": spec.page.size})
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (package / "template-spec.json").write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")
    return {"template_id": template_id, "display_name": display_name, "description": description, "status": "updated"}


def delete_user_template(root: Path, template_id: str) -> None:
    shutil.rmtree(_package(root, template_id))


def save_user_template(root: Path, spec: TemplateSpec, display_name: str, description: str, source_dir: Path | None = None) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    template_id = ""
    package_dir: Path | None = None
    for _ in range(5):
        candidate = f"user-{uuid.uuid4().hex}"
        candidate_dir = root / candidate
        try:
            candidate_dir.mkdir()
            template_id = candidate
            package_dir = candidate_dir
            break
        except FileExistsError:
            continue
    if package_dir is None:
        raise RuntimeError("Could not allocate a template ID.")

    manifest = {
        "id": template_id,
        "display_name": display_name,
        "description": description,
        "version": "1.0",
        "enabled": True,
        "supported_outputs": ["html", "docx", "pdf"],
        "page_size": spec.page.size,
        "aliases": [],
        "assets": {},
        "download_base_name": template_id,
        "user_created": True,
    }
    try:
        (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (package_dir / "template-spec.json").write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")
        if source_dir:
            for filename in ("original.pdf", "extracted_data.json"):
                source = source_dir / filename
                if source.is_file():
                    shutil.copy2(source, package_dir / filename)
    except Exception:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise
    return {"template_id": template_id, "display_name": display_name, "description": description, "status": "saved"}
