import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UploadResponse } from '../../models/resume.model';
import { TemplateCardComponent } from '../template-card/template-card.component';

@Component({
  selector: 'app-results-view',
  standalone: true,
  imports: [CommonModule, TemplateCardComponent],
  templateUrl: './results-view.component.html',
  styleUrl: './results-view.component.scss'
})
export class ResultsViewComponent {
  @Input({ required: true }) sessionData!: UploadResponse;
  @Output() reset = new EventEmitter<void>();

  get expCount() { return this.sessionData.resume_data.experience.length; }
  get skillCount() {
    return Object.values(this.sessionData.resume_data.skills).flat().length;
  }
  get certCount() { return this.sessionData.resume_data.certifications.length; }
}
