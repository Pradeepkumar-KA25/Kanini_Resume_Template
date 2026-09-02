import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { SavedResumesComponent } from './saved-resumes.component';
import { ResumeService } from '../../services/resume.service';

describe('SavedResumesComponent', () => {
 let fixture: ComponentFixture<SavedResumesComponent>; let component: SavedResumesComponent;
 const service=jasmine.createSpyObj<ResumeService>('ResumeService',['listSavedResumes','openSavedResume','deleteSavedResume']); const item={id:'r1',name:'Engineer Resume',email:'',filename:'',created_at:'2026-08-31'};
 beforeEach(async()=>{service.listSavedResumes.and.returnValue(of({resumes:[item],count:1}));service.openSavedResume.and.returnValue(of({session_id:'r1',resume_data:{} as never,preview_html:{template1:'',template2:''}}));service.deleteSavedResume.and.returnValue(of(void 0));await TestBed.configureTestingModule({imports:[SavedResumesComponent],providers:[{provide:ResumeService,useValue:service}]}).compileComponents();fixture=TestBed.createComponent(SavedResumesComponent);component=fixture.componentInstance;fixture.detectChanges();});
 it('loads saved metadata',()=>expect(component.resumes()[0].name).toBe('Engineer Resume'));
 it('opens a saved resume',()=>{spyOn(component.open,'emit');component.openResume(item);expect(component.open.emit).toHaveBeenCalled();});
 it('confirms before deleting',()=>{component.confirmDelete(item);expect(component.pendingDelete()).toBe(item);component.delete();expect(service.deleteSavedResume).toHaveBeenCalledWith('r1');});
});