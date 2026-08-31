from resume_parser import parse_resume
from template_generator import generate_preview_html_template1, generate_preview_html_deloitte
import json

file_path = "realistic_resume.docx"
file_type = "docx"

# Parse the resume
result = parse_resume(file_path, file_type)

print("=" * 60)
print("PARSED DATA STRUCTURE")
print("=" * 60)
print("\n[CONTACT]")
print(json.dumps(result["contact"], indent=2))

print("\n[SUMMARY]")
print(result["summary"][:150] + "...")

print("\n[SKILLS] - Keys and item counts")
for cat, items in result["skills"].items():
    print(f"  {cat}: {items}")

print("\n[EXPERIENCE]")
for i, exp in enumerate(result["experience"]):
    print(f"\n  [{i+1}] {exp.get('company')} - {exp.get('title')}")
    print(f"      Dates: {exp.get('dates')}")
    print(f"      Responsibilities: {len(exp.get('responsibilities', []))} items")

print("\n[PROJECTS]")
for i, proj in enumerate(result["projects"]):
    print(f"  [{i+1}] {proj.get('name')} ({proj.get('client')})")

print("\n[EDUCATION]")
for edu in result["education"]:
    print(f"  {edu}")

print("\n[CERTIFICATIONS]")
for cert in result["certifications"]:
    print(f"  {cert}")

print("\n" + "=" * 60)
print("TEMPLATE 1 (KANINI CLASSIC) HTML PREVIEW")
print("=" * 60)
html1 = generate_preview_html_template1(result)
# Count sections
sections_in_html = [
    ("Work Experience", html1.count("Work Experience:")),
    ("Technical Skills", html1.count("Technical Skills:")),
    ("Professional Summary", html1.count("Professional Summary:")),
    ("Project Summary", html1.count("Project Summary:")),
    ("Education", html1.count("EDUCATIONAL")),
    ("Certifications", html1.count("Certifications:")),
]
print("\nSections found in HTML1:")
for section, count in sections_in_html:
    print(f"  {section}: {count}x")

# Check if experience content appears in skills section
exp_content_in_skills = "Designed" in html1 and html1.find("Technical Skills") < html1.find("Designed")
print(f"\nExperience content in Skills section: {exp_content_in_skills}")

print("\n" + "=" * 60)
print("TEMPLATE 2 (DELOITTE) HTML PREVIEW")
print("=" * 60)
html2 = generate_preview_html_deloitte(result)
# Count sections
sections_in_html2 = [
    ("Working Experience", html2.count("Working Experience:")),
    ("Technical Skills", html2.count("Technical Skills:")),
    ("Professional Summary", html2.count("Professional Summary:")),
    ("Project Summary", html2.count("Project Summary:")),
]
print("\nSections found in HTML2:")
for section, count in sections_in_html2:
    print(f"  {section}: {count}x")

# Show first part of each template
print("\nFirst 500 chars of HTML1:")
print(html1[:500])
print("\n" + "-" * 60)
print("First 500 chars of HTML2:")
print(html2[:500])
