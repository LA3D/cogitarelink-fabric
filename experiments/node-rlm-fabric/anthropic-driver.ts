/**
 * Anthropic Messages API driver for node-rlm.
 *
 * node-rlm's only built-in driver (`fromOpenRouterCompatible`) targets
 * OpenAI-compatible `/chat/completions` endpoints.  Anthropic's API uses
 * `/v1/messages` with a different auth header and message format.
 *
 * This driver implements the `CallLLM` interface by translating between
 * node-rlm's flat message array and Anthropic's Messages API.
 */
import type { CallLLM, CallLLMResponse } from "node-rlm";
import { translateMessages } from "node-rlm/drivers/openrouter-compatible";

const DEFAULT_TIMEOUT_MS = 120_000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_MAX_TOKENS = 16384;
const BASE_DELAY_MS = 1000;

export interface AnthropicDriverOptions {
  apiKey: string;
  model: string;
  baseUrl?: string;
  timeoutMs?: number;
  maxRetries?: number;
  maxTokens?: number;
  reasoningEffort?: string;
}

// Anthropic message content block types
interface TextBlock {
  type: "text";
  text: string;
}

interface ThinkingBlock {
  type: "thinking";
  thinking: string;
}

interface ToolUseBlock {
  type: "tool_use";
  id: string;
  name: string;
  input: Record<string, unknown>;
}

type ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock;

interface AnthropicMessage {
  role: "user" | "assistant";
  content: string | ContentBlock[];
}

interface AnthropicResponse {
  content: ContentBlock[];
  usage?: {
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens?: number;
    cache_read_input_tokens?: number;
  };
  stop_reason: string;
  error?: { type: string; message: string };
}

// The execute_code tool in Anthropic's tool format
const EXECUTE_CODE_TOOL_ANTHROPIC = {
  name: "execute_code",
  description:
    "Execute JavaScript in a persistent Node.js REPL. console.log() output is returned. Call return(value) to produce your final answer.",
  input_schema: {
    type: "object" as const,
    properties: {
      code: { type: "string" as const, description: "JavaScript code to execute" },
    },
    required: ["code"],
  },
};

/**
 * Convert OpenAI-format chat messages (from translateMessages) to
 * Anthropic Messages API format.
 *
 * Key differences:
 * - System prompt is a top-level field, not a message
 * - Tool calls are content blocks `{ type: "tool_use" }` in assistant messages
 * - Tool results are content blocks `{ type: "tool_result" }` in user messages
 * - Messages must strictly alternate user/assistant
 */
function toAnthropicMessages(
  openaiMessages: Array<{
    role: string;
    content: string | null;
    tool_calls?: Array<{
      id: string;
      type: "function";
      function: { name: string; arguments: string };
    }>;
    tool_call_id?: string;
  }>,
): AnthropicMessage[] {
  const result: AnthropicMessage[] = [];

  for (const msg of openaiMessages) {
    if (msg.role === "system") {
      // Skip — system prompt handled separately
      continue;
    }

    if (msg.role === "assistant" && msg.tool_calls?.length) {
      // Assistant message with tool call
      const content: ContentBlock[] = [];
      if (msg.content) {
        content.push({ type: "text", text: msg.content });
      }
      for (const tc of msg.tool_calls) {
        let input: Record<string, unknown>;
        try {
          input = JSON.parse(tc.function.arguments);
        } catch {
          input = { code: tc.function.arguments };
        }
        content.push({
          type: "tool_use",
          id: tc.id,
          name: tc.function.name,
          input,
        });
      }
      result.push({ role: "assistant", content });
    } else if (msg.role === "tool") {
      // Tool result — must be in a user message
      const toolResult: ContentBlock[] = [
        {
          type: "tool_result" as any,
          tool_use_id: msg.tool_call_id,
          content: msg.content ?? "",
        } as any,
      ];
      // Merge with previous user message if the last message is also user
      if (result.length > 0 && result[result.length - 1].role === "user") {
        const prev = result[result.length - 1];
        if (Array.isArray(prev.content)) {
          prev.content.push(...toolResult);
        } else {
          prev.content = [
            { type: "text", text: prev.content as string },
            ...toolResult,
          ];
        }
      } else {
        result.push({ role: "user", content: toolResult });
      }
    } else if (msg.role === "assistant") {
      result.push({ role: "assistant", content: msg.content ?? "" });
    } else {
      // user message
      result.push({ role: "user", content: msg.content ?? "" });
    }
  }

  return result;
}

export function fromAnthropic(options: AnthropicDriverOptions): CallLLM {
  const {
    apiKey,
    model,
    baseUrl = "https://api.anthropic.com",
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxRetries = DEFAULT_MAX_RETRIES,
    maxTokens = DEFAULT_MAX_TOKENS,
    reasoningEffort: defaultReasoningEffort,
  } = options;

  const endpoint = `${baseUrl.replace(/\/+$/, "")}/v1/messages`;
  let callCount = 0;

  return async (messages, systemPrompt, callOptions) => {
    // Use node-rlm's translateMessages to get OpenAI format, then convert
    const openaiMessages = translateMessages(messages);
    const anthropicMessages = toAnthropicMessages(openaiMessages);

    // Ensure first message is from user (Anthropic requirement)
    if (anthropicMessages.length === 0 || anthropicMessages[0].role !== "user") {
      anthropicMessages.unshift({ role: "user", content: "Begin." });
    }

    const callId = ++callCount;
    const inputChars = messages.reduce((n, m) => n + m.content.length, 0);

    const effort = callOptions?.reasoningEffort ?? defaultReasoningEffort;
    const useReasoning = !!(effort && effort !== "none");

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const t0 = Date.now();

      const reqBody: Record<string, unknown> = {
        model,
        system: systemPrompt,
        messages: anthropicMessages,
        max_tokens: maxTokens,
        tools: [EXECUTE_CODE_TOOL_ANTHROPIC],
        tool_choice: { type: "any" }, // Force tool use (like TOOL_CHOICE in OpenAI driver)
      };

      // Extended thinking for Claude models
      if (useReasoning) {
        reqBody.thinking = { type: "enabled", budget_tokens: 10000 };
        // Extended thinking is incompatible with forced tool_choice
        reqBody.tool_choice = { type: "auto" };
      }

      const abortController = new AbortController();
      const timeoutId = setTimeout(() => abortController.abort(), timeoutMs);

      let response: Response;
      try {
        response = await fetch(endpoint, {
          signal: abortController.signal,
          method: "POST",
          headers: {
            "x-api-key": apiKey,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
          },
          body: JSON.stringify(reqBody),
        });
      } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === "AbortError") {
          throw new Error(`${model}: request timed out after ${timeoutMs}ms`);
        }
        throw err;
      }

      if (!response.ok) {
        clearTimeout(timeoutId);
        const text = await response.text();
        const status = response.status;
        if ((status === 429 || status >= 500) && attempt < maxRetries) {
          const delay = BASE_DELAY_MS * 2 ** attempt;
          console.error(
            `[${model}] HTTP ${status}, retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries})...`,
          );
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }
        throw new Error(`${model} API error (${status}): ${text}`);
      }

      clearTimeout(timeoutId);
      const data = (await response.json()) as AnthropicResponse;

      if (data.error) {
        throw new Error(`${model} error: ${data.error.message}`);
      }

      // Extract reasoning (text blocks + thinking blocks) and tool use
      let reasoning = "";
      let code: string | null = null;
      let toolUseId: string | null = null;

      for (const block of data.content) {
        if (block.type === "thinking") {
          reasoning += (reasoning ? "\n" : "") + block.thinking;
        } else if (block.type === "text") {
          reasoning += (reasoning ? "\n" : "") + block.text;
        } else if (block.type === "tool_use" && block.name === "execute_code") {
          toolUseId = block.id;
          code = (block.input as { code?: string }).code ?? null;
        }
      }

      // Extract token usage from Anthropic response
      const usage = data.usage
        ? {
            promptTokens: data.usage.input_tokens,
            completionTokens: data.usage.output_tokens,
            cacheReadTokens: data.usage.cache_read_input_tokens ?? 0,
            cacheWriteTokens: data.usage.cache_creation_input_tokens ?? 0,
          }
        : undefined;

      const elapsed = Date.now() - t0;
      const outChars = reasoning.length + (code?.length ?? 0);
      const inTok = usage?.promptTokens ?? 0;
      const outTok = usage?.completionTokens ?? 0;
      console.error(
        `[${model} #${callId}] ${elapsed}ms, in=${inTok}tok, out=${outTok}tok, stop=${data.stop_reason}`,
      );

      const result: CallLLMResponse & { usage?: typeof usage } = { reasoning, code };
      if (toolUseId) {
        result.toolUseId = toolUseId;
      }
      if (usage) {
        result.usage = usage;
      }
      return result;
    }

    throw new Error(`${model}: exhausted all retries`);
  };
}
