import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

const STEPS = [
  'Extracting text from your resume...',
  'Analysing sections and structure...',
  'Identifying skills and experience...',
  'Generating Kanini Template 1...',
  'Generating Kanini Template 2...',
];

@Component({
  selector: 'app-loading-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './loading-view.component.html',
  styleUrl: './loading-view.component.scss'
})
export class LoadingViewComponent {
  readonly steps = STEPS;
}
