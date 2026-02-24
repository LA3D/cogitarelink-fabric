# Credo sidecar — must run as linux/amd64 on Apple Silicon (Rosetta, D8)
# Node 20: @credo-ts/core 0.6.x has ESM import without .js extension in nativeDocumentLoader.mjs
# that breaks on Node 22's strict ESM resolution. Node 20 LTS resolves this correctly.
FROM node:20-slim

WORKDIR /app

# Native build deps for aries-askar
RUN apt-get update && apt-get install -y \
    python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
RUN npm install

COPY tsconfig.json .
COPY src/ ./src/

EXPOSE 3000

# --transpile-only: skip TypeScript type-checking; validates Rosetta/Askar runtime loading
CMD ["npx", "ts-node", "--transpile-only", "src/index.ts"]
