import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LlmModelOption, PreviewResponse, ResumeData, SavedResumeSummary, TemplateMetadata, UploadResponse } from '../models/resume.model';

@Injectable({ providedIn: 'root' })
export class ResumeService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = this.resolveApiBaseUrl();

  private resolveApiBaseUrl(): string {
    const configured = (globalThis as { __KANINI_API_BASE_URL__?: string }).__KANINI_API_BASE_URL__;
    const base = (configured || 'http://localhost:8000').trim();
    return base.replace(/\/$/, '');
  }

  uploadResume(file: File, llmModel = 'auto'): Observable<UploadResponse> {
    const form = new FormData();
    form.append('file', file);
    form.append('llm_model', llmModel);
    return this.http.post<UploadResponse>(`${this.apiBaseUrl}/api/upload`, form);
  }

  getLlmModels(): Observable<{ models: LlmModelOption[] }> {
    return this.http.get<{ models: LlmModelOption[] }>(`${this.apiBaseUrl}/api/llm-models`);
  }

  getDownloadUrl(sessionId: string, templateId: string, format: 'html' | 'docx' | 'pdf'): string {
    return `${this.apiBaseUrl}/api/download/${sessionId}/${templateId}/${format}`;
  }

  downloadResume(sessionId: string, templateId: string, format: 'html' | 'docx' | 'pdf'): Observable<HttpResponse<Blob>> {
    return this.http.get(this.getDownloadUrl(sessionId, templateId, format), { observe: 'response', responseType: 'blob' });
  }

  getReview(sessionId: string): Observable<{ session_id: string; resume_data: ResumeData }> {
    return this.http.get<{ session_id: string; resume_data: ResumeData }>(`${this.apiBaseUrl}/api/resumes/${sessionId}/review`);
  }

  updateReview(sessionId: string, resume: ResumeData): Observable<UploadResponse> {
    return this.http.put<UploadResponse>(`${this.apiBaseUrl}/api/resumes/${sessionId}/review`, resume);
  }

  updateSelectedTemplate(sessionId: string, templateId: string): Observable<{ session_id: string; template_id: string }> {
    return this.http.put<{ session_id: string; template_id: string }>(`${this.apiBaseUrl}/api/resumes/${sessionId}/template`, { template_id: templateId });
  }

  getTemplates(): Observable<{ templates: TemplateMetadata[] }> {
    return this.http.get<{ templates: TemplateMetadata[] }>(`${this.apiBaseUrl}/api/templates`);
  }

  getPreview(sessionId: string, templateId: string): Observable<PreviewResponse> {
    return this.http.post<PreviewResponse>(`${this.apiBaseUrl}/api/resumes/${sessionId}/render`, { template_id: templateId, output_format: 'html' });
  }

  listSavedResumes(): Observable<{ resumes: SavedResumeSummary[]; count: number }> { return this.http.get<{ resumes: SavedResumeSummary[]; count: number }>(`${this.apiBaseUrl}/api/resumes`); }
  openSavedResume(id: string): Observable<UploadResponse> { return this.http.get<UploadResponse>(`${this.apiBaseUrl}/api/resumes/${id}`); }
  deleteSavedResume(id: string): Observable<void> { return this.http.delete<void>(`${this.apiBaseUrl}/api/resumes/${id}`); }
}
