import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import { TemplateDraftPreviewComponent } from './template-draft-preview.component';
import { TemplateService } from '../../services/template.service';

describe('TemplateDraftPreviewComponent', () => {
  let fixture: ComponentFixture<TemplateDraftPreviewComponent>;
  let component: TemplateDraftPreviewComponent;
  const service = jasmine.createSpyObj<TemplateService>('TemplateService', ['saveTemplateDraft']);
  const draft = { draft_id: 'draft-1', status: 'generated' as const, filename: 'sample.pdf', extracted_data: {} as never, template_spec: {} as never, suggested_description: 'Single-column Calibri resume template.', preview_html: '<main></main>' };
  const saved = { template_id: 'user-123', display_name: 'Clean Resume', description: 'Single-column Calibri resume template.', status: 'saved' as const };

  beforeEach(async () => {
    service.saveTemplateDraft.calls.reset();
    service.saveTemplateDraft.and.returnValue(of(saved));
    await TestBed.configureTestingModule({ imports: [TemplateDraftPreviewComponent], providers: [{ provide: TemplateService, useValue: service }] }).compileComponents();
    fixture = TestBed.createComponent(TemplateDraftPreviewComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('draft', draft);
    fixture.detectChanges();
  });

  it('shows the generated description and allows editing it', () => { expect(component.description).toBe(draft.suggested_description); component.description = 'Edited description.'; expect(component.description).toBe('Edited description.'); });
  it('requires a non-empty template name', () => { component.templateName = '  '; component.save(); expect(component.error()).toBe('Template name is required.'); expect(service.saveTemplateDraft).not.toHaveBeenCalled(); });
  it('saves valid template metadata and emits the saved template', () => { spyOn(component.saved, 'emit'); component.templateName = 'Clean Resume'; component.save(); expect(service.saveTemplateDraft).toHaveBeenCalledWith('draft-1', 'Clean Resume', draft.suggested_description); expect(component.success()).toContain('user-123'); expect(component.saved.emit).toHaveBeenCalledWith(saved); });
  it('shows save failures', () => { service.saveTemplateDraft.and.returnValue(throwError(() => ({ error: { detail: 'Save failed' } }))); component.templateName = 'Clean Resume'; component.save(); expect(component.error()).toBe('Save failed'); expect(component.saving()).toBeFalse(); });
  it('prevents duplicate submissions while saving', () => { service.saveTemplateDraft.and.returnValue(new Subject()); component.templateName = 'Clean Resume'; component.save(); component.save(); expect(component.saving()).toBeTrue(); expect(service.saveTemplateDraft).toHaveBeenCalledTimes(1); });
});
