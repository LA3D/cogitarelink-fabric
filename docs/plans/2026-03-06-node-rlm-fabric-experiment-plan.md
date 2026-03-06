# node-rlm Fabric Experiment — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run SIO navigation tasks against the fabric using node-rlm's JS RLM engine with Comunica as the SPARQL layer, comparing behavior across tool conditions.

**Architecture:** Standalone experiment in `experiments/node-rlm-fabric/` that imports `runEval` from node-rlm (github dependency) and `@comunica/query-sparql` for all SPARQL interaction. Custom `fetch` wrapper handles VP auth + Caddy TLS. Four conditions control which sandbox tools the agent sees.

**Tech Stack:** TypeScript, node-rlm (github:openprose/node-rlm), @comunica/query-sparql, @comunica/query-sparql-link-traversal, jsonld, Node.js v25+

**Design doc:** `docs/plans/2026-03-06-node-rlm-fabric-experiment-design.md`

---

## Prerequisites

- node-rlm cloned at `~/dev/git/LA3D/agents/node-rlm`, built, tests passing (DONE)
- Phase 2.5a infrastructure complete — `/ontology/{vocab}`, `@context` files, `_inject_context()`, `void:vocabulary`, shapes JSON-LD (DONE)
- Docker fabric stack running at `https://bootstrap.cogitarelink.ai` (DONE)
- `ANTHROPIC_API_KEY` in environment
- `caddy-root.crt` exported from fabric stack (exists at repo root)

---

### Task 1: Scaffold — package.json and tsconfig

**Files:**
- Create: `experiments/node-rlm-fabric/package.json`
- Create: `experiments/node-rlm-fabric/tsconfig.json`

**Step 1: Create package.json**

```json
{
  "name": "node-rlm-fabric-experiment",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "experiment": "tsx run-experiment.ts",
    "test": "vitest --run"
  },
  "dependencies": {
    "node-rlm": "github:openprose/node-rlm",
    "@comunica/query-sparql": "^4.0.0",
    "@comunica/query-sparql-link-traversal": "^0.8.0",
    "jsonld": "^8.3.0"
  },
  "devDependencies": {
    "@types/jsonld": "^1.5.0",
    "@types/node": "^24.0.0",
    "tsx": "^4.0.0",
    "typescript": "^5.7.0",
    "vitest": "^3.2.0"
  }
}
```

**Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": ".",
    "declaration": false,
    "sourceMap": true
  },
  "include": ["*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 3: Run npm install**

Run: `cd experiments/node-rlm-fabric && npm install`
Expected: Installs all dependencies including node-rlm from GitHub.

**Step 4: Verify node-rlm import works**

Create a quick smoke test:
```bash
cd experiments/node-rlm-fabric && npx tsx -e "import { rlm } from 'node-rlm'; console.log('node-rlm imported OK')"
```
Expected: `node-rlm imported OK`

**Step 5: Verify Comunica import works**

```bash
cd experiments/node-rlm-fabric && npx tsx -e "import { QueryEngine } from '@comunica/query-sparql'; const e = new QueryEngine(); console.log('Comunica OK')"
```
Expected: `Comunica OK`

**Step 6: Commit**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
git add experiments/node-rlm-fabric/package.json experiments/node-rlm-fabric/tsconfig.json experiments/node-rlm-fabric/package-lock.json
git commit -m "[Agent: Claude] scaffold: node-rlm fabric experiment package

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Scoring function

**Files:**
- Create: `experiments/node-rlm-fabric/scoring.ts`
- Test: `experiments/node-rlm-fabric/scoring.test.ts`

**Step 1: Write the failing test**

```typescript
// scoring.test.ts
import { describe, it, expect } from "vitest";
import { substringMatch } from "./scoring.js";

describe("substringMatch", () => {
  it("matches case-insensitive substring", () => {
    expect(substringMatch("The answer is 23.5 degrees", "23.5")).toBe(1.0);
  });

  it("returns 0 for no match", () => {
    expect(substringMatch("no match here", "42")).toBe(0.0);
  });

  it("matches any alternative in array", () => {
    expect(substringMatch("result is mA", ["milliampere", "mA"])).toBe(1.0);
  });

  it("handles case differences", () => {
    expect(substringMatch("SOSA:OBSERVATION found", "sosa:observation")).toBe(1.0);
  });

  it("returns 0 for empty prediction", () => {
    expect(substringMatch("", "something")).toBe(0.0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd experiments/node-rlm-fabric && npx vitest --run scoring.test.ts`
Expected: FAIL — `Cannot find module './scoring.js'`

**Step 3: Write minimal implementation**

```typescript
// scoring.ts
export function substringMatch(
  predicted: string,
  expected: string | string[],
): number {
  const lower = predicted.toLowerCase();
  const targets = Array.isArray(expected) ? expected : [expected];
  return targets.some((e) => lower.includes(e.toLowerCase())) ? 1.0 : 0.0;
}
```

**Step 4: Run test to verify it passes**

Run: `cd experiments/node-rlm-fabric && npx vitest --run scoring.test.ts`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add experiments/node-rlm-fabric/scoring.ts experiments/node-rlm-fabric/scoring.test.ts
git commit -m "[Agent: Claude] feat: substring match scorer for node-rlm fabric experiment

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Authenticated fetch wrapper

Creates the custom `fetch` function that handles VP auth headers and Caddy TLS for both Comunica and discovery tools.

**Files:**
- Create: `experiments/node-rlm-fabric/fabric-fetch.ts`
- Test: `experiments/node-rlm-fabric/fabric-fetch.test.ts`

**Step 1: Write the failing test**

```typescript
// fabric-fetch.test.ts
import { describe, it, expect } from "vitest";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";

describe("createFabricFetch", () => {
  it("returns a function", () => {
    const f = createFabricFetch({ vpToken: "test-token" });
    expect(typeof f).toBe("function");
  });

  it("adds Authorization header when vpToken provided", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string, options?: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        new Headers(options?.headers).entries(),
      );
      return new Response("ok");
    };

    const f = createFabricFetch({
      vpToken: "my-token",
      baseFetch: mockFetch as typeof fetch,
    });
    await f("https://example.com/sparql", {});
    expect(capturedHeaders["authorization"]).toBe("Bearer my-token");
  });

  it("does not add Authorization when no vpToken", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string, options?: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        new Headers(options?.headers).entries(),
      );
      return new Response("ok");
    };

    const f = createFabricFetch({
      baseFetch: mockFetch as typeof fetch,
    });
    await f("https://example.com/void", {});
    expect(capturedHeaders["authorization"]).toBeUndefined();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd experiments/node-rlm-fabric && npx vitest --run fabric-fetch.test.ts`
Expected: FAIL — `Cannot find module './fabric-fetch.js'`

**Step 3: Write minimal implementation**

```typescript
// fabric-fetch.ts

export interface FabricFetchOptions {
  vpToken?: string;
  baseFetch?: typeof fetch;
}

export function createFabricFetch(options: FabricFetchOptions = {}): typeof fetch {
  const { vpToken, baseFetch = globalThis.fetch } = options;

  return async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const headers = new Headers(init?.headers);

    if (vpToken) {
      headers.set("Authorization", `Bearer ${vpToken}`);
    }

    return baseFetch(url, { ...init, headers });
  };
}

export async function acquireVpToken(endpoint: string, fetchFn: typeof fetch = globalThis.fetch): Promise<string> {
  const resp = await fetchFn(`${endpoint}/test/create-vp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agentRole: "IngestCurator", validMinutes: 120 }),
  });
  if (!resp.ok) throw new Error(`VP token acquisition failed: ${resp.status}`);
  const data = await resp.json() as { token: string };
  return data.token;
}
```

**Step 4: Run test to verify it passes**

Run: `cd experiments/node-rlm-fabric && npx vitest --run fabric-fetch.test.ts`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add experiments/node-rlm-fabric/fabric-fetch.ts experiments/node-rlm-fabric/fabric-fetch.test.ts
git commit -m "[Agent: Claude] feat: authenticated fetch wrapper for fabric TLS + VP auth

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Sandbox tools — Comunica SPARQL + discovery fetch

The agent-visible tools injected via `sandboxGlobals`. Comunica handles SPARQL; raw fetch handles `.well-known/*` and entity dereference.

**Files:**
- Create: `experiments/node-rlm-fabric/sandbox-tools.ts`
- Test: `experiments/node-rlm-fabric/sandbox-tools.test.ts`

**Step 1: Write the failing test**

```typescript
// sandbox-tools.test.ts
import { describe, it, expect } from "vitest";
import { createSandboxTools, bindingsToJson } from "./sandbox-tools.js";

describe("bindingsToJson", () => {
  it("serializes RDF/JS bindings to JSON string", () => {
    // Mock RDF/JS binding
    const mockBinding = {
      entries: () => new Map([
        ["s", { value: "http://example.org/obs-1", termType: "NamedNode" }],
        ["p", { value: "http://www.w3.org/ns/sosa/hasResult", termType: "NamedNode" }],
        ["o", { value: "42.5", termType: "Literal" }],
      ]).entries(),
    };
    const result = JSON.parse(bindingsToJson([mockBinding as any]));
    expect(result).toHaveLength(1);
    expect(result[0].s).toBe("http://example.org/obs-1");
    expect(result[0].o).toBe("42.5");
  });

  it("truncates to maxChars", () => {
    const mockBindings = Array.from({ length: 100 }, (_, i) => ({
      entries: () => new Map([
        ["s", { value: `http://example.org/item-${i}`, termType: "NamedNode" }],
      ]).entries(),
    }));
    const result = bindingsToJson(mockBindings as any[], 500);
    expect(result.length).toBeLessThanOrEqual(500 + 50); // allow for truncation message
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
});
```

**Step 2: Run test to verify it fails**

Run: `cd experiments/node-rlm-fabric && npx vitest --run sandbox-tools.test.ts`
Expected: FAIL — `Cannot find module './sandbox-tools.js'`

**Step 3: Write minimal implementation**

```typescript
// sandbox-tools.ts
import { QueryEngine } from "@comunica/query-sparql";
import type { Bindings } from "@rdfjs/types";

const MAX_RESULT_CHARS = 10_000;

export function bindingsToJson(bindings: Bindings[], maxChars: number = MAX_RESULT_CHARS): string {
  const rows: Record<string, string>[] = [];
  for (const binding of bindings) {
    const row: Record<string, string> = {};
    for (const [key, term] of binding.entries()) {
      row[key] = term.value;
    }
    rows.push(row);
  }
  let json = JSON.stringify(rows, null, 2);
  if (json.length > maxChars) {
    json = json.slice(0, maxChars) + `\n[truncated at ${maxChars} chars, ${rows.length} total rows]`;
  }
  return json;
}

export interface SandboxToolsConfig {
  endpoint: string;
  fabricFetch: typeof fetch;
}

export function createSandboxTools(config: SandboxToolsConfig) {
  const { endpoint, fabricFetch } = config;
  const engine = new QueryEngine();

  async function comunica_query(query: string, sources?: string[]): Promise<string> {
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
    return resp.text();
  }

  async function fetchShapes(): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/.well-known/shacl`, {
      headers: { Accept: "text/turtle" },
    });
    return resp.text();
  }

  async function fetchExamples(): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/.well-known/sparql-examples`, {
      headers: { Accept: "text/turtle" },
    });
    return resp.text();
  }

  async function fetchEntity(entityId: string): Promise<string> {
    const resp = await fabricFetch(`${endpoint}/entity/${entityId}`, {
      headers: { Accept: "application/ld+json" },
    });
    return resp.text();
  }

  return { comunica_query, fetchVoID, fetchShapes, fetchExamples, fetchEntity };
}
```

**Step 4: Run test to verify it passes**

Run: `cd experiments/node-rlm-fabric && npx vitest --run sandbox-tools.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add experiments/node-rlm-fabric/sandbox-tools.ts experiments/node-rlm-fabric/sandbox-tools.test.ts
git commit -m "[Agent: Claude] feat: sandbox tools — Comunica SPARQL + discovery fetch

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Setup and teardown — test data lifecycle via Comunica

**Files:**
- Create: `experiments/node-rlm-fabric/setup-teardown.ts`
- Test: `experiments/node-rlm-fabric/setup-teardown.test.ts`

**Step 1: Write the failing test**

```typescript
// setup-teardown.test.ts
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
```

**Step 2: Run test to verify it fails**

Run: `cd experiments/node-rlm-fabric && npx vitest --run setup-teardown.test.ts`
Expected: FAIL — `Cannot find module './setup-teardown.js'`

**Step 3: Write minimal implementation**

Port the Python `_build_insert()` and `_build_sensor_insert()` logic to TypeScript. Uses Comunica `queryVoid()` for execution.

```typescript
// setup-teardown.ts
import { QueryEngine } from "@comunica/query-sparql";

const PREFIXES = `
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX sio: <http://semanticscience.org/resource/>
`;

export interface TaskRecord {
  subject: string;
  record_type?: string;
  [key: string]: string | undefined;
}

export function buildInsertQuery(graphUri: string, record: TaskRecord): string {
  const subj = `<${record.subject}>`;

  if (record.record_type === "sensor") {
    const label = record["rdfs:label"] ?? "unknown";
    const observes = record["sosa:observes"];
    let body = `${subj} a sosa:Sensor ;\n    rdfs:label "${label}" .`;
    if (observes) {
      body = `${subj} a sosa:Sensor ;\n    rdfs:label "${label}" ;\n    sosa:observes <${observes}> .`;
    }
    return `${PREFIXES}\nINSERT DATA {\n  GRAPH <${graphUri}> {\n    ${body}\n  }\n}`;
  }

  // Default: observation
  const triples: string[] = [`${subj} a sosa:Observation`];
  if (record["sosa:madeBySensor"]) triples.push(`  sosa:madeBySensor <${record["sosa:madeBySensor"]}>`);
  if (record["sosa:hasSimpleResult"]) triples.push(`  sosa:hasSimpleResult "${record["sosa:hasSimpleResult"]}"`);
  if (record["sosa:resultTime"]) triples.push(`  sosa:resultTime "${record["sosa:resultTime"]}"^^xsd:dateTime`);
  if (record["sosa:observedProperty"]) triples.push(`  sosa:observedProperty <${record["sosa:observedProperty"]}>`);

  // SIO attributes
  for (const [key, val] of Object.entries(record)) {
    if (key.startsWith("sio:") && val) {
      triples.push(`  <http://semanticscience.org/resource/${key.slice(4)}> ${val.startsWith("http") ? `<${val}>` : `"${val}"`}`);
    }
  }

  const body = triples.join(" ;\n    ") + " .";
  return `${PREFIXES}\nINSERT DATA {\n  GRAPH <${graphUri}> {\n    ${body}\n  }\n}`;
}

export function buildDropQuery(graphUri: string): string {
  return `DROP SILENT GRAPH <${graphUri}>`;
}

export async function setupTaskData(
  task: { metadata?: Record<string, unknown> },
  fabricFetch: typeof fetch,
  endpoint: string,
): Promise<void> {
  const setup = task.metadata?.setup as { type?: string; graph?: string; data?: TaskRecord[] } | undefined;
  if (!setup || setup.type !== "sparql_insert" || !setup.data) return;

  const engine = new QueryEngine();
  const graphUri = setup.graph ?? `${endpoint}/graph/observations`;

  for (const record of setup.data) {
    const query = buildInsertQuery(graphUri, record);
    await engine.queryVoid(query, {
      sources: [`${endpoint}/sparql`],
      fetch: fabricFetch,
    });
  }
}

export async function teardownTaskData(
  task: { metadata?: Record<string, unknown> },
  fabricFetch: typeof fetch,
  endpoint: string,
): Promise<void> {
  const setup = task.metadata?.setup as { type?: string; graph?: string; extra_graphs?: string[] } | undefined;
  if (!setup || setup.type !== "sparql_insert") return;

  const engine = new QueryEngine();
  const graphs = [setup.graph ?? `${endpoint}/graph/observations`];
  if (setup.extra_graphs) graphs.push(...setup.extra_graphs);

  for (const graphUri of graphs) {
    const query = buildDropQuery(graphUri);
    await engine.queryVoid(query, {
      sources: [`${endpoint}/sparql`],
      fetch: fabricFetch,
    });
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd experiments/node-rlm-fabric && npx vitest --run setup-teardown.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add experiments/node-rlm-fabric/setup-teardown.ts experiments/node-rlm-fabric/setup-teardown.test.ts
git commit -m "[Agent: Claude] feat: test data setup/teardown via Comunica SPARQL UPDATE

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Task file — phase1-sio-baseline.json

Port the 6 SIO tasks from the Python `phase3-sio-tbox.json` file. Adapt `context` field handling — in the Python version this is just the URL; for node-rlm, context is fetched at runtime.

**Files:**
- Create: `experiments/node-rlm-fabric/tasks/phase1-sio-baseline.json`
- Read: `experiments/fabric_navigation/tasks/phase3-sio-tbox.json` (reference)

**Step 1: Read the Python task file**

Run: Read `experiments/fabric_navigation/tasks/phase3-sio-tbox.json`

**Step 2: Create the JS task file**

Copy the 6 SIO tasks. Keep `context` as the endpoint URL — the runner will replace it with the full SD string at runtime. Keep `metadata` (setup/teardown data) identical.

```bash
cp experiments/fabric_navigation/tasks/phase3-sio-tbox.json experiments/node-rlm-fabric/tasks/phase1-sio-baseline.json
```

Adjust the `context` field values to use the HTTPS endpoint (`https://bootstrap.cogitarelink.ai` instead of `http://localhost:8080`). This can be done with a sed or manual edit.

**Step 3: Commit**

```bash
git add experiments/node-rlm-fabric/tasks/phase1-sio-baseline.json
git commit -m "[Agent: Claude] data: SIO baseline tasks for node-rlm experiment (from phase3)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: globalDocs — agent tool documentation

The `globalDocs` string tells the agent what sandbox tools are available. This is the node-rlm equivalent of our Python `_RDFS_TOOL_HINT` / `endpoint_sd`.

**Files:**
- Create: `experiments/node-rlm-fabric/global-docs.ts`

**Step 1: Create the globalDocs module**

```typescript
// global-docs.ts

export const BASELINE_DOCS = `
## Fabric Endpoint Tools

You are querying a self-describing SPARQL endpoint (cogitarelink fabric node).
The endpoint serves RDF data in named graphs.

### Available Functions

**comunica_query(query, sources?)** — Execute SPARQL SELECT or CONSTRUCT.
  - query: SPARQL query string
  - sources: optional array of SPARQL endpoint URLs (defaults to the fabric endpoint)
  - Returns: JSON array of result bindings (max 10K chars)
  - Example: const results = await comunica_query("SELECT ?s ?p ?o WHERE { GRAPH <.../graph/observations> { ?s ?p ?o } } LIMIT 10")

**fetchVoID()** — Fetch the endpoint's service description (VoID/SD).
  - Returns: Turtle string describing available named graphs, shapes, SPARQL examples
  - Start here to understand what data the endpoint has

**fetchShapes()** — Fetch SHACL shapes describing data constraints.
  - Returns: Turtle string with NodeShape/PropertyShape declarations
  - Shapes include sh:agentInstruction hints for query construction

**fetchExamples()** — Fetch SPARQL example queries.
  - Returns: Turtle string with example SELECT/CONSTRUCT patterns
  - Use these as templates for your queries

**fetchEntity(entityId)** — Dereference an entity by UUID.
  - entityId: UUID7 string (e.g., "01234567-89ab-cdef-0123-456789abcdef")
  - Returns: JSON-LD representation of the entity

### Discovery Strategy

1. Call fetchVoID() to understand the endpoint structure (named graphs, vocabularies)
2. Call fetchShapes() for data constraints and agent hints
3. Call fetchExamples() for query templates
4. Use comunica_query() to execute SPARQL against specific named graphs
`.trim();

export const JSONLD_DOCS = `
${BASELINE_DOCS}

### JSON-LD Processing (additional)

**jsonld.expand(doc)** — Expand JSON-LD to canonical form (full IRIs)
**jsonld.compact(doc, context)** — Compact using a context (readable prefixes)
**jsonld.frame(doc, frame)** — Reshape JSON-LD into a tree structure matching a template
**jsonld.fromRDF(nquads, options)** — Convert N-Quads to JSON-LD
**jsonld.toRDF(doc, options)** — Convert JSON-LD to N-Quads

The jsonld document loader resolves fabric vocabulary URIs to local /ontology/{vocab} endpoints.
`.trim();

export const LTQP_DOCS = `
${BASELINE_DOCS}

### Link Traversal (additional)

**comunica_traverse(query, seedUrls)** — Execute SPARQL with link traversal.
  - The engine follows RDF links automatically during query execution
  - seedUrls: starting points for traversal (e.g., VoID endpoint, entity URIs)
  - Results arrive progressively as links are discovered
  - Useful for exploring data without knowing the exact graph structure
`.trim();

export const COMBINED_DOCS = `
${JSONLD_DOCS}

### Link Traversal (additional)

**comunica_traverse(query, seedUrls)** — Execute SPARQL with link traversal.
  - The engine follows RDF links automatically during query execution
  - seedUrls: starting points for traversal
  - Results arrive progressively as links are discovered
`.trim();

export function getGlobalDocs(condition: string): string {
  switch (condition) {
    case "js-baseline": return BASELINE_DOCS;
    case "js-jsonld": return JSONLD_DOCS;
    case "js-ltqp": return LTQP_DOCS;
    case "js-combined": return COMBINED_DOCS;
    default: return BASELINE_DOCS;
  }
}
```

**Step 2: Commit**

```bash
git add experiments/node-rlm-fabric/global-docs.ts
git commit -m "[Agent: Claude] feat: globalDocs — agent tool documentation per condition

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Main runner — run-experiment.ts

The CLI entry point that wires everything together. Imports `runEval` from node-rlm, creates the Anthropic driver, loads tasks, configures sandbox tools, and runs the experiment.

**Files:**
- Create: `experiments/node-rlm-fabric/run-experiment.ts`

**Step 1: Write the runner**

```typescript
// run-experiment.ts
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { runEval } from "node-rlm/eval/harness.js";
import { fromOpenRouterCompatible } from "node-rlm/drivers/openrouter-compatible";
import type { EvalTask } from "node-rlm/eval/types.js";
import { substringMatch } from "./scoring.js";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";
import { createSandboxTools } from "./sandbox-tools.js";
import { setupTaskData, teardownTaskData } from "./setup-teardown.js";
import { getGlobalDocs } from "./global-docs.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadEnv(): void {
  try {
    const content = readFileSync(join(__dirname, ".env"), "utf-8");
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eqIdx = trimmed.indexOf("=");
      if (eqIdx === -1) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      const value = trimmed.slice(eqIdx + 1).trim();
      if (!process.env[key]) process.env[key] = value;
    }
  } catch {
    // No .env file, continue
  }
}

interface CliArgs {
  tasks: string;
  condition: string;
  model: string;
  maxIterations: number;
  maxDepth: number;
  concurrency: number;
  endpoint: string;
}

function parseArgs(argv: string[]): CliArgs {
  const args: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--") && i + 1 < argv.length) {
      args[argv[i].slice(2)] = argv[i + 1];
      i++;
    }
  }

  if (!args.tasks) {
    console.error("Usage: npx tsx run-experiment.ts --tasks <path> --condition <name> [options]");
    console.error("\nConditions: js-baseline, js-jsonld, js-ltqp, js-combined");
    console.error("\nOptions:");
    console.error("  --model <id>           Model (default: claude-sonnet-4-6-20250514)");
    console.error("  --max-iterations <n>   REPL iterations (default: 10)");
    console.error("  --max-depth <n>        Recursion depth (default: 1)");
    console.error("  --concurrency <n>      Parallel tasks (default: 1)");
    console.error("  --endpoint <url>       Fabric endpoint (default: https://bootstrap.cogitarelink.ai)");
    process.exit(1);
  }

  return {
    tasks: args.tasks,
    condition: args.condition ?? "js-baseline",
    model: args.model ?? "claude-sonnet-4-6-20250514",
    maxIterations: parseInt(args["max-iterations"] ?? "10", 10),
    maxDepth: parseInt(args["max-depth"] ?? "1", 10),
    concurrency: parseInt(args.concurrency ?? "1", 10),
    endpoint: args.endpoint ?? "https://bootstrap.cogitarelink.ai",
  };
}

async function main(): Promise<void> {
  loadEnv();

  const args = parseArgs(process.argv.slice(2));

  console.log("node-rlm Fabric Experiment");
  console.log("==========================");
  console.log(`Condition:       ${args.condition}`);
  console.log(`Model:           ${args.model}`);
  console.log(`Endpoint:        ${args.endpoint}`);
  console.log(`Max Iterations:  ${args.maxIterations}`);
  console.log(`Max Depth:       ${args.maxDepth}`);
  console.log(`Concurrency:     ${args.concurrency}`);
  console.log();

  // Verify API key
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY not set.");
    process.exit(1);
  }

  // Create Anthropic driver
  const callLLM = fromOpenRouterCompatible({
    baseUrl: "https://api.anthropic.com/v1",
    apiKey,
    model: args.model,
  });

  // Acquire VP token for authenticated SPARQL
  console.log("Acquiring VP token...");
  const vpToken = await acquireVpToken(args.endpoint);
  console.log("  VP token acquired");

  // Create authenticated fetch
  const fabricFetch = createFabricFetch({ vpToken });

  // Fetch endpoint SD for context
  console.log("Fetching endpoint service description...");
  const voidResp = await fabricFetch(`${args.endpoint}/.well-known/void`, {
    headers: { Accept: "text/turtle" },
  });
  const endpointSD = await voidResp.text();
  console.log(`  SD: ${endpointSD.length} chars`);
  console.log();

  // Load tasks
  const tasksRaw = JSON.parse(readFileSync(args.tasks, "utf-8")) as Array<{
    id: string; query: string; context: string; expected: string | string[];
    metadata?: Record<string, unknown>;
  }>;

  // Replace context with full SD string
  const tasks: EvalTask[] = tasksRaw.map((t) => ({
    ...t,
    context: endpointSD,
  }));
  console.log(`Loaded ${tasks.length} tasks`);

  // Create sandbox tools
  const tools = createSandboxTools({ endpoint: args.endpoint, fabricFetch });

  // Run eval
  const result = await runEval(tasks, {
    benchmark: `fabric-${args.condition}`,
    model: args.model,
    callLLM,
    scoringFn: substringMatch,
    maxIterations: args.maxIterations,
    maxDepth: args.maxDepth,
    concurrency: args.concurrency,
    resultsDir: join(__dirname, "results"),
    globalDocs: getGlobalDocs(args.condition),
    setupSandbox: () => ({ ...tools }),
    cleanupTask: async (task) => {
      await teardownTaskData(task, fabricFetch, args.endpoint);
    },
    onProgress: (completed, total, r) => {
      const status = r.error ? "FAIL" : `score=${r.score.toFixed(2)}`;
      console.log(`  [${completed}/${total}] ${r.taskId}: ${status}, ${r.iterations} iters`);
    },
  });

  // Print summary
  console.log();
  console.log("=".repeat(50));
  console.log(`  Score:  ${(result.aggregate.meanScore * 100).toFixed(1)}%`);
  console.log(`  Iters:  ${result.aggregate.meanIterations.toFixed(1)} mean`);
  console.log(`  Cost:   $${result.aggregate.costEstimateUsd.toFixed(2)}`);
  console.log("=".repeat(50));
}

main().catch((err) => {
  console.error("Fatal:", err.message ?? err);
  process.exit(1);
});
```

**Step 2: Verify it compiles**

Run: `cd experiments/node-rlm-fabric && npx tsx --check run-experiment.ts`
Expected: No errors (type-check only, no execution)

Note: Full integration test requires Docker stack running. Defer to Task 9.

**Step 3: Commit**

```bash
git add experiments/node-rlm-fabric/run-experiment.ts
git commit -m "[Agent: Claude] feat: main experiment runner — wires runEval + Comunica + fabric

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Integration smoke test

Run a single task end-to-end against the live fabric stack. This validates the full pipeline: Anthropic driver → node-rlm harness → sandbox tools → Comunica → fabric SPARQL → scoring.

**Prerequisite:** Docker fabric stack running, `ANTHROPIC_API_KEY` set.

**Step 1: Run with a single task**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
NODE_EXTRA_CA_CERTS=./caddy-root.crt \
npx tsx experiments/node-rlm-fabric/run-experiment.ts \
  --tasks experiments/node-rlm-fabric/tasks/phase1-sio-baseline.json \
  --condition js-baseline \
  --max-iterations 10 \
  --concurrency 1
```

Expected: Runs all 6 SIO tasks, prints scores. Target: 6/6 matching Python phase3b.

**Step 2: Verify results file saved**

```bash
ls experiments/node-rlm-fabric/results/
```

Expected: `fabric-js-baseline_claude-sonnet-4-6-20250514_<timestamp>.json`

**Step 3: Compare with Python results**

```bash
# Python phase3b score
cat experiments/fabric_navigation/results/phase3b-* | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Python: {d[\"aggregate\"][\"meanScore\"]}')"

# JS baseline score
cat experiments/node-rlm-fabric/results/fabric-js-baseline* | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'JS: {d[\"aggregate\"][\"meanScore\"]}')"
```

**Step 4: Debug if needed**

If JS-baseline score < Python phase3b, check:
1. Are sandbox tools returning usable output? (Check events in results JSON)
2. Is Comunica connecting to the right SPARQL endpoint?
3. Is VP auth working? (Look for 401/403 in Comunica errors)
4. Is the globalDocs adequate? (Compare with Python endpoint_sd)

**Step 5: Commit results gitignore**

```bash
echo "results/" >> experiments/node-rlm-fabric/.gitignore
git add experiments/node-rlm-fabric/.gitignore
git commit -m "[Agent: Claude] chore: gitignore experiment results

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 10: README

**Files:**
- Create: `experiments/node-rlm-fabric/README.md`

**Step 1: Write README**

Document: what the experiment tests, how to run it, prerequisites, conditions, how to compare with Python results.

**Step 2: Commit**

```bash
git add experiments/node-rlm-fabric/README.md
git commit -m "[Agent: Claude] docs: node-rlm fabric experiment README

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task Summary

| Task | What | Est. |
|------|------|------|
| 1 | Scaffold: package.json, tsconfig, npm install | 5 min |
| 2 | Scoring function + tests | 5 min |
| 3 | Authenticated fetch wrapper + tests | 5 min |
| 4 | Sandbox tools (Comunica + discovery) + tests | 10 min |
| 5 | Setup/teardown via Comunica + tests | 10 min |
| 6 | Task file (port SIO tasks) | 5 min |
| 7 | globalDocs per condition | 5 min |
| 8 | Main runner (run-experiment.ts) | 10 min |
| 9 | Integration smoke test | 15 min |
| 10 | README | 5 min |

Phase 1 scope: Tasks 1-10 deliver js-baseline condition only. js-jsonld, js-ltqp, and js-combined are Phase 2 (separate plan after Phase 1 results are validated).
