import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import { TemplateGenerationComponent } from './template-generation.component';
import { TemplateService } from '../../services/template.service';

describe('TemplateGenerationComponent', () => {
  let fixture: ComponentFixture<TemplateGenerationComponent>;
  let component: TemplateGenerationComponent;
  const service = jasmine.createSpyObj<TemplateService>('TemplateService', ['generateTemplateDraft']);
  const draft = { draft_id: 'draft-1', status: 'generated' as const, filename: 'sample.pdf', extracted_data: {} as never, template_spec: {} as never, suggested_description: 'Single-column Calibri resume template.', preview_html: '<main></main>' };

  beforeEach(async () => {
    service.generateTemplateDraft.calls.reset();
    service.generateTemplateDraft.and.returnValue(of(draft));
    await TestBed.configureTestingModule({ imports: [TemplateGenerationComponent], providers: [{ provide: TemplateService, useValue: service }] }).compileComponents();
    fixture = TestBed.createComponent(TemplateGenerationComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('draftId', 'draft-1');
  });

  it('shows a loading state while generation is pending', () => { service.generateTemplateDraft.and.returnValue(new Subject()); fixture.detectChanges(); expect(component.loading()).toBeTrue(); expect(fixture.nativeElement.textContent).toContain('Generating Template...'); });
  it('emits generated drafts for preview navigation', () => { spyOn(component.generated, 'emit'); fixture.detectChanges(); expect(service.generateTemplateDraft).toHaveBeenCalledWith('draft-1'); expect(component.generated.emit).toHaveBeenCalledWith(draft); });
  it('shows a generation failure and retries without another upload', () => { service.generateTemplateDraft.and.returnValue(throwError(() => ({ error: { detail: 'Ollama is unavailable.' } }))); fixture.detectChanges(); expect(component.error()).toBe('Ollama is unavailable.'); service.generateTemplateDraft.and.returnValue(of(draft)); component.generate(); expect(service.generateTemplateDraft).toHaveBeenCalledTimes(2); expect(component.error()).toBe(''); });
});
