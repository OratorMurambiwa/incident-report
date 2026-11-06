export const severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export const statuses = [
  "PENDING",
  "RECEIVED",
  "DIAGNOSED",
  "RESOLVED",
  "ANALYZING",
  "FAILED",
] as const;
export interface Incident {
  id: string;
  service: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}
export interface IncidentPage {
  content: Incident[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
}
export interface Statement {
  text: string;
  sources: string[];
}
export interface Diagnosis {
  id: string;
  mode: string;
  provider: string;
  model: string | null;
  summary: string;
  recommendations: string;
  uncertainty: string;
  likelyCauses: Statement[];
  investigationSteps: Statement[];
  suggestedRemediation: Statement[];
  citedRunbooks: string[];
  retrievedEvidence: {
    chunkId: string;
    source: string;
    similarity: number;
    excerpt: string;
  }[];
}
export interface Draft {
  service: string;
  title: string;
  description: string;
  severity: string;
}
export function validate(d: Draft): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [field, max] of [
    ["service", 100],
    ["title", 200],
    ["description", 10000],
  ] as const) {
    if (!d[field].trim()) errors[field] = "This field is required.";
    else if (d[field].length > max)
      errors[field] = `Use at most ${max} characters.`;
  }
  if (!(severities as readonly string[]).includes(d.severity))
    errors.severity = "Choose a valid severity.";
  return errors;
}
export function modeLabel(mode: string): string {
  return mode === "GENERATED"
    ? "AI-generated diagnosis"
    : mode === "RETRIEVAL_ONLY"
      ? "Retrieved evidence only"
      : "Legacy diagnosis";
}
export function listQuery(
  page: number,
  severity: string,
  status: string,
  service: string,
): string {
  const q = new URLSearchParams({ page: String(page), size: "20" });
  if (severity) q.set("severity", severity);
  if (status) q.set("status", status);
  if (service.trim()) q.set("service", service.trim());
  return "/api/incidents?" + q.toString();
}
