import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata } from '../../models/resume.model';

@Component({ selector: 'app-download', standalone: true, imports: [CommonModule], templateUrl: './download.component.html', styleUrl: './download.component.scss' })
export class DownloadComponent {
  private readonly service = inject(ResumeService);
  @Input({ required: true }) sessionId!: string; @Input({ required: true }) template!: TemplateMetadata;
  @Output() changeTemplate = new EventEmitter<void>();
  readonly activeFormat = signal<string>(''); readonly message = signal(''); readonly error = signal('');
  label(format: string): string { return format === 'pdf' ? 'Best for sharing' : format === 'docx' ? 'Editable document' : 'Web version'; }
  download(format: 'html' | 'docx' | 'pdf'): void {
    if (this.activeFormat()) return;
    this.activeFormat.set(format);
    this.error.set('');
    this.message.set(`Preparing ${format.toUpperCase()}...`);
    this.service.downloadResume(this.sessionId, this.template.id, format).subscribe({
      next: response => {
        const link = document.createElement('a');
        const filename = this.filename(response.headers.get('content-disposition'), format);
        link.href = URL.createObjectURL(response.body || new Blob());
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(link.href);
        this.message.set(`${format.toUpperCase()} download started.`);
        this.activeFormat.set('');
      },
      error: () => {
        this.error.set(`Unable to download ${format.toUpperCase()}. Please try again.`);
        this.message.set('');
        this.activeFormat.set('');
      }
    });
  }

  private filename(header: string | null, format: string): string {
    const matched = /filename="?([^";]+)"?/i.exec(header || '');
    return matched?.[1] || `resume.${format}`;
  }
}