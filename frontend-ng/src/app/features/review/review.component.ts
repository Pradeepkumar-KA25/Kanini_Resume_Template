import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ResumeData, UploadResponse } from '../../models/resume.model';
import { ResumeService } from '../../services/resume.service';

@Component({ selector: 'app-review', standalone: true, imports: [CommonModule, ReactiveFormsModule], templateUrl: './review.component.html', styleUrl: './review.component.scss' })
export class ReviewComponent {
  private readonly service = inject(ResumeService);
  private readonly formBuilder = inject(FormBuilder);
  @Input({ required: true }) sessionId!: string;
  @Input({ required: true }) resume!: ResumeData;
  @Output() saved = new EventEmitter<UploadResponse>();
  @Output() cancelled = new EventEmitter<void>();
  readonly saving = signal(false);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly form = this.formBuilder.nonNullable.group({ contact: this.formBuilder.nonNullable.group({ name: ['', Validators.required], email: ['', Validators.email], phone: [''], location: [''], linkedin: [''], github: [''] }), summary: [''], skills: [''], certifications: [''], achievements: [''], education: [''], experience: this.formBuilder.array([]), projects: this.formBuilder.array([]) });

  get experience(): FormArray { return this.form.controls.experience; } get projects(): FormArray { return this.form.controls.projects; }
  ngOnInit(): void { this.service.getReview(this.sessionId).subscribe({ next: value => { this.populate(value.resume_data); this.loading.set(false); }, error: () => { this.populate(this.resume); this.error.set('Could not load full review details.'); this.loading.set(false); } }); }
  addExperience(value: Partial<ResumeData['experience'][number]> = {}): void { this.experience.push(this.formBuilder.nonNullable.group({ company: [value.company || ''], title: [value.title || ''], dates: [value.dates || ''], responsibilities: [(value.responsibilities || []).join('\n')] })); }
  addProject(value: Partial<ResumeData['projects'][number]> = {}): void { this.projects.push(this.formBuilder.nonNullable.group({ name: [value.name || ''], client: [value.client || ''], role: [value.role || ''], duration: [value.duration || ''], technologies: [(value.technologies || []).join(', ')], description: [value.description || ''], responsibilities: [(value.responsibilities || []).join('\n')] })); }
  remove(items: FormArray, index: number): void { items.removeAt(index); }
  cancel(): void { if (!this.form.dirty || confirm('Discard unsaved resume changes?')) this.cancelled.emit(); }
  save(): void { if (this.saving()) return; if (this.form.invalid) { this.form.markAllAsTouched(); this.error.set('Some fields need your attention.'); return; } this.saving.set(true); this.service.updateReview(this.sessionId, this.payload()).subscribe({ next: value => { this.saving.set(false); this.form.markAsPristine(); this.saved.emit(value); }, error: err => { this.saving.set(false); this.error.set(String(err?.error?.detail || 'Unable to save your resume. Please try again.')); } }); }
  private populate(data: ResumeData): void { this.form.patchValue({ contact: data.contact, summary: data.summary, skills: Object.entries(data.skills).map(([key, values]) => `${key}: ${values.join(', ')}`).join('\n'), certifications: data.certifications.join('\n'), achievements: data.achievements.join('\n'), education: data.education.map(item => [item.degree, item.year, item.institution, item.gpa].filter(Boolean).join(' | ')).join('\n') }); data.experience.forEach(item => this.addExperience(item)); data.projects.forEach(item => this.addProject(item)); this.form.markAsPristine(); }
  private payload(): ResumeData { const raw = this.form.getRawValue(); const list = (value: string) => value.split('\n').map(item => item.trim()).filter(Boolean); const skills = raw.skills.split('\n').reduce<Record<string, string[]>>((result, line) => { const [category, ...items] = line.split(':'); if (category.trim()) result[category.trim()] = items.join(':').split(',').map(item => item.trim()).filter(Boolean); return result; }, {}); const experience = raw.experience as Array<{ company: string; title: string; dates: string; responsibilities: string }>; const projects = raw.projects as Array<{ name: string; client: string; role: string; duration: string; technologies: string; description: string; responsibilities: string }>; return { contact: raw.contact, summary: raw.summary.trim(), skills, experience: experience.map(item => ({ ...item, location: '', company_name: item.company, company_sector: '', responsibilities: list(item.responsibilities), projects: [] })), projects: projects.map(item => ({ ...item, technologies: item.technologies.split(',').map((value: string) => value.trim()).filter(Boolean), responsibilities: list(item.responsibilities) })), education: list(raw.education).map(line => { const [degree = '', year = '', institution = '', gpa = ''] = line.split('|').map(value => value.trim()); return { degree, year, institution, gpa }; }), certifications: list(raw.certifications), achievements: list(raw.achievements), additional_sections: {} }; }
}