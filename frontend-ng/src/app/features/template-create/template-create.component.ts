import { Component, ElementRef, EventEmitter, Output, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateDraft } from '../../models/resume.model';
import { TemplateService } from '../../services/template.service';

@Component({
  selector: 'app-template-create',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './template-create.component.html',
  styleUrl: './template-create.component.scss'
})
export class TemplateCreateComponent {
  private readonly templateService = inject(TemplateService);
  @Output() cancelled = new EventEmitter<void>();
  @Output() uploaded = new EventEmitter<TemplateDraft>();
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  readonly selectedFile = signal<File | null>(null);
  readonly error = signal('');
  readonly uploading = signal(false);

  selectFile(file: File): void {
    if (!file.name.toLowerCase().endsWith('.pdf') || (file.type && file.type !== 'application/pdf')) {
      this.selectedFile.set(null);
      this.error.set('Please select a PDF file.');
      return;
    }
    this.selectedFile.set(file);
    this.error.set('');
  }

  onInputChange(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.selectFile(file);
  }

  browse(): void { this.fileInput.nativeElement.click(); }

  upload(): void {
    const file = this.selectedFile();
    if (!file) {
      this.error.set('Select a sample resume PDF to continue.');
      return;
    }
    this.uploading.set(true);
    this.error.set('');
    this.templateService.uploadSamplePdf(file).subscribe({
      next: draft => { this.uploading.set(false); this.uploaded.emit(draft); },
      error: response => {
        this.uploading.set(false);
        this.error.set(String(response?.error?.detail || 'Unable to upload the sample PDF. Please try again.'));
      }
    });
  }
}
