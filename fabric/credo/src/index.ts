/**
 * Credo-TS sidecar — DID/VC identity layer for cogitarelink-fabric (D3, D8)
 *
 * Phase 2: full identity bootstrap — agent init, did:webvh creation,
 * FabricConformanceCredential self-issuance, VC verify.
 * Shares DID log + conformance VC with FastAPI gateway via /shared volume.
 *
 * VC signing uses eddsa-jcs-2022 Data Integrity proofs implemented inline
 * (json-canonicalize + Ed25519 from Credo KMS). This bypasses Credo's
 * W3cJsonLdCredentialService which has a broken ESM import in 0.6.x.
 */
import express from 'express'
import fs from 'fs'
import path from 'path'
import {
  Agent,
  Buffer,
  ConsoleLogger,
  DidsModule,
  Hasher,
  Kms,
  LogLevel,
  TypedArrayEncoder,
  getPublicJwkFromVerificationMethod,
} from '@credo-ts/core'
import type { InitConfig } from '@credo-ts/core'
import {
  agentDependencies,
  NodeKeyManagementService,
  NodeInMemoryKeyManagementStorage,
} from '@credo-ts/node'
import { AskarModule } from '@credo-ts/askar'
import { askar } from '@openwallet-foundation/askar-nodejs'
import { WebVhModule, WebVhDidRegistrar, WebVhDidResolver } from '@credo-ts/webvh'
import { canonicalize } from 'json-canonicalize'

const PORT = parseInt(process.env.PORT ?? '3000', 10)
const NODE_DOMAIN = process.env.NODE_DOMAIN ?? 'localhost:8080'
const NODE_BASE = process.env.NODE_BASE ?? 'http://localhost:8080'
const SHARED_DIR = process.env.SHARED_DIR ?? '/shared'

const config: InitConfig = {
  label: 'cogitarelink-fabric-credo',
  allowInsecureHttpUrls: true,
  logger: new ConsoleLogger(LogLevel.warn),
}

const agent = new Agent({
  config,
  dependencies: agentDependencies,
  modules: {
    askar: new AskarModule({
      askar,
      store: {
        id: 'fabric-node-wallet',
        key: process.env.WALLET_KEY ?? 'fabric-dev-key-change-in-production',
      },
    }),
    kms: new Kms.KeyManagementModule({
      backends: [
        new NodeKeyManagementService(new NodeInMemoryKeyManagementStorage()),
      ],
    }),
    webvh: new WebVhModule(),
    dids: new DidsModule({
      registrars: [new WebVhDidRegistrar()],
      resolvers: [new WebVhDidResolver()],
    }),
  },
})

const app = express()
app.use(express.json())

let agentStatus: 'initializing' | 'ready' | 'failed' = 'initializing'
let agentError: string | null = null
let nodeDid: string | null = null
let conformanceVCIssued = false

// --------------- eddsa-jcs-2022 inline (D5) ---------------
// Implements DataIntegrityProof with eddsa-jcs-2022 cryptosuite.
// Uses JCS canonicalization — no JSON-LD processing needed.

const BASE58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
function base58btcEncode(bytes: Uint8Array): string {
  // multibase prefix 'z' = base58btc
  let result = ''
  let num = BigInt('0x' + Buffer.from(bytes).toString('hex'))
  while (num > 0n) {
    result = BASE58_CHARS[Number(num % 58n)] + result
    num = num / 58n
  }
  for (const b of bytes) {
    if (b === 0) result = '1' + result
    else break
  }
  return 'z' + result
}

function base58btcDecode(encoded: string): Uint8Array {
  // strip multibase prefix 'z'
  const str = encoded.startsWith('z') ? encoded.slice(1) : encoded
  let num = 0n
  for (const c of str) {
    const idx = BASE58_CHARS.indexOf(c)
    if (idx === -1) throw new Error(`Invalid base58 char: ${c}`)
    num = num * 58n + BigInt(idx)
  }
  const hex = num.toString(16).padStart(2, '0')
  const bytes = Buffer.from(hex.length % 2 ? '0' + hex : hex, 'hex')
  // leading zeros
  let leadingZeros = 0
  for (const c of str) {
    if (c === '1') leadingZeros++
    else break
  }
  return Uint8Array.from([...new Uint8Array(leadingZeros), ...bytes])
}

function jcsHash(obj: unknown): Uint8Array {
  return Hasher.hash(TypedArrayEncoder.fromString(canonicalize(obj)), 'sha-256')
}

async function createProof(
  unsecuredDoc: Record<string, unknown>,
  proofOptions: Record<string, string>,
): Promise<Record<string, unknown>> {
  const docHash = jcsHash(unsecuredDoc)
  const optHash = jcsHash(proofOptions)
  const hashData = new Uint8Array(optHash.length + docHash.length)
  hashData.set(optHash, 0)
  hashData.set(docHash, optHash.length)

  // Find signing key from DID record
  const vmId = proofOptions.verificationMethod
  const didDoc = await agent.dids.resolveDidDocument(vmId)
  const [didRecord] = await agent.dids.getCreatedDids({ did: didDoc.id })
  const vm = didDoc.dereferenceVerificationMethod(vmId)
  const publicJwk = getPublicJwkFromVerificationMethod(vm)

  const keyApi = agent.agentContext.dependencyManager.resolve(Kms.KeyManagementApi)
  const keyId = didRecord.keys?.find(
    (k: any) => k.didDocumentRelativeKeyId === `#${vm.publicKeyMultibase}`,
  )?.kmsKeyId ?? publicJwk.legacyKeyId

  const { signature } = await keyApi.sign({
    keyId,
    algorithm: 'EdDSA',
    data: Buffer.from(hashData),
  })

  return { ...proofOptions, proofValue: base58btcEncode(signature) }
}

async function verifyProof(
  securedDoc: Record<string, unknown>,
): Promise<{ verified: boolean; verifiedDocument?: Record<string, unknown> }> {
  const { proof, ...unsecuredDoc } = securedDoc
  const proofObj = proof as Record<string, string>
  const { proofValue, ...proofOptions } = proofObj

  const docHash = jcsHash(unsecuredDoc)
  const optHash = jcsHash(proofOptions)
  const hashData = new Uint8Array(optHash.length + docHash.length)
  hashData.set(optHash, 0)
  hashData.set(docHash, optHash.length)

  const sigBytes = base58btcDecode(proofValue)
  const vmId = proofOptions.verificationMethod
  const didDoc = await agent.dids.resolveDidDocument(vmId)
  const vm = didDoc.dereferenceVerificationMethod(vmId)
  const publicJwk = getPublicJwkFromVerificationMethod(vm)

  const keyApi = agent.agentContext.dependencyManager.resolve(Kms.KeyManagementApi)
  const { verified } = await keyApi.verify({
    key: { publicJwk: publicJwk.toJson() },
    algorithm: 'EdDSA',
    signature: sigBytes,
    data: hashData,
  })

  return { verified, verifiedDocument: verified ? unsecuredDoc : undefined }
}

// --------------- helpers ---------------

function ensureSharedDir() {
  if (!fs.existsSync(SHARED_DIR)) fs.mkdirSync(SHARED_DIR, { recursive: true })
}

function encodeDomain(domain: string): string {
  return domain.replace(':', '%3A')
}

async function writeDIDLog(did: string) {
  const records = await agent.dids.getCreatedDids({ method: 'webvh' })
  const record = records.find(r => r.did === did)
  if (!record) throw new Error(`DID record not found for ${did}`)

  const log = record.metadata.get('log')
  if (!log) throw new Error(`DID log metadata not found for ${did}`)

  ensureSharedDir()
  const logLines = Array.isArray(log)
    ? log.map((entry: unknown) => JSON.stringify(entry)).join('\n')
    : JSON.stringify(log)
  fs.writeFileSync(path.join(SHARED_DIR, 'did.jsonl'), logLines + '\n')
}

function getVerificationMethodId(didDoc: any): string {
  const vmId = didDoc.assertionMethod?.[0]
    ?? didDoc.authentication?.[0]
    ?? didDoc.verificationMethod?.[0]?.id
  if (!vmId) throw new Error('No verification method on node DID')
  return typeof vmId === 'string' ? vmId : vmId.id
}

async function issueVC(
  type: string[],
  subject: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  if (!nodeDid) throw new Error('Node DID not initialized')

  const didDoc = await agent.dids.resolveDidDocument(nodeDid)
  const vmId = getVerificationMethodId(didDoc)

  const credential: Record<string, unknown> = {
    '@context': ['https://www.w3.org/ns/credentials/v2'],
    type: ['VerifiableCredential', ...type],
    issuer: nodeDid,
    validFrom: new Date().toISOString(),
    credentialSubject: { ...subject },
  }

  const proof = await createProof(credential, {
    type: 'DataIntegrityProof',
    cryptosuite: 'eddsa-jcs-2022',
    verificationMethod: vmId,
    proofPurpose: 'assertionMethod',
  })

  return { ...credential, proof }
}

// --------------- routes ---------------

app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    agent: agentStatus,
    ...(nodeDid ? { did: nodeDid } : {}),
    ...(conformanceVCIssued ? { conformanceVC: true } : {}),
    ...(agentError ? { error: agentError } : {}),
  })
})

app.post('/dids/node', async (_req, res) => {
  try {
    if (nodeDid) {
      const didDoc = await agent.dids.resolveDidDocument(nodeDid)
      return res.json({ did: nodeDid, didDocument: didDoc.toJSON() })
    }

    const domain = encodeDomain(NODE_DOMAIN)
    const result = await agent.dids.create({ method: 'webvh', domain } as any)

    if (result.didState.state !== 'finished' || !result.didState.did) {
      return res.status(500).json({
        error: 'DID creation failed',
        reason: (result.didState as any).reason ?? 'unknown',
      })
    }

    nodeDid = result.didState.did
    await writeDIDLog(nodeDid)

    console.log(`Node DID created: ${nodeDid}`)
    return res.json({
      did: nodeDid,
      didDocument: result.didState.didDocument?.toJSON(),
    })
  } catch (err) {
    console.error('DID creation error:', err)
    return res.status(500).json({ error: String(err) })
  }
})

app.get('/did.jsonl', (_req, res) => {
  const logPath = path.join(SHARED_DIR, 'did.jsonl')
  if (!fs.existsSync(logPath)) {
    return res.status(404).json({ error: 'DID log not found' })
  }
  res.setHeader('content-type', 'application/jsonl')
  return res.send(fs.readFileSync(logPath, 'utf-8'))
})

app.post('/credentials/issue', async (req, res) => {
  try {
    const { type, credentialSubject } = req.body
    if (!type || !credentialSubject) {
      return res.status(400).json({ error: 'type and credentialSubject required' })
    }
    const types = Array.isArray(type) ? type : [type]
    const vc = await issueVC(types, credentialSubject)
    return res.json(vc)
  } catch (err) {
    console.error('VC issuance error:', err)
    return res.status(500).json({ error: String(err) })
  }
})

app.post('/credentials/verify', async (req, res) => {
  try {
    const vcJson = req.body
    if (!vcJson || !vcJson.proof) {
      return res.status(400).json({ error: 'signed VC with proof required' })
    }

    const result = await verifyProof(vcJson)
    return res.json({
      verified: result.verified,
      ...(result.verified ? {} : { error: 'Proof verification failed' }),
    })
  } catch (err) {
    // DID resolution failures, missing keys, etc. = verification failure (not server error)
    console.error('VC verification error:', err)
    return res.json({ verified: false, error: String(err) })
  }
})

// --------------- startup bootstrap ---------------

async function bootstrap() {
  // 1. Create node DID
  const domain = encodeDomain(NODE_DOMAIN)
  const existing = await agent.dids.getCreatedDids({ method: 'webvh' })
  const existingRecord = existing.find(r => r.did?.includes(domain))

  if (existingRecord?.did) {
    nodeDid = existingRecord.did
    console.log(`Reusing existing node DID: ${nodeDid}`)
  } else {
    const result = await agent.dids.create({ method: 'webvh', domain } as any)
    if (result.didState.state !== 'finished' || !result.didState.did) {
      throw new Error(`DID creation failed: ${(result.didState as any).reason ?? 'unknown'}`)
    }
    nodeDid = result.didState.did
    console.log(`Node DID created: ${nodeDid}`)
  }

  await writeDIDLog(nodeDid)

  // 2. Self-issue FabricConformanceCredential (D12)
  const vc = await issueVC(
    ['FabricConformanceCredential'],
    {
      id: nodeDid,
      conformsTo: 'https://w3id.org/cogitarelink/fabric#CoreProfile',
      sparqlEndpoint: `${NODE_BASE}/sparql`,
      shaclEndpoint: `${NODE_BASE}/.well-known/shacl`,
      attestedAt: new Date().toISOString(),
    },
  )

  ensureSharedDir()
  fs.writeFileSync(
    path.join(SHARED_DIR, 'conformance-vc.json'),
    JSON.stringify(vc, null, 2),
  )
  conformanceVCIssued = true
  console.log('FabricConformanceCredential self-issued and written to /shared')
}

async function main() {
  app.listen(PORT, () => {
    console.log(`Credo sidecar listening on :${PORT}`)
  })

  try {
    await agent.initialize()
    agentStatus = 'ready'
    console.log('Credo agent initialized successfully')

    await bootstrap()
  } catch (err) {
    agentStatus = 'failed'
    agentError = String(err)
    console.error('Credo agent startup failed:', err)
  }
}

main()
