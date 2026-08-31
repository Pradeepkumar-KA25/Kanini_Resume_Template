import json
from resume_parser import parse_resume

data = parse_resume('realistic_resume.docx', 'docx')

print('=== CONTACT ===')
print(json.dumps(data['contact'], indent=2))

print('\n=== SKILLS ===')
for cat, items in data['skills'].items():
    print(f'  {cat}: {items}')

print('\n=== EXPERIENCE ===')
for exp in data['experience']:
    print(f'  Title: {exp.get("title")}')
    print(f'  Company: {exp.get("company")}')
    print(f'  Location: {exp.get("location")}')
    print(f'  Dates: {exp.get("dates")}')
    print(f'  Responsibilities ({len(exp.get("responsibilities",[]))}):')
    for r in exp.get('responsibilities', []):
        print(f'    - {r}')
    print()

print('=== EDUCATION ===')
print(json.dumps(data['education'], indent=2))

print('\n=== CERTIFICATIONS ===')
for c in data['certifications']:
    print(f'  - {c}')

print('\n=== PROJECTS ===')
for p in data['projects']:
    print(f'  Name: {p.get("name")}')
    print(f'  Tech: {p.get("technologies")}')
    print(f'  Desc: {p.get("description")}')
    print()
