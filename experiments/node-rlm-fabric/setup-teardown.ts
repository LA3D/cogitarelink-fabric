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

  const graphUri = setup.graph ?? `${endpoint}/graph/observations`;

  for (const record of setup.data) {
    const query = buildInsertQuery(graphUri, record);
    const resp = await fabricFetch(`${endpoint}/sparql/update`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `update=${encodeURIComponent(query)}`,
    });
    if (!resp.ok) {
      throw new Error(`Setup INSERT failed (${resp.status}): ${await resp.text()}`);
    }
  }
}

export async function teardownTaskData(
  task: { metadata?: Record<string, unknown> },
  fabricFetch: typeof fetch,
  endpoint: string,
): Promise<void> {
  const setup = task.metadata?.setup as { type?: string; graph?: string; extra_graphs?: string[] } | undefined;
  if (!setup || setup.type !== "sparql_insert") return;

  const graphs = [setup.graph ?? `${endpoint}/graph/observations`];
  if (setup.extra_graphs) graphs.push(...setup.extra_graphs);

  for (const graphUri of graphs) {
    const query = buildDropQuery(graphUri);
    const resp = await fabricFetch(`${endpoint}/sparql/update`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `update=${encodeURIComponent(query)}`,
    });
    if (!resp.ok) {
      console.error(`Teardown DROP failed (${resp.status}): ${await resp.text()}`);
    }
  }
}
