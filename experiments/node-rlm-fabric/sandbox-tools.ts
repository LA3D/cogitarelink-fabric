import { QueryEngine } from "@comunica/query-sparql";
import type { Bindings } from "@rdfjs/types";

const MAX_RESULT_CHARS = 10_000;

/**
 * Serialize an array of RDF/JS Bindings into a JSON string.
 * Each binding becomes a {varName: termValue} object.
 * Truncates output beyond maxChars to keep LLM context bounded.
 */
export function bindingsToJson(
  bindings: Bindings[],
  maxChars: number = MAX_RESULT_CHARS,
): string {
  const rows: Record<string, string>[] = [];
  for (const binding of bindings) {
    const row: Record<string, string> = {};
    // Bindings implements Iterable<[Variable, Term]>
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
 * - comunica_query: SPARQL SELECT via Comunica against the fabric endpoint
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
    const effectiveSources = sources ?? [`${endpoint}/sparql`];
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

  return { comunica_query, fetchVoID, fetchShapes, fetchExamples, fetchEntity };
}
