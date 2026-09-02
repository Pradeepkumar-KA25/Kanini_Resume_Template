from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from models.resume import ResumeData
from renderers.format1_view_model import Format1ViewModel

def apply_format1_page_setup(section) -> None:
    section.page_width = Cm(21.59)
    section.page_height = Cm(27.94)
    section.top_margin = Cm(2.96)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def set_times(run, bold: bool = False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = bold
    if bold:
        run.font.color.rgb = RGBColor(0, 0, 0)


def render(resume: ResumeData, output_path: Path, logo_path: Path | None = None) -> Path:
    document = Document()
    section = document.sections[0]
    apply_format1_page_setup(section)
    if logo_path and logo_path.exists():
        header = section.header
        run = header.paragraphs[0].add_run()
        run.add_picture(str(logo_path), width=Cm(3.33))
    view = Format1ViewModel(resume)
    _paragraph(document, view.name.upper(), bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    if view.contact_parts:
        _paragraph(document, " | ".join(view.contact_parts))
    _section(document, "Profile Summary", [resume.summary] if resume.summary else [])
    _section(document, "Technical Skills", [f"{category}: {', '.join(items)}" for category, items in resume.skills.items()])
    _experience(document, resume)
    _projects(document, view)
    _section(document, "Educational Qualification", [" ".join(filter(None, (item.degree, f"({item.year})" if item.year else "", f"from {item.institution}" if item.institution else "", f"GPA: {item.gpa}" if item.gpa else ""))) for item in resume.education])
    _section(document, "Certifications", resume.certifications)
    _section(document, "Achievements", resume.achievements)
    document.save(output_path)
    return output_path


def _paragraph(document, text: str, bold: bool = False, alignment=None):
    paragraph = document.add_paragraph()
    if alignment is not None:
        paragraph.alignment = alignment
    set_times(paragraph.add_run(text), bold=bold)
    return paragraph


def _section(document, heading: str, items: list[str]) -> None:
    if not items:
        return
    _paragraph(document, heading.upper(), bold=True)
    for item in items:
        _paragraph(document, item)


def _experience(document, resume: ResumeData) -> None:
    if not resume.experience:
        return
    _paragraph(document, "WORK EXPERIENCE", bold=True)
    for entry in resume.experience:
        table = document.add_table(rows=0, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        for label, value in (("Company Name", entry.company_name or entry.company), ("Designation", entry.title), ("Duration", entry.dates)):
            cells = table.add_row().cells
            _cell(cells[0], label)
            _cell(cells[1], ":")
            _cell(cells[2], value or "-")
        for responsibility in entry.responsibilities:
            _paragraph(document, responsibility)


def _projects(document, view: Format1ViewModel) -> None:
    if not view.projects:
        return
    _paragraph(document, "PROJECT SUMMARY", bold=True)
    for index, project in enumerate(view.projects, start=1):
        _paragraph(document, (view.project_label(index) + ":").upper(), bold=True)
        _paragraph(document, project.name.upper(), bold=True)
        for label, value in (("Client", project.client), ("Technologies", ", ".join(project.technologies)), ("Description", project.description)):
            if value:
                _paragraph(document, f"{label}: {value}")
        if project.responsibilities:
            _paragraph(document, "ROLES AND RESPONSIBILITIES:", bold=True)
            for responsibility in project.responsibilities:
                _paragraph(document, responsibility)


def _cell(cell, text: str) -> None:
    cell.paragraphs[0].clear()
    set_times(cell.paragraphs[0].add_run(text))