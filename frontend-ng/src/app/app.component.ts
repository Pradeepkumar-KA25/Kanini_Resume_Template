import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumeService } from './services/resume.service';
import { AppStatus, TemplateMetadata, UploadResponse } from './models/resume.model';
import { FileUploadComponent, UploadSelection } from './components/file-upload/file-upload.component';
import { LoadingViewComponent } from './components/loading-view/loading-view.component';
import { ResultsViewComponent } from './components/results-view/results-view.component';
import { ReviewComponent } from './features/review/review.component';
import { TemplateSelectionComponent } from './features/templates/template-selection.component';
import { ResumePreviewComponent } from './features/preview/resume-preview.component';
import { DownloadComponent } from './features/download/download.component';
import { SavedResumesComponent } from './components/saved-resumes/saved-resumes.component';
import { HomeComponent } from './features/home/home.component';
import { TemplateCreateComponent } from './features/template-create/template-create.component';
import { GeneratedTemplateDraft, SavedUserTemplate, TemplateDraft, UserTemplateAction } from './models/resume.model';
import { TemplateGenerationComponent } from './features/template-generation/template-generation.component';
import { TemplateDraftPreviewComponent } from './features/template-draft-preview/template-draft-preview.component';
import { TemplateManageComponent } from './features/template-manage/template-manage.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FileUploadComponent, LoadingViewComponent, ResultsViewComponent, ReviewComponent, TemplateSelectionComponent, ResumePreviewComponent, DownloadComponent, SavedResumesComponent, HomeComponent, TemplateCreateComponent, TemplateGenerationComponent, TemplateDraftPreviewComponent, TemplateManageComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  private readonly resumeService = inject(ResumeService);
  private toastTimer?: ReturnType<typeof setTimeout>;
  readonly toastDurationMs = 4500;

  status = signal<AppStatus>('home');
  sessionData = signal<UploadResponse | null>(null);
  errorMsg = signal<string>('');
  toastVisible = signal<boolean>(false);
  selectedTemplate = signal<TemplateMetadata | null>(null);
  templateDraft = signal<TemplateDraft | null>(null);
  generatedTemplateDraft = signal<GeneratedTemplateDraft | null>(null);
  savedUserTemplate = signal<SavedUserTemplate | null>(null);
  managedTemplate = signal<TemplateMetadata | null>(null);
  managedTemplateAction = signal<UserTemplateAction>('edit');
  allowTemplateCreation = signal(false);
  isDarkTheme = signal(localStorage.getItem('resume-builder-theme') === 'dark');

  constructor() {
    this.applyTheme();
  }

  navigateTo(status: 'home' | 'idle' | 'saved' | 'templates'): void {
    this.allowTemplateCreation.set(status === 'templates');
    this.status.set(status);
  }

  toggleTheme(): void {
    this.isDarkTheme.update(value => !value);
    this.applyTheme();
  }

  private applyTheme(): void {
    document.documentElement.classList.toggle('dark-theme', this.isDarkTheme());
    localStorage.setItem('resume-builder-theme', this.isDarkTheme() ? 'dark' : 'light');
  }

  onFileSelected(selection: UploadSelection): void {
    this.status.set('uploading');
    this.errorMsg.set('');
    this.resumeService.uploadResume(selection.file, selection.llmModel).subscribe({
      next: (data) => {
        this.sessionData.set(data);
        this.status.set('review');
      },
      error: (err) => {
        const statusCode = Number(err?.status ?? 0);
        const invalidMsg = 'Resume upload is invalid. Please upload a valid resume.';
        const detail = String(err?.error?.detail ?? '').trim();
        let msg = detail || invalidMsg;
        if (statusCode === 0) {
          msg = 'Cannot reach backend API. Ensure backend is running at http://localhost:8000.';
        } else if (statusCode === 413) {
          msg = 'File is too large. Please upload a file up to 10 MB.';
        }
        // Stay on upload page and show notification instead of routing to error view.
        this.status.set('idle');
        this.showToast(msg);
      }
    });
  }

  private showToast(message: string): void {
    this.errorMsg.set(message);
    this.toastVisible.set(true);
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
    this.toastTimer = setTimeout(() => {
      this.toastVisible.set(false);
    }, this.toastDurationMs);
  }

  dismissToast(): void {
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
    this.toastVisible.set(false);
  }

  openTemplateCreation(): void { this.status.set('template-create'); }
  closeTemplateCreation(): void { this.allowTemplateCreation.set(true); this.status.set('templates'); }
  onTemplateDraftUploaded(draft: TemplateDraft): void { this.templateDraft.set(draft); this.status.set('template-generating'); }
  onTemplateDraftGenerated(draft: GeneratedTemplateDraft): void { this.generatedTemplateDraft.set(draft); this.status.set('template-draft-preview'); }
  onTemplateDraftSaved(template: SavedUserTemplate): void { this.savedUserTemplate.set(template); this.allowTemplateCreation.set(true); this.status.set('templates'); this.showToast(`Template "${template.display_name}" saved successfully.`); }
  manageTemplate(event: { template: TemplateMetadata; action: UserTemplateAction }): void { this.managedTemplate.set(event.template); this.managedTemplateAction.set(event.action); this.status.set('template-manage'); }
  closeTemplateManagement(): void { this.allowTemplateCreation.set(true); this.status.set('templates'); }

  reset(): void {
    this.status.set('idle');
    this.sessionData.set(null);
    this.errorMsg.set('');
  }

  onReviewSaved(data: UploadResponse): void { this.sessionData.set(data); this.allowTemplateCreation.set(false); this.status.set('templates'); this.showToast('Resume saved successfully.'); }
  onTemplateSelected(template: TemplateMetadata): void {
    const sessionId = this.sessionData()?.session_id;
    if (!sessionId) { this.showToast('Resume session is unavailable. Please reopen the resume.'); return; }
    this.resumeService.updateSelectedTemplate(sessionId, template.id).subscribe({
      next: () => { this.selectedTemplate.set(template); this.status.set('preview'); },
      error: response => this.showToast(String(response?.error?.detail || 'Unable to save the selected template. Please try again.'))
    });
  }
  backToTemplates(): void { this.allowTemplateCreation.set(false); this.status.set('templates'); }
  showDownload(): void { this.status.set('download'); }
  openSaved(data: UploadResponse): void { this.sessionData.set(data); this.status.set('review'); }

  ngOnDestroy(): void {
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
  }

  readonly year = new Date().getFullYear();
}
