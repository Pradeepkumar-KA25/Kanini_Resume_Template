import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from template_generator import generate_preview_html_template1

data = {
    'contact': {'name': 'Indira Eswaran', 'email': 'indira@kanini.com',
                'phone': '+91 9876543210', 'location': 'Chennai', 'linkedin': '', 'github': ''},
    'summary': 'Experienced developer. Works with Python. Builds enterprise apps.',
    'skills': {'Programming Languages': ['Python', 'JavaScript'],
               'Other Skills': ['SAP', 'SDLC', 'Talend']},
    'experience': [{'title': 'Engineer', 'company': 'Kanini',
                    'dates': '2020-Present', 'location': '', 'responsibilities': []}],
    'education': [], 'certifications': [], 'projects': [], 'achievements': []
}

html = generate_preview_html_template1(data)
skills_sec = html[html.find('Technical Skills'):html.find('Work Experience')]

print('SKILLS HTML section:')
# Show category headers
for m in re.findall(r't1-skill-cat[^>]*>(.*?)</div>', skills_sec):
    print('  CATEGORY:', repr(m))
# Show each bullet
for m in re.findall(r'<li[^>]*>(.*?)</li>', skills_sec):
    print('  BULLET:  ', repr(m))

print()
# Ensure "Other Skills" only appears once as a category header
other_count = skills_sec.count('Other Skills')
print(f'"Other Skills" appears {other_count} time(s) in skills section')
print('PASS' if other_count == 1 else 'FAIL - still repeated')
