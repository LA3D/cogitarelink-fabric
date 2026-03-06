/**
 * Test 03: Explicit Source Type Workaround
 *
 * Using { type: "sparql", value: url } bypasses SD auto-detection
 * and sends queries directly to the specified URL.
 *
 * This is the workaround used in sandbox-tools.ts.
 *
 * Expected output:
 *   OK — 1 results (sends GET with ?query= directly, no SD discovery)
 */
import { QueryEngine } from "@comunica/query-sparql";
import { createFabricFetch, acquireVpToken } from "../fabric-fetch.js";

const endpoint = "https://bootstrap.cogitarelink.ai";

async function main() {
  const token = await acquireVpToken(endpoint);
  const fabricFetch = createFabricFetch({ vpToken: token });

  // Logging wrapper to show what URLs Comunica actually requests
  const loggingFetch: typeof fetch = async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    console.log(`  FETCH: ${url}`);
    const resp = await fabricFetch(input, init);
    console.log(`  RESP:  ${resp.status} ${resp.url}`);
    return resp;
  };

  console.log("Query with explicit type: 'sparql'...");
  const engine = new QueryEngine();
  try {
    const stream = await engine.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [{ type: "sparql" as const, value: `${endpoint}/sparql` }],
      fetch: loggingFetch,
    });
    const results = await stream.toArray();
    console.log(`OK — ${results.length} results`);
  } catch (err: any) {
    console.log(`Error: ${err.message}`);
    if (err.cause) console.log(`Cause: ${err.cause.message}`);
  }
}

main().catch(console.error);
