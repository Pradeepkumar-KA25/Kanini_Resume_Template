import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { TemplateManageComponent } from './template-manage.component';
import { TemplateService } from '../../services/template.service';

describe('TemplateManageComponent', () => {
  let fixture: ComponentFixture<TemplateManageComponent>; let component: TemplateManageComponent;
  const service = jasmine.createSpyObj<TemplateService>('TemplateService', ['getUserTemplate', 'updateUserTemplate', 'deleteUserTemplate', 'regenerateUserTemplate', 'confirmRegeneration', 'cancelRegeneration']);
  const spec: any = { page: { size: 'A4' }, typography: { font_family: 'Calibri' }, layout: { columns: 1 } };
  beforeEach(async () => { service.getUserTemplate.and.returnValue(of({ template_id: 'user-1', display_name: 'Mine', description: 'Description', template_spec: spec, has_source: true })); service.updateUserTemplate.and.returnValue(of({ template_id: 'user-1', display_name: 'Mine', description: 'Description', status: 'updated' })); await TestBed.configureTestingModule({ imports: [TemplateManageComponent], providers: [{ provide: TemplateService, useValue: service }] }).compileComponents(); fixture = TestBed.createComponent(TemplateManageComponent); component = fixture.componentInstance; fixture.componentRef.setInput('template', { id: 'user-1', display_name: 'Mine', description: 'Description', version: '1', enabled: true, supported_outputs: ['html'], page_size: 'A4', user_created: true }); fixture.componentRef.setInput('action', 'edit'); fixture.detectChanges(); });
  it('loads editable user template details and saves changes', () => { component.name = 'Renamed'; component.save(); expect(service.updateUserTemplate).toHaveBeenCalled(); });
  it('shows delete confirmation only for delete action', () => { fixture.componentRef.setInput('action', 'delete'); component.ngOnInit(); expect(component.confirmDelete()).toBeTrue(); });
});
