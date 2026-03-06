/**
 * Single-task test: Run one SIO task through the full RLM agent loop
 * with detailed trajectory output.
 *
 * Usage:
 *   NODE_EXTRA_CA_CERTS=../../caddy-root.crt npx tsx single-task-test.ts
 *
 * What to look for:
 *   - Does the agent call fetchVoID() first? (discovery strategy)
 *   - Does it call fetchShapes() / fetchExamples()? (D9 four-layer KR)
 *   - Does comunica_query() work and return results?
 *   - Does the agent reason from the results to produce a correct answer?
 *   - How many iterations does it take?
 */
import { rlm, RlmObserver } from "node-rlm";
import { fromAnthropic } from "./anthropic-driver.js";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";
import { createSandboxTools } from "./sandbox-tools.js";
import { getGlobalDocs } from "./global-docs.js";

const endpoint = "https://bootstrap.cogitarelink.ai";
const model = "claude-sonnet-4-6";

// Pick the simplest task: no data setup needed, just ontology query
const TASK = {
  id: "sio-has-value-type",
  query:
    "Is sio:has-value a datatype property or an object property according to the SIO ontology?",
  expected: ["DatatypeProperty"],
};

async function main() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY not set");
    process.exit(1);
  }

  console.log("=== Single Task Agent Test ===");
  console.log(`Task:     ${TASK.id}`);
  console.log(`Query:    ${TASK.query}`);
  console.log(`Expected: ${TASK.expected}`);
  console.log(`Model:    ${model}`);
  console.log(`Endpoint: ${endpoint}`);
  console.log();

  // Setup
  console.log("1. Acquiring VP token...");
  const vpToken = await acquireVpToken(endpoint);
  console.log(`   OK (${vpToken.length} chars)`);

  const fabricFetch = createFabricFetch({ vpToken });

  console.log("2. Fetching endpoint SD...");
  const voidResp = await fabricFetch(`${endpoint}/.well-known/void`, {
    headers: { Accept: "text/turtle" },
  });
  const endpointSD = await voidResp.text();
  console.log(`   OK (${endpointSD.length} chars)`);

  // Create tools
  const tools = createSandboxTools({ endpoint, fabricFetch });
  const globalDocs = getGlobalDocs("js-baseline");

  // Observer for trajectory logging
  const observer = new RlmObserver();

  // Log iterations in real-time
  observer.on("iteration:start", (e) => {
    console.log(`\n--- Iteration ${e.iteration} ---`);
  });

  observer.on("llm:response", (e) => {
    console.log(`\n[LLM reasoning] (${e.duration}ms)`);
    if (e.reasoning) {
      // Truncate long reasoning for readability
      const lines = e.reasoning.split("\n");
      if (lines.length > 20) {
        console.log(lines.slice(0, 20).join("\n"));
        console.log(`  ... (${lines.length - 20} more lines)`);
      } else {
        console.log(e.reasoning);
      }
    }
    if (e.code) {
      console.log(`\n[Code]`);
      console.log(e.code);
    }
    if (e.usage) {
      console.log(
        `\n[Tokens] prompt=${e.usage.promptTokens} completion=${e.usage.completionTokens} cache_read=${e.usage.cacheReadTokens ?? 0}`,
      );
    }
  });

  observer.on("iteration:end", (e) => {
    if (e.error) {
      console.log(`\n[Sandbox error] ${e.error}`);
    }
    if (e.output) {
      // Truncate long output
      const output =
        e.output.length > 2000
          ? e.output.slice(0, 2000) + `\n... (${e.output.length} total chars)`
          : e.output;
      console.log(`\n[Output]`);
      console.log(output);
    }
    if (e.returned) {
      console.log(`\n[SUBMITTED answer]`);
    }
  });

  // Run
  console.log("\n3. Running RLM agent...\n");
  console.log("=".repeat(60));

  const t0 = Date.now();
  try {
    const result = await rlm(TASK.query, endpointSD, {
      callLLM: fromAnthropic({ apiKey, model }),
      maxIterations: 15,
      sandboxGlobals: { ...tools },
      globalDocs,
      observer,
    });

    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

    console.log("\n" + "=".repeat(60));
    console.log(`\n4. Result`);
    console.log(`   Answer:     ${result.answer}`);
    console.log(`   Expected:   ${TASK.expected}`);
    console.log(`   Iterations: ${result.iterations}`);
    console.log(`   Time:       ${elapsed}s`);

    // Check match
    const answer = result.answer.toLowerCase();
    const match = TASK.expected.some((e) =>
      answer.includes(e.toLowerCase()),
    );
    console.log(`   Match:      ${match ? "✅ YES" : "❌ NO"}`);
  } catch (err: any) {
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log("\n" + "=".repeat(60));
    console.log(`\n4. ERROR after ${elapsed}s`);
    console.log(`   ${err.message}`);
    if (err.iterations !== undefined) {
      console.log(`   Iterations: ${err.iterations}`);
    }
  }

  // Dump full event log for analysis
  const events = observer.getEvents();
  console.log(`\n5. Event summary: ${events.length} events`);
  const types = events.reduce(
    (acc, e) => {
      acc[e.type] = (acc[e.type] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  console.log(`   ${JSON.stringify(types)}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
