import requests, json

with open('realistic_resume.docx', 'rb') as f:
    r = requests.post('http://localhost:8000/api/upload', files={'file': ('realistic_resume.docx', f)})

data = r.json()
print('Status:', r.status_code)
rd = data['resume_data']
print('Name:', rd['contact']['name'])
print('Experience count:', len(rd['experience']))
for exp in rd['experience']:
    print('  Title:', exp['title'])
    print('  Company:', exp['company'])
    print('  Location:', exp['location'])
    print('  Dates:', exp['dates'])
    print()
print('Education:')
for e in rd['education']:
    print(' ', e['degree'], '|', e['institution'], '|', e['year'])
print('Skills categories:', list(rd['skills'].keys()))
print('Certs:', rd['certifications'])
print('Projects:', [p['name'] for p in rd['projects']])
