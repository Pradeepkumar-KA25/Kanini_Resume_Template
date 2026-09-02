import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ReviewComponent } from './review.component';
import { ResumeService } from '../../services/resume.service';
import { ResumeData } from '../../models/resume.model';

describe('ReviewComponent', () => {
  let fixture: ComponentFixture<ReviewComponent>;
  let component: ReviewComponent;
  const resume: ResumeData = { contact: { name: 'Riya', email: 'riya@example.com', phone: '1234567890', location: '', linkedin: '', github: '' }, summary: 'Summary', skills: { Data: ['Python'] }, experience: [], projects: [], education: [], certifications: [], achievements: [], additional_sections: {} };
  const service = jasmine.createSpyObj<ResumeService>('ResumeService', ['getReview', 'getTemplates', 'updateReview']);

  beforeEach(async () => { service.getReview.and.returnValue(of({ session_id: 's1', resume_data: resume })); service.getTemplates.and.returnValue(of({ templates: [] })); await TestBed.configureTestingModule({ imports: [ReviewComponent], providers: [{ provide: ResumeService, useValue: service }] }).compileComponents(); fixture = TestBed.createComponent(ReviewComponent); component = fixture.componentInstance; component.sessionId = 's1'; component.resume = resume; fixture.detectChanges(); });
  it('loads canonical review data into the form', () => { expect(service.getReview).toHaveBeenCalledWith('s1'); expect(component.form.controls.contact.controls.name.value).toBe('Riya'); });
  it('adds and removes repeatable experience and projects', () => { component.addExperience(); component.addProject(); expect(component.experience.length).toBe(1); expect(component.projects.length).toBe(1); component.remove(component.experience, 0); component.remove(component.projects, 0); expect(component.experience.length).toBe(0); expect(component.projects.length).toBe(0); });
  it('keeps unsaved changes unless cancellation is confirmed', () => { spyOn(window, 'confirm').and.returnValue(false); component.form.controls.summary.setValue('Changed'); component.cancel(); expect(component.cancelled.observed).toBeFalse(); });
  it('saves canonical form data and emits refreshed artifacts', () => { service.updateReview.and.returnValue(of({ session_id: 's1', resume_data: resume, preview_html: { template1: '', template2: '' } })); spyOn(component.saved, 'emit'); component.save(); expect(service.updateReview).toHaveBeenCalled(); expect(component.saved.emit).toHaveBeenCalled(); });
  it('shows controlled save errors', () => { service.updateReview.and.returnValue(throwError(() => ({ error: { detail: 'Invalid reviewed resume' } }))); component.save(); expect(component.error()).toBe('Invalid reviewed resume'); });
  it('shows persistent associated labels for an empty experience entry', () => { component.addExperience(); fixture.detectChanges(); const root = fixture.nativeElement as HTMLElement; const labels = Array.from(root.querySelectorAll<HTMLLabelElement>('label')).map(label => label.textContent?.trim()); expect(labels).toContain('Company'); expect(labels).toContain('Designation'); expect(labels).toContain('Duration'); expect(labels).toContain('Responsibilities'); expect(root.querySelector('label[for="experience-company-0"]')).not.toBeNull(); });
  it('shows persistent associated labels for an empty project entry', () => { component.addProject(); fixture.detectChanges(); const root = fixture.nativeElement as HTMLElement; const labels = Array.from(root.querySelectorAll<HTMLLabelElement>('label')).map(label => label.textContent?.trim()); expect(labels).toContain('Project Name'); expect(labels).toContain('Client'); expect(labels).toContain('Role'); expect(labels).toContain('Technical Stack'); expect(root.querySelector('label[for="project-name-0"]')).not.toBeNull(); });
});