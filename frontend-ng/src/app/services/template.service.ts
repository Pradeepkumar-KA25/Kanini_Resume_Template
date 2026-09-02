import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GeneratedTemplateDraft, SavedUserTemplate, TemplateDraft, TemplateSpec, UserTemplateDetail } from '../models/resume.model';

@Injectable({ providedIn: 'root' })
export class TemplateService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = this.resolveApiBaseUrl();

  private resolveApiBaseUrl(): string {
    const configured = (globalThis as { __KANINI_API_BASE_URL__?: string }).__KANINI_API_BASE_URL__;
    return (configured || 'http://localhost:8000').trim().replace(/\/$/, '');
  }

  uploadSamplePdf(file: File): Observable<TemplateDraft> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<TemplateDraft>(`${this.apiBaseUrl}/api/template-drafts`, form);
  }

  generateTemplateDraft(draftId: string): Observable<GeneratedTemplateDraft> {
    return this.http.post<GeneratedTemplateDraft>(`${this.apiBaseUrl}/api/template-drafts/${draftId}/generate`, {});
  }

  saveTemplateDraft(draftId: string, templateName: string, description: string): Observable<SavedUserTemplate> {
    return this.http.post<SavedUserTemplate>(`${this.apiBaseUrl}/api/template-drafts/${draftId}/save`, { template_name: templateName, description });
  }
  getUserTemplate(templateId: string): Observable<UserTemplateDetail> { return this.http.get<UserTemplateDetail>(`${this.apiBaseUrl}/api/user-templates/${templateId}`); }
  updateUserTemplate(templateId: string, templateName: string, description: string, templateSpec: TemplateSpec): Observable<{ template_id: string; display_name: string; description: string; status: 'updated' }> { return this.http.put<{ template_id: string; display_name: string; description: string; status: 'updated' }>(`${this.apiBaseUrl}/api/user-templates/${templateId}`, { template_name: templateName, description, template_spec: templateSpec }); }
  deleteUserTemplate(templateId: string): Observable<void> { return this.http.delete<void>(`${this.apiBaseUrl}/api/user-templates/${templateId}`); }
  regenerateUserTemplate(templateId: string): Observable<{ template_id: string; template_spec: TemplateSpec; preview_html: string }> { return this.http.post<{ template_id: string; template_spec: TemplateSpec; preview_html: string }>(`${this.apiBaseUrl}/api/user-templates/${templateId}/regenerate`, {}); }
  confirmRegeneration(templateId: string): Observable<void> { return this.http.post<void>(`${this.apiBaseUrl}/api/user-templates/${templateId}/regenerate/confirm`, {}); }
  cancelRegeneration(templateId: string): Observable<void> { return this.http.delete<void>(`${this.apiBaseUrl}/api/user-templates/${templateId}/regenerate`); }
}
