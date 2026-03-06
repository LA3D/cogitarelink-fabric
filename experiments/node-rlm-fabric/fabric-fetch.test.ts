import { describe, it, expect } from "vitest";
import { createFabricFetch, acquireVpToken } from "./fabric-fetch.js";

describe("createFabricFetch", () => {
  it("returns a function", () => {
    const f = createFabricFetch({ vpToken: "test-token" });
    expect(typeof f).toBe("function");
  });

  it("adds Authorization header when vpToken provided", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string | URL | Request, options?: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        new Headers(options?.headers).entries(),
      );
      return new Response("ok");
    };

    const f = createFabricFetch({
      vpToken: "my-token",
      baseFetch: mockFetch as typeof fetch,
    });
    await f("https://example.com/sparql", {});
    expect(capturedHeaders["authorization"]).toBe("Bearer my-token");
  });

  it("does not add Authorization when no vpToken", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = async (url: string | URL | Request, options?: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        new Headers(options?.headers).entries(),
      );
      return new Response("ok");
    };

    const f = createFabricFetch({
      baseFetch: mockFetch as typeof fetch,
    });
    await f("https://example.com/void", {});
    expect(capturedHeaders["authorization"]).toBeUndefined();
  });
});
