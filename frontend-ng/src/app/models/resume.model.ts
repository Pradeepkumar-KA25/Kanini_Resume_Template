export interface ContactInfo {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
}

export interface Experience {
  title: string;
  company: string;
  dates: string;
  location: string;
  responsibilities: string[];
  company_name: string;
  company_sector: string;
  projects: Project[];
}

export interface Education {
  degree: string;
  institution: string;
  year: string;
  gpa: string;
}

export interface Project {
  name: string;
  client: string;
  duration: string;
  role: string;
  description: string;
  technologies: string[];
  responsibilities: string[];
}

export interface TemplateMetadata {
  id: string;
  display_name: string;
  description: string;
  version: string;
  enabled: boolean;
  supported_outputs: Array<'html' | 'docx' | 'pdf'>;
  page_size: 'LETTER' | 'A4';
  user_created?: boolean;
}

export interface TemplateDraft {
  draft_id: string;
  status: 'uploaded' | 'generated';
  filename: string;
  extracted_data: ResumeData;
}

export interface TemplateSpec {
  page: { size: 'A4' | 'LETTER'; orientation: 'portrait'; margin_inches: number };
  typography: { font_family: 'Arial' | 'Calibri' | 'Georgia' | 'Helvetica' | 'Times New Roman'; base_size_pt: number; heading_size_pt: number };
  colors: { text: string; accent: string; muted: string };
  header: { layout: 'centered' | 'left'; contact_layout: 'inline' | 'stacked'; show_divider: boolean };
  layout: { columns: 1 | 2; sidebar_position: 'left' | 'right' | 'none'; section_alignment: 'left' | 'justified' };
  sections: Array<'summary' | 'skills' | 'experience' | 'projects' | 'education' | 'certifications' | 'achievements'>;
  spacing: { section_gap_pt: number; line_height: number; divider_style: 'none' | 'solid' | 'accent'; skill_style: 'inline' | 'bullets' | 'tags' };
}

export interface GeneratedTemplateDraft extends TemplateDraft {
  status: 'generated';
  template_spec: TemplateSpec;
  suggested_description: string;
  preview_html: string;
}

export interface SavedUserTemplate {
  template_id: string;
  display_name: string;
  description: string;
  status: 'saved';
}

export interface UserTemplateDetail { template_id: string; display_name: string; description: string; template_spec: TemplateSpec; has_source: boolean; }
export type UserTemplateAction = 'edit' | 'rename' | 'regenerate' | 'delete';

export interface PreviewResponse {
  session_id: string;
  template_id: string;
  output_format: 'html';
  preview_html: string;
}

export interface SavedResumeSummary { id: string; name: string; email: string; filename: string; created_at: string; }

export interface ResumeData {
  contact: ContactInfo;
  summary: string;
  skills: Record<string, string[]>;
  experience: Experience[];
  education: Education[];
  certifications: string[];
  projects: Project[];
  achievements: string[];
  additional_sections: Record<string, string[]>;
}

export interface UploadResponse {
  session_id: string;
  resume_data: ResumeData;
  selected_template_id?: string;
  llm_requested?: string;
  llm_used?: string;
  preview_html: {
    template1: string;
    template2: string;
  };
}

export interface LlmModelOption {
  label: string;
  value: string;
  available: boolean;
  reason?: string;
  provider?: string;
  provider_label?: string;
}

export type AppStatus = 'home' | 'idle' | 'uploading' | 'review' | 'templates' | 'template-create' | 'template-generating' | 'template-draft-preview' | 'template-manage' | 'preview' | 'download' | 'saved' | 'success' | 'error';
