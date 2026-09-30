/** Mirror of the Django API shapes in the backend DRF serializers. */

export type Role = 'admin' | 'teacher' | 'student' | 'parent';

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
}

export interface Subject {
  id: number;
  name: string;
  slug: string;
  description: string;
  topics: Topic[];
}

export interface Topic {
  id: number;
  subject: number;
  name: string;
  order: number;
}

export interface WorksheetPage {
  id: number;
  order: number;
  image_key: string;
  width: number | null;
  height: number | null;
  answer_regions: { x: number; y: number; w: number; h: number; label?: string }[];
}

export interface AnswerSheet {
  id: number;
  file_key: string;
  notes: string;
  uploaded_at: string;
}

export interface Worksheet {
  id: number;
  subject: number;
  subject_name: string;
  topic: number | null;
  title: string;
  description: string;
  exam_year: number | null;
  source: string;
  status: 'draft' | 'published';
  pages: WorksheetPage[];
  answer_sheets: AnswerSheet[];
  created_at: string;
  updated_at: string;
}

export interface PageDownload {
  page_id: number;
  order: number;
  url: string;
  width: number | null;
  height: number | null;
  answer_regions: WorksheetPage['answer_regions'];
}

export interface WorksheetBundle extends Worksheet {
  page_downloads: PageDownload[];
}

export type AttemptStatus =
  | 'in_progress'
  | 'submitted'
  | 'grading'
  | 'graded'
  | 'returned';

export interface StrokePoint {
  x: number; // normalized 0–1
  y: number;
  t: number;
  pressure?: number;
}

export interface Stroke {
  points: StrokePoint[];
  color: string;
  width: number;
}

export interface PageSubmission {
  id: number;
  worksheet_page: number;
  strokes_key: string;
  image_key: string;
  url: string | null;
  uploaded_at: string;
}

export interface GradeJob {
  id: number;
  status: 'pending' | 'running' | 'done' | 'failed';
  transcribe_model: string;
  grade_model: string;
  transcript: Record<string, unknown>;
  decisions: Record<string, unknown>;
  error: string;
  created_at: string;
  finished_at: string | null;
}

export interface Mark {
  id: number;
  attempt: number;
  score: number;
  max_score: number;
  per_page: Record<string, number>;
  feedback: string;
  auto_suggested: boolean;
  marked_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface Attempt {
  id: number;
  student: User;
  worksheet: Worksheet;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  returned_at: string | null;
  pages: PageSubmission[];
  mark: Mark | null;
  grade_jobs: GradeJob[];
}

export interface Dashboard {
  attempts_total: number;
  attempts_by_status: Record<string, number>;
  returned_avg_percent: number | null;
  submitted_pending_review: number;
}

export interface Classroom {
  id: number;
  name: string;
  teacher: User;
  enrollments: { id: number; student: User }[];
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
