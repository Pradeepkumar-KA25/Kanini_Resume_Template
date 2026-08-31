from resume_parser import parse_resume
from template_generator import generate_preview_html_template1, generate_preview_html_template2

data = parse_resume('realistic_resume.docx', 'docx')
h1 = generate_preview_html_template1(data)
h2 = generate_preview_html_template2(data)
print('Template1 HTML length:', len(h1))
print('Template2 HTML length:', len(h2))
print()
print('--- TEMPLATE 1 (first 2000 chars) ---')
print(h1[:2000])
print()
print('--- TEMPLATE 2 (first 2000 chars) ---')
print(h2[:2000])
