from resume_parser import parse_resume
import json

file_path = "realistic_resume.docx"
file_type = "docx"

result = parse_resume(file_path, file_type)
print("=== SKILLS ===")
print(json.dumps(result["skills"], indent=2))
print("\n=== EXPERIENCE ===")
for i, exp in enumerate(result["experience"]):
    print(f"\n[Experience {i+1}]")
    print(f"  Company: {exp.get('company')}")
    print(f"  Title: {exp.get('title')}")
    print(f"  Dates: {exp.get('dates')}")
    print(f"  Responsibilities (first 2): {exp.get('responsibilities', [])[:2]}")
