import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata, UserTemplateAction } from '../../models/resume.model';

@Component({ selector: 'app-template-selection', standalone: true, imports: [CommonModule], templateUrl: './template-selection.component.html', styleUrl: './template-selection.component.scss' })
export class TemplateSelectionComponent {
  private readonly service = inject(ResumeService);
  @Input() allowTemplateCreation = false;
  @Output() selected = new EventEmitter<TemplateMetadata>();
  @Output() create = new EventEmitter<void>();
  @Output() manage = new EventEmitter<{ template: TemplateMetadata; action: UserTemplateAction }>();
  readonly templates = signal<TemplateMetadata[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly selectedId = signal('');
  ngOnInit(): void { this.load(); }
  load(): void { this.loading.set(true); this.error.set(''); this.service.getTemplates().subscribe({ next: value => { this.templates.set(value.templates); this.loading.set(false); }, error: () => { this.error.set('Unable to load resume templates. Please try again.'); this.loading.set(false); } }); }
  choose(template: TemplateMetadata): void { if (template.enabled) this.selectedId.set(template.id); }
  continue(): void { const template = this.templates().find(item => item.id === this.selectedId()); if (!template) { this.error.set('Please select a template to continue.'); return; } this.selected.emit(template); }
  manageTemplate(template: TemplateMetadata, action: UserTemplateAction): void { this.manage.emit({ template, action }); }
  hasUserTemplates(): boolean { return this.templates().some(template => template.user_created); }
}