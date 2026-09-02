from __future__ import annotations

from models.resume import ResumeData
from templates.registry import TemplateRegistry

from .base import RendererError
from .format1_service import Format1RenderService
from .format2_service import Format2RenderService
from .user_template_service import UserTemplateRenderService


class RendererFactory:
    """Resolve a renderer by stable registry ID without template conditionals."""

    _services = {"kanini-format-1": Format1RenderService, "kanini-format-2": Format2RenderService}

    def __init__(self, registry: TemplateRegistry) -> None:
        self.registry = registry

    def get(self, template_id: str) -> Format1RenderService | Format2RenderService | UserTemplateRenderService:
        template = self.registry.get(template_id)
        if template.user_created:
            return UserTemplateRenderService(template, self.registry.template_root(template.id))
        service_type = self._services.get(template.id)
        if service_type is None:
            raise RendererError(f"No migrated renderer is registered for {template.id}.")
        return service_type(template)

    def supports(self, template_id: str) -> bool:
        return self.registry.is_user_template(template_id) or self.registry.resolve(template_id) in self._services