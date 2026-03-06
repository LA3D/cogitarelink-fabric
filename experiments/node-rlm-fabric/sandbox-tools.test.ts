import { describe, it, expect } from "vitest";
import { createSandboxTools, sparqlResultsToJson } from "./sandbox-tools.js";

describe("sparqlResultsToJson", () => {
  it("serializes SPARQL JSON results to compact JSON", () => {
    const sparqlResults = {
      head: { vars: ["s", "p", "o"] },
      results: {
        bindings: [
          {
            s: { type: "uri", value: "http://example.org/obs-1" },
            p: { type: "uri", value: "http://www.w3.org/ns/sosa/hasResult" },
            o: { type: "literal", value: "42.5" },
          },
        ],
      },
    };
    const result = JSON.parse(sparqlResultsToJson(sparqlResults));
    expect(result).toHaveLength(1);
    expect(result[0].s).toBe("http://example.org/obs-1");
    expect(result[0].p).toBe("http://www.w3.org/ns/sosa/hasResult");
    expect(result[0].o).toBe("42.5");
  });

  it("handles multiple bindings", () => {
    const sparqlResults = {
      head: { vars: ["x"] },
      results: {
        bindings: [
          { x: { type: "uri", value: "http://example.org/a" } },
          { x: { type: "uri", value: "http://example.org/b" } },
        ],
      },
    };
    const result = JSON.parse(sparqlResultsToJson(sparqlResults));
    expect(result).toHaveLength(2);
    expect(result[0].x).toBe("http://example.org/a");
    expect(result[1].x).toBe("http://example.org/b");
  });

  it("truncates to maxChars", () => {
    const bindings = Array.from({ length: 100 }, (_, i) => ({
      s: { type: "uri", value: `http://example.org/item-${i}` },
    }));
    const sparqlResults = { head: { vars: ["s"] }, results: { bindings } };
    const result = sparqlResultsToJson(sparqlResults, 500);
    expect(result.length).toBeLessThanOrEqual(500 + 100);
    expect(result).toContain("[truncated");
  });
});

describe("createSandboxTools", () => {
  it("returns object with expected tool functions", () => {
    const tools = createSandboxTools({
      endpoint: "https://bootstrap.cogitarelink.ai",
      fabricFetch: globalThis.fetch,
    });
    expect(typeof tools.comunica_query).toBe("function");
    expect(typeof tools.fetchVoID).toBe("function");
    expect(typeof tools.fetchShapes).toBe("function");
    expect(typeof tools.fetchExamples).toBe("function");
    expect(typeof tools.fetchEntity).toBe("function");
  });

  it("comunica_query POSTs to /sparql", async () => {
    let capturedUrl = "";
    let capturedMethod = "";
    let capturedBody = "";
    const mockFetch = async (url: string | URL | Request, init?: RequestInit) => {
      capturedUrl = String(url);
      capturedMethod = init?.method ?? "GET";
      capturedBody = String(init?.body ?? "");
      return new Response(JSON.stringify({
        head: { vars: ["g"] },
        results: { bindings: [{ g: { type: "uri", value: "http://example.org/graph" } }] },
      }));
    };

    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.comunica_query("SELECT ?g WHERE { GRAPH ?g { ?s ?p ?o } }");
    expect(capturedUrl).toBe("https://example.org/sparql");
    expect(capturedMethod).toBe("POST");
    expect(capturedBody).toContain("query=");
    const parsed = JSON.parse(result);
    expect(parsed[0].g).toBe("http://example.org/graph");
  });

  it("fetchVoID calls correct URL with turtle accept", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string | URL | Request, init?: RequestInit) => {
      capturedUrl = String(url);
      capturedHeaders = Object.fromEntries(new Headers(init?.headers).entries());
      return new Response("<void-doc>");
    };

    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchVoID();
    expect(capturedUrl).toBe("https://example.org/.well-known/void");
    expect(capturedHeaders["accept"]).toBe("text/turtle");
    expect(result).toBe("<void-doc>");
  });

  it("fetchShapes calls correct URL", async () => {
    let capturedUrl = "";
    const mockFetch = async (url: string | URL | Request) => {
      capturedUrl = String(url);
      return new Response("<shapes>");
    };
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    await tools.fetchShapes();
    expect(capturedUrl).toBe("https://example.org/.well-known/shacl");
  });

  it("fetchExamples calls correct URL", async () => {
    let capturedUrl = "";
    const mockFetch = async (url: string | URL | Request) => {
      capturedUrl = String(url);
      return new Response("<examples>");
    };
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    await tools.fetchExamples();
    expect(capturedUrl).toBe("https://example.org/.well-known/sparql-examples");
  });

  it("fetchEntity builds correct entity URL", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string | URL | Request, init?: RequestInit) => {
      capturedUrl = String(url);
      capturedHeaders = Object.fromEntries(new Headers(init?.headers).entries());
      return new Response('{"@id": "urn:uuid:abc"}');
    };
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchEntity("abc-123");
    expect(capturedUrl).toBe("https://example.org/entity/abc-123");
    expect(capturedHeaders["accept"]).toBe("application/ld+json");
    expect(result).toContain("abc");
  });

  it("returns error string for non-ok responses", async () => {
    const mockFetch = async () => new Response("Not Found", { status: 404 });
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchVoID();
    expect(result).toContain("HTTP 404");
  });
});
