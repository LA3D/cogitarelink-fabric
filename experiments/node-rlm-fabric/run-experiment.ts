// run-experiment.ts
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { rlm, RlmObserver } from "node-rlm";
import { fromAnthropic } from "./anthropic-driver.js";
import { substringMatch } from "./scoring.js";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";
import { createSandboxTools } from "./sandbox-tools.js";
import { setupTaskData, teardownTaskData } from "./setup-teardown.js";
import { getGlobalDocs } from "./global-docs.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Anthropic pricing (USD per million tokens)
const PRICING: Record<string, { input: number; output: number }> = {
  "claude-sonnet-4-6": { input: 3, output: 15 },
  "claude-sonnet-4-5-20250929": { input: 3, output: 15 },
  "claude-sonnet-4-20250514": { input: 3, output: 15 },
  "claude-opus-4-6": { input: 15, output: 75 },
  "claude-haiku-4-5-20251001": { input: 0.80, output: 4 },
};

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
  trajectory: TrajectoryStep[];
  tokenUsage?: { promptTokens: number; completionTokens: number };
}

interface TrajectoryStep {
  iteration: number;
  reasoning: string;
  code: string | null;
  output: string;
  error: string | null;
  returned: boolean;
  durationMs: number;
  usage?: { promptTokens?: number; completionTokens?: number };
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
    console.error("  --model <id>           Model (default: claude-sonnet-4-6)");
    console.error("  --max-iterations <n>   REPL iterations (default: 10)");
    console.error("  --endpoint <url>       Fabric endpoint (default: https://bootstrap.cogitarelink.ai)");
    process.exit(1);
  }

  return {
    tasks: args.tasks,
    condition: args.condition ?? "js-baseline",
    model: args.model ?? "claude-sonnet-4-6",
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

  // Pricing for cost tracking
  const pricing = PRICING[args.model] ?? { input: 3, output: 15 };

  // Verify API key
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY not set.");
    process.exit(1);
  }

  // Create Anthropic driver
  const callLLM = fromAnthropic({ apiKey, model: args.model });

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

  // Create sandbox tools and select per condition
  const tools = createSandboxTools({ endpoint: args.endpoint, fabricFetch });
  const globalDocs = getGlobalDocs(args.condition);

  const baseSandbox = {
    fetchVoID: tools.fetchVoID,
    fetchShapes: tools.fetchShapes,
    fetchExamples: tools.fetchExamples,
    fetchEntity: tools.fetchEntity,
  };

  const sandboxGlobals: Record<string, unknown> = (() => {
    switch (args.condition) {
      case "js-jsonld":
        return { ...baseSandbox, comunica_query: tools.comunica_query, fetchJsonLd: tools.fetchJsonLd, jsonld: tools.jsonld };
      case "js-combined":
        return { ...baseSandbox, comunica_query: tools.comunica_query, fetchJsonLd: tools.fetchJsonLd, jsonld: tools.jsonld };
      default:
        return { ...baseSandbox, comunica_query: tools.comunica_query };
    }
  })();

  // Run tasks sequentially
  const results: TaskResult[] = [];

  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i];
    console.log(`[${i + 1}/${tasks.length}] ${task.id}: "${task.query}"`);

    const t0 = Date.now();
    let answer = "";
    let iterations = 0;
    let error: string | undefined;

    // Per-task observer for trajectory capture
    const observer = new RlmObserver();
    const trajectory: TrajectoryStep[] = [];
    let currentStep: Partial<TrajectoryStep> = {};

    observer.on("llm:response", (e) => {
      currentStep = {
        iteration: e.iteration,
        reasoning: e.reasoning,
        code: e.code,
        durationMs: e.duration,
        usage: e.usage
          ? { promptTokens: e.usage.promptTokens, completionTokens: e.usage.completionTokens }
          : undefined,
      };
    });

    observer.on("iteration:end", (e) => {
      trajectory.push({
        iteration: e.iteration,
        reasoning: currentStep.reasoning ?? "",
        code: e.code,
        output: e.output,
        error: e.error,
        returned: e.returned,
        durationMs: currentStep.durationMs ?? 0,
        usage: currentStep.usage,
      });
      currentStep = {};
    });

    try {
      // Setup test data
      await setupTaskData(task, fabricFetch, args.endpoint);

      // Run RLM agent
      const result = await rlm(task.query, endpointSD, {
        callLLM,
        maxIterations: args.maxIterations,
        sandboxGlobals,
        globalDocs,
        observer,
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

    // Aggregate token usage across trajectory
    const totalPrompt = trajectory.reduce((s, t) => s + (t.usage?.promptTokens ?? 0), 0);
    const totalCompletion = trajectory.reduce((s, t) => s + (t.usage?.completionTokens ?? 0), 0);

    results.push({
      taskId: task.id,
      query: task.query,
      answer,
      expected: task.expected,
      score,
      iterations,
      wallTimeMs,
      trajectory,
      tokenUsage: totalPrompt > 0 ? { promptTokens: totalPrompt, completionTokens: totalCompletion } : undefined,
      ...(error ? { error } : {}),
    });

    const taskCost = totalPrompt > 0
      ? (totalPrompt / 1e6) * pricing.input + (totalCompletion / 1e6) * pricing.output
      : 0;
    console.log(`  score=${score.toFixed(2)}, iters=${iterations}, time=${(wallTimeMs / 1000).toFixed(1)}s, tokens=${totalPrompt}+${totalCompletion}, cost=$${taskCost.toFixed(4)}`);
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

  // Aggregate token usage and cost
  const totalPromptTokens = results.reduce((s, r) => s + (r.tokenUsage?.promptTokens ?? 0), 0);
  const totalCompletionTokens = results.reduce((s, r) => s + (r.tokenUsage?.completionTokens ?? 0), 0);

  const costUsd =
    (totalPromptTokens / 1_000_000) * pricing.input +
    (totalCompletionTokens / 1_000_000) * pricing.output;

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
      totalPromptTokens,
      totalCompletionTokens,
      costUsd,
      costPerTask: costUsd / results.length,
    },
    results,
  };

  writeFileSync(resultsFile, JSON.stringify(output, null, 2));
  console.log(`Results saved to ${resultsFile}`);

  // Save compact trajectory file (one per run, for analysis)
  const trajectoryFile = join(
    resultsDir,
    `trajectory-${args.condition}_${args.model}_${timestamp}.json`,
  );
  const trajectoryOutput = results.map((r) => ({
    taskId: r.taskId,
    score: r.score,
    iterations: r.iterations,
    tokenUsage: r.tokenUsage,
    trajectory: r.trajectory,
  }));
  writeFileSync(trajectoryFile, JSON.stringify(trajectoryOutput, null, 2));
  console.log(`Trajectories saved to ${trajectoryFile}`);

  // Print summary
  console.log();
  console.log("=".repeat(50));
  console.log(`  Condition:  ${args.condition}`);
  console.log(`  Score:      ${(meanScore * 100).toFixed(1)}% (${results.filter(r => r.score === 1).length}/${results.length})`);
  console.log(`  Iters:      ${meanIters.toFixed(1)} mean`);
  console.log(`  Time:       ${(totalWallMs / 1000).toFixed(1)}s total`);
  console.log(`  Tokens:     ${totalPromptTokens.toLocaleString()} in / ${totalCompletionTokens.toLocaleString()} out`);
  console.log(`  Cost:       $${costUsd.toFixed(4)} total ($${(costUsd / results.length).toFixed(4)}/task)`);
  console.log("=".repeat(50));
}

main().catch((err) => {
  console.error("Fatal:", err.message ?? err);
  process.exit(1);
});
