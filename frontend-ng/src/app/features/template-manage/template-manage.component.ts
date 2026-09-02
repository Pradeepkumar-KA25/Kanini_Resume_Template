import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TemplateMetadata, TemplateSpec, UserTemplateAction, UserTemplateDetail } from '../../models/resume.model';
import { TemplateService } from '../../services/template.service';

@Component({ selector: 'app-template-manage', standalone: true, imports: [FormsModule], templateUrl: './template-manage.component.html', styleUrl: './template-manage.component.scss' })
export class TemplateManageComponent implements OnInit {
  private readonly service = inject(TemplateService);
  @Input({ required: true }) template!: TemplateMetadata;
  @Input({ required: true }) action!: UserTemplateAction;
  @Output() closed = new EventEmitter<void>();
  @Output() changed = new EventEmitter<void>();
  readonly detail = signal<UserTemplateDetail | null>(null); readonly error = signal(''); readonly busy = signal(false); readonly regeneratedPreview = signal(''); readonly confirmDelete = signal(false);
  name = ''; description = ''; spec!: TemplateSpec;
  ngOnInit(): void { this.load(); }
  load(): void { this.service.getUserTemplate(this.template.id).subscribe({ next: value => { this.detail.set(value); this.name = value.display_name; this.description = value.description; this.spec = value.template_spec; if (this.action === 'delete') this.confirmDelete.set(true); if (this.action === 'regenerate') this.regenerate(); }, error: () => this.error.set('Unable to load this user template.') }); }
  save(): void { if (!this.name.trim()) { this.error.set('Template name is required.'); return; } this.busy.set(true); this.service.updateUserTemplate(this.template.id, this.name.trim(), this.description.trim(), this.spec).subscribe({ next: () => { this.busy.set(false); this.changed.emit(); this.closed.emit(); }, error: response => { this.busy.set(false); this.error.set(String(response?.error?.detail || 'Unable to save template changes.')); } }); }
  remove(): void { this.busy.set(true); this.service.deleteUserTemplate(this.template.id).subscribe({ next: () => { this.busy.set(false); this.changed.emit(); this.closed.emit(); }, error: () => { this.busy.set(false); this.error.set('Unable to delete this template.'); } }); }
  regenerate(): void { this.busy.set(true); this.service.regenerateUserTemplate(this.template.id).subscribe({ next: value => { this.busy.set(false); this.spec = value.template_spec; this.regeneratedPreview.set(value.preview_html); }, error: response => { this.busy.set(false); this.error.set(String(response?.error?.detail || 'Unable to regenerate template.')); } }); }
  confirmRegeneration(): void { this.busy.set(true); this.service.confirmRegeneration(this.template.id).subscribe({ next: () => { this.busy.set(false); this.changed.emit(); this.closed.emit(); }, error: () => { this.busy.set(false); this.error.set('Unable to apply regenerated template.'); } }); }
  cancelRegeneration(): void { this.service.cancelRegeneration(this.template.id).subscribe({ next: () => this.closed.emit(), error: () => this.closed.emit() }); }
}
