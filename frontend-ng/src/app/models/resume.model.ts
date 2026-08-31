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
}

export interface Education {
  degree: string;
  institution: string;
  year: string;
  gpa: string;
}

export interface Project {
  name: string;
  description: string;
  technologies: string[];
}

export interface ResumeData {
  contact: ContactInfo;
  summary: string;
  skills: Record<string, string[]>;
  experience: Experience[];
  education: Education[];
  certifications: string[];
  projects: Project[];
  achievements: string[];
}

export interface UploadResponse {
  session_id: string;
  resume_data: ResumeData;
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

export type AppStatus = 'idle' | 'uploading' | 'success' | 'error';
