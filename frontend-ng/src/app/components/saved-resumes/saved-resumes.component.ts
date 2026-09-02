import { Component, EventEmitter, OnInit, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumeService } from '../../services/resume.service';
import { SavedResumeSummary, UploadResponse } from '../../models/resume.model';

@Component({ selector: 'app-saved-resumes', standalone: true, imports: [CommonModule], templateUrl: './saved-resumes.component.html', styleUrl: './saved-resumes.component.scss' })
export class SavedResumesComponent implements OnInit {
	private readonly service = inject(ResumeService);
	@Output() open = new EventEmitter<UploadResponse>(); @Output() create = new EventEmitter<void>();
	readonly resumes = signal<SavedResumeSummary[]>([]); readonly loading = signal(true); readonly error = signal(''); readonly pendingDelete = signal<SavedResumeSummary | null>(null);
	ngOnInit(): void { this.load(); }
	load(): void { this.loading.set(true); this.error.set(''); this.service.listSavedResumes().subscribe({ next: value => { this.resumes.set(value.resumes); this.loading.set(false); }, error: () => { this.error.set('Unable to load saved resumes.'); this.loading.set(false); } }); }
	openResume(item: SavedResumeSummary): void { this.service.openSavedResume(item.id).subscribe({ next: value => this.open.emit(value), error: () => this.error.set('Unable to open this resume. Please try again.') }); }
	confirmDelete(item: SavedResumeSummary): void { this.pendingDelete.set(item); }
	delete(): void { const item = this.pendingDelete(); if (!item) return; this.service.deleteSavedResume(item.id).subscribe({ next: () => { this.pendingDelete.set(null); this.load(); }, error: () => this.error.set('Unable to delete this resume. Please try again.') }); }
}
