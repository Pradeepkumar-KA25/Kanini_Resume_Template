import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GeneratedTemplateDraft, SavedUserTemplate } from '../../models/resume.model';
import { TemplateService } from '../../services/template.service';

@Component({
  selector: 'app-template-draft-preview',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './template-draft-preview.component.html',
  styleUrl: './template-draft-preview.component.scss'
})
export class TemplateDraftPreviewComponent implements OnInit {
  private readonly templateService = inject(TemplateService);
  @Input({ required: true }) draft!: GeneratedTemplateDraft;
  @Output() saved = new EventEmitter<SavedUserTemplate>();
  @Output() closed = new EventEmitter<void>();
  readonly saving = signal(false);
  readonly error = signal('');
  readonly success = signal('');
  templateName = '';
  description = '';

  ngOnInit(): void { this.description = this.draft.suggested_description; }

  save(): void {
    const name = this.templateName.trim();
    const description = this.description.trim();
    if (!name) { this.error.set('Template name is required.'); return; }
    if (name.length > 80) { this.error.set('Template name must be 80 characters or fewer.'); return; }
    if (!description) { this.error.set('Template description is required.'); return; }
    if (description.length > 240) { this.error.set('Template description must be 240 characters or fewer.'); return; }
    if (this.saving()) return;

    this.saving.set(true);
    this.error.set('');
    this.templateService.saveTemplateDraft(this.draft.draft_id, name, description).subscribe({
      next: template => {
        this.saving.set(false);
        this.success.set(`Template saved as ${template.template_id}.`);
        this.saved.emit(template);
      },
      error: response => {
        this.saving.set(false);
        this.error.set(String(response?.error?.detail || 'Unable to save the template. Please try again.'));
      }
    });
  }
}
