from template_generator import generate_template1, generate_template_deloitte, generate_preview_html_template1, generate_preview_html_deloitte

data = {
    'contact': {'name': 'Indira Eswaran', 'phone': '9360380740', 'email': 'IndiraE2001@gmail.com'},
    'summary': '2 years of experience in development using Microsoft Technologies. Proficiency in React JS, Redux, HTML, CSS, JavaScript, C#, .NET. Quick learner and excellent team player.',
    'skills': {
        'Programming': ['React JS', 'Redux', 'HTML', 'CSS', 'JavaScript', 'C#', '.NET'],
        'Relational Databases': ['MS SQL Server'],
        'Integrated Development Environments': ['MS Visual Studio'],
        'Architecture': ['N-Tier', 'Client Server']
    },
    'experience': [{
        'title': 'Junior Associate',
        'company': 'KANINI SOFTWARE SOLUTIONS',
        'dates': 'July 2022 - Till date',
        'responsibilities': [
            'Analyze the software requirement by the customer and develop the application.',
            'Developed Test Cases and Unit Testing to identify and resolve issues.',
            'Assist and support other team members on multiple projects.',
            'Drive team members to keep up with project deadlines.',
            'Implement best practices and procedures.'
        ]
    }],
    'projects': [{
        'name': 'Deloitte - ESG',
        'description': 'ESG which stands for Environmental Social and Governance refers to evaluation of a company performance.',
        'technologies': ['React', 'Redux', 'JavaScript', 'CSS', 'Azure', 'C# .Net', 'HTML', 'SQL']
    }],
    'education': [{'degree': 'BE', 'year': '2022', 'institution': 'Erode Sengunthur Engineering College'}],
    'certifications': [],
    'achievements': []
}

generate_template1(data, 'test_kanini_classic.docx')
print('Template 1 (Kanini Format ) - OK')

generate_template_deloitte(data, 'test_kanini_profile.docx')
print('Template 2 (Kanini Profile Format) - OK')

h1 = generate_preview_html_template1(data)
h2 = generate_preview_html_deloitte(data)
print('HTML1 length:', len(h1))
print('HTML2 uses kf classes:', 'kf-resume' in h2)
print('Skills all-bold:', '<strong>Programming:' in h1 and 'Programming: React' in h1)
print('Project Summary combined header:', 'Project Summary:' in h1)
print('Project I in header:', 'Project I:' in h1)
print('Role/Company shows:', 'Junior Associate | KANINI' in h1)
print('Deloitte ESG client:', 'Deloitte - ESG' in h2)
print('Project dash em:', 'Project &ndash; I' in h2)
print('All checks passed.')
