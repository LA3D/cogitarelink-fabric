export interface FabricFetchOptions {
  vpToken?: string;
  baseFetch?: typeof fetch;
}

export function createFabricFetch(options: FabricFetchOptions = {}): typeof fetch {
  const { vpToken, baseFetch = globalThis.fetch } = options;

  return async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const headers = new Headers(init?.headers);

    if (vpToken) {
      headers.set("Authorization", `Bearer ${vpToken}`);
    }

    return baseFetch(url, { ...init, headers });
  };
}

export async function acquireVpToken(endpoint: string, fetchFn: typeof fetch = globalThis.fetch): Promise<string> {
  const resp = await fetchFn(`${endpoint}/test/create-vp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agentRole: "IngestCurator", validMinutes: 120 }),
  });
  if (!resp.ok) throw new Error(`VP token acquisition failed: ${resp.status}`);
  const data = await resp.json() as { token: string };
  return data.token;
}
