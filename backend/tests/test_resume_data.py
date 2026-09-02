from models.resume import ResumeData
from services.resume_adapter import ResumeAdapter
from services.resume_normalization import normalise_resume, validate_resume


def test_ai_and_regex_adapters_preserve_supported_fields(normal_resume):
    ai_resume = ResumeAdapter.adapt_ai_output(normal_resume)
    regex_resume = ResumeAdapter.adapt_regex_output(normal_resume)

    for resume in (ai_resume, regex_resume):
        project = resume.projects[0]
        assert project.client == "Contoso"
        assert project.role == "Lead"
        assert project.duration == "2023"
        assert project.responsibilities == ["Designed ingestion"]


def test_normalisation_deduplicates_without_losing_unicode_or_project_fields(normal_resume):
    unicode_technology = "Datenbank \u00fcber"
    normal_resume["projects"][0]["technologies"].append(unicode_technology)
    resume = normalise_resume(ResumeAdapter.from_legacy(normal_resume))

    assert resume.skills["Data"] == ["Python", "SQL"]
    assert resume.projects[0].client == "Contoso"
    assert unicode_technology in resume.projects[0].technologies
    assert resume.experience[0].company_name == "Kanini"


def test_legacy_serialization_matches_existing_contract(normal_resume):
    serialized = ResumeAdapter.to_legacy(ResumeAdapter.from_legacy(normal_resume))

    assert set(serialized) == {"contact", "summary", "skills", "experience", "education", "certifications", "projects", "achievements"}
    assert serialized["projects"][0]["client"] == "Contoso"


def test_optional_sections_are_safe_and_validation_is_clear():
    resume = ResumeData(contact={"email": "candidate@example.com", "phone": "1234567890"})
    assert validate_resume(resume, "sufficient readable source text " * 3) == (True, "")
    assert resume.projects == []
    assert resume.certifications == []


def test_validation_rejects_missing_required_contact():
    valid, reason = validate_resume(ResumeData(), "sufficient readable source text " * 3)
    assert not valid
    assert "email address or phone number" in reason


def test_minimal_resume_is_canonical_and_valid(minimal_resume):
    resume = ResumeAdapter.from_legacy(minimal_resume)
    assert resume.education == []
    assert validate_resume(resume, "sufficient readable source text " * 3) == (True, "")


def test_multiple_companies_and_projects_are_retained(multiple_companies_resume, multiple_projects_resume):
    assert len(ResumeAdapter.from_legacy(multiple_companies_resume).experience) == 2
    assert len(ResumeAdapter.from_legacy(multiple_projects_resume).projects) == 2


def test_optional_sections_long_content_and_large_skills_are_safe(
    missing_optional_sections_resume, long_responsibilities_resume, large_skill_list_resume
):
    assert ResumeAdapter.from_legacy(missing_optional_sections_resume).certifications == []
    assert len(ResumeAdapter.from_legacy(long_responsibilities_resume).experience[0].responsibilities[0]) > 200
    assert len(ResumeAdapter.from_legacy(large_skill_list_resume).skills["Platform"]) == 50


def test_unicode_and_special_characters_round_trip(unicode_special_character_resume):
    serialized = ResumeAdapter.to_legacy(ResumeAdapter.from_legacy(unicode_special_character_resume))
    assert serialized["contact"]["name"] == "Zo\u00eb D\u2019Arcy"
    assert "100% coverage for C# & Python" in serialized["projects"][0]["description"]


def test_adapters_normalise_parser_aliases_without_template_concerns():
    raw = {
        "contact": None,
        "professional_summary": "  Data engineer  ",
        "skills": ["Python", "SQL"],
        "experience": [{"company": "Contoso", "designation": "Engineer", "duration": "2022 - Present"}],
        "projects": [{"project_name": "Warehouse", "technical_stack": "Python, SQL", "roles_and_responsibilities": "Built pipelines"}],
    }
    resume = ResumeAdapter.adapt_ai_output(raw)

    assert resume.summary == "Data engineer"
    assert resume.skills == {"Technical Skills": ["Python", "SQL"]}
    assert resume.experience[0].title == "Engineer"
    assert resume.experience[0].dates == "2022 - Present"
    assert resume.projects[0].name == "Warehouse"
    assert resume.projects[0].technologies == ["Python", "SQL"]
    assert resume.projects[0].responsibilities == ["Built pipelines"]


def test_normaliser_recovers_summary_and_experience_from_pdf_like_text():
    raw_text = """Profile Summary:
Experienced data engineer building reliable platforms.
Technical Skills:
Python, SQL
: Kanini Software Solutions
: Associate Developer
: July 2022 - Till date
Working Experience:
"""
    resume = ResumeAdapter.from_legacy({"contact": {"email": "candidate@example.com", "phone": "1234567890"}, "summary": "", "experience": []})
    normalized = normalise_resume(resume, raw_text=raw_text)

    assert normalized.summary == "Experienced data engineer building reliable platforms."
    assert normalized.experience[0].company == "Kanini Software Solutions"
    assert normalized.experience[0].title == "Associate Developer"
    assert normalized.experience[0].dates == "July 2022 - Till date"


def test_normaliser_removes_existing_skill_and_project_noise(normal_resume):
    normal_resume["skills"] = {"Data:": [" Python ", "Python", "Company Name", "Senior Data Engineer"]}
    normal_resume["projects"] = [{"name": "A, B, C", "client": "Noise", "description": "word " * 50}]
    normalized = normalise_resume(ResumeAdapter.from_legacy(normal_resume))

    assert normalized.skills == {"Data": ["Python"]}
    assert normalized.projects == []