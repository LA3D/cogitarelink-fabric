import { QueryEngine } from "@comunica/query-sparql";
import type { Bindings } from "@rdfjs/types";
import jsonldLib from "jsonld";

const MAX_RESULT_CHARS = 10_000;

/**
 * Serialize RDF/JS Bindings (from Comunica queryBindings) into a compact
 * JSON string for the agent. Each binding becomes a {varName: termValue} object.
 * Truncates beyond maxChars to keep LLM context bounded.
 */
export function bindingsToJson(
  bindings: Bindings[],
  maxChars: number = MAX_RESULT_CHARS,
): string {
  const rows: Record<string, string>[] = [];
  for (const binding of bindings) {
    const row: Record<string, string> = {};
    for (const [variable, term] of binding) {
      row[variable.value] = term.value;
    }
    rows.push(row);
  }
  let json = JSON.stringify(rows, null, 2);
  if (json.length > maxChars) {
    json =
      json.slice(0, maxChars) +
      `\n[truncated at ${maxChars} chars, ${rows.length} total rows]`;
  }
  return json;
}

export interface SandboxToolsConfig {
  endpoint: string;
  fabricFetch: typeof fetch;
}

/**
 * Create the sandbox-injected tool functions for the RLM agent.
 * - comunica_query: SPARQL SELECT/CONSTRUCT via Comunica (W3C spec-tested)
 * - fetchVoID / fetchShapes / fetchExamples: .well-known/* discovery
 * - fetchEntity: dereference an entity by ID
 */
export function createSandboxTools(config: SandboxToolsConfig) {
  const { endpoint, fabricFetch } = config;
  const engine = new QueryEngine();

  async function comunica_query(
    query: string,
    sources?: string[],
  ): Promise<string> {
    const effectiveSources = (sources ?? [`${endpoint}/sparql`]).map(
      (s) => ({ type: "sparql" as const, value: s }),
    );
    try {
      const bindingsStream = await engine.queryBindings(query, {
        sources: effectiveSources,
        fetch: fabricFetch,
      });
      const results = await bindingsStream.toArray();
      return bindingsToJson(results);
    } catch (err) {
      return `SPARQL error: ${err instanceof Error ? err.message : String(err)}`;
    }
  }

  async function fetchVoID(): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/.well-known/void`, {
      headers: { Accept: "text/turtle" },
    });
    if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
    return resp.text();
  }

  async function fetchShapes(): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/.well-known/shacl`, {
      headers: { Accept: "text/turtle" },
    });
    if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
    return resp.text();
  }

  async function fetchExamples(): Promise<string> {
    const resp = await fabricFetch(
      `${endpoint}/.well-known/sparql-examples`,
      { headers: { Accept: "text/turtle" } },
    );
    if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
    return resp.text();
  }

  async function fetchEntity(entityId: string): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/entity/${entityId}`, {
      headers: { Accept: "application/ld+json" },
    });
    if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
    return resp.text();
  }

  async function fetchJsonLd(url: string): Promise<string> {
    try {
      const resp = await fabricFetch(url, {
        headers: { Accept: "application/ld+json" },
      });
      if (!resp.ok) return `HTTP ${resp.status}: ${await resp.text()}`;
      const text = await resp.text();
      if (text.length > MAX_RESULT_CHARS) {
        return (
          text.slice(0, MAX_RESULT_CHARS) +
          `\n[truncated at ${MAX_RESULT_CHARS} chars, full document is ${text.length} chars. Use comunica_query() with SPARQL for targeted access, or jsonld.frame() to extract specific patterns.]`
        );
      }
      return text;
    } catch (err) {
      return `Fetch error: ${err instanceof Error ? err.message : String(err)}`;
    }
  }

  const jsonld = {
    async expand(doc: unknown): Promise<unknown> {
      try {
        return await jsonldLib.expand(doc as jsonldLib.JsonLdDocument);
      } catch (err) {
        return `jsonld.expand error: ${err instanceof Error ? err.message : String(err)}`;
      }
    },
    async compact(doc: unknown, context: unknown): Promise<unknown> {
      try {
        return await jsonldLib.compact(
          doc as jsonldLib.JsonLdDocument,
          context as jsonldLib.ContextDocument,
        );
      } catch (err) {
        return `jsonld.compact error: ${err instanceof Error ? err.message : String(err)}`;
      }
    },
    async frame(doc: unknown, frameDoc: unknown): Promise<unknown> {
      try {
        return await jsonldLib.frame(
          doc as jsonldLib.JsonLdDocument,
          frameDoc as jsonldLib.Frame,
        );
      } catch (err) {
        return `jsonld.frame error: ${err instanceof Error ? err.message : String(err)}`;
      }
    },
  };

  return { comunica_query, fetchVoID, fetchShapes, fetchExamples, fetchEntity, fetchJsonLd, jsonld };
}
