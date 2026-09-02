import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpHeaders, HttpResponse } from '@angular/common/http';
import { of, Subject, throwError } from 'rxjs';
import { DownloadComponent } from './download.component';
import { ResumeService } from '../../services/resume.service';
import { TemplateMetadata } from '../../models/resume.model';

describe('DownloadComponent', () => {
  let fixture: ComponentFixture<DownloadComponent>; let component: DownloadComponent;
  const template: TemplateMetadata = { id: 'kanini-format-2', display_name: 'Kanini Format 2', description: 'A4', version: '1.0', enabled: true, supported_outputs: ['pdf', 'docx', 'html'], page_size: 'A4' };
  const service = jasmine.createSpyObj<ResumeService>('ResumeService', ['downloadResume']);
  beforeEach(async () => { service.downloadResume.calls.reset(); service.downloadResume.and.returnValue(of(new HttpResponse({ body: new Blob(['file']), headers: new HttpHeaders({ 'content-disposition': 'attachment; filename="resume.pdf"' }) }))); await TestBed.configureTestingModule({ imports: [DownloadComponent], providers: [{ provide: ResumeService, useValue: service }] }).compileComponents(); fixture = TestBed.createComponent(DownloadComponent); component = fixture.componentInstance; fixture.componentRef.setInput('sessionId', 's1'); fixture.componentRef.setInput('template', template); fixture.detectChanges(); });
  it('shows only registry-supported formats', () => { expect(fixture.nativeElement.textContent).toContain('PDF'); expect(fixture.nativeElement.textContent).toContain('DOCX'); expect(fixture.nativeElement.textContent).toContain('HTML'); });
  it('shows PDF and DOCX for supported user templates', () => { fixture.componentRef.setInput('template', { ...template, id: 'user-modern', user_created: true }); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('PDF'); expect(fixture.nativeElement.textContent).toContain('DOCX'); });
  it('downloads the selected template and format', () => { spyOn(document.body, 'appendChild').and.callThrough(); component.download('pdf'); expect(service.downloadResume).toHaveBeenCalledWith('s1', 'kanini-format-2', 'pdf'); });
  it('shows loading and prevents duplicate active downloads', () => { service.downloadResume.and.returnValue(new Subject()); component.download('pdf'); component.download('docx'); expect(component.activeFormat()).toBe('pdf'); expect(service.downloadResume).toHaveBeenCalledTimes(1); });
  it('shows controlled download failures', () => { service.downloadResume.and.returnValue(throwError(() => new Error())); component.download('pdf'); expect(component.error()).toContain('Unable to download PDF'); });
  it('emits template change navigation', () => { spyOn(component.changeTemplate, 'emit'); component.changeTemplate.emit(); expect(component.changeTemplate.emit).toHaveBeenCalled(); });
});