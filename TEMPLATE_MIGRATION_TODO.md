# Template Migration TODO

## Status

- [x] Discovery completed against the current source code.
- [x] Angular production build baseline passed.
- [x] Backend Python syntax baseline passed.
- [x] Confirmed MiKTeX is the preferred Windows LaTeX distribution.
- [x] Obtain `docs/template-references/kanini-format-1-reference.pdf`.
- [x] Obtain `docs/template-references/kanini-format-2-reference.pdf`.
- [x] Confirm a MiKTeX compiler is available on `PATH` (`xelatex` preferred).

The reference PDFs are available for development-time visual analysis and validation only. They will never be read by the application at runtime. MiKTeX is installed, but its compiler executable was not discoverable on `PATH` during this analysis.

## Reference Analysis Gate

- [x] Record page size, page count, margins, header/footer bounds, and content bounds for Format 1.
- [x] Record embedded fonts, font sizes, weights, and colors for Format 1.
- [x] Record heading, candidate name, logo, bullets, tables, indentation, and page-break behavior for Format 1.
- [x] Record page size, page count, margins, header/footer bounds, and content bounds for Format 2.
- [x] Record embedded fonts, font sizes, weights, and colors for Format 2.
- [x] Record heading, candidate name, logo, bullets, tables, indentation, and page-break behavior for Format 2.
- [x] Produce an evidence-based Format 1 versus Format 2 comparison.
- [x] Document visual properties that cannot be measured exactly from the PDFs.

## Phase 1: Canonical ResumeData

- [x] Add canonical Pydantic models in `backend/models/resume.py`.
- [x] Add lossless AI and regex legacy-output adapters in `backend/services/resume_adapter.py`.
- [x] Add model-based normalization and structural validation in `backend/services/resume_normalization.py`.
- [x] Pass upload parser outputs through the canonical model while preserving the current API response dictionary.
- [x] Preserve template IDs, download URLs, renderer calls, persistence payloads, and frontend response compatibility.
- [x] Add pytest configuration and deterministic fixtures for minimal, normal, multi-company, multi-project, optional-section, long-content, large-skill-list, and Unicode/special-character resumes.
- [x] Validate the canonical suite, Python syntax, existing template generation, FastAPI startup/health, and Angular production build.

Canonical hierarchy:

```text
ResumeData
|- ContactInfo
|- Experience
|  `- Project
|- Project
`- Education
```

The adapter serializes canonical models back to the existing dictionary contract used by templates, ChromaDB, API responses, and Angular. The legacy normalizer in `main.py` remains active during this incremental phase for established PDF recovery behavior; the typed normalization service performs the canonical downstream pass. Template, renderer, persistence, and UI restructuring remains intentionally incomplete.

## Phase 2: Typed Normalization Pipeline

- [x] Move the active upload and PDF-parser-blend normalization path to `backend/services/resume_normalization.py`.
- [x] Remove the duplicated legacy dictionary normalizer and validator from `backend/main.py`.
- [x] Extend adapters to normalize supported legacy aliases: `professional_summary`, `designation`, `duration`, `project_name`, `technical_stack`, and `roles_and_responsibilities`.
- [x] Preserve typed summary recovery, malformed PDF experience recovery, experience cleanup, skills filtering/deduplication, project cleanup, education cleanup, and contact recovery validation.
- [x] Add tests for aliases, whitespace, duplicate values, skill/project noise, malformed PDF-style parser data, and API route registration compatibility.
- [x] Validate 13 pytest tests, Python syntax, existing DOCX/HTML generation, FastAPI startup/health, and Angular production build.

`main.py` is now a thinner compatibility facade: it receives parser output, adapts it to `ResumeData`, delegates normalization and validation to the typed service, serializes the established legacy dictionary only for current enrichment, templates, persistence, and API response consumers, and preserves all existing routes and template IDs. Remaining historical helper functions will be removed only when their debug/scoring dependencies are extracted in a later service-focused cleanup.

## Phase 3: Template Registry and Metadata

- [x] Add filesystem-discovered, Pydantic-validated template manifests under `backend/templates/`.
- [x] Register stable IDs `kanini-format-1` and `kanini-format-2` with `template1` and `template2` compatibility aliases.
- [x] Add `TemplateRegistry` resolution, existence, enabled listing, and supported-output checks in `backend/templates/registry/`.
- [x] Resolve download template IDs through the registry while retaining existing generated artifact keys and download URLs.
- [x] Add `GET /api/templates` to return enabled public metadata without internal paths, aliases, assets, or renderer details.
- [x] Add deterministic registry and API-route compatibility tests.
- [x] Validate 19 pytest tests, Python syntax, existing DOCX/HTML generation, FastAPI startup/health/template listing, and Angular production build.

Manifests currently establish template identity, page-size metadata, supported output formats, aliases, logo references, and download naming only. Existing DOCX, HTML preview, and PDF implementation remains in `template_generator.py` until the renderer migration phase; no LaTeX or frontend redesign was introduced.

## Phase 4: Format 1 Renderer Migration

- [x] Add typed render results, controlled renderer errors, renderer factory, and a Format 1 view model under `backend/renderers/`.
- [x] Add code-defined Kanini Format 1 HTML, DOCX, and LaTeX layout resources under `backend/templates/kanini-format-1/`.
- [x] Add centralized `escape_latex()` handling for candidate-controlled special characters.
- [x] Render Format 1 HTML, DOCX, and LaTeX source from canonical `ResumeData` and a template-specific view model.
- [x] Integrate Format 1 as the primary session HTML/DOCX renderer while leaving Format 2 on `template_generator.py`.
- [x] Add controlled XeLaTeX discovery and use the established Format 1 generator only when XeLaTeX is unavailable.
- [x] Preserve `template1`/`template2`, existing artifact keys, downloads, and Format 2 output behavior.
- [x] Add renderer tests for factory resolution, HTML, DOCX, LaTeX source, optional sections, Unicode, long content, special-character escaping, and the unavailable-compiler path.
- [x] Validate 25 pytest tests, Python syntax, real session artifacts, existing DOCX/HTML generation, FastAPI startup/health/template listing, and Angular production build.
- [x] Compile the new Format 1 PDF with XeLaTeX and complete its reference-PDF visual comparison.

The new Format 1 source uses Letter page geometry, 1-inch margins, a repeated Kanini logo header, Times New Roman with TeX Gyre Termes fallback, black 12pt hierarchy, label/value experience rows, Roman-numeral projects, and bullet education. XeLaTeX edge-case compilation covers short/normal/long resumes, multi-entry content, optional sections, Unicode, and LaTeX-sensitive characters. The generated logo width and repeated-page behavior match the reference; its vertical position is approximately 8pt lower than the reference's measured image band. It does not read reference PDFs at runtime. Format 2 remains intentionally unmigrated.

## Phase 5: Format 2 Renderer Migration

- [x] Add Format 2-specific view model, HTML, DOCX, LaTeX, and section resources under `backend/templates/kanini-format-2/`.
- [x] Register the Format 2 renderer with `RendererFactory` through its stable `kanini-format-2` ID and `template2` compatibility alias.
- [x] Integrate Format 2 HTML, DOCX, and XeLaTeX PDF generation into session artifacts while retaining the legacy generator for the unavailable-XeLaTeX environment fallback.
- [x] Add compiler-backed Format 2 tests for registry lookup, HTML/DOCX/LaTeX output, A4 geometry, repeated logos, long content, multiple projects, Unicode, and LaTeX-sensitive characters.
- [x] Validate deterministic Format 2 PDF geometry and repeated branding against the reference PDF.
- [x] Validate 40 pytest tests, Python syntax, existing DOCX/HTML generation, FastAPI startup/health/template listing, and Angular production build.

Format 2 uses A4 geometry, a 46pt left/12pt right dense body layout, compact label/value rows, `Project – I` labels, Client/Technical Stack/Role fields, responsibility bullets, and prose education. Its generated page/logo dimensions match the reference; the logo band is approximately 9pt lower. Format 1 remains unchanged and `template_generator.py` remains available as a compatibility fallback.

## Phase 6: Review/Edit and Template Workflow Foundation

- [x] Retain the full canonical parsed resume separately in active sessions while retaining redacted render data for previews/downloads.
- [x] Add controlled `GET` and `PUT /api/resumes/{session_id}/review` endpoints for canonical review data and validated update/regeneration.
- [x] Add registry-validated `POST /api/resumes/{session_id}/render` for selected HTML previews or safe download URL references.
- [x] Preserve existing upload responses, download URLs, aliases, rendering, persistence, and saved-resume behavior.
- [x] Extend Angular resume types to match canonical experience and project fields.
- [x] Add a minimal feature-oriented Angular review screen with editable contact, summary, skills, experience, projects, certifications, achievements, API-driven template selection, save, cancel, errors, and rendering state.
- [x] Add review API/session isolation/invalid-template tests and route compatibility coverage.
- [x] Validate 43 pytest tests, Python syntax, existing document smoke generation, FastAPI startup/health/template listing, and Angular production build.

The review API remains session-based and unauthenticated like the existing application, so it must not be publicly exposed until authentication and session ownership controls are introduced. Saved resumes, a full visual redesign, and Angular component test infrastructure remain deferred.

## Phase 7: Angular Review/Edit UI

- [x] Replace the prototype template-driven review surface with a reactive-form feature that loads canonical session review data.
- [x] Support structured contact, summary, skills, experience, projects, education, certifications, and achievements editing.
- [x] Support add/remove repeatable experience and project items, line-based skill categories, and list editing without raw JSON.
- [x] Add required-name and email integrity validation, save/loading/error states, visible unsaved state, and discard confirmation.
- [x] Load template metadata through the existing API and present a minimal template selection control before the existing result/preview flow.
- [x] Add five Angular component tests covering load, repeatable editing, unsaved cancellation, save success, and save failure.
- [x] Validate Angular tests, production build, 43 backend pytest tests, and backend syntax compilation.

The review editor intentionally preserves the existing results/preview screen after a successful save. Saved resumes, authentication/session ownership, a full preview redesign, and broader Angular feature organization remain deferred.

## Phase 8: Template Selection

- [x] Add a dedicated API-driven template selection feature using `GET /api/templates` as the sole metadata source.
- [x] Display responsive, keyboard-accessible template cards with selected, unavailable, loading, error, and retry states.
- [x] Require an enabled selected template before progressing to the existing preview/download screen.
- [x] Preserve the selected stable template metadata in the current root workflow state.
- [x] Move template choice out of the review editor so review save transitions into template selection.
- [x] Add five Angular tests for loading, selection, validation, disabled templates, retry, and navigation output.
- [x] Validate 10 Angular tests, Angular production build, 43 backend pytest tests, and Python syntax compilation.

The existing result/preview screen remains the temporary destination after selection and continues to expose both legacy previews/downloads. Applying the chosen template to a dedicated preview surface is deferred to the preview workflow phase.

## Phase 9: Dedicated Responsive Preview

- [x] Add a dedicated preview feature that requests selected-template HTML through the existing registry-validated render API.
- [x] Display only the selected template and preserve its stable ID across selection-to-preview workflow state.
- [x] Replace the old fixed-width transform/nested-scroll primary path with natural page-level scrolling and responsive document width constraints.
- [x] Add preview loading, controlled error, retry, missing-session, change-template, and safe download entry states.
- [x] Isolate Angular trusted HTML handling to the backend-controlled template-render response; no candidate-provided HTML enters this boundary.
- [x] Add five Angular preview tests for selected-template request, one-template rendering, loading/error retry, missing-session handling, and template-change navigation.
- [x] Validate 15 Angular tests, Angular production build, 43 backend pytest tests, and Python syntax compilation.

The existing results component and legacy dual-preview APIs remain available for compatibility but are no longer the primary workflow destination. Dedicated download UX and visual page pagination remain deferred.

## Phase 10: Download and Artifact Regeneration UX

- [x] Add a dedicated selected-template download workflow surface driven by template registry supported outputs.
- [x] Route preview download navigation into the new final workflow state while preserving existing download endpoints.
- [x] Extend the existing validated download endpoint to serve backend-rendered HTML attachments alongside DOCX and PDF.
- [x] Preserve server-side template/format validation, canonical template alias resolution, safe candidate filename normalization, and current-session artifact consistency after review regeneration.
- [x] Add download controls with available-format filtering, duplicate-click prevention, lightweight success status, and change-template navigation.
- [x] Add Angular tests for formats, selected-template URL requests, duplicate prevention, and navigation; add backend HTML download coverage.
- [x] Validate 19 Angular tests, Angular production build, 44 backend pytest tests, and Python syntax compilation.

Artifacts remain eagerly regenerated after a successful review save by the existing session flow, which prevents stale reviewed data from being downloaded. Per-format lazy regeneration and a richer binary download progress lifecycle remain deferred.

## Phase 11: Saved Resumes

- [x] Reuse existing ChromaDB-backed canonical resume persistence through the existing list, retrieve, update, and delete APIs.
- [x] Implement the previously empty Saved Resumes Angular feature with loading, empty, error/retry, open, and confirmed-delete states.
- [x] Reopen persisted resumes into an active session and route them into the existing Review/Edit workflow without re-uploading the original file.
- [x] Add typed saved-resume metadata service methods and navigation from the application header.
- [x] Add Angular tests for loading metadata, opening a saved resume, and confirmed deletion.
- [x] Validate 22 Angular tests, Angular production build, 44 backend pytest tests, and Python syntax compilation.

Saved records persist canonical resume content across backend restart through ChromaDB; opening a record regenerates an active working session for review, template selection, preview, and download. Authentication and ownership are intentionally absent. Custom saved-resume titles and persisted selected-template metadata require a future Chroma metadata extension and are not inferred from filenames.

## Phase 12: Lazy Artifact Generation

- [x] Change session preparation to generate HTML compatibility previews only; no DOCX/PDF/LaTeX artifact is created on upload, review save, or preview.
- [x] Generate DOCX only on a validated DOCX download request and PDF only on a validated PDF download request through the selected registry renderer.
- [x] Generate downloadable HTML on demand from the selected registry renderer.
- [x] Invalidate all derived artifact paths when review updates regenerate the session, ensuring later downloads use current reviewed ResumeData.
- [x] Preserve legacy download URLs, aliases, registry checks, filename sanitization, and `template_generator.py` fallback ownership.
- [x] Add lazy DOCX/PDF and stale-artifact invalidation tests.
- [x] Validate 46 backend pytest tests, 22 Angular tests, Angular production build, Python syntax, and existing document smoke generation.

`main.py` remains the current session/artifact compatibility facade; renderers remain the primary document generators, and `template_generator.py` remains only for the explicit unavailable-XeLaTeX compatibility path. LaTeX compiler intermediates remain session-scoped; debug-retention and broader configuration extraction remain future cleanup work.

## Phase 13: Production Readiness and Windows Packaging

- [x] Replace hard-coded PyInstaller and Python paths with repository-relative packaging paths.
- [x] Package Angular production assets and backend template manifests/layout resources in the Windows distribution.
- [x] Build and run the packaged executable from `dist/KaniniResumeBuilder` and verify `/api/health` and `/api/templates`.
- [x] Ignore LaTeX intermediates, Office lock files, and development validation artifacts.
- [x] Update README for canonical review workflow, lazy downloads, renderers, tests, MiKTeX requirements, packaging, and template authoring.
- [x] Audit tracked secret indicators; only environment-variable lookups and placeholder documentation were found.

The packaged app serves the Angular production build through FastAPI. MiKTeX/XeLaTeX and Ollama remain external Windows dependencies. The application remains unauthenticated and stores sensitive canonical resume data locally, so it is suitable only for trusted/internal use until access control and retention policies are implemented.

## Backend Migration

- [ ] Add Pydantic canonical resume models for contact, skills, experience, projects, education, certifications, achievements, and optional extensions.
- [ ] Add adapters so AI and regex parsing both return canonical `ResumeData`.
- [ ] Move normalization, validation, enrichment, artifact/session management, and persistence behind services while preserving existing endpoints.
- [ ] Isolate ChromaDB behind a repository interface while retaining full-record retrieval, list, search, and delete behavior.
- [ ] Add a template registry with metadata, enabled status, supported outputs, and stable IDs.
- [ ] Replace template-specific backend conditionals with registry lookup.
- [ ] Keep compatibility aliases for existing `template1` and `template2` download URLs during migration.

## Renderer and Template System

- [ ] Create separate HTML, DOCX, and LaTeX/PDF renderer interfaces.
- [ ] Create code-defined folders for `kanini-format-1`, `kanini-format-2`, and shared LaTeX commands/assets.
- [ ] Implement centralized LaTeX escaping for all candidate-controlled fields.
- [ ] Use XeLaTeX with Unicode-aware fonts and controlled fallback handling.
- [ ] Compile PDFs in session-specific temporary directories and clean intermediate artifacts.
- [ ] Ensure headings remain with their following content and tables/entries avoid unsafe page splits.
- [ ] Ensure long prose, skills, project text, and Unicode wrap without clipping or overflow.
- [ ] Keep DOCX rendering separate from PDF generation and preserve content/hierarchy parity.
- [ ] Produce page-based HTML previews from the same template data and layout semantics.

## API and Frontend Migration

- [ ] Add template listing/detail APIs and a backward-compatible render/update path.
- [ ] Add a controlled session-resume update endpoint for reviewed edits and regeneration.
- [ ] Extend Angular `ResumeData` types to cover all canonical project and experience fields.
- [ ] Replace the three-state flow with upload, processing, review, template selection, preview, and download states.
- [ ] Move model selection into an advanced option and add selected-file, size, replace, remove, and accessible error states.
- [ ] Replace `alert()` client validation with the application notification system.
- [ ] Implement deterministic processing stages that reflect actual client/server milestones.
- [ ] Replace fixed-width scaled, nested-scroll previews with responsive page-based previews and a focused preview mode.
- [ ] Implement or remove the incomplete saved-resumes component before exposing it.
- [ ] Consolidate colors, spacing, type, focus, border, and elevation values into design tokens.

## Test and Execution Gates

- [ ] Add pytest configuration and deterministic resume fixtures.
- [ ] Test PDF, DOCX, and DOC extraction behavior.
- [ ] Test AI adapter, regex adapter, normalization, validation, and parser fallback.
- [ ] Test LaTeX escaping for `&`, `%`, `$`, `#`, `_`, `{`, `}`, and backslashes.
- [ ] Test Unicode, short, long, missing optional fields, multi-company, multi-project, and long-list fixtures.
- [ ] Test template registry, HTML renderer, DOCX renderer, LaTeX renderer, and compiler failures.
- [ ] Test API compatibility, errors, resume updates, artifact regeneration, Chroma retrieval/search/delete, and downloads.
- [ ] Add Angular tests for upload validation, review edits, selection, previews, downloads, errors, and keyboard operation.
- [ ] Run backend tests and Python syntax checks.
- [ ] Run `npm test` and `npm run build`.
- [ ] Start backend and frontend successfully with documented environment settings.
- [ ] Generate both formats as PDF, DOCX, and HTML from stable fixtures.
- [ ] Compare generated PDFs visually against the supplied references at desktop and mobile preview widths.
- [ ] Verify no text clipping, horizontal overflow, overlap, unintended blank pages, or broken page transitions.
- [ ] Validate packaging with repository-relative paths.

## Completion Criteria

- [ ] Candidate resume data, canonical data, templates, renderers, persistence, and UI are separate concerns.
- [ ] Adding a template requires no parser changes.
- [ ] Existing upload, model selection, fallback, persistence, retrieval, search, delete, preview, DOCX, and PDF behavior remains available.
- [ ] The reference PDFs are used only for development-time visual validation.