from resume_parser import extract_text, split_sections
import json

# Test with an existing resume
file_path = "realistic_resume.docx"
file_type = "docx"

try:
    raw_text = extract_text(file_path, file_type)
    print("=== RAW TEXT (first 1500 chars) ===")
    print(raw_text[:1500])
    print("\n=== SECTIONS ===")
    sections = split_sections(raw_text)
    for section_name, lines in sections.items():
        print(f"\n[{section_name}] ({len(lines)} lines)")
        for i, line in enumerate(lines[:15]):  # first 15 lines of each section
            print(f"  {i}: {repr(line[:80])}")
except FileNotFoundError:
    print("Test file not found")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
