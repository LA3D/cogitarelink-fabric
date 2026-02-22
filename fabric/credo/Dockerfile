# Credo sidecar — must run as linux/amd64 on Apple Silicon (Rosetta, D8)
# Phase 1: ts-node --transpile-only (skip type-checking; focus on Rosetta runtime compat)
FROM node:22-slim

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
