from __future__ import annotations

import html
import importlib.util
from pathlib import Path

from models.resume import ResumeData
from templates.registry.metadata import TemplateMetadata

from .base import RenderResult
from .format1_view_model import Format1ViewModel
from .latex_renderer import XeLatexCompiler, escape_latex


class Format1RenderService:
    template_id = "kanini-format-1"

    def __init__(self, template: TemplateMetadata) -> None:
        self.template = template
        self.root = Path(__file__).resolve().parents[1] / "templates" / self.template.id
        self.logo_path = self.root / "assets" / "kanini-logo.png"

    def render_html(self, resume: ResumeData) -> RenderResult:
        view = Format1ViewModel(resume)
        content = self._html_content(view)
        css = (self.root / "html" / "template.css").read_text(encoding="utf-8")
        return RenderResult(self.template_id, "html", content=f"<style>{css}</style>{content}")

    def render_docx(self, resume: ResumeData, output_path: Path) -> RenderResult:
        module_path = self.root / "docx" / "renderer.py"
        spec = importlib.util.spec_from_file_location("kanini_format_1_docx", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Format 1 DOCX renderer could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return RenderResult(self.template_id, "docx", path=module.render(resume, output_path, self.logo_path))

    def render_latex(self, resume: ResumeData, output_path: Path) -> RenderResult:
        template = (self.root / "latex" / "template.tex").read_text(encoding="utf-8")
        logo = self.logo_path.resolve().as_posix().replace(" ", r"\ ")
        (output_path.parent / "sections.tex").write_text(
            (self.root / "latex" / "sections.tex").read_text(encoding="utf-8"), encoding="utf-8"
        )
        output_path.write_text(template.replace("__LOGO_PATH__", logo).replace("__CONTENT__", self._latex_content(Format1ViewModel(resume))), encoding="utf-8")
        return RenderResult(self.template_id, "tex", path=output_path)

    def render_pdf(self, resume: ResumeData, tex_path: Path) -> RenderResult:
        self.render_latex(resume, tex_path)
        return XeLatexCompiler().compile(tex_path)

    def _html_content(self, view: Format1ViewModel) -> str:
        esc = lambda value: html.escape(str(value or ""))
        sections = []
        if view.resume.summary:
            sections.append(self._html_section("Profile Summary", [f"<ul>{''.join(f'<li>{esc(item)}</li>' for item in view.resume.summary.splitlines() if item)}</ul>"]))
        if view.resume.skills:
            sections.append(self._html_section("Technical Skills", [f"<ul>{''.join(f'<li><strong>{esc(category)}:</strong> {esc(', '.join(items))}</li>' for category, items in view.resume.skills.items())}</ul>"]))
        if view.resume.experience:
            entries = []
            for entry in view.resume.experience:
                rows = "".join(f'<div class="label-row"><span>{label}</span><span>:</span><span>{esc(value or "-")}</span></div>' for label, value in (("Company Name", entry.company_name or entry.company), ("Designation", entry.title), ("Duration", entry.dates)))
                duties = "".join(f"<li>{esc(item)}</li>" for item in entry.responsibilities)
                entries.append(f'<div class="experience">{rows}{f"<ul>{duties}</ul>" if duties else ""}</div>')
            sections.append(self._html_section("Work Experience", entries))
        if view.projects:
            projects = []
            for index, project in enumerate(view.projects, 1):
                details = "".join(f"<p><strong>{label}:</strong> {esc(value)}</p>" for label, value in (("Client", project.client), ("Technologies", ", ".join(project.technologies)), ("Description", project.description)) if value)
                duties = "".join(f"<li>{esc(item)}</li>" for item in project.responsibilities)
                projects.append(f'<article class="project"><div class="project-title">{view.project_label(index)}:</div><p><strong>{esc(project.name)}</strong></p>{details}{f"<div class=\"responsibilities-title\">Roles and Responsibilities:</div><ul>{duties}</ul>" if duties else ""}</article>')
            sections.append(self._html_section("Project Summary", projects))
        education = [" ".join(filter(None, (item.degree, f"({item.year})" if item.year else "", f"from {item.institution}" if item.institution else "", f"GPA: {item.gpa}" if item.gpa else ""))) for item in view.resume.education]
        if education:
            sections.append(self._html_section("Educational Qualification", [f"<ul>{''.join(f'<li>{esc(item)}</li>' for item in education)}</ul>"]))
        if view.resume.certifications:
            sections.append(self._html_section("Certifications", [f"<ul>{''.join(f'<li>{esc(item)}</li>' for item in view.resume.certifications)}</ul>"]))
        if view.resume.achievements:
            sections.append(self._html_section("Achievements", [f"<ul>{''.join(f'<li>{esc(item)}</li>' for item in view.resume.achievements)}</ul>"]))
        contact = f'<p class="resume-contact">{esc(" | ".join(view.contact_parts))}</p>' if view.contact_parts else ""
        return f'<main class="resume-page"><h1 class="resume-name">{esc(view.name.upper())}</h1>{contact}{"".join(sections)}</main>'

    @staticmethod
    def _html_section(title: str, content: list[str]) -> str:
        return f'<section class="resume-section"><h2>{title}</h2>{"".join(content)}</section>'

    def _latex_content(self, view: Format1ViewModel) -> str:
        lines = [r"\begin{center}\textbf{" + escape_latex(view.name.upper()) + r"}\end{center}"]
        if view.contact_parts:
            lines.append(escape_latex(" | ".join(view.contact_parts)) + r"\par")
        self._latex_section(lines, "Profile Summary", view.resume.summary.splitlines(), bullets=True)
        if view.resume.skills:
            lines.append(r"\KaniniSection{Technical Skills}")
            lines.append(r"\begin{itemize}")
            lines.extend(r"\item \textbf{" + escape_latex(category) + r":} " + escape_latex(", ".join(items)) for category, items in view.resume.skills.items())
            lines.append(r"\end{itemize}")
        if view.resume.experience:
            lines.append(r"\KaniniSection{Work Experience}")
            for entry in view.resume.experience:
                for label, value in (("Company Name", entry.company_name or entry.company), ("Designation", entry.title), ("Duration", entry.dates)):
                    lines.append(r"\KaniniLabelRow{" + label + "}{" + escape_latex(value or "-") + "}")
                self._latex_items(lines, entry.responsibilities)
        if view.projects:
            lines.append(r"\KaniniSection{Project Summary}")
            for index, project in enumerate(view.projects, 1):
                lines.append(r"\textbf{" + self._escape_template_text((view.project_label(index) + ":").upper()) + r"}\par")
                if project.name:
                    lines.append(r"\textbf{" + escape_latex(project.name.upper()) + r"}\par")
                for label, value in (("Client", project.client), ("Technologies", ", ".join(project.technologies)), ("Description", project.description)):
                    if value:
                        lines.append(r"\textbf{" + label + r":} " + escape_latex(value) + r"\par")
                if project.responsibilities:
                    lines.append(r"\textbf{ROLES AND RESPONSIBILITIES:}\par")
                    self._latex_items(lines, project.responsibilities)
        education = [" ".join(filter(None, (item.degree, f"({item.year})" if item.year else "", f"from {item.institution}" if item.institution else "", f"GPA: {item.gpa}" if item.gpa else ""))) for item in view.resume.education]
        self._latex_section(lines, "Educational Qualification", education, bullets=True)
        self._latex_section(lines, "Certifications", view.resume.certifications, bullets=True)
        self._latex_section(lines, "Achievements", view.resume.achievements, bullets=True)
        return "\n".join(lines)

    @staticmethod
    def _escape_template_text(value: str) -> str:
        return escape_latex(value)

    def _latex_section(self, lines: list[str], title: str, values: list[str], bullets: bool = False) -> None:
        values = [value for value in values if value]
        if not values:
            return
        lines.append(r"\KaniniSection{" + title + "}")
        if bullets:
            self._latex_items(lines, values)
        else:
            lines.extend(escape_latex(value) + r"\par" for value in values)

    @staticmethod
    def _latex_items(lines: list[str], values: list[str]) -> None:
        values = [value for value in values if value]
        if values:
            lines.append(r"\begin{itemize}")
            lines.extend(r"\item " + escape_latex(value) for value in values)
            lines.append(r"\end{itemize}")