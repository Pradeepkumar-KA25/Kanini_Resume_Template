import { Component, ElementRef, EventEmitter, Output, ViewChild, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ResumeService } from '../../services/resume.service';
import { LlmModelOption } from '../../models/resume.model';

export interface UploadSelection {
  file: File;
  llmModel: string;
}

interface LlmOptionGroup {
  key: string;
  label: string;
  options: LlmModelOption[];
}

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './file-upload.component.html',
  styleUrl: './file-upload.component.scss'
})
export class FileUploadComponent implements OnInit {
  private readonly resumeService = inject(ResumeService);

  @Output() fileSelected = new EventEmitter<UploadSelection>();
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  dragOver = false;
  readonly allowed = ['pdf', 'docx', 'doc'];
  readonly defaultLlmOptions: LlmModelOption[] = [
    { label: 'Auto (default)', value: 'auto', available: true },
    { label: 'Qwen3 32B', value: 'ollama:qwen3:32b', available: true, provider: 'ollama', provider_label: 'Ollama' },
    { label: 'Qwen3 14B', value: 'ollama:qwen3:14b', available: true, provider: 'ollama', provider_label: 'Ollama' },
    { label: 'Llama 3.3 70B', value: 'ollama:llama3.3:70b', available: true, provider: 'ollama', provider_label: 'Ollama' },
    { label: 'Devstral', value: 'ollama:devstral', available: true, provider: 'ollama', provider_label: 'Ollama' },
    { label: 'Gemma 3 27B', value: 'ollama:gemma3:27b', available: true, provider: 'ollama', provider_label: 'Ollama' },
    { label: 'Mistral Small 3.2', value: 'ollama:mistral-small3.2', available: true, provider: 'ollama', provider_label: 'Ollama' },
  ];
  llmOptions: LlmModelOption[] = [...this.defaultLlmOptions];
  llmOptionGroups: LlmOptionGroup[] = [];
  selectedLlmModel = 'auto';

  private readonly providerLabelMap: Record<string, string> = {
    auto: 'Auto',
    ollama: 'Ollama',
  };

  ngOnInit(): void {
    this.resumeService.getLlmModels().subscribe({
      next: (resp) => {
        const options = Array.isArray(resp?.models) && resp.models.length
          ? resp.models
          : this.defaultLlmOptions;
        this.llmOptions = options;
        this.rebuildOptionGroups();
      },
      error: () => {
        this.llmOptions = [...this.defaultLlmOptions];
        this.rebuildOptionGroups();
      },
    });
  }

  private rebuildOptionGroups(): void {
    const byProvider = new Map<string, LlmModelOption[]>();
    const providerOrder = ['auto', 'ollama'];

    for (const option of this.llmOptions) {
      const provider = (option.provider || option.provider_label || option.value.split(':', 1)[0] || 'other').toLowerCase();
      if (!byProvider.has(provider)) {
        byProvider.set(provider, []);
      }
      byProvider.get(provider)?.push(option);
    }

    const sortedProviders = [
      ...providerOrder.filter((provider) => byProvider.has(provider)),
      ...Array.from(byProvider.keys()).filter((provider) => !providerOrder.includes(provider)).sort(),
    ];

    this.llmOptionGroups = sortedProviders.map((provider) => ({
      key: provider,
      label: this.providerLabelMap[provider] || provider,
      options: byProvider.get(provider) || [],
    }));
  }

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.dragOver = true;
  }

  onDragLeave(): void { this.dragOver = false; }

  onDrop(e: DragEvent): void {
    e.preventDefault();
    this.dragOver = false;
    const file = e.dataTransfer?.files[0];
    if (file) this.handleFile(file);
  }

  onBoxClick(): void { this.fileInput.nativeElement.click(); }

  onBrowseClick(e: MouseEvent): void {
    e.stopPropagation();
    this.fileInput.nativeElement.click();
  }

  onInputChange(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) this.handleFile(file);
  }

  private handleFile(file: File): void {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!this.allowed.includes(ext)) {
      alert('Please upload a PDF, DOCX or DOC file.');
      return;
    }
    this.fileSelected.emit({ file, llmModel: this.selectedLlmModel });
  }
}
