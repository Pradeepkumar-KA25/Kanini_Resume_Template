import json

from models.resume import ResumeData
from models.template_spec import TemplateSpec
from renderers.template_draft_renderer import render_template_draft_preview
from renderers.user_template_service import UserTemplateRenderService
from templates.registry.metadata import TemplateMetadata
from tests.test_template_generation import VALID_SPEC


def _spec(**changes):
    payload = {**VALID_SPEC, **changes}
    return TemplateSpec.model_validate(payload)


def test_same_template_renders_different_resume_data(normal_resume):
    spec = _spec()
    first = render_template_draft_preview(ResumeData.model_validate(normal_resume), spec)
    second_data = {**normal_resume, "contact": {"name": "Sam Lee", "email": "sam@example.com", "phone": "1234567890"}, "summary": "Product-focused engineer."}
    second = render_template_draft_preview(ResumeData.model_validate(second_data), spec)
    assert "Riya Raman" in first
    assert "Sam Lee" in second
    assert "Product-focused engineer." in second
    assert "Riya Raman" not in second


def test_long_entries_and_multiple_projects_wrap_without_fixed_content_height(normal_resume):
    normal_resume["experience"] = [{"company": "Contoso", "title": "Staff Engineer", "dates": "2020 - Present", "responsibilities": ["Long responsibility " * 180]}]
    normal_resume["projects"] = [
        {"name": f"Project {index}", "description": "Long project description " * 100, "responsibilities": ["Delivered work"]}
        for index in range(3)
    ]
    html = render_template_draft_preview(ResumeData.model_validate(normal_resume), _spec(sections=["experience", "projects"]))
    assert html.count('class="entry"') == 4
    assert "height:760" not in html
    assert "overflow-wrap:anywhere" in html
    assert "Project 2" in html


def test_missing_sections_do_not_render_empty_headings():
    resume = ResumeData(contact={"name": "Minimal Candidate"})
    html = render_template_draft_preview(resume, _spec(sections=["summary", "skills", "experience", "projects", "education", "certifications", "achievements"]))
    assert "Minimal Candidate" in html
    assert "<h2>" not in html


def test_single_column_layout_preserves_requested_section_order(normal_resume):
    html = render_template_draft_preview(ResumeData.model_validate(normal_resume), _spec(sections=["education", "summary", "skills"]))
    assert 'class="template-column template-sidebar"' not in html
    assert html.index("Education") < html.index("Summary") < html.index("Skills")


def test_two_column_layout_uses_sidebar_and_main_content(normal_resume):
    layout = {"columns": 2, "sidebar_position": "right", "section_alignment": "left"}
    html = render_template_draft_preview(ResumeData.model_validate(normal_resume), _spec(layout=layout, sections=["summary", "skills", "experience", "education", "certifications"]))
    assert "template-sidebar" in html
    assert "sidebar-right" in html
    assert "grid-template-areas:'main sidebar'" in html
    assert "Experience" in html and "Skills" in html


def test_draft_and_saved_user_template_use_identical_rendering(normal_resume, tmp_path):
    spec = _spec()
    package = tmp_path / "user-consistent"
    package.mkdir()
    (package / "template-spec.json").write_text(json.dumps(spec.model_dump()), encoding="utf-8")
    metadata = TemplateMetadata(id="user-consistent", display_name="Consistent", description="Test", version="1.0", enabled=True, supported_outputs=["html"], page_size="A4", user_created=True)
    resume = ResumeData.model_validate(normal_resume)
    draft_html = render_template_draft_preview(resume, spec)
    saved_html = UserTemplateRenderService(metadata, package).render_html(resume).content
    assert saved_html == draft_html