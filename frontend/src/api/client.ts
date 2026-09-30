import { tokenStore } from '@/auth/token-store';
import type {
  Attempt,
  Classroom,
  Dashboard,
  Paginated,
  Stroke,
  Subject,
  User,
  Worksheet,
  WorksheetBundle,
} from './types';

const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

let refreshing: Promise<string | null> | null = null;

async function refreshAccess(): Promise<string | null> {
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = await tokenStore.refresh();
      if (!refresh) return null;
      const res = await fetch(`${API_URL}/api/v1/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });
      if (!res.ok) {
        await tokenStore.clear();
        return null;
      }
      const data = (await res.json()) as { access: string };
      const current = await tokenStore.refresh();
      await tokenStore.save(data.access, current ?? '');
      return data.access;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = await tokenStore.access();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });

  if (res.status === 401 && retry) {
    const next = await refreshAccess();
    if (next) return request<T>(path, init, false);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API ${status}: ${body.slice(0, 200)}`);
  }
}

interface TokenPair {
  access: string;
  refresh: string;
}

export const api = {
  async login(username: string, password: string): Promise<void> {
    const pair = await request<TokenPair>('/api/v1/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    await tokenStore.save(pair.access, pair.refresh);
  },

  async logout(): Promise<void> {
    await tokenStore.clear();
  },

  me: () => request<User>('/api/v1/users/me/'),

  subjects: () => request<Paginated<Subject>>('/api/v1/subjects/'),

  worksheets: (subjectId?: number) =>
    request<Paginated<Worksheet>>(
      `/api/v1/worksheets/${subjectId ? `?subject=${subjectId}` : ''}`,
    ),

  worksheetBundle: (id: number) =>
    request<WorksheetBundle>(`/api/v1/worksheets/${id}/bundle/`),

  startAttempt: (worksheetId: number) =>
    request<Attempt>('/api/v1/attempts/', {
      method: 'POST',
      body: JSON.stringify({ worksheet_id: worksheetId }),
    }),

  uploadStrokes: (attemptId: number, pageId: number, strokes: Stroke[]) =>
    request(`/api/v1/attempts/${attemptId}/pages/`, {
      method: 'POST',
      body: JSON.stringify({ worksheet_page: pageId, strokes }),
    }),

  submitAttempt: (attemptId: number) =>
    request<Attempt>(`/api/v1/attempts/${attemptId}/submit/`, {
      method: 'POST',
    }),

  returnAttempt: (attemptId: number) =>
    request<Attempt>(`/api/v1/attempts/${attemptId}/return/`, {
      method: 'POST',
    }),

  attempts: (status?: string) =>
    request<Paginated<Attempt>>(
      `/api/v1/attempts/${status ? `?status=${status}` : ''}`,
    ),

  attempt: (id: number) => request<Attempt>(`/api/v1/attempts/${id}/`),

  saveMark: (
    attemptId: number,
    mark: { score: number; max_score: number; feedback: string },
    markId?: number,
  ) =>
    markId
      ? request(`/api/v1/marks/${markId}/`, {
          method: 'PATCH',
          body: JSON.stringify(mark),
        })
      : request('/api/v1/marks/', {
          method: 'POST',
          body: JSON.stringify({ attempt: attemptId, ...mark }),
        }),

  dashboard: () => request<Dashboard>('/api/v1/dashboard/'),

  classrooms: () => request<Paginated<Classroom>>('/api/v1/classrooms/'),

  createUser: (u: {
    username: string;
    password: string;
    role: string;
    first_name?: string;
    last_name?: string;
    email?: string;
  }) =>
    request<User>('/api/v1/users/', {
      method: 'POST',
      body: JSON.stringify(u),
    }),

  createSubject: (name: string) =>
    request<Subject>('/api/v1/subjects/', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  createWorksheet: (w: {
    subject: number;
    title: string;
    description?: string;
    exam_year?: number | null;
    source?: string;
    status?: string;
  }) =>
    request<Worksheet>('/api/v1/worksheets/', {
      method: 'POST',
      body: JSON.stringify(w),
    }),

  updateWorksheet: (id: number, patch: Partial<Worksheet>) =>
    request<Worksheet>(`/api/v1/worksheets/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),

  uploadUrl: (worksheetId: number, filename: string, contentType: string) =>
    request<{ key: string; upload_url: string }>(
      `/api/v1/worksheets/${worksheetId}/upload-url/`,
      {
        method: 'POST',
        body: JSON.stringify({ filename, content_type: contentType }),
      },
    ),

  registerPage: (
    worksheetId: number,
    page: {
      image_key: string;
      order: number;
      width?: number;
      height?: number;
    },
  ) =>
    request(`/api/v1/worksheets/${worksheetId}/pages/`, {
      method: 'POST',
      body: JSON.stringify(page),
    }),

  rasterize: (worksheetId: number, pdfKey: string) =>
    request<{ task_id: string }>(`/api/v1/worksheets/${worksheetId}/rasterize/`, {
      method: 'POST',
      body: JSON.stringify({ pdf_key: pdfKey }),
    }),

  registerAnswerSheet: (
    worksheetId: number,
    sheet: { file_key: string; notes?: string },
  ) =>
    request(`/api/v1/worksheets/${worksheetId}/answer-sheets/`, {
      method: 'POST',
      body: JSON.stringify(sheet),
    }),
};
