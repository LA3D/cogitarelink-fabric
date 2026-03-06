/**
 * Test 02: Fresh Engine Baseline Failure
 *
 * A fresh Comunica engine with auth, single query, no priming.
 * Demonstrates the baseline failure: ENOTFOUND oxigraph.
 *
 * Compare with test 01 (test 2) which succeeds after priming.
 *
 * Expected output:
 *   Error: fetch failed
 *   Cause: getaddrinfo ENOTFOUND oxigraph
 */
import { QueryEngine } from "@comunica/query-sparql";
import { createFabricFetch, acquireVpToken } from "../fabric-fetch.js";

const endpoint = "https://bootstrap.cogitarelink.ai";

async function main() {
  const token = await acquireVpToken(endpoint);
  const fabricFetch = createFabricFetch({ vpToken: token });

  console.log("Single query with fresh engine and fabricFetch...");
  const engine = new QueryEngine();
  try {
    const stream = await engine.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [`${endpoint}/sparql`],
      fetch: fabricFetch,
    });
    const results = await stream.toArray();
    console.log(`OK — ${results.length} results`);
  } catch (err: any) {
    console.log(`Error: ${err.message}`);
    if (err.cause) console.log(`Cause: ${err.cause.message} (${err.cause.code})`);
  }
}

main().catch(console.error);
