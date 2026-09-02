import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import { TemplateCreateComponent } from './template-create.component';
import { TemplateService } from '../../services/template.service';

describe('TemplateCreateComponent', () => {
  let fixture: ComponentFixture<TemplateCreateComponent>;
  let component: TemplateCreateComponent;
  const service = jasmine.createSpyObj<TemplateService>('TemplateService', ['uploadSamplePdf']);
  const draft = { draft_id: 'draft-1', status: 'uploaded' as const, filename: 'sample.pdf', extracted_data: {} as never };

  beforeEach(async () => {
    service.uploadSamplePdf.and.returnValue(of(draft));
    await TestBed.configureTestingModule({ imports: [TemplateCreateComponent], providers: [{ provide: TemplateService, useValue: service }] }).compileComponents();
    fixture = TestBed.createComponent(TemplateCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders the PDF upload screen', () => { expect(fixture.nativeElement.textContent).toContain('Create Template'); expect(fixture.nativeElement.textContent).toContain('Upload and Continue'); });
  it('rejects a non-PDF file', () => { component.selectFile(new File(['test'], 'sample.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })); expect(component.error()).toContain('PDF'); expect(component.selectedFile()).toBeNull(); });
  it('uploads a selected PDF and emits its draft', () => { spyOn(component.uploaded, 'emit'); const file = new File(['test'], 'sample.pdf', { type: 'application/pdf' }); component.selectFile(file); component.upload(); expect(service.uploadSamplePdf).toHaveBeenCalledWith(file); expect(component.uploaded.emit).toHaveBeenCalledWith(draft); expect(component.uploading()).toBeFalse(); });
  it('shows an upload failure', () => { service.uploadSamplePdf.and.returnValue(throwError(() => ({ error: { detail: 'Extraction failed' } }))); component.selectFile(new File(['test'], 'sample.pdf', { type: 'application/pdf' })); component.upload(); expect(component.error()).toBe('Extraction failed'); expect(component.uploading()).toBeFalse(); });
  it('shows loading state while the upload request is pending', () => { service.uploadSamplePdf.and.returnValue(new Subject()); component.selectFile(new File(['test'], 'sample.pdf', { type: 'application/pdf' })); component.upload(); expect(component.uploading()).toBeTrue(); });
});
