import type { ServiceSummary, Status } from "./types";

export function currentService(
  service: ServiceSummary,
  generatedAt: number,
  now: number,
): ServiceSummary {
  if (
    now - generatedAt > 20 ||
    service.checked_at == null ||
    now - service.checked_at > 20 ||
    service.checked_at > now + 5
  ) {
    return {
      ...service,
      status: "unknown",
      latency_ms: null,
      availability_percent: null,
    };
  }
  return service;
}

export function combinedStatus(statuses: Status[]): Status {
  if (!statuses.length) return "unknown";
  if (statuses.includes("critical")) return "critical";
  if (statuses.includes("warning")) return "warning";
  if (statuses.includes("unknown")) return "unknown";
  return "ok";
}

export const emptyPostgres: ServiceSummary = {
  id: "postgres",
  name: "PostgreSQL",
  protocol: "SQL",
  target: "postgres:5432/lab_network",
  status: "unknown",
  checked_at: null,
  latency_ms: null,
  availability_percent: null,
};
