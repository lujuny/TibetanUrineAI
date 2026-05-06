import type {
  CaseCreatePayload,
  CaseSummary,
  HealthResponse,
  ImageUploadResponse,
  ObservationCreatePayload,
  ObservationUpdatePayload,
  ObservationRecord
} from "../types/domain";

const API_BASE = "/api";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("API health check failed");
  }
  return response.json();
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json();
}

export function listCases(): Promise<CaseSummary[]> {
  return requestJson<CaseSummary[]>("/cases");
}

export function createCase(payload: CaseCreatePayload): Promise<CaseSummary> {
  return requestJson<CaseSummary>("/cases", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getCase(caseId: string): Promise<CaseSummary> {
  return requestJson<CaseSummary>(`/cases/${caseId}`);
}

export function listCaseObservations(caseId: string): Promise<ObservationRecord[]> {
  return requestJson<ObservationRecord[]>(`/cases/${caseId}/observations`);
}

export function getObservation(observationId: string): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>(`/observations/${observationId}`);
}

export async function uploadImage(file: File): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/uploads`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export function createObservation(payload: ObservationCreatePayload): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>("/observations", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateObservation(
  observationId: string,
  payload: ObservationUpdatePayload
): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>(`/observations/${observationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function assessObservationQuality(observationId: string): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>(`/observations/${observationId}/quality`, {
    method: "POST"
  });
}

export function extractObservationFeatures(observationId: string): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>(`/observations/${observationId}/features`, {
    method: "POST"
  });
}

export function normalizeObservationSymptoms(observationId: string): Promise<ObservationRecord> {
  return requestJson<ObservationRecord>(`/observations/${observationId}/symptoms`, {
    method: "POST"
  });
}
