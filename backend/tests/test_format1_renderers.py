from pathlib import Path
import shutil

import pytest
import pymupdf
from docx import Document

from models.resume import ResumeData
from renderers.base import LatexUnavailableError
from renderers.format1_service import Format1RenderService
from renderers.latex_renderer import escape_latex
from renderers.render_service import RendererFactory
from templates.registry import TemplateRegistry


@pytest.fixture
def renderer():
    return Format1RenderService(TemplateRegistry.discover().get("kanini-format-1"))


@pytest.fixture
def format1_resume():
    return ResumeData(
        contact={"name": "Zoë D’Arcy", "email": "zoe@example.com", "phone": "+91 90000 00000"},
        summary="Built resilient C# & Python data services." * 8,
        skills={"Data": ["Python", "SQL", "Spark"]},
        experience=[{"company": "Kanini", "title": "Senior Data Engineer", "dates": "2022 - Present", "responsibilities": ["Built reliable pipelines."]}],
        projects=[{"name": "Data Platform", "client": "Contoso", "role": "Lead", "description": "A long project description " * 10, "technologies": ["Python", "SQL"], "responsibilities": ["Delivered 100% coverage."]}],
        education=[{"degree": "B.Tech", "institution": "Example University", "year": "2020"}],
    )


def test_format1_renderer_factory_uses_registry_alias():
    factory = RendererFactory(TemplateRegistry.discover())
    assert factory.get("template1").template_id == "kanini-format-1"
    assert factory.supports("template2")


def test_escape_latex_handles_all_sensitive_characters():
    assert escape_latex("&%$#_{}~^\\") == r"\&\%\$\#\_\{\}\textasciitilde{}\textasciicircum{}\textbackslash{}"


def test_format1_html_contains_expected_sections_and_print_css(renderer, format1_resume):
    html = renderer.render_html(format1_resume).content or ""
    assert "@page { size: letter" in html
    assert "Project I:" in html
    assert "Work Experience" in html
    assert "C# &amp; Python" in html


def test_format1_docx_is_valid_and_contains_expected_sections(renderer, format1_resume, tmp_path: Path):
    result = renderer.render_docx(format1_resume, tmp_path / "format1.docx")
    text = "\n".join(paragraph.text for paragraph in Document(result.path).paragraphs)
    assert result.path and result.path.stat().st_size > 0
    assert "PROJECT SUMMARY" in text
    assert "EDUCATIONAL QUALIFICATION" in text


def test_format1_latex_renders_data_and_omits_empty_optional_sections(renderer, format1_resume, tmp_path: Path):
    result = renderer.render_latex(format1_resume, tmp_path / "format1.tex")
    source = result.path.read_text(encoding="utf-8")
    assert "ZOË D’ARCY" in source
    assert r"C\# \& Python" in source
    assert "Certifications" not in source
    assert (tmp_path / "sections.tex").exists()


def test_latex_unavailable_is_controlled(renderer, format1_resume, tmp_path: Path, monkeypatch):
    monkeypatch.setattr("renderers.latex_renderer.shutil.which", lambda _: None)
    with pytest.raises(LatexUnavailableError, match="XeLaTeX is not available"):
        renderer.render_pdf(format1_resume, tmp_path / "format1.tex")


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="XeLaTeX is not installed")
@pytest.mark.parametrize(
    "case_data",
    [
        {},
        {"summary": "Normal resume content."},
        {"summary": "Long summary content. " * 120},
        {"experience": [{"company": "One", "title": "Engineer"}, {"company": "Two", "title": "Lead"}]},
        {"projects": [{"name": "One"}, {"name": "Two"}]},
        {"skills": {"Platform": [f"Skill {index}" for index in range(60)]}},
        {"experience": [{"company": "Contoso", "title": "Engineer", "responsibilities": ["Long responsibility. " * 100]}]},
        {"certifications": [], "achievements": [], "education": [], "projects": []},
        {"summary": "Zoë D’Arcy delivered analytics in München."},
        {"summary": "Characters: & % $ # _ { } ~ ^ \\"},
    ],
)
def test_format1_pdf_edge_cases_compile_without_clipping(renderer, tmp_path: Path, case_data):
    base = {
        "contact": {"name": "Candidate Name"},
        "summary": "Base summary.",
        "skills": {"Data": ["Python"]},
        "experience": [{"company": "Contoso", "title": "Data Engineer", "dates": "2022 - Present"}],
        "projects": [{"name": "Platform", "client": "Northwind"}],
        "education": [{"degree": "B.Tech", "institution": "Example University", "year": "2020"}],
    }
    base.update(case_data)
    result = renderer.render_pdf(ResumeData(**base), tmp_path / "case.tex")
    document = pymupdf.open(result.path)

    assert len(document) >= 1
    for page in document:
        assert page.rect.width == pytest.approx(612.0)
        assert page.rect.height == pytest.approx(792.0)
        assert page.get_image_info(xrefs=True)
        for block in page.get_text("blocks"):
            assert block[0] >= 0
            assert block[2] <= page.rect.width + 0.1
            assert block[3] <= page.rect.height + 0.1