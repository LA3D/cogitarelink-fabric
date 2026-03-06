/**
 * Test 04: Full Fetch URL Trace
 *
 * Wraps fabricFetch with logging to capture EVERY URL that Comunica
 * requests during source auto-detection and query execution.
 *
 * This is the key diagnostic: it shows that Comunica makes two fetches:
 *   1. GET https://bootstrap.cogitarelink.ai/sparql (SD discovery) → 200 OK
 *   2. GET https://oxigraph:7878/query?query=... (actual query) → ENOTFOUND
 *
 * The second URL has the internal Docker hostname with HTTPS scheme.
 * The HTTPS scheme comes from Comunica's `inferHttpsEndpoint` flag
 * rewriting http: → https: when the original URL starts with https.
 *
 * Expected output:
 *   FETCH: GET https://bootstrap.cogitarelink.ai/sparql [...] isRequest=false
 *   RESP:  200 https://bootstrap.cogitarelink.ai/sparql
 *   FETCH: GET https://oxigraph:7878/query?query=... [...] isRequest=false
 *   FAIL:  fetch failed cause=getaddrinfo ENOTFOUND oxigraph
 */
import { QueryEngine } from "@comunica/query-sparql";
import { createFabricFetch, acquireVpToken } from "../fabric-fetch.js";

const endpoint = "https://bootstrap.cogitarelink.ai";

async function main() {
  const token = await acquireVpToken(endpoint);
  const baseFabricFetch = createFabricFetch({ vpToken: token });

  // Wrap fetch to log ALL URLs Comunica requests
  const loggingFetch: typeof fetch = async (input, init) => {
    const isReq = input instanceof Request;
    const url = isReq ? input.url : String(input);
    const method = init?.method ?? (isReq ? input.method : "GET");
    const accept = init?.headers
      ? new Headers(init.headers).get("accept")
      : isReq
        ? (input as Request).headers.get("accept")
        : undefined;
    console.log(
      `  FETCH: ${method} ${url} [Accept: ${accept?.slice(0, 60)}...] isRequest=${isReq}`,
    );
    if (isReq) {
      console.log(
        `    Request headers:`,
        Object.fromEntries((input as Request).headers.entries()),
      );
    }
    try {
      const resp = await baseFabricFetch(input, init);
      console.log(`  RESP:  ${resp.status} ${resp.url}`);
      return resp;
    } catch (err: any) {
      console.log(
        `  FAIL:  ${err.message} cause=${err.cause?.message}`,
      );
      throw err;
    }
  };

  console.log("Query with logging fetch (auto-detect source type)...");
  const engine = new QueryEngine();
  try {
    const stream = await engine.queryBindings("SELECT * WHERE {} LIMIT 1", {
      sources: [`${endpoint}/sparql`],
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
