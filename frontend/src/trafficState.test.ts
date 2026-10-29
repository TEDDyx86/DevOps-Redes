import { describe, it, expect } from "vitest";
import {
  trafficValue,
  currentTraffic,
  type TrafficService,
} from "./trafficState";

const row: TrafficService = {
  id: "smtp",
  name: "SMTP",
  unit: "msg/min",
  scale: 60,
  status: "anomalous",
  rate: 0.5,
  baseline: 0.05,
  threshold: 0.15,
  calibrated_at: 100,
  checked_at: 200,
  learning_seconds: 120,
};
describe("referência de tráfego", () => {
  it("converte taxa, referência e limiar SMTP na mesma unidade", () => {
    expect(
      [row.rate, row.baseline, row.threshold].map((value) =>
        trafficValue(value, row.scale),
      ),
    ).toEqual([30, 3, 9]);
    expect(trafficValue(0, 60)).toBe(0);
    expect(trafficValue(null, 60)).toBeNull();
  });
  it("expira o estado atual sem apagar a referência persistida", () => {
    const current = currentTraffic(row, 225);
    expect(current.status).toBe("unknown");
    expect(current.rate).toBeNull();
    expect(current.baseline).toBe(0.05);
    expect(currentTraffic(row, 205).status).toBe("anomalous");
  });
});
