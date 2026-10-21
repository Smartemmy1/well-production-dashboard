import type {
  Alert,
  DashboardSummary,
  ProductionInput,
  ProductionPoint,
  UploadResult,
  WellStatus,
  WellSummary,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    // FastAPI puts a readable message in `detail` (a string, or a list for validation errors).
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join("; ")
          : `Request failed (${res.status})`;
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

function query(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  fields: () => request<string[]>("/api/wells/fields"),
  wells: (field?: string) => request<WellSummary[]>(`/api/wells${query({ field })}`),
  well: (id: number) => request<WellSummary>(`/api/wells/${id}`),
  setStatus: (id: number, status: WellStatus) =>
    request<WellSummary>(`/api/wells/${id}`, json("PATCH", { status })),
  production: (id: number, start?: string) =>
    request<ProductionPoint[]>(`/api/wells/${id}/production${query({ start })}`),
  addProduction: (id: number, data: ProductionInput) =>
    request<ProductionPoint>(`/api/wells/${id}/production`, json("POST", data)),
  dashboard: (field: string | undefined, days: number) =>
    request<DashboardSummary>(`/api/dashboard${query({ field, days })}`),
  alerts: (field?: string) => request<Alert[]>(`/api/alerts${query({ field })}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResult>("/api/production/upload", { method: "POST", body: form });
  },
};
