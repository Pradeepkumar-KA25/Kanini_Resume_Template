# Kanini Resume Builder — POC Documentation

**Project Type:** Internal Proof of Concept (POC)  
**Prepared by:** Kanini Software Solutions  
**Date:** July 2026

---

## 1. Overview

The **Kanini Resume Builder** is a web application that automatically converts any uploaded resume (PDF or Word) into two standardised, professionally formatted Word documents:

| Template                         | Format                               | Purpose                                   |
| -------------------------------- | ------------------------------------ | ----------------------------------------- |
| **Template 1 — Kanini Format **  | Matches `Sample KANINI Profile.docx` | Internal Kanini standard format           |
| **Template 2 — Deloitte Format** | Matches `Kanini Format .docx` | Client submission format (e.g., Deloitte) |

The application uses **OpenAI GPT-4o-mini** to intelligently parse and extract all resume sections, then populates both templates accurately.

---

## 2. How It Works — End-to-End Flow

```
User uploads PDF / DOCX resume
        │
        ▼
Backend extracts raw text
        │
        ▼
OpenAI GPT-4o-mini parses text → structured JSON
  (contact, summary, skills, experience, education, projects)
        │
        ▼
Two Word documents are generated:
  • kanini_classic.docx    (Template 1)
  • deloitte_format.docx   (Template 2)
        │
        ▼
HTML previews rendered in browser (side-by-side)
        │
        ▼
User downloads either template as .docx or .pdf
```

---

## 3. Technology Stack

| Layer               | Technology         | Version      |
| ------------------- | ------------------ | ------------ |
| **Frontend**        | Angular            | 19           |
| **Backend**         | Python / FastAPI   | 3.14 / 0.104 |
| **AI Parsing**      | OpenAI GPT-4o-mini | API v1       |
| **Word Generation** | python-docx        | 1.1.0        |
| **PDF Parsing**     | pdfminer.six       | 20221105     |
| **DOCX Reading**    | docx2txt           | 0.8          |
| **Dev Server**      | Uvicorn            | 0.24         |

---

## 4. Project Structure

```
Kanini_Template_POC/
│
├── backend/                        ← Python / FastAPI backend
│   ├── main.py                     ← API routes (upload, download, health)
│   ├── ai_parser.py                ← OpenAI GPT integration
│   ├── resume_parser.py            ← Regex fallback parser
│   ├── template_generator.py       ← Word doc + HTML preview generators
│   ├── requirements.txt            ← Python dependencies
│   └── .env                        ← API key (OPENAI_API_KEY)
│
├── frontend-ng/                    ← Angular 19 frontend
│   └── src/app/
│       ├── components/
│       │   ├── file-upload/        ← Drag & drop upload UI
│       │   ├── loading-view/       ← Processing spinner
│       │   ├── results-view/       ← Side-by-side template previews
│       │   └── template-card/      ← Individual template preview + download
│       ├── services/
│       │   └── resume.service.ts   ← HTTP calls to backend API
│       └── models/
│           └── resume.model.ts     ← TypeScript interfaces
│
├── setup.bat                       ← One-click environment setup
└── start.bat                       ← Start both servers
```

---

## 5. API Endpoints

| Method | Endpoint                                   | Description                                         |
| ------ | ------------------------------------------ | --------------------------------------------------- |
| `GET`  | `/api/health`                              | Backend health check                                |
| `POST` | `/api/upload`                              | Upload resume → returns parsed data + HTML previews |
| `GET`  | `/api/download/{session}/{template}/{fmt}` | Download generated file (docx or pdf)               |

### Upload Response Schema

```json
{
  "session_id": "uuid",
  "resume_data": {
    "contact":        { "name", "email", "phone", "location", "linkedin" },
    "summary":        "Professional summary text",
    "skills":         { "Category": ["skill1", "skill2"] },
    "experience":     [{ "title", "company", "dates", "responsibilities": [] }],
    "education":      [{ "degree", "institution", "year" }],
    "certifications": [],
    "projects":       [{ "name", "description", "technologies": [] }],
    "achievements":   []
  },
  "preview_html": {
    "template1": "<html string>",
    "template2": "<html string>"
  }
}
```

---

## 6. AI Parsing — OpenAI Integration

**File:** `backend/ai_parser.py`

- Uses **GPT-4o-mini** with `response_format: json_object` for reliable structured output
- Sends up to 14,000 characters of resume text per request
- Returns the exact same data schema as the regex parser so both are interchangeable
- **Fallback chain:**
  1. If `OPENAI_API_KEY` is set → use GPT-4o-mini
  2. If AI fails → fall back to regex parser (`resume_parser.py`)
  3. If regex also fails → return HTTP 422 error to user

**API Key configuration:** Add your key to `backend/.env`:

```
OPENAI_API_KEY=sk-...your-key...
```

---

## 7. Template Formats

### Template 1 — Kanini Format 

Matches the exact structure of `Sample KANINI Profile.docx`:

```
CANDIDATE NAME  (bold, 14pt, Calibri)
Mobile No: xxx  |  Email Id: xxx

Profile Summary  (bold header)
  • Summary bullet 1
  • Summary bullet 2

Technical Skills:  (bold header)
  • Category: skill1, skill2, skill3  (entire line bold)

Work Experience:  (bold header)

  ┌─────────────────┬────────────────────────┐
  │ Company Name    │ : Company Name         │
  │ Designation     │ : Job Title            │
  │ Duration        │ : Jan 2020 – Present   │
  └─────────────────┴────────────────────────┘

Project Summary:

Project I:
  (line break)
  Job Title | Company Name
  Roles and Responsibilities:
  (line break)
  • Responsibility 1
  • Responsibility 2

Educational Qualification:  (bold header)
  Degree (Year) from Institution
```

### Template 2 — Deloitte Format (Kanini Profile Format)

Matches the exact structure of `Kanini Format .docx`:

```
                                     CANDIDATE NAME  (right-aligned, 10pt, bold)

Professional Summary:   ← Heading 1 style
(blank line)
Summary sentence 1.
Summary sentence 2.

Technical Skills:   ← Heading 1 style
(blank line)
Programming         : React JS, JavaScript, C#, .NET
Databases           : MS SQL Server
Tools               : MS Visual Studio

Working Experience:   ← Heading 1 style
(blank line)
Company Name        : KANINI SOFTWARE SOLUTIONS
Designation         : Junior Associate
Duration            : July 2022 - Till date

Project Summary:   ← Heading 1 style
(blank line)
Project – I  (bold)
Client              : Deloitte - ESG
Technologies        : React, Redux, JavaScript, CSS, Azure
Role                : Developer

Description of Project:   ← Heading 1 style
ESG stands for Environmental, Social, and Governance...

Roles and Responsibilities:   ← Heading 1 style
Analyze the software requirement by the customer...
Developed Test Cases and Unit Testing...

EDUCATIONAL QUALIFICATION:   ← Heading 1 style
(blank line)
BE (2022) from Erode Sengunthur Engineering College
```

---

## 8. Supported Input Formats

| Format     | Extension | Parser       |
| ---------- | --------- | ------------ |
| PDF        | `.pdf`    | pdfminer.six |
| Word 2007+ | `.docx`   | docx2txt     |

**Constraints:**

- Maximum file size: **10 MB**
- Text must be selectable (scanned/image PDFs are not supported)

---

## 9. Frontend Features

- **Drag & drop** or click-to-browse file upload
- **Real-time processing** indicator with status steps
- **Side-by-side preview** of both templates, scaled to fit screen
- Candidate name displayed in each template card header
- **One-click download** as `.docx` (Word) or `.pdf`
- Responsive layout (stacks to single column on mobile)

---

## 10. Setup & Running

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

### Quick Start

```bash
# First time setup
setup.bat

# Start both servers
start.bat
```

### Manual Start

**Backend:**

```bash
cd backend
python -m uvicorn main:app --port 8000
```

**Frontend:**

```bash
cd frontend-ng
ng serve --port 4200
```

**Application URL:** `http://localhost:4200`

---

## 11. Key Dependencies

```
# Backend
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
python-docx==1.1.0        # Word document generation
pdfminer.six==20221105    # PDF text extraction
openai>=1.0.0             # GPT-4o-mini API
python-dotenv>=1.0.0      # .env file loading

# Frontend
@angular/core: ^19.0.0    # UI framework
```

---

## 12. Security Notes

- The OpenAI API key is stored in `backend/.env` (not committed to source control)
- Uploaded files are stored in a temporary OS directory and scoped to a UUID session
- CORS is configured to allow all origins (suitable for POC; restrict in production)
- File type validation prevents non-PDF/DOCX uploads
- File size is capped at 10 MB

---

## 13. Limitations (POC Scope)

| Limitation                 | Note                                           |
| -------------------------- | ---------------------------------------------- |
| No user authentication     | Sessions are ephemeral (UUID only)             |
| Temporary file storage     | Files are not persisted across server restarts |
| OpenAI API cost            | Each upload consumes ~1,000–3,000 GPT tokens   |
| Scanned PDFs not supported | Requires text-based PDFs                       |
| Single-page sessions       | No history or dashboard                        |

---

_This document covers the complete POC implementation as of July 2026._
