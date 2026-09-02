import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'app-home',
  standalone: true,
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  @Output() createResume = new EventEmitter<void>();
  @Output() viewResumes = new EventEmitter<void>();
  @Output() createTemplate = new EventEmitter<void>();
}