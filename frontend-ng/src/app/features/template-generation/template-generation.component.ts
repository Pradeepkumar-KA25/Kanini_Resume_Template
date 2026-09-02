import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GeneratedTemplateDraft } from '../../models/resume.model';
import { TemplateService } from '../../services/template.service';

@Component({
  selector: 'app-template-generation',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './template-generation.component.html',
  styleUrl: './template-generation.component.scss'
})
export class TemplateGenerationComponent implements OnInit {
  private readonly templateService = inject(TemplateService);
  @Input({ required: true }) draftId!: string;
  @Output() generated = new EventEmitter<GeneratedTemplateDraft>();
  @Output() cancelled = new EventEmitter<void>();

  readonly loading = signal(false);
  readonly error = signal('');

  ngOnInit(): void { this.generate(); }

  generate(): void {
    this.loading.set(true);
    this.error.set('');
    this.templateService.generateTemplateDraft(this.draftId).subscribe({
      next: draft => { this.loading.set(false); this.generated.emit(draft); },
      error: response => {
        this.loading.set(false);
        this.error.set(String(response?.error?.detail || 'Unable to generate the template. Please try again.'));
      }
    });
  }
}
