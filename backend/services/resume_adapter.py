from __future__ import annotations

from typing import Any, Mapping

from models.resume import ResumeData


class ResumeAdapter:
    """Losslessly translate legacy parser dictionaries to and from ResumeData."""

    @staticmethod
    def from_legacy(data: Mapping[str, Any] | None) -> ResumeData:
        payload = dict(data or {})
        payload["contact"] = payload.get("contact") or {}
        payload["summary"] = payload.get("summary") or payload.get("professional_summary") or ""
        payload["experience"] = [ResumeAdapter._adapt_experience(item) for item in payload.get("experience") or []]
        payload["projects"] = [ResumeAdapter._adapt_project(item) for item in payload.get("projects") or []]
        return ResumeData.model_validate(payload)

    @staticmethod
    def to_legacy(resume: ResumeData) -> dict[str, Any]:
        payload = resume.model_dump()
        # Existing parsers, templates, persistence, and Angular expect this shape.
        payload.pop("additional_sections", None)
        return payload

    @classmethod
    def adapt_ai_output(cls, data: Mapping[str, Any] | None) -> ResumeData:
        return cls.from_legacy(data)

    @classmethod
    def adapt_regex_output(cls, data: Mapping[str, Any] | None) -> ResumeData:
        return cls.from_legacy(data)

    @staticmethod
    def _adapt_experience(value: Any) -> dict[str, Any]:
        item = dict(value) if isinstance(value, Mapping) else {}
        item["title"] = item.get("title") or item.get("designation") or item.get("role") or ""
        item["dates"] = item.get("dates") or item.get("duration") or ""
        item["projects"] = [ResumeAdapter._adapt_project(project) for project in item.get("projects") or []]
        return item

    @staticmethod
    def _adapt_project(value: Any) -> dict[str, Any]:
        item = dict(value) if isinstance(value, Mapping) else {}
        item["name"] = item.get("name") or item.get("project_name") or ""
        item["description"] = item.get("description") or item.get("summary") or ""
        item["duration"] = item.get("duration") or item.get("dates") or ""
        technologies = item.get("technologies") or item.get("technical_stack") or []
        item["technologies"] = [part.strip() for part in technologies.split(",") if part.strip()] if isinstance(technologies, str) else technologies
        item["responsibilities"] = item.get("responsibilities") or item.get("roles_and_responsibilities") or []
        return item