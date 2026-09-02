import { Component, EventEmitter, Input, OnChanges, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata } from '../../models/resume.model';

@Component({ selector: 'app-resume-preview', standalone: true, imports: [CommonModule], templateUrl: './resume-preview.component.html', styleUrl: './resume-preview.component.scss' })
export class ResumePreviewComponent implements OnChanges {
  private readonly service = inject(ResumeService); private readonly sanitizer = inject(DomSanitizer);
  @Input({ required: true }) sessionId!: string; @Input({ required: true }) template!: TemplateMetadata;
  @Output() changeTemplate = new EventEmitter<void>(); @Output() download = new EventEmitter<void>();
  readonly loading = signal(true); readonly error = signal(''); safeHtml: SafeHtml = '';
  ngOnChanges(): void { if (this.sessionId && this.template) this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.service.getPreview(this.sessionId, this.template.id).subscribe({ next: value => { this.safeHtml = this.sanitizer.bypassSecurityTrustHtml(value.preview_html); this.loading.set(false); }, error: () => { this.error.set("We couldn't generate the preview. Please try again."); this.loading.set(false); } }); }
  downloadFile(format: 'docx' | 'pdf'): void { window.location.assign(this.service.getDownloadUrl(this.sessionId, this.template.id, format)); }
}