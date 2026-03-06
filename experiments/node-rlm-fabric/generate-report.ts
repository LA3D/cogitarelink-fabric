/**
 * Generate a markdown summary report from experiment results.
 *
 * Usage:
 *   npx tsx generate-report.ts results/fabric-*.json
 *
 * Produces: reports/<condition>_<model>_<date>.md (committed to git)
 * Raw JSON in results/ stays gitignored.
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Anthropic pricing (USD per million tokens)
const PRICING: Record<string, { input: number; output: number }> = {
  "claude-sonnet-4-6": { input: 3, output: 15 },
  "claude-sonnet-4-5-20250929": { input: 3, output: 15 },
  "claude-opus-4-6": { input: 15, output: 75 },
  "claude-haiku-4-5-20251001": { input: 0.80, output: 4 },
};

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

interface ExperimentResult {
  benchmark: string;
  model: string;
  condition: string;
  endpoint: string;
  timestamp: string;
  aggregate: {
    meanScore: number;
    meanIterations: number;
    totalWallTimeMs: number;
    taskCount: number;
    totalPromptTokens: number;
    totalCompletionTokens: number;
    costUsd: number;
    costPerTask: number;
  };
  results: TaskResult[];
}

function extractToolCalls(trajectory: TrajectoryStep[]): string[] {
  const calls: string[] = [];
  for (const step of trajectory) {
    if (!step.code) continue;
    // Extract function calls from code
    const matches = step.code.match(/(?:await\s+)?(fetchVoID|fetchShapes|fetchExamples|fetchEntity|comunica_query)\s*\(/g);
    if (matches) {
      calls.push(...matches.map((m) => m.replace(/^await\s+/, "").replace(/\s*\($/, "")));
    }
  }
  return calls;
}

function extractSparqlQueries(trajectory: TrajectoryStep[]): string[] {
  const queries: string[] = [];
  for (const step of trajectory) {
    if (!step.code) continue;
    // Extract SPARQL from comunica_query calls (backtick or quote strings)
    const matches = step.code.match(/comunica_query\s*\(\s*[`"']([\s\S]*?)[`"']/g);
    if (matches) {
      for (const m of matches) {
        const inner = m.replace(/^comunica_query\s*\(\s*[`"']/, "").replace(/[`"']$/, "");
        queries.push(inner.trim());
      }
    }
  }
  return queries;
}

function classifyStrategy(toolCalls: string[]): string {
  if (toolCalls.length === 0) return "none";
  const first = toolCalls[0];
  if (first === "fetchVoID") return "discovery-first";
  if (first === "comunica_query") return "query-first";
  if (first === "fetchShapes") return "shapes-first";
  if (first === "fetchExamples") return "examples-first";
  return first;
}

function generateReport(data: ExperimentResult): string {
  const pricing = PRICING[data.model] ?? { input: 3, output: 15 };
  const date = data.timestamp.split("T")[0];
  const lines: string[] = [];

  lines.push(`# Experiment Report: ${data.condition}`);
  lines.push("");
  lines.push(`**Date**: ${data.timestamp}  `);
  lines.push(`**Model**: ${data.model}  `);
  lines.push(`**Endpoint**: ${data.endpoint}  `);
  lines.push(`**Condition**: ${data.condition}  `);
  lines.push(`**Pricing**: $${pricing.input}/MTok in, $${pricing.output}/MTok out`);
  lines.push("");

  // Aggregate
  const a = data.aggregate;
  lines.push("## Summary");
  lines.push("");
  lines.push("| Metric | Value |");
  lines.push("|--------|-------|");
  lines.push(`| Score | ${(a.meanScore * 100).toFixed(1)}% (${data.results.filter((r) => r.score === 1).length}/${a.taskCount}) |`);
  lines.push(`| Mean iterations | ${a.meanIterations.toFixed(1)} |`);
  lines.push(`| Total wall time | ${(a.totalWallTimeMs / 1000).toFixed(1)}s |`);
  lines.push(`| Total tokens | ${a.totalPromptTokens.toLocaleString()} in / ${a.totalCompletionTokens.toLocaleString()} out |`);
  lines.push(`| Total cost | $${a.costUsd.toFixed(4)} |`);
  lines.push(`| Cost per task | $${a.costPerTask.toFixed(4)} |`);
  lines.push("");

  // Per-task table
  lines.push("## Per-Task Results");
  lines.push("");
  lines.push("| Task | Score | Iters | Time | Tokens (in/out) | Cost | Strategy |");
  lines.push("|------|-------|-------|------|-----------------|------|----------|");

  for (const r of data.results) {
    const toolCalls = extractToolCalls(r.trajectory);
    const strategy = classifyStrategy(toolCalls);
    const tokIn = r.tokenUsage?.promptTokens ?? 0;
    const tokOut = r.tokenUsage?.completionTokens ?? 0;
    const cost = (tokIn / 1e6) * pricing.input + (tokOut / 1e6) * pricing.output;
    lines.push(
      `| ${r.taskId} | ${r.score.toFixed(1)} | ${r.iterations} | ${(r.wallTimeMs / 1000).toFixed(1)}s | ${tokIn.toLocaleString()}/${tokOut.toLocaleString()} | $${cost.toFixed(4)} | ${strategy} |`,
    );
  }
  lines.push("");

  // Tool usage analysis
  lines.push("## Tool Usage");
  lines.push("");

  for (const r of data.results) {
    const toolCalls = extractToolCalls(r.trajectory);
    const sparqlQueries = extractSparqlQueries(r.trajectory);
    lines.push(`### ${r.taskId}`);
    lines.push("");
    lines.push(`**Tool sequence**: ${toolCalls.join(" → ") || "none"}`);
    lines.push("");
    if (sparqlQueries.length > 0) {
      lines.push(`**SPARQL queries** (${sparqlQueries.length}):`);
      for (let i = 0; i < sparqlQueries.length; i++) {
        // Compact: single-line the query
        const compact = sparqlQueries[i].replace(/\s+/g, " ").slice(0, 200);
        lines.push(`${i + 1}. \`${compact}\``);
      }
      lines.push("");
    }
    if (r.error) {
      lines.push(`**Error**: ${r.error}`);
      lines.push("");
    }
  }

  // Trajectory detail (compact: code + output per iteration, no reasoning)
  lines.push("## Trajectory Detail");
  lines.push("");

  for (const r of data.results) {
    lines.push(`### ${r.taskId} (${r.iterations} iterations)`);
    lines.push("");

    for (const step of r.trajectory) {
      const tok = step.usage
        ? ` [${step.usage.promptTokens ?? 0}+${step.usage.completionTokens ?? 0} tok, ${step.durationMs}ms]`
        : ` [${step.durationMs}ms]`;
      lines.push(`**Iter ${step.iteration}**${tok}:`);

      if (step.code) {
        // Truncate long code blocks
        const code = step.code.length > 500 ? step.code.slice(0, 500) + "\n// ... truncated" : step.code;
        lines.push("```javascript");
        lines.push(code);
        lines.push("```");
      }

      if (step.output) {
        const output = step.output.length > 300 ? step.output.slice(0, 300) + "\n// ... truncated" : step.output;
        lines.push(`Output: \`${output.replace(/\n/g, " ").slice(0, 200)}\``);
      }
      if (step.error) {
        lines.push(`Error: \`${step.error}\``);
      }
      if (step.returned) {
        lines.push("**→ SUBMITTED answer**");
      }
      lines.push("");
    }
  }

  return lines.join("\n");
}

function main() {
  // Find input file(s)
  let inputFiles = process.argv.slice(2);
  if (inputFiles.length === 0) {
    // Auto-discover most recent results file
    const resultsDir = join(__dirname, "results");
    try {
      const files = readdirSync(resultsDir)
        .filter((f) => f.startsWith("fabric-") && f.endsWith(".json"))
        .sort()
        .reverse();
      if (files.length > 0) {
        inputFiles = [join(resultsDir, files[0])];
        console.log(`Auto-discovered: ${files[0]}`);
      } else {
        console.error("No result files found in results/");
        process.exit(1);
      }
    } catch {
      console.error("No results/ directory found. Run an experiment first.");
      process.exit(1);
    }
  }

  const reportsDir = join(__dirname, "reports");
  mkdirSync(reportsDir, { recursive: true });

  for (const inputFile of inputFiles) {
    const data: ExperimentResult = JSON.parse(readFileSync(inputFile, "utf-8"));
    const report = generateReport(data);
    const date = data.timestamp.split("T")[0];
    const outFile = join(reportsDir, `${data.condition}_${data.model}_${date}.md`);
    writeFileSync(outFile, report);
    console.log(`Report: ${outFile}`);
  }
}

main();
