/**
 * Test 01: Engine Priming Effect
 *
 * Demonstrates that a failed call (401, no auth) to the same engine
 * "primes" it so subsequent authenticated calls succeed. A fresh engine
 * without this priming fails.
 *
 * This suggests Comunica caches something from the 401 response that
 * prevents the problematic SD re-discovery on the second call.
 *
 * Expected output:
 *   Test 1: fails (401 — no auth, expected)
 *   Test 2: succeeds (same engine, now with auth)
 *   Test 3: fails (fresh engine, ENOTFOUND oxigraph)
 */
import { QueryEngine } from "@comunica/query-sparql";
import { createFabricFetch, acquireVpToken } from "../fabric-fetch.js";

const endpoint = "https://bootstrap.cogitarelink.ai";

async function main() {
  const token = await acquireVpToken(endpoint);
  const fabricFetch = createFabricFetch({ vpToken: token });

  const engine = new QueryEngine();

  // Test 1: Failing call (no auth, primes engine)
  console.log("Test 1: Failing call (no auth, primes engine)...");
  try {
    await engine.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [`${endpoint}/sparql`],
    });
    console.log("  Unexpected success");
  } catch (err: any) {
    console.log(`  Expected failure: ${err.message.slice(0, 80)}`);
  }

  // Test 2: Working call (with auth, same engine)
  console.log("Test 2: Working call (with auth, same engine)...");
  try {
    const stream = await engine.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [`${endpoint}/sparql`],
      fetch: fabricFetch,
    });
    const results = await stream.toArray();
    console.log(`  OK — ${results.length} results`);
  } catch (err: any) {
    console.log(`  Error: ${err.message}`);
    if (err.cause) console.log(`  Cause: ${err.cause.message}`);
  }

  // Test 3: Fresh engine, no priming
  console.log("Test 3: Fresh engine, no priming...");
  const engine2 = new QueryEngine();
  try {
    const stream = await engine2.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [`${endpoint}/sparql`],
      fetch: fabricFetch,
    });
    const results = await stream.toArray();
    console.log(`  OK — ${results.length} results`);
  } catch (err: any) {
    console.log(`  Error: ${err.message}`);
    if (err.cause) console.log(`  Cause: ${err.cause.message}`);
  }
}

main().catch(console.error);
