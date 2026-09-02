from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .metadata import TemplateMetadata


class TemplateRegistryError(ValueError):
    pass


class TemplateNotFoundError(TemplateRegistryError):
    pass


class TemplateRegistry:
    """Discover and resolve template metadata without coupling to renderers."""

    def __init__(self, templates: list[TemplateMetadata | tuple[TemplateMetadata, Path]], built_in_root: Path | None = None, user_root: Path | None = None) -> None:
        self._by_id: dict[str, TemplateMetadata] = {}
        self._aliases: dict[str, str] = {}
        self._roots: dict[str, Path] = {}
        self._built_in_templates_dir = (built_in_root or Path(__file__).resolve().parents[1]).resolve()
        self._user_templates_dir = (user_root or self._built_in_templates_dir.parent / "user_templates").resolve()
        for item in templates:
            template, root = item if isinstance(item, tuple) else (item, self._built_in_templates_dir / item.id)
            if template.id in self._by_id:
                raise TemplateRegistryError(f"Duplicate template id: {template.id}")
            if template.id in self._aliases:
                raise TemplateRegistryError(f"Template id conflicts with alias: {template.id}")
            self._by_id[template.id] = template
            self._roots[template.id] = root
            for alias in template.aliases:
                if alias in self._by_id or alias in self._aliases:
                    raise TemplateRegistryError(f"Duplicate or conflicting template alias: {alias}")
                self._aliases[alias] = template.id

    @classmethod
    def discover(cls, templates_dir: Path | None = None, user_templates_dir: Path | None = None) -> "TemplateRegistry":
        built_in_root = (templates_dir or Path(__file__).resolve().parents[1]).resolve()
        user_root = (user_templates_dir or built_in_root.parent / "user_templates").resolve()
        templates: list[tuple[TemplateMetadata, Path]] = []

        def load_manifests(root: Path, user_created: bool, ignore_invalid: bool) -> None:
            if not root.is_dir():
                return
            for manifest_path in sorted(root.glob("*/manifest.json")):
                package_root = manifest_path.parent.resolve()
                if package_root.parent != root:
                    continue
                try:
                    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                    payload["user_created"] = user_created
                    if user_created:
                        payload["supported_outputs"] = ["html", "docx", "pdf"]
                    templates.append((TemplateMetadata.model_validate(payload), package_root))
                except (OSError, json.JSONDecodeError, ValidationError) as exc:
                    if ignore_invalid:
                        continue
                    raise TemplateRegistryError(f"Invalid template manifest {manifest_path}: {exc}") from exc

        load_manifests(built_in_root, user_created=False, ignore_invalid=False)
        load_manifests(user_root, user_created=True, ignore_invalid=True)
        return cls(templates, built_in_root=built_in_root, user_root=user_root)

    def reload(self) -> None:
        refreshed = self.discover(self._built_in_templates_dir, self._user_templates_dir)
        self._by_id = refreshed._by_id
        self._aliases = refreshed._aliases
        self._roots = refreshed._roots

    def template_root(self, template_id: str) -> Path:
        return self._roots[self.resolve(template_id)]

    def is_user_template(self, template_id: str) -> bool:
        return self.get(template_id).user_created
    def resolve(self, template_id: str) -> str:
        key = str(template_id or "").strip()
        canonical_id = self._aliases.get(key, key)
        if canonical_id not in self._by_id:
            raise TemplateNotFoundError(f"Unknown template: {key or '<empty>'}")
        return canonical_id

    def get(self, template_id: str) -> TemplateMetadata:
        return self._by_id[self.resolve(template_id)]

    def exists(self, template_id: str) -> bool:
        try:
            self.resolve(template_id)
        except TemplateNotFoundError:
            return False
        return True

    def list_enabled(self) -> list[TemplateMetadata]:
        return [template for template in self._by_id.values() if template.enabled]

    def supports_output(self, template_id: str, output: str) -> bool:
        return output in self.get(template_id).supported_outputs