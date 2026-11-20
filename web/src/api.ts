// Typed client for the FastAPI backend (src/invoice_extractor/api/app.py).

export interface LineItem {
  description: string;
  quantity: number | null;
  amount: number;
}

/** The output schema from the brief. */
export interface InvoiceResult {
  is_invoice: boolean;
  vendor: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  currency: string | null;
  line_items: LineItem[] | null;
  tax_total: number | null;
  total: number | null;
}

export type FieldName = keyof InvoiceResult;
export type Severity = "error" | "warning" | "info";

export interface Issue {
  code: string;
  severity: Severity;
  message: string;
  field: string | null;
  retryable: boolean;
}

export interface Review {
  needs_review: boolean;
  confidence: number;
  reasons: string[];
}

export interface Usage {
  calls: number;
  input_tokens: number;
  image_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  cost_usd: number;
  priced: boolean;
}

export interface TaxLine {
  label: string;
  rate_percent: number | null;
  amount: number;
}

export interface Evidence {
  invoice_date_as_printed: string | null;
  date_reasoning: string | null;
  subtotal: number | null;
  tax_lines: TaxLine[];
  unit_prices: (number | null)[];
  uncertain_fields: string[];
}

export interface Attempt {
  attempt: number;
  purpose: "extraction" | "correction" | "verification";
  served_by: string;
  errors: string[];
  latency_ms: number;
  cost_usd: number;
}

export interface Meta {
  document: {
    name: string;
    kind: "pdf" | "image";
    pages: number;
    has_text_layer: boolean;
    scanned: boolean;
    rotations_applied: number[];
    warnings: string[];
  };
  status: "ok" | "needs_review" | "error";
  review: Review;
  issues: Issue[];
  model: string;
  served_by: string[];
  input_mode: string;
  classification: { document_type: string; reason: string; legibility: string };
  evidence: Evidence;
  attempts: Attempt[];
  usage: Usage;
  latency_ms: number;
  notes: string[];
}

export interface FieldComparison {
  field: FieldName;
  correct: boolean;
  expected: unknown;
  predicted: unknown;
  detail: string;
}

export interface PageRef {
  index: number;
  width: number;
  height: number;
  url: string;
}

/** One document open in the review workspace (a sample or an upload). */
export interface ReviewPayload {
  id: string;
  source: "sample" | "upload";
  file_name: string;
  set: "labelled" | "unlabelled" | null;
  pages: PageRef[];
  result: InvoiceResult | null;
  meta: Meta | null;
  ground_truth: InvoiceResult | null;
  comparison: FieldComparison[] | null;
}

export interface DocumentRow {
  code: string;
  file_name: string;
  set: "labelled" | "unlabelled";
  kind: "digital" | "scan" | "photo";
  result: InvoiceResult | null;
  status: "ok" | "needs_review" | "error" | "not_run";
  confidence: number | null;
  review_reasons: string[];
  cost_usd: number | null;
  latency_ms: number | null;
  fields_correct: number | null;
  fields_total: number | null;
}

export interface Health {
  api_key_configured: boolean;
  model: string;
  fallback_model: string | null;
  input_mode: string;
  thinking_level: string;
  prompt_version: string;
  price_per_m_tokens: { input: number; output: number } | null;
  prices_as_of: string;
  sample_pack_present: boolean;
}

export interface ValidationResponse {
  result: InvoiceResult | null;
  issues: Issue[];
  review: Review;
}

export interface FieldAccuracy {
  correct: number;
  total: number;
  accuracy: number;
  invoices_correct: number;
  invoices_total: number;
}

export interface EvalRun {
  model: string;
  input_mode: string;
  thinking_level: string;
  prompt_version: string;
  documents: number;
  source: string;
  perturbation?: string | null;
  orientation_fix?: boolean;
  second_read?: boolean;
  evaluated_at: string;
}

export interface ReviewAnalysis {
  documents: number;
  flagged: number;
  documents_with_errors: number;
  errors_caught: number;
  false_alarms: number;
  missed: string[];
  recall: number | null;
  precision: number | null;
  field_errors: number;
  field_errors_in_flagged: number;
  share_of_errors_in_flagged: number | null;
}

export interface CostSummary {
  documents: number;
  avg_input_tokens: number;
  avg_image_tokens: number;
  avg_output_tokens: number;
  avg_thinking_tokens: number;
  avg_calls: number;
  avg_cost_usd: number;
  total_cost_usd: number;
  cost_per_1000_docs_usd: number;
  avg_cost_by_source: Record<string, number>;
  avg_latency_ms: number | null;
  max_latency_ms: number | null;
}

export interface EvalDocument {
  name: string;
  source: string;
  is_invoice: boolean;
  error: string | null;
  flagged: boolean;
  confidence: number | null;
  review_reasons: string[];
  wrong_fields: string[];
  fields: FieldComparison[];
  cost_usd: number | null;
  attempts: number;
}

export interface EvalReport {
  run: EvalRun;
  field_accuracy: Record<FieldName | "all_fields", FieldAccuracy>;
  line_items: {
    expected_rows: number;
    predicted_rows: number;
    matched_rows: number;
    precision: number;
    recall: number;
    f1: number;
    description_accuracy: number;
    quantity_accuracy: number;
    amount_accuracy: number;
  };
  review: ReviewAnalysis;
  cost: CostSummary;
  documents: EvalDocument[];
}

export interface EvalListing {
  tag: string;
  group: "main" | "experiments";
  run: EvalRun;
  all_fields: FieldAccuracy;
  field_accuracy: EvalReport["field_accuracy"];
  line_items: EvalReport["line_items"];
  review: ReviewAnalysis;
  cost: CostSummary;
  failed: number;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(0, "network", "The server is not reachable. Is `python serve.py` running?");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error ?? { code: "http_" + response.status, message: body?.detail ?? response.statusText };
    throw new ApiError(response.status, error.code, error.message);
  }
  return body as T;
}

const json = (payload: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(payload),
});

export const api = {
  health: () => request<Health>("/api/health"),
  documents: () => request<DocumentRow[]>("/api/documents"),
  document: (code: string) => request<ReviewPayload>(`/api/documents/${encodeURIComponent(code)}`),
  reextract: (code: string) =>
    request<ReviewPayload>(`/api/documents/${encodeURIComponent(code)}/extract`, { method: "POST" }),
  extract: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ReviewPayload>("/api/extract", { method: "POST", body: form });
  },
  validate: (result: InvoiceResult, evidence: Partial<Evidence> | null, classification: Meta["classification"] | null) =>
    request<ValidationResponse>("/api/validate", json({ result, evidence, classification })),
  evaluations: () => request<EvalListing[]>("/api/evaluations"),
  evaluation: (tag: string) => request<EvalReport>(`/api/evaluations/${encodeURIComponent(tag)}`),
};
