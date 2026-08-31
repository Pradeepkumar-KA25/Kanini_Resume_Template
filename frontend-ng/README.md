# Kanini Resume Builder — Frontend

Angular 19 frontend for the **Kanini Resume Builder** POC. Allows users to upload a resume (PDF or Word) and download it as a professionally formatted, plain Word document in either Kanini Format  or Deloitte format.

---

## Prerequisites

- Node.js 18+
- Angular CLI 19 (`npm install -g @angular/cli`)
- Backend running on `http://localhost:8000` (see `backend/` folder)

---

## Getting Started

### 1. Install dependencies

```bash
cd frontend-ng
npm install
```

### 2. Start the dev server

```bash
ng serve --port 4200
```

Open `http://localhost:4200` in your browser. The app proxies API calls to the backend via `proxy.conf.json`.

---

## Project Structure

```
src/app/
├── components/
│   ├── file-upload/      ← Drag & drop resume upload UI
│   ├── loading-view/     ← Processing spinner
│   ├── results-view/     ← Side-by-side template previews + download buttons
│   └── template-card/    ← Individual template card with download action
├── services/
│   └── resume.service.ts ← HTTP calls to FastAPI backend
└── models/
    └── resume.model.ts   ← TypeScript interfaces for resume data
```

---

## Features

- Drag & drop or click-to-browse file upload (PDF / DOCX)
- Live HTML preview of both output formats side by side
- Download as a **plain Word document** (`.docx`) — not a template file
- Supports two output formats:
  - **Kanini Format ** — internal Kanini standard profile format
  - **Deloitte Format** — client submission format

---

## API Proxy

`proxy.conf.json` forwards all `/api/*` requests to `http://localhost:8000`, so the frontend can call the backend without CORS issues during development.

---

## Build

```bash
ng build
```

Output is placed in `dist/`. For production, set the backend URL directly in `resume.service.ts`.

---

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
