from __future__ import annotations

import html
import importlib.util
from pathlib import Path

from models.resume import ResumeData
from templates.registry.metadata import TemplateMetadata

from .base import RenderResult
from .format2_view_model import Format2ViewModel
from .latex_renderer import XeLatexCompiler, escape_latex


class Format2RenderService:
    template_id = "kanini-format-2"

    def __init__(self, template: TemplateMetadata) -> None:
        self.template = template
        self.root = Path(__file__).resolve().parents[1] / "templates" / template.id
        self.logo_path = self.root / "assets" / "kanini-logo.png"

    def render_html(self, resume: ResumeData) -> RenderResult:
        css = (self.root / "html" / "template.css").read_text(encoding="utf-8")
        return RenderResult(self.template_id, "html", content=f"<style>{css}</style>{self._html(Format2ViewModel(resume))}")

    def render_docx(self, resume: ResumeData, output_path: Path) -> RenderResult:
        path = self.root / "docx" / "renderer.py"
        spec = importlib.util.spec_from_file_location("kanini_format_2_docx", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Format 2 DOCX renderer could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return RenderResult(self.template_id, "docx", path=module.render(resume, output_path, self.logo_path))

    def render_latex(self, resume: ResumeData, output_path: Path) -> RenderResult:
        template = (self.root / "latex" / "template.tex").read_text(encoding="utf-8")
        (output_path.parent / "sections.tex").write_text((self.root / "latex" / "sections.tex").read_text(encoding="utf-8"), encoding="utf-8")
        logo = self.logo_path.resolve().as_posix().replace(" ", r"\ ")
        output_path.write_text(template.replace("__LOGO_PATH__", logo).replace("__CONTENT__", self._latex(Format2ViewModel(resume))), encoding="utf-8")
        return RenderResult(self.template_id, "tex", path=output_path)

    def render_pdf(self, resume: ResumeData, tex_path: Path) -> RenderResult:
        self.render_latex(resume, tex_path)
        return XeLatexCompiler().compile(tex_path)

    def _html(self, view: Format2ViewModel) -> str:
        esc = lambda value: html.escape(str(value or ""))
        section = lambda title, body: f'<section><h2>{title}</h2>{body}</section>' if body else ""
        rows = lambda pairs: "".join(f'<div class="row"><span>{key}</span><span>:</span><span>{esc(value or "-")}</span></div>' for key, value in pairs)
        skills = rows((category, ", ".join(items)) for category, items in view.resume.skills.items())
        experience = "".join(
            f'<article>{rows((("Company Name", item.company_name or item.company_sector or item.company), ("Designation", item.title), ("Duration", item.dates)))}'
            f'{f"<ul>{''.join(f'<li>{esc(responsibility)}</li>' for responsibility in item.responsibilities)}</ul>" if item.responsibilities else ""}</article>'
            for item in view.resume.experience
        )
        projects = "".join(f'<article><h3>{view.project_label(index)}</h3>{rows((("Client", project.client), ("Technical Stack", ", ".join(project.technologies)), ("Role", project.role)))}{f"<h4>Description of Project:</h4><p>{esc(project.description)}</p>" if project.description else ""}{f"<h4>Roles and Responsibilities:</h4><ul>{''.join(f'<li>{esc(item)}</li>' for item in project.responsibilities)}</ul>" if project.responsibilities else ""}</article>' for index, project in enumerate(view.projects, 1))
        education = "".join(f"<p>{esc(' '.join(filter(None, (item.degree, item.year, item.institution, item.gpa))))}</p>" for item in view.resume.education)
        summary = "".join(f"<p>{esc(item)}</p>" for item in view.resume.summary.splitlines() if item)
        return f'<main class="resume-page"><h1>{esc(view.name.upper())}</h1>{section("Professional Summary:", summary)}{section("Technical Skills:", skills)}{section("Working Experience:", experience)}{section("Project Summary:", projects)}{section("EDUCATIONAL QUALIFICATION:", education)}{section("Certifications:", "".join(f"<p>{esc(x)}</p>" for x in view.resume.certifications))}{section("Achievements:", "".join(f"<p>{esc(x)}</p>" for x in view.resume.achievements))}</main>'

    def _latex(self, view: Format2ViewModel) -> str:
        lines = [r"\begin{center}\textbf{" + escape_latex(view.name.upper()) + r"}\end{center}"]
        self._section(lines, "Professional Summary:", view.resume.summary.splitlines())
        self._section(lines, "Technical Skills:", [], rows=[(key, ", ".join(value)) for key, value in view.resume.skills.items()])
        if view.resume.experience:
            lines.append(r"\KaniniSection{Working Experience:}")
            for entry in view.resume.experience:
                self._rows(lines, [("Company Name", entry.company_name or entry.company_sector or entry.company), ("Designation", entry.title), ("Duration", entry.dates)])
                self._items(lines, entry.responsibilities)
        if view.projects:
            lines.append(r"\KaniniSection{Project Summary:}")
            for index, project in enumerate(view.projects, 1):
                lines.append(r"\textbf{" + escape_latex(view.project_label(index).upper()) + r"}\par")
                self._rows(lines, [("Client", project.client), ("Technical Stack", ", ".join(project.technologies)), ("Role", project.role)])
                if project.description:
                    lines.extend((r"\textbf{DESCRIPTION OF PROJECT:}\par", escape_latex(project.description) + r"\par"))
                if project.responsibilities:
                    lines.append(r"\textbf{ROLES AND RESPONSIBILITIES:}\par")
                    self._items(lines, project.responsibilities)
        self._section(lines, "EDUCATIONAL QUALIFICATION:", [" ".join(filter(None, (x.degree, x.year, x.institution, x.gpa))) for x in view.resume.education])
        self._section(lines, "Certifications:", view.resume.certifications)
        self._section(lines, "Achievements:", view.resume.achievements)
        return "\n".join(lines)

    def _section(self, lines, title, values, rows=None):
        if not values and not rows: return
        lines.append(r"\KaniniSection{" + title + "}")
        if rows: self._rows(lines, rows)
        else: lines.extend(escape_latex(value) + r"\par" for value in values if value)

    @staticmethod
    def _rows(lines, rows):
        lines.extend(r"\KaniniRow{" + escape_latex(key) + "}{" + escape_latex(value or "-") + "}" for key, value in rows)

    @staticmethod
    def _items(lines, values):
        values = [value for value in values if value]
        if values:
            lines.append(r"\begin{itemize}"); lines.extend(r"\item " + escape_latex(value) for value in values); lines.append(r"\end{itemize}")