from __future__ import annotations

import html

from models.resume import ResumeData
from models.template_spec import TemplateSpec


def render_template_draft_preview(resume: ResumeData, spec: TemplateSpec) -> str:
    """Render user-template previews from validated data only, with no executable content."""
    rendered_sections = [(name, _section(name, resume, spec)) for name in spec.sections]
    rendered_sections = [(name, content) for name, content in rendered_sections if content]
    header = _header(resume, spec)
    layout = _layout(rendered_sections, spec)
    return f"<style>{_style(spec)}</style><main class=\"generated-resume columns-{spec.layout.columns} sidebar-{spec.layout.sidebar_position}\">{header}{layout}</main>"


def _style(spec: TemplateSpec) -> str:
    page_width = "210mm" if spec.page.size == "A4" else "8.5in"
    page_height = "297mm" if spec.page.size == "A4" else "11in"
    divider = "none" if spec.spacing.divider_style == "none" else f"1px solid {spec.colors.accent if spec.spacing.divider_style == 'accent' else spec.colors.muted}"
    return (
        "*{box-sizing:border-box}.generated-resume{"
        f"width:min(100%,{page_width});min-height:{page_height};margin:0 auto;padding:{spec.page.margin_inches}in;background:#fff;color:{spec.colors.text};"
        f"font-family:{spec.typography.font_family},sans-serif;font-size:{spec.typography.base_size_pt}pt;line-height:{spec.spacing.line_height};overflow-wrap:anywhere;}}"
        f".template-header{{text-align:{spec.header.layout};border-bottom:{divider};padding-bottom:{spec.spacing.section_gap_pt}pt;margin-bottom:{spec.spacing.section_gap_pt}pt;}}"
        ".template-header h1{margin:0;color:#000000;font-size:12pt;font-weight:700;line-height:1.2;text-transform:uppercase}.contact-inline{display:flex;flex-wrap:wrap;gap:3pt 8pt;margin-top:5pt}.contact-stacked{display:grid;gap:2pt;margin-top:5pt}.contact-item{min-width:0}.template-layout{display:grid;gap:"
        f"{spec.spacing.section_gap_pt}pt;}}.template-column{{display:grid;align-content:start;gap:{spec.spacing.section_gap_pt}pt;min-width:0;}}"
        f".template-section{{min-width:0;text-align:{spec.layout.section_alignment};break-inside:avoid;}}.template-section h2{{margin:0 0 4pt;color:#000000;font-size:12pt;font-weight:700;line-height:1.2;text-transform:uppercase;}}"
        ".template-section p{margin:0 0 4pt}.entry{margin:0 0 8pt;break-inside:avoid}.entry:last-child{margin-bottom:0}.entry-meta{margin-bottom:3pt}.template-section ul{margin:3pt 0 0 18pt;padding:0}.template-section li{margin-bottom:2pt}.skill-tags{display:flex;flex-wrap:wrap;gap:4pt}.skill-tags span{max-width:100%;padding:2pt 5pt;border:1px solid currentColor;border-radius:3pt;overflow-wrap:anywhere}.columns-2 .template-layout{grid-template-columns:minmax(0,.8fr) minmax(0,2fr);grid-template-areas:'sidebar main'}.sidebar-left .template-sidebar{grid-area:sidebar}.sidebar-left .template-main{grid-area:main}.sidebar-right .template-layout{grid-template-areas:'main sidebar'}.sidebar-right .template-sidebar{grid-area:sidebar}.sidebar-right .template-main{grid-area:main}@media(max-width:640px){.generated-resume{padding:18pt}.columns-2 .template-layout,.sidebar-right .template-layout{grid-template-columns:1fr;grid-template-areas:'sidebar' 'main'}}"
    )


def _header(resume: ResumeData, spec: TemplateSpec) -> str:
    parts = [value for value in (resume.contact.email, resume.contact.phone, resume.contact.location, resume.contact.linkedin, resume.contact.github) if value]
    contact_class = "contact-stacked" if spec.header.contact_layout == "stacked" else "contact-inline"
    contacts = f"<div class=\"{contact_class}\">{''.join(f'<span class=\"contact-item\">{_escape(value)}</span>' for value in parts)}</div>" if parts else ""
    return f"<header class=\"template-header\"><h1>{_escape(resume.contact.name or 'Candidate Name')}</h1>{contacts}</header>"


def _layout(rendered_sections: list[tuple[str, str]], spec: TemplateSpec) -> str:
    if spec.layout.columns == 1:
        return f"<div class=\"template-layout\"><div class=\"template-column template-main\">{''.join(content for _, content in rendered_sections)}</div></div>"

    sidebar_sections = {"skills", "education", "certifications", "achievements"}
    sidebar = [(name, content) for name, content in rendered_sections if name in sidebar_sections]
    main = [(name, content) for name, content in rendered_sections if name not in sidebar_sections]
    if not sidebar or not main:
        return f"<div class=\"template-layout\"><div class=\"template-column template-main\">{''.join(content for _, content in rendered_sections)}</div></div>"
    return (
        f"<div class=\"template-layout\"><aside class=\"template-column template-sidebar\">{''.join(content for _, content in sidebar)}</aside>"
        f"<div class=\"template-column template-main\">{''.join(content for _, content in main)}</div></div>"
    )


def _section(name: str, resume: ResumeData, spec: TemplateSpec) -> str:
    title = name.replace("_", " ").title()
    if name == "summary": body = "".join(f"<p>{_escape(line)}</p>" for line in resume.summary.splitlines() if line)
    elif name == "skills": body = _skills(resume, spec)
    elif name == "experience": body = "".join(_experience(item) for item in resume.experience)
    elif name == "projects": body = "".join(_project(item) for item in resume.projects)
    elif name == "education": body = "".join(f"<p>{_escape(' | '.join(part for part in (item.degree, item.institution, item.year) if part))}</p>" for item in resume.education)
    elif name == "certifications": body = _list(resume.certifications)
    elif name == "achievements": body = _list(resume.achievements)
    else: body = ""
    return f"<section class=\"template-section\"><h2>{title}</h2>{body}</section>" if body else ""


def _experience(item) -> str:
    details = [item.title, item.company_name or item.company, item.dates, item.location]
    meta = " | ".join(_escape(value) for value in details if value)
    body = f"<p class=\"entry-meta\"><strong>{meta}</strong></p>" if meta else ""
    body += _list(item.responsibilities)
    return f"<article class=\"entry\">{body}</article>" if body else ""


def _project(item) -> str:
    details = [item.name, item.client, item.role, item.duration]
    meta = " | ".join(_escape(value) for value in details if value)
    description = f"<p>{_escape(item.description)}</p>" if item.description else ""
    body = f"<p class=\"entry-meta\"><strong>{meta}</strong></p>" if meta else ""
    body += description + _list(item.responsibilities)
    return f"<article class=\"entry\">{body}</article>" if body else ""


def _skills(resume: ResumeData, spec: TemplateSpec) -> str:
    values = [f"{category}: {', '.join(items)}" for category, items in resume.skills.items()]
    if not values:
        return ""
    if spec.spacing.skill_style == "tags": return f"<div class=\"skill-tags\">{''.join(f'<span>{_escape(value)}</span>' for value in values)}</div>"
    if spec.spacing.skill_style == "bullets": return _list(values)
    return "".join(f"<p>{_escape(value)}</p>" for value in values)


def _list(values: list[str]) -> str:
    return f"<ul>{''.join(f'<li>{_escape(value)}</li>' for value in values if value)}</ul>" if values else ""


def _escape(value: str) -> str:
    return html.escape(str(value or ""))
