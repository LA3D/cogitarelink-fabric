# KF Prototype Decisions Index

Always loaded. Concise index of all architectural decisions.

D1: Hyperledger role — narrowed to SHACL attestation VCs + DID PIDs only; no on-chain SPARQL, no chaincode, no orderer
D2: RLM as agent execution substrate — dspy.RLM (dspy.predict.rlm, dspy 3.1) is the implementation; REPL loop with tools=[sparql_query, fetch_void, ...]; fabric is infrastructure RLM navigates
D3: Credo (OpenWallet Foundation) + did:webvh for identity layer (version: Credo 0.6.x)
D4: Oxigraph Server for fabric nodes (HTTP SPARQL 1.2), pyoxigraph for agent working graph (in-process)
D5: did:webvh + digestMultibase — content integrity + node identity; did:key for witness signing
D6: Per-node URI space — node domain as URI authority; named graphs: /graph/observations, /graph/entities, /graph/claims, /graph/security, /graph/audit, /graph/pending, /graph/approvals, /graph/crosswalks, /graph/mappings
D7: PROF + VoID + SHACL + SPARQL examples at .well-known/; fabric:CoreProfile published once (shared); nodes declare dct:conformsTo
D8: Docker Compose (Phase 1-2), K8s (Phase 3); platform: linux/amd64 on Credo sidecar (Apple Silicon)
D9: Four-layer KR — SD+VoID (L1) → TBox cache ontologies+standard shapes (L2) → endpoint SHACL shapes (L3) → SPARQL examples+SSSOM (L4)
D10: Curator write tools — discover_write_targets, write_triples, validate_graph, commit_graph
D11: UUIDv7 PID minting + entity URI https://{node}/entity/{uuid7}; SSSOM crosswalks at /graph/crosswalks (entity PID dedup across sources) — distinct from D21
D12: Bootstrap node admission — did:webvh (node DID) + did:key (witness) + FabricConformanceCredential; /graph/registry self-entry
D13: did:webvh agent identity + AgentAuthorizationCredential; agent DID separate from node DID
D14: Agent role taxonomy — IngestCurator, LinkingCurator, Q&A, Maintenance, SecurityMonitor, IntegrityAuditor, DevelopmentAgent (Claude Code)
D15: Human-agent credential composition — three-way intersection; Solid WAC/ACP; ZCAP-LD (Community Group only — use FabricDelegationCredential VC as safe fallback)
D16: Phoenix + OTEL + SPDX 3.0 + PROV-O observability stack; DSPy openinference instrumentation
D17: Claude Code tooling — .claude/ in repo; SPDX/PROV-O bootstrap provenance; mock VC for DevelopmentAgent; Codemeta v3
D18: Nanopub compatibility — four-graph pattern (head/assertion/provenance/pubinfo); UUIDv7→TrustyURI; three-tier use cases (scientific/industry/DoD)
D19: HitL enforcement — VC 2.0 multi-proof + previousProof chaining; wallet separation (node wallet ≠ agent wallet); agentic escalation; session=delegation VC
D20: SDL instrument station use case — Phase 1 motivating use case (D2+D9+OD-1); electrochemical station (potentiostat); RLM REPL progressive disclosure; instrument ≠ agent (sosa:Sensor + DID); IngestCurator writes, Q&A navigates; SOSA/SSN+QUDT+PROV-O (local TBox) + PubChem CID via QLever SERVICE (https://qlever.dev/api/pubchem)
D21: SSSOM as native vocabulary alignment structure — /graph/mappings (vocab terms→standard IRIs); distinct from D11 /graph/crosswalks (entity PID dedup); CoreProfile role:mapping; validate_graph enforces SSSOM coverage; sssom-py for serialization; QLever PubChem chains via SERVICE

D22: Fabric ontology — FAIR vocabulary at https://w3id.org/cogitarelink/fabric; OWL 2 DL; 5 modules; follows Five Stars of Linked Data Vocabulary Use (Janowicz et al. 2014, co-authored Vardeman) — current rating ★★★★; ★★★ alignments: FabricNode→dcat:DataService+prov:Agent, AgentRole→prov:Role, FabricApprovalRequest→prov:Entity, ApprovalStatus/PublicationStatus→skos:Concept, delegatedBy→prov:wasAttributedTo; voaf:reliesOn × 5; stored at /ontology/fabric (D9 L2 TBox); CC-BY 4.0

Full log: ~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-Decisions.md
Use case: ~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Use-Case-SDL-Instrument.md
