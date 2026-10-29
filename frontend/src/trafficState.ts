export interface TrafficService {
  id: string;
  name: string;
  unit: string;
  scale: number;
  status: "normal" | "anomalous" | "learning" | "unknown";
  rate: number | null;
  baseline: number | null;
  threshold: number | null;
  calibrated_at: number | null;
  checked_at: number | null;
  learning_seconds: number;
}
export interface TrafficOverview {
  generated_at: number;
  window_seconds: number;
  factor: number;
  learning_required_seconds: number;
  services: TrafficService[];
}
export function trafficValue(
  value: number | null,
  scale: number,
): number | null {
  return value == null || !Number.isFinite(value) ? null : value * scale;
}
export function currentTraffic(
  row: TrafficService,
  now: number,
): TrafficService {
  return row.checked_at == null ||
    now - row.checked_at > 20 ||
    row.checked_at > now + 5
    ? { ...row, status: "unknown", rate: null }
    : row;
}
