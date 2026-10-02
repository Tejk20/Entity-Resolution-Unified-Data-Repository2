export type Dataset = {
  id: number;
  name: string;
  source_tag: string;
  description: string;
  status: string;
  record_count: number;
  created_at: string;
  updated_at: string;
  file_count: number;
  table_count: number;
};

export type Job = {
  id: number;
  dataset_id: number | null;
  stage: string;
  progress: number;
  message: string;
  records_processed: number;
  records_total: number;
  matches_found: number;
  new_entities: number;
  duplicates_caught: number;
  started_at: string;
  finished_at: string | null;
  error: string;
};

export type Stats = {
  total_records: number;
  total_sources: number;
  total_datasets: number;
  matched_entities: number;
  unmatched_entities: number;
  total_entities: number;
  duplicates_caught: number;
  jobs_completed: number;
  avg_processing_seconds: number;
  last_job_seconds: number;
  pipeline_stages: { stage: string; count: number }[];
};

export type MappingSuggestion = {
  source_column: string;
  canonical_field: string | null;
  confidence: number;
  reason: string;
};

export type TableMapping = {
  table_id: number;
  table_name: string;
  columns: string[];
  mapping: Record<string, string>;
  suggestions: MappingSuggestion[];
  mapping_confirmed: boolean;
  row_count: number;
};

export type FieldAttribution = {
  field_name: string;
  original_value: string;
  normalized_value: string;
  source_db: string;
  source_table: string;
  row_id: string;
  timestamp: string;
  is_primary: boolean;
};

export type EntityCard = {
  id: number;
  status: string;
  display_name: string;
  match_count: number;
  source_count: number;
  created_at: string;
  updated_at: string;
  identifiers: Record<string, string[]>;
  fields: FieldAttribution[];
  linked_sources: {
    dataset_id: number;
    dataset_name: string;
    source_tag: string;
    table_name: string;
    row_id: string;
    raw: Record<string, string>;
  }[];
  merged: Record<string, string>;
};

export type SearchResult = {
  query: string;
  hops: {
    hop: number;
    identifier_type: string;
    identifier_value: string;
    records_found: number;
    new_identifiers: { identifier_type: string; identifier_value: string }[];
  }[];
  entity: EntityCard | null;
  records_visited: number;
  datasets_touched: string[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  stats: () => request<Stats>("/api/stats"),
  datasets: () => request<Dataset[]>("/api/datasets"),
  dataset: (id: number) => request<Dataset>(`/api/datasets/${id}`),
  createDataset: (payload: { name: string; source_tag: string; description: string }) =>
    request<Dataset>("/api/datasets", { method: "POST", body: JSON.stringify(payload) }),
  upload: async (id: number, files: FileList, partName = "") => {
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    form.append("part_name", partName);
    const res = await fetch(`/api/datasets/${id}/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  inspect: (id: number) => request(`/api/datasets/${id}/inspect`, { method: "POST" }),
  mappings: (id: number) => request<TableMapping[]>(`/api/datasets/${id}/mappings`),
  saveMapping: (datasetId: number, tableId: number, mapping: Record<string, string>) =>
    request(`/api/datasets/${datasetId}/tables/${tableId}/mapping`, {
      method: "PUT",
      body: JSON.stringify({ mapping }),
    }),
  confirmMappings: (id: number) =>
    request(`/api/datasets/${id}/confirm-mappings`, { method: "POST" }),
  process: (id: number, autoConfirm = false) =>
    request(`/api/datasets/${id}/process?auto_confirm=${autoConfirm}`, { method: "POST" }),
  jobs: (datasetId?: number) =>
    request<Job[]>(datasetId ? `/api/jobs?dataset_id=${datasetId}` : "/api/jobs"),
  job: (id: number) => request<Job>(`/api/jobs/${id}`),
  search: (query: string, identifierType?: string) =>
    request<SearchResult>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, identifier_type: identifierType || null }),
    }),
  entities: (status?: string) =>
    request<{ total: number; items: EntityCard[] }>(
      status ? `/api/entities?status=${status}` : "/api/entities"
    ),
  entity: (id: number) => request<EntityCard>(`/api/entities/${id}`),
  samples: () => request<{ files: { name: string; size: number; path: string }[] }>("/api/samples"),
  bootstrap: () => request("/api/bootstrap", { method: "POST" }),
  health: () => request<{ status: string }>("/api/health"),
};
