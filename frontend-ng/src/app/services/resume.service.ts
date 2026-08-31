import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LlmModelOption, UploadResponse } from '../models/resume.model';

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

  getDownloadUrl(sessionId: string, templateId: string, format: 'docx' | 'pdf'): string {
    return `${this.apiBaseUrl}/api/download/${sessionId}/${templateId}/${format}`;
  }
}
