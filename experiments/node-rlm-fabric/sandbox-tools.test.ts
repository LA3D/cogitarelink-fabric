import { describe, it, expect } from "vitest";
import { createSandboxTools, bindingsToJson } from "./sandbox-tools.js";
import type { Bindings } from "@rdfjs/types";

/**
 * Create a mock RDF/JS Bindings object matching Comunica's output.
 * Bindings is iterable over [Variable, Term] tuples.
 */
function mockBindings(
  entries: Record<string, string>,
): Bindings {
  const pairs: [{ value: string }, { value: string }][] = Object.entries(
    entries,
  ).map(([k, v]) => [{ value: k }, { value: v }]);
  return {
    [Symbol.iterator]: () => pairs[Symbol.iterator](),
  } as unknown as Bindings;
}

describe("bindingsToJson", () => {
  it("serializes RDF/JS Bindings to compact JSON", () => {
    const bindings = [
      mockBindings({
        s: "http://example.org/obs-1",
        p: "http://www.w3.org/ns/sosa/hasResult",
        o: "42.5",
      }),
    ];
    const result = JSON.parse(bindingsToJson(bindings));
    expect(result).toHaveLength(1);
    expect(result[0].s).toBe("http://example.org/obs-1");
    expect(result[0].p).toBe("http://www.w3.org/ns/sosa/hasResult");
    expect(result[0].o).toBe("42.5");
  });

  it("handles multiple bindings", () => {
    const bindings = [
      mockBindings({ x: "http://example.org/a" }),
      mockBindings({ x: "http://example.org/b" }),
    ];
    const result = JSON.parse(bindingsToJson(bindings));
    expect(result).toHaveLength(2);
    expect(result[0].x).toBe("http://example.org/a");
    expect(result[1].x).toBe("http://example.org/b");
  });

  it("truncates to maxChars", () => {
    const bindings = Array.from({ length: 100 }, (_, i) =>
      mockBindings({ s: `http://example.org/item-${i}` }),
    );
    const result = bindingsToJson(bindings, 500);
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
    expect(typeof tools.fetchJsonLd).toBe("function");
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

describe("fetchJsonLd", () => {
  it("fetches URL with application/ld+json accept header", async () => {
    let capturedUrl = "";
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string | URL | Request, init?: RequestInit) => {
      capturedUrl = String(url);
      capturedHeaders = Object.fromEntries(new Headers(init?.headers).entries());
      return new Response('{"@context": "http://schema.org/", "@type": "Thing"}');
    };

    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchJsonLd("https://example.org/ontology/sosa");
    expect(capturedUrl).toBe("https://example.org/ontology/sosa");
    expect(capturedHeaders["accept"]).toBe("application/ld+json");
    expect(result).toContain("@context");
  });

  it("returns error string for non-ok responses", async () => {
    const mockFetch = async () => new Response("Not Found", { status: 404 });
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchJsonLd("https://example.org/bad");
    expect(result).toContain("HTTP 404");
  });

  it("returns error string for fetch failures", async () => {
    const mockFetch = async () => { throw new Error("Network error"); };
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: mockFetch as typeof fetch,
    });
    const result = await tools.fetchJsonLd("https://example.org/bad");
    expect(result).toContain("Fetch error");
  });
});

describe("jsonld namespace", () => {
  it("returns object with expand, compact, frame functions", () => {
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: globalThis.fetch,
    });
    expect(typeof tools.jsonld.expand).toBe("function");
    expect(typeof tools.jsonld.compact).toBe("function");
    expect(typeof tools.jsonld.frame).toBe("function");
  });

  it("expand resolves prefixes to full IRIs", async () => {
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: globalThis.fetch,
    });
    const doc = {
      "@context": { "schema": "http://schema.org/" },
      "@type": "schema:Thing",
      "schema:name": "Test",
    };
    const expanded = await tools.jsonld.expand(doc);
    expect(expanded).toBeInstanceOf(Array);
    expect(expanded.length).toBeGreaterThan(0);
    const first = expanded[0];
    expect(first["@type"]).toContain("http://schema.org/Thing");
  });

  it("compact applies context to expanded document", async () => {
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: globalThis.fetch,
    });
    const expanded = [{
      "@type": ["http://schema.org/Thing"],
      "http://schema.org/name": [{ "@value": "Test" }],
    }];
    const ctx = { "schema": "http://schema.org/", "name": "schema:name" };
    const compacted = await tools.jsonld.compact(expanded, ctx);
    expect(compacted["name"]).toBe("Test");
  });

  it("frame extracts matching subgraph", async () => {
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: globalThis.fetch,
    });
    const doc = {
      "@context": { "schema": "http://schema.org/" },
      "@graph": [
        { "@type": "schema:Person", "schema:name": "Alice" },
        { "@type": "schema:Thing", "schema:name": "Widget" },
      ],
    };
    const frameDoc = {
      "@context": { "schema": "http://schema.org/" },
      "@type": "schema:Person",
    };
    const framed = await tools.jsonld.frame(doc, frameDoc);
    expect(framed["schema:name"]).toBe("Alice");
  });

  it("expand returns error string on invalid input", async () => {
    const tools = createSandboxTools({
      endpoint: "https://example.org",
      fabricFetch: globalThis.fetch,
    });
    const result = await tools.jsonld.expand("not a valid json-ld doc");
    expect(typeof result).toBe("string");
    expect(result as unknown as string).toContain("error");
  });
});
