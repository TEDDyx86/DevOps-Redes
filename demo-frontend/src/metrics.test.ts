import { describe, expect, it } from "vitest";
import { parseDemoCounters } from "./metrics";

const exposition = [
  "# HELP demo_http_requests_total Completed HTTP requests",
  "# TYPE demo_http_requests_total counter",
  'demo_http_requests_total{path="/work",status="200"} 12.0',
  'demo_http_requests_total{path="/work",status="503"} 3.0',
  'demo_http_requests_total{path="/mode",status="200"} 2.0',
  'demo_other_metric_total{path="/work",status="200"} 99.0',
].join("\n");

describe("parseDemoCounters", () => {
  it("sums totals and groups by status", () => {
    const data = parseDemoCounters(exposition);
    expect(data.total).toBe(17);
    expect(data.byStatus).toEqual({ "200": 14, "503": 3 });
  });

  it("counts work requests separately", () => {
    expect(parseDemoCounters(exposition).work).toBe(15);
  });

  it("returns zeros for exposition without demo counters", () => {
    const data = parseDemoCounters("# HELP demo_http_duration_seconds nothing\n");
    expect(data).toEqual({ total: 0, byStatus: {}, work: 0 });
  });
});
