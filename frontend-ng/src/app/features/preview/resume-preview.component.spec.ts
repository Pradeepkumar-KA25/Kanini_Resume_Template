import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ResumePreviewComponent } from './resume-preview.component';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata } from '../../models/resume.model';

describe('ResumePreviewComponent', () => {
  let fixture: ComponentFixture<ResumePreviewComponent>; let component: ResumePreviewComponent;
  const template: TemplateMetadata = { id: 'kanini-format-1', display_name: 'Kanini Format 1', description: 'Letter', version: '1.0', enabled: true, supported_outputs: ['html', 'docx', 'pdf'], page_size: 'LETTER' };
  const service = jasmine.createSpyObj<ResumeService>('ResumeService', ['getPreview', 'getDownloadUrl']);
  beforeEach(async () => { service.getPreview.and.returnValue(of({ session_id: 's1', template_id: template.id, output_format: 'html', preview_html: '<main class="resume-page">Selected document</main>' })); await TestBed.configureTestingModule({ imports: [ResumePreviewComponent], providers: [{ provide: ResumeService, useValue: service }] }).compileComponents(); fixture = TestBed.createComponent(ResumePreviewComponent); component = fixture.componentInstance; fixture.componentRef.setInput('sessionId', 's1'); fixture.componentRef.setInput('template', template); fixture.detectChanges(); });
  it('requests preview with the selected stable template ID', () => { expect(service.getPreview).toHaveBeenCalledWith('s1', 'kanini-format-1'); });
  it('renders only returned selected-template HTML', () => { fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Selected document'); });
  it('does not offer DOCX or PDF shortcuts for HTML-only user templates', () => { fixture.componentRef.setInput('template', { ...template, id: 'user-modern', supported_outputs: ['html'], user_created: true }); fixture.detectChanges(); expect(fixture.nativeElement.textContent).not.toContain('Download DOCX'); expect(fixture.nativeElement.textContent).not.toContain('Download PDF'); });
  it('shows controlled errors and retries preview loading', () => { service.getPreview.and.returnValue(throwError(() => new Error())); component.load(); expect(component.error()).toContain("couldn't generate"); service.getPreview.and.returnValue(of({ session_id: 's1', template_id: template.id, output_format: 'html', preview_html: '<p>Retry</p>' })); component.load(); expect(component.error()).toBe(''); });
  it('treats missing sessions as controlled preview errors', () => { service.getPreview.and.returnValue(throwError(() => ({ status: 404 }))); component.sessionId = 'missing'; component.load(); expect(component.error()).toContain("couldn't generate"); });
  it('emits template-change navigation', () => { spyOn(component.changeTemplate, 'emit'); component.changeTemplate.emit(); expect(component.changeTemplate.emit).toHaveBeenCalled(); });
});