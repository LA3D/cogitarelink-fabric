const MAX_RESULT_CHARS = 10_000;

interface SparqlBinding {
  [varName: string]: { type: string; value: string; datatype?: string };
}

interface SparqlResults {
  head: { vars: string[] };
  results: { bindings: SparqlBinding[] };
}

/**
 * Serialize SPARQL JSON results into a compact JSON string for the agent.
 * Truncates beyond maxChars to keep LLM context bounded.
 */
export function sparqlResultsToJson(
  sparqlResults: SparqlResults,
  maxChars: number = MAX_RESULT_CHARS,
): string {
  const rows: Record<string, string>[] = [];
  for (const binding of sparqlResults.results.bindings) {
    const row: Record<string, string> = {};
    for (const [varName, term] of Object.entries(binding)) {
      row[varName] = term.value;
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
 * - comunica_query: SPARQL SELECT via POST to fabric /sparql endpoint
 * - fetchVoID / fetchShapes / fetchExamples: .well-known/* discovery
 * - fetchEntity: dereference an entity by ID
 */
export function createSandboxTools(config: SandboxToolsConfig) {
  const { endpoint, fabricFetch } = config;

  async function comunica_query(
    query: string,
    sources?: string[],
  ): Promise<string> {
    const sparqlUrl = sources?.[0] ?? `${endpoint}/sparql`;
    try {
      const resp = await fabricFetch(sparqlUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "Accept": "application/sparql-results+json",
        },
        body: `query=${encodeURIComponent(query)}`,
      });
      if (!resp.ok) {
        return `SPARQL error (HTTP ${resp.status}): ${await resp.text()}`;
      }
      const data = (await resp.json()) as SparqlResults;
      return sparqlResultsToJson(data);
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
