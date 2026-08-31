import {
  Component, Input, ElementRef, OnChanges,
  OnDestroy, AfterViewInit, ViewChild
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

const TEMPLATE_WIDTH = 780;

@Component({
  selector: 'app-template-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './template-card.component.html',
  styleUrl: './template-card.component.scss'
})
export class TemplateCardComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) title!: string;
  @Input() badge = '';
  @Input() description = '';
  @Input() icon = '📑';
  @Input() iconSrc = '';
  @Input() candidateName = '';
  @Input({ required: true }) previewHtml!: string;
  @Input({ required: true }) sessionId!: string;
  @Input({ required: true }) templateId!: string;

  @ViewChild('previewArea') previewAreaRef!: ElementRef<HTMLDivElement>;

  safeHtml: SafeHtml = '';
  scale = 1;
  previewAreaHeight = '500px';
  pdfLoading = false;
  private readonly apiBaseUrl = this.resolveApiBaseUrl();

  private ro?: ResizeObserver;

  constructor(private sanitizer: DomSanitizer) {}

  private resolveApiBaseUrl(): string {
    const configured = (globalThis as { __KANINI_API_BASE_URL__?: string }).__KANINI_API_BASE_URL__;
    const base = (configured || 'http://localhost:8000').trim();
    return base.replace(/\/$/, '');
  }

  ngOnChanges(): void {
    this.safeHtml = this.sanitizer.bypassSecurityTrustHtml(this.previewHtml ?? '');
    if (this.previewAreaRef) {
      setTimeout(() => this.update(), 80);
    }
  }

  ngAfterViewInit(): void {
    this.update();
    this.ro = new ResizeObserver(() => this.update());
    this.ro.observe(this.previewAreaRef.nativeElement);
  }

  ngOnDestroy(): void { this.ro?.disconnect(); }

  private update(): void {
    const el = this.previewAreaRef?.nativeElement;
    if (!el) return;
    const styles = getComputedStyle(el);
    const padLeft = parseFloat(styles.paddingLeft || '0');
    const padRight = parseFloat(styles.paddingRight || '0');
    const available = Math.max(0, el.clientWidth - padLeft - padRight);
    this.scale = Math.min(1, available / TEMPLATE_WIDTH);

    // Scale the container height to match the visually-rendered content height.
    // CSS transform doesn't affect layout — the inner div still occupies its natural
    // height in the DOM. We read that natural height and set the container to
    // naturalHeight * scale so there is no blank space below the content.
    const inner = el.firstElementChild as HTMLElement;
    if (inner) {
      const scaledH = Math.round(inner.scrollHeight * this.scale);
      // Cap at 75 vh so the card stays on-screen and the user can scroll inside it
      const maxH = Math.round(window.innerHeight * 0.75);
      this.previewAreaHeight = `${Math.min(scaledH + 24, maxH)}px`;
    }
  }

  get marginRight(): string {
    return `${-TEMPLATE_WIDTH * (1 - this.scale)}px`;
  }

  download(fmt: 'docx' | 'pdf'): void {
    const url = `${this.apiBaseUrl}/api/download/${this.sessionId}/${this.templateId}/${fmt}`;

    if (fmt === 'docx') {
      this.triggerDownload(url, `${this.title.replace(/\s+/g, '_')}_${this.candidateName || 'resume'}.docx`);
      return;
    }

    this.pdfLoading = true;
    fetch(url)
      .then(async (res) => {
        const blob = await res.blob();
        const contentType = res.headers.get('content-type') || blob.type || '';
        const extension = contentType.includes('pdf') ? 'pdf' : 'docx';
        const filename = `${this.title.replace(/\s+/g, '_')}_${this.candidateName || 'resume'}.${extension}`;
        const objectUrl = URL.createObjectURL(blob);
        this.triggerDownload(objectUrl, filename);
        URL.revokeObjectURL(objectUrl);
      })
      .catch(() => {
        this.triggerDownload(url, `${this.title.replace(/\s+/g, '_')}_${this.candidateName || 'resume'}.pdf`);
      })
      .finally(() => {
        this.pdfLoading = false;
      });
  }

  private triggerDownload(url: string, filename: string): void {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  get isKaniniTemplate(): boolean {
    return this.templateId === 'template1';
  }

  get isDeloitteTemplate(): boolean {
    return this.templateId === 'template2';
  }
}
