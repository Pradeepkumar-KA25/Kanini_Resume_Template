from resume_parser import parse_resume
from template_generator import generate_preview_html_template1
import re

file_path = "realistic_resume.docx"
file_type = "docx"

result = parse_resume(file_path, file_type)
html1 = generate_preview_html_template1(result)

# Extract sections from HTML
def extract_sections(html):
    # Find all section headers and their positions
    pattern = r'<div class="t1-section-hdr">([^<]+)</div>'
    matches = list(re.finditer(pattern, html))
    
    sections = {}
    for i, match in enumerate(matches):
        section_name = match.group(1)
        start_pos = match.start()
        # Next section starts at the next section header or end of HTML
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(html)
        
        section_content = html[start_pos:end_pos]
        sections[section_name] = section_content
    
    return sections

sections = extract_sections(html1)

print("=" * 80)
print("HTML TEMPLATE 1 - SECTIONS IN ORDER")
print("=" * 80)

for section_name, content in sections.items():
    # Count section content (without section header)
    content_preview = content[:300].replace('\n', ' ')
    content_lines = content.count('<li class="t1-bullet">')
    print(f"\n[{section_name}]")
    print(f"  Items/Rows: {content_lines}")
    print(f"  Preview: {content_preview}...")
    
    # Check for suspicious content
    if "Designed" in content or "Built" in content or "Integrated" in content:
        print(f"  ⚠️  Contains experience/job description verbs")
    if "Spring" in content or "Docker" in content or "AWS" in content:
        print(f"  ✓ Contains technical skills")

# Now show exact section content for Technical Skills and Work Experience
print("\n" + "=" * 80)
print("DETAILED VIEW: Technical Skills vs Work Experience")
print("=" * 80)

if "Technical Skills:" in sections:
    skills_section = sections["Technical Skills:"]
    # Extract just the content part
    content_start = skills_section.find("</div>", skills_section.find("Technical Skills:")) + 6
    content_end = skills_section.find("</div>") if "</div>" in skills_section[content_start:] else len(skills_section)
    print("\n[Technical Skills] Content:")
    print(skills_section[content_start:content_start+500])

if "Work Experience:" in sections:
    exp_section = sections["Work Experience:"]
    content_start = exp_section.find("</div>", exp_section.find("Work Experience:")) + 6
    print("\n[Work Experience] Content:")
    print(exp_section[content_start:content_start+500])
