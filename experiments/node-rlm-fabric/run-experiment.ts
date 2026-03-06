// run-experiment.ts
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { rlm } from "node-rlm";
import { fromOpenRouterCompatible } from "node-rlm/drivers/openrouter-compatible";
import { substringMatch } from "./scoring.js";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";
import { createSandboxTools } from "./sandbox-tools.js";
import { setupTaskData, teardownTaskData } from "./setup-teardown.js";
import { getGlobalDocs } from "./global-docs.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

interface Task {
  id: string;
  query: string;
  context: string;
  expected: string | string[];
  metadata?: Record<string, unknown>;
}

interface TaskResult {
  taskId: string;
  query: string;
  answer: string;
  expected: string | string[];
  score: number;
  iterations: number;
  wallTimeMs: number;
  error?: string;
}

interface CliArgs {
  tasks: string;
  condition: string;
  model: string;
  maxIterations: number;
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
    console.error("  --endpoint <url>       Fabric endpoint (default: https://bootstrap.cogitarelink.ai)");
    process.exit(1);
  }

  return {
    tasks: args.tasks,
    condition: args.condition ?? "js-baseline",
    model: args.model ?? "claude-sonnet-4-6-20250514",
    maxIterations: parseInt(args["max-iterations"] ?? "10", 10),
    endpoint: args.endpoint ?? "https://bootstrap.cogitarelink.ai",
  };
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  console.log("node-rlm Fabric Experiment");
  console.log("==========================");
  console.log(`Condition:       ${args.condition}`);
  console.log(`Model:           ${args.model}`);
  console.log(`Endpoint:        ${args.endpoint}`);
  console.log(`Max Iterations:  ${args.maxIterations}`);
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
  const tasks: Task[] = JSON.parse(readFileSync(args.tasks, "utf-8"));
  console.log(`Loaded ${tasks.length} tasks`);
  console.log();

  // Create sandbox tools
  const tools = createSandboxTools({ endpoint: args.endpoint, fabricFetch });
  const globalDocs = getGlobalDocs(args.condition);

  // Run tasks sequentially
  const results: TaskResult[] = [];

  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i];
    console.log(`[${i + 1}/${tasks.length}] ${task.id}: "${task.query}"`);

    const t0 = Date.now();
    let answer = "";
    let iterations = 0;
    let error: string | undefined;

    try {
      // Setup test data
      await setupTaskData(task, fabricFetch, args.endpoint);

      // Run RLM agent
      const result = await rlm(task.query, endpointSD, {
        callLLM,
        maxIterations: args.maxIterations,
        sandboxGlobals: { ...tools },
        globalDocs,
      });

      answer = result.answer;
      iterations = result.iterations;
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      console.error(`  ERROR: ${error}`);
    } finally {
      // Always teardown
      try {
        await teardownTaskData(task, fabricFetch, args.endpoint);
      } catch (teardownErr) {
        console.error(`  Teardown error: ${teardownErr}`);
      }
    }

    const wallTimeMs = Date.now() - t0;
    const score = error ? 0.0 : substringMatch(answer, task.expected);

    results.push({
      taskId: task.id,
      query: task.query,
      answer,
      expected: task.expected,
      score,
      iterations,
      wallTimeMs,
      ...(error ? { error } : {}),
    });

    console.log(`  score=${score.toFixed(2)}, iters=${iterations}, time=${(wallTimeMs / 1000).toFixed(1)}s`);
    console.log();
  }

  // Save results
  const resultsDir = join(__dirname, "results");
  mkdirSync(resultsDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const resultsFile = join(
    resultsDir,
    `fabric-${args.condition}_${args.model}_${timestamp}.json`,
  );

  const meanScore = results.reduce((s, r) => s + r.score, 0) / results.length;
  const meanIters = results.reduce((s, r) => s + r.iterations, 0) / results.length;
  const totalWallMs = results.reduce((s, r) => s + r.wallTimeMs, 0);

  const output = {
    benchmark: `fabric-${args.condition}`,
    model: args.model,
    condition: args.condition,
    endpoint: args.endpoint,
    timestamp: new Date().toISOString(),
    aggregate: {
      meanScore,
      meanIterations: meanIters,
      totalWallTimeMs: totalWallMs,
      taskCount: results.length,
    },
    results,
  };

  writeFileSync(resultsFile, JSON.stringify(output, null, 2));
  console.log(`Results saved to ${resultsFile}`);

  // Print summary
  console.log();
  console.log("=".repeat(50));
  console.log(`  Condition: ${args.condition}`);
  console.log(`  Score:     ${(meanScore * 100).toFixed(1)}% (${results.filter(r => r.score === 1).length}/${results.length})`);
  console.log(`  Iters:     ${meanIters.toFixed(1)} mean`);
  console.log(`  Time:      ${(totalWallMs / 1000).toFixed(1)}s total`);
  console.log("=".repeat(50));
}

main().catch((err) => {
  console.error("Fatal:", err.message ?? err);
  process.exit(1);
});
