/**
 * Credo-TS sidecar — DID/VC identity layer for cogitarelink-fabric (D3, D8)
 *
 * Phase 1: minimal Express server with /health endpoint.
 * Agent initialization is attempted but failures are non-fatal at this stage
 * to validate Rosetta (platform: linux/amd64) compatibility on Apple Silicon.
 */
import express from 'express'
import { Agent, InitConfig } from '@credo-ts/core'
import { agentDependencies } from '@credo-ts/node'
import { AskarModule } from '@credo-ts/askar'
import { ariesAskar } from '@hyperledger/aries-askar-nodejs'

const PORT = parseInt(process.env.PORT ?? '3000', 10)

const config: InitConfig = {
  label: 'cogitarelink-fabric-credo',
  walletConfig: {
    id: 'fabric-node-wallet',
    key: process.env.WALLET_KEY ?? 'fabric-dev-key-change-in-production',
  },
}

const agent = new Agent({
  config,
  dependencies: agentDependencies,
  modules: {
    askar: new AskarModule({ ariesAskar }),
  },
})

const app = express()
app.use(express.json())

let agentStatus: 'initializing' | 'ready' | 'failed' = 'initializing'
let agentError: string | null = null

app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    agent: agentStatus,
    ...(agentError ? { error: agentError } : {}),
  })
})

async function main() {
  app.listen(PORT, () => {
    console.log(`Credo sidecar listening on :${PORT}`)
  })

  try {
    await agent.initialize()
    agentStatus = 'ready'
    console.log('Credo agent initialized successfully')
  } catch (err) {
    agentStatus = 'failed'
    agentError = String(err)
    // Non-fatal in Phase 1 — surface via /health for Rosetta diagnostics (D8)
    console.error('WARNING: Credo agent initialization failed:', err)
  }
}

main()
