import { describe, it, expect } from "vitest";
import { buildInsertQuery, buildDropQuery } from "./setup-teardown.js";

describe("buildInsertQuery", () => {
  it("builds INSERT DATA for observation record", () => {
    const query = buildInsertQuery(
      "https://bootstrap.cogitarelink.ai/graph/observations",
      {
        subject: "https://bootstrap.cogitarelink.ai/entity/test-obs-1",
        "sosa:madeBySensor": "https://bootstrap.cogitarelink.ai/entity/sensor-1",
        "sosa:hasSimpleResult": "23.5",
        "sosa:resultTime": "2026-02-22T12:00:00Z",
      },
    );
    expect(query).toContain("INSERT DATA");
    expect(query).toContain("GRAPH");
    expect(query).toContain("sosa:Observation");
    expect(query).toContain("23.5");
  });

  it("builds INSERT DATA for sensor entity", () => {
    const query = buildInsertQuery(
      "https://bootstrap.cogitarelink.ai/graph/entities",
      {
        subject: "https://bootstrap.cogitarelink.ai/entity/sensor-1",
        "rdfs:label": "sensor-1",
        "sosa:observes": "http://sweetontology.net/matrRockite/pH",
        record_type: "sensor",
      },
    );
    expect(query).toContain("INSERT DATA");
    expect(query).toContain("sosa:Sensor");
    expect(query).toContain("sensor-1");
  });
});

describe("buildDropQuery", () => {
  it("builds DROP SILENT GRAPH", () => {
    const query = buildDropQuery("https://bootstrap.cogitarelink.ai/graph/observations");
    expect(query).toBe("DROP SILENT GRAPH <https://bootstrap.cogitarelink.ai/graph/observations>");
  });
});
