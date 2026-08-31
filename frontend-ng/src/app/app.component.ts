import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumeService } from './services/resume.service';
import { AppStatus, UploadResponse } from './models/resume.model';
import { FileUploadComponent, UploadSelection } from './components/file-upload/file-upload.component';
import { LoadingViewComponent } from './components/loading-view/loading-view.component';
import { ResultsViewComponent } from './components/results-view/results-view.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FileUploadComponent, LoadingViewComponent, ResultsViewComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  private readonly resumeService = inject(ResumeService);
  private toastTimer?: ReturnType<typeof setTimeout>;
  readonly toastDurationMs = 4500;

  status = signal<AppStatus>('idle');
  sessionData = signal<UploadResponse | null>(null);
  errorMsg = signal<string>('');
  toastVisible = signal<boolean>(false);

  onFileSelected(selection: UploadSelection): void {
    this.status.set('uploading');
    this.errorMsg.set('');
    this.resumeService.uploadResume(selection.file, selection.llmModel).subscribe({
      next: (data) => {
        this.sessionData.set(data);
        this.status.set('success');
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

  reset(): void {
    this.status.set('idle');
    this.sessionData.set(null);
    this.errorMsg.set('');
  }

  ngOnDestroy(): void {
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }
  }

  readonly year = new Date().getFullYear();
}
