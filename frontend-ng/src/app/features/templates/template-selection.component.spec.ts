import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { TemplateSelectionComponent } from './template-selection.component';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata } from '../../models/resume.model';

describe('TemplateSelectionComponent', () => {
  let fixture: ComponentFixture<TemplateSelectionComponent>; let component: TemplateSelectionComponent;
  const active: TemplateMetadata = { id: 'kanini-format-1', display_name: 'Format 1', description: 'Letter', version: '1.0', enabled: true, supported_outputs: ['html', 'pdf'], page_size: 'LETTER' };
  const userTemplate: TemplateMetadata = { id: 'user-modern', display_name: 'My Modern Resume', description: 'Professional user template.', version: '1.0', enabled: true, supported_outputs: ['html'], page_size: 'A4', user_created: true };
  const disabled: TemplateMetadata = { ...active, id: 'disabled', enabled: false };
  const service = jasmine.createSpyObj<ResumeService>('ResumeService', ['getTemplates']);
  beforeEach(async () => { service.getTemplates.and.returnValue(of({ templates: [active, disabled] })); await TestBed.configureTestingModule({ imports: [TemplateSelectionComponent], providers: [{ provide: ResumeService, useValue: service }] }).compileComponents(); fixture = TestBed.createComponent(TemplateSelectionComponent); component = fixture.componentInstance; fixture.detectChanges(); });
  it('loads and displays registry templates', () => { expect(service.getTemplates).toHaveBeenCalled(); expect(component.templates().length).toBe(2); });
  it('requires a selected template before continuation', () => { component.continue(); expect(component.error()).toContain('Please select'); });
  it('selects enabled templates and emits navigation data', () => { spyOn(component.selected, 'emit'); component.choose(active); component.continue(); expect(component.selectedId()).toBe(active.id); expect(component.selected.emit).toHaveBeenCalledWith(active); });
  it('displays and selects user-created templates alongside built-ins', () => { service.getTemplates.and.returnValue(of({ templates: [active, userTemplate] })); component.load(); fixture.detectChanges(); spyOn(component.selected, 'emit'); expect(fixture.nativeElement.textContent).toContain('User-created'); component.choose(userTemplate); component.continue(); expect(component.selected.emit).toHaveBeenCalledWith(userTemplate); });
  it('shows Create Template only in template management mode', () => { expect(fixture.nativeElement.textContent).not.toContain('Create Template'); fixture.componentRef.setInput('allowTemplateCreation', true); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Create Template'); });
  it('does not select disabled templates', () => { component.choose(disabled); expect(component.selectedId()).toBe(''); });
  it('shows controlled errors and retries', () => { service.getTemplates.and.returnValue(throwError(() => new Error())); component.load(); expect(component.error()).toContain('Unable to load'); service.getTemplates.and.returnValue(of({ templates: [active] })); component.load(); expect(component.error()).toBe(''); });
});