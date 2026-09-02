import pytest


@pytest.fixture
def normal_resume():
    return {
        "contact": {"name": "Riya Raman", "email": "riya@example.com", "phone": "+91 90000 00000"},
        "summary": "Senior data engineer with platform and analytics experience.",
        "skills": {"Data": ["Python", "SQL", "Python"]},
        "experience": [{"company": "Kanini", "title": "Data Engineer", "dates": "2022 - Present", "responsibilities": ["Built pipelines"]}],
        "education": [{"degree": "B.Tech", "institution": "Example University", "year": "2020"}],
        "certifications": ["Azure Data Engineer"],
        "projects": [{"name": "Data Platform", "client": "Contoso", "role": "Lead", "duration": "2023", "description": "Platform delivery", "technologies": ["Python", "Spark"], "responsibilities": ["Designed ingestion"]}],
        "achievements": ["Reduced processing time"],
    }


@pytest.fixture
def minimal_resume():
    return {"contact": {"email": "minimal@example.com", "phone": "1234567890"}}


@pytest.fixture
def multiple_companies_resume(normal_resume):
    normal_resume["experience"].append(
        {"company": "Contoso", "title": "Engineer", "dates": "2020 - 2022", "responsibilities": ["Maintained services"]}
    )
    return normal_resume


@pytest.fixture
def multiple_projects_resume(normal_resume):
    normal_resume["projects"].append(
        {"name": "Analytics", "client": "Fabrikam", "role": "Engineer", "technologies": ["SQL"], "responsibilities": ["Built reports"]}
    )
    return normal_resume


@pytest.fixture
def missing_optional_sections_resume(normal_resume):
    for key in ("education", "certifications", "projects", "achievements"):
        normal_resume.pop(key)
    return normal_resume


@pytest.fixture
def long_responsibilities_resume(normal_resume):
    normal_resume["experience"][0]["responsibilities"] = ["Built resilient data-processing services with observability, validation, recovery, and stakeholder reporting across a distributed platform." * 3]
    return normal_resume


@pytest.fixture
def large_skill_list_resume(normal_resume):
    normal_resume["skills"] = {"Platform": [f"Skill {index}" for index in range(50)]}
    return normal_resume


@pytest.fixture
def unicode_special_character_resume(normal_resume):
    normal_resume["contact"]["name"] = "Zo\u00eb D\u2019Arcy"
    normal_resume["projects"][0]["description"] = "Delivered 100% coverage for C# & Python systems in M\u00fcnchen."
    return normal_resume