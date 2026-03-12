# Architecture deep dive

*This essay is part of the [cogitarelink-fabric](../README.md) project documentation.*

**Summary.** The fabric's architecture rests on four pillars: self-description as linked contracts (PROF profiles threading shape IRIs through VoID, Service Description, and SHACL documents), the RLM agent substrate (REPL-based context engineering separating variable space from token space), map-reduce federation (TBox routing pass + ABox data pass across multiple endpoints), and standards-based identity and trust (DIDs, VCs, content integrity hashes, LDN messaging). Each pillar is detailed below with the full technical exposition.

---

## Self-description as linked contracts

The four layers aren't just stacked — they're linked. The same shape IRI threads through VoID, the Service Description, and the SHACL document, creating a chain of metadata that an agent (or a validator) can follow from any entry point.

The chain works like this. The PROF profile (`fabric:CoreProfile` in `ontology/fabric-core-profile.ttl`) declares what a conforming node must provide, organized by role: `role:schema` for TBox ontologies, `role:constraints` for SHACL shapes, `role:example` for SPARQL query catalogs, `role:guidance` for agent navigation instructions. A node asserts `dct:conformsTo fabric:CoreProfile` in its VoID root dataset to claim conformance.

Each named graph then declares its own governing shape. The VoID description for `/graph/observations` includes `dct:conformsTo fabric:ObservationShape`; the Service Description's `sd:namedGraph` entry for the same graph carries the same `dct:conformsTo` link. That IRI — `fabric:ObservationShape` — names the actual `sh:NodeShape` in the SHACL document, which declares `sh:targetClass sosa:Observation`, lists required and optional properties with cardinalities and datatypes, and includes `sh:agentInstruction` text with concrete query patterns. The SPARQL examples catalog completes the chain with working queries that demonstrate access patterns against that graph.

```
fabric:CoreProfile (PROF)
  ├── role:schema      → SOSA, SIO, OWL-Time, PROV-O (TBox ontologies)
  ├── role:constraints → fabric:ObservationShape, fabric:EntityShape (SHACL)
  ├── role:example     → SPARQL examples catalog
  └── role:guidance    → progressive disclosure instructions

VoID root dataset
  dct:conformsTo → fabric:CoreProfile
  void:subset /graph/observations
    dct:conformsTo → fabric:ObservationShape  ←──┐
  void:subset /graph/entities                     │
    dct:conformsTo → fabric:EntityShape           │
                                                  │
SD sd:namedGraph /graph/observations              │
    dct:conformsTo → fabric:ObservationShape  ←───┤
                                                  │
SHACL shapes document                             │
    fabric:ObservationShape  ←────────────────────┘
      sh:targetClass sosa:Observation
      sh:property sosa:resultTime (required, xsd:dateTime)
      sh:property sosa:hasSimpleResult (optional)
      sh:property sio:has-attribute (optional, class sio:MeasuredValue)
      sh:agentInstruction "Observations use one of two result patterns..."
```

This linking creates two kinds of contracts:

**Read contracts.** An agent discovering the endpoint reads VoID, sees that `/graph/observations` conforms to `fabric:ObservationShape`, looks up that shape in the SHACL document, and knows what properties to expect before issuing a single data query. The shape is a guaranteed description of what the graph contains — not a hint, but a constraint the data was validated against. The agent can construct targeted SPARQL queries directly from the shape's property declarations rather than exploring blind.

**Write contracts.** When a curator agent writes new data, the same shapes serve as validation gates. D24 (shape-bound minting) enforces this: `commit_graph` runs SHACL validation against the governing shape before allowing data into the named graph. The `dct:conformsTo` link on the graph tells the validator which shape to apply. Data that doesn't conform doesn't get written. Trust gaps — missing credentials, ambiguous entity deduplication, shape version conflicts — surface as `fabric:PendingTask` notifications delivered to the responsible party's LDN inbox rather than silently accepted.

**Vocabulary contracts.** The same governance mechanism applies upward to the TBox ontologies at L2 — not just the data they describe. The Five Stars of Linked Data Vocabulary Use (Janowicz et al., 2014) and the Ten Simple Rules for Making a Vocabulary FAIR (Cox et al., 2021) define what a well-formed vocabulary should provide: persistent URIs, machine-readable metadata (`voaf:Vocabulary`, `dct:creator`, `dct:license`), explicit links to other vocabularies (`voaf:reliesOn`, `rdfs:subClassOf`), version information, and documentation. These criteria are expressible as SHACL shapes. A `VocabularyMetadataShape` can require `dct:license`, `owl:versionInfo`, at least one `voaf:reliesOn` declaration, and term-level `rdfs:label` + `rdfs:comment` coverage — the same kind of constraint that `ObservationShape` enforces on observation data. When a node caches a TBox ontology in its `/ontology/{vocab}` named graph, the `commit_graph` validation that governs data writes can enforce vocabulary quality standards on the ontology itself. An ontology missing its license, lacking version information, or failing to declare its vocabulary dependencies doesn't get admitted to the TBox cache. The fabric's own vocabulary (`ontology/fabric.ttl`) is built to pass these checks: it carries Five Stars metadata through ★★★★, declares five `voaf:reliesOn` dependencies, provides `dct:bibliographicCitation` for its design references, and reports machine-readable term counts (`voaf:classNumber`, `voaf:propertyNumber`). The Five Stars criteria become machine-enforceable admission requirements rather than manual checklists — and because they're SHACL shapes, the same agent tooling that validates data can validate the vocabularies the data is described with.

The PROF profile ties the bundle together. A new node joining the fabric asserts conformance to `fabric:CoreProfile`, which means it commits to providing all four layers with their linking metadata. A bootstrap witness can verify this claim by checking that the `.well-known/` endpoints exist, the VoID subsets declare `dct:conformsTo`, and the referenced shapes are present in the SHACL document. The `FabricConformanceCredential` (D26) then binds these artifacts to cryptographic hashes, so any subsequent tampering is detectable.

The result is metadata that's self-describing all the way down. An agent doesn't need to trust that a graph contains what it claims — it can verify the chain from profile to shape to data. And the same chain that enables agent navigation also enables automated validation, content integrity checking, and human-in-the-loop approval workflows.

## Agent substrate: RLM as context engineering

Agents are [DSPy](https://github.com/stanfordnlp/dspy) RLM programs — Recursive Language Models (Zhang, Kraska, & Khattab, 2025). An RLM operates a Python REPL loop: the LLM writes code, executes it, reads the output, writes more code — iterating until it can produce an answer. Fabric tools (`sparql_query`, `analyze_rdfs_routes`) are injected into the REPL namespace so the agent can call them from generated code.

The agent substrate is separate from the fabric infrastructure. Agents connect externally via HTTP; the fabric node does not host agents.

**What RLM gets right.** Zhang et al. identify three flaws in prior long-context scaffolding approaches: (1) feeding the full user prompt directly into the LLM context window, inheriting its size limits; (2) generating output autoregressively, so output can't exceed the context window either; and (3) lacking symbolic recursion, so the model can only delegate a few verbalized sub-tasks rather than looping programmatically over input slices. RLM fixes all three with a single mechanism: the prompt is loaded as a variable in a persistent Python REPL, not placed in the LLM's context. The model writes code to inspect, slice, and transform the variable contents, and can recursively invoke itself on sub-problems via `llm_query()` calls. This enables processing inputs two orders of magnitude beyond the model's native context window (10M+ tokens), with median cost *lower* than direct ingestion because the model reads selectively rather than consuming everything.

The key insight, in their words: "arbitrarily long user prompts should not be fed into the neural network directly but should instead be treated as part of the environment that the LLM is tasked to symbolically and recursively interact with."

**Why this matters for knowledge graphs.** The core problem with knowledge graph navigation is that the relevant data far exceeds any context window. A SPARQL endpoint might hold millions of triples across dozens of named graphs. RAG's answer — embed everything, retrieve the top-k chunks — doesn't work here because the "relevant" triples depend on schema relationships the agent hasn't discovered yet. You can't embed your way to understanding that `sio:has-attribute` chains to `sio:has-value` via an intermediate `MeasuredValue` node; you have to read the ontology structure and follow it.

RLM solves this by separating two spaces:

- **Variable space** holds arbitrarily large artifacts. Full SPARQL result sets, parsed ontology graphs, and accumulated entity data live in Python variables across iterations. The agent can hold an entire TBox in a variable and query it locally without consuming context tokens.
- **Token space** holds bounded observations. Each iteration, the agent sees only a size-capped view of what its code produced — enough to reason about what to do next, not enough to overwhelm the context window.

This separation turns the agent into a context engineering system. The agent doesn't receive a pre-built prompt with all relevant information stuffed in; it actively constructs its own context by writing code to fetch metadata, parsing the response into variables, inspecting the parts it needs, and building progressively more targeted queries. Each REPL iteration narrows the search space rather than broadening the context. In Zhang et al.'s terminology, the agent performs Ω(|P|) semantic work — processing proportional to the input size — while keeping the LLM's context window bounded to a constant size per iteration. For a federated knowledge fabric with multiple endpoints, each hosting different vocabularies and named graphs, this is the difference between scalable navigation and context window overflow.

## Map-reduce and agentic search

A single fabric node is useful, but the architecture is designed for federation: multiple autonomous nodes, each self-describing, each queryable by the same agent using the same tools.

Navigating a federation is iterative map-reduce (in the MPI/distributed-computing sense, not the Hadoop batch-processing sense). The agent maps queries to multiple endpoints in parallel, reduces the results through semantic judgment (ontology alignment, entity resolution, conflict handling), and decides what to query next based on what it learned. This operates at two levels:

**TBox map-reduce** (run once per fabric, cacheable): The agent queries each endpoint's `.well-known/` metadata — VoID descriptions, SHACL shapes, SPARQL examples, and the DCAT catalog. It assesses vocabulary quality, identifies shared and divergent terms, and builds a navigation map of what data exists where and how vocabularies relate. The catalog (D23/D29) now includes both local named graphs and external SPARQL endpoints that the node vouches for — QLever's PubChem, Wikidata, and OpenStreetMap endpoints are registered as `dcat:DataService` entries with `fabric:vouchedBy`, vocabulary declarations, and example SPARQL queries. This means an agent can discover both fabric-internal and fabric-external data sources through the same `/.well-known/catalog` interface. This phase is cheap (metadata is small) and produces the routing knowledge that makes data queries efficient.

**ABox map-reduce** (per question, iterative): Using the navigation map, the agent dispatches data queries to the right endpoints with the right vocabulary. Results come back, the agent resolves entities across sources, handles conflicts, identifies gaps, and iterates. The reduce step requires semantic judgment — recognizing that `up:encodedBy` and `gene:expresses` describe the same biological relationship across two endpoints — which is exactly what LLMs are good at.

**How self-description reduces iterations.** Without self-describing metadata, an agent encountering an unfamiliar endpoint must explore by trial and error: guess at property names, issue broad queries, read the returned predicates, infer the schema post-hoc, and try again with better-informed queries. Our Phase 3 experiments measured this directly — against SIO (a vocabulary outside the LLM's pretraining), agents without TBox structural hints failed on schema reasoning tasks that required knowing property directions and range constraints.

With self-description, the agent reads the endpoint's VoID to learn what named graphs and vocabularies exist, reads the SHACL shapes to learn what properties connect which classes, and reads the SPARQL examples to see working query patterns. Each of these steps narrows the search space *before the first data query is issued*. The agent doesn't have to guess what the endpoint contains; the endpoint tells it. Our Phase 3b result — a 0.167 score lift from adding TBox path hints — quantifies the difference between grounded and ungrounded query construction for unfamiliar vocabularies.

This is also a response to the needle-in-a-haystack problem at a structural level. The traditional version of this problem asks whether an LLM can find a specific fact buried in a long context. The fabric version asks whether an agent can find the right triples across a federation of endpoints it has never seen before. Self-describing metadata converts this from a search problem (scan everything until you find it) into a navigation problem (follow the metadata to the right graph, the right shape, the right query pattern). Navigation scales; exhaustive search does not.

## Identity, credentials, and content integrity

The fabric uses W3C and Decentralized Identity Foundation (DIF) standards for node identity and trust. Every standard referenced here has an existing specification, multiple interoperable implementations, and an active community. We chose to adopt them rather than design custom authentication or integrity mechanisms for the same reason we use SHACL rather than inventing a constraint language: the problems are already solved, the edge cases are already discovered, and agents that learn to work with one fabric node can transfer that knowledge to any conformant node.

**Decentralized Identifiers (DIDs)** — Each fabric node has a [did:webvh](https://w3c-ccg.github.io/did-method-webvh/) identifier, a DID method that combines web discoverability with a cryptographically verifiable history log. The node's DID document advertises its verification keys and service endpoints (SPARQL, SHACL, VoID, LDN inbox). Agents resolve DIDs via the W3C DID Resolution HTTP API to discover what a node offers before interacting with it.

Why DIDs and not API keys or OAuth? Because the trust relationship is peer-to-peer, not client-server. A fabric is a federation of autonomous nodes. No central authority issues tokens. Each node proves its identity through its own key material, and any node can verify any other node's claims by resolving its DID and checking signatures. This is the same trust model that the web itself uses (DNS + TLS), extended to machine-readable identity documents.

**Verifiable Credentials (VCs)** — At bootstrap, each node self-issues a `FabricConformanceCredential` following the [W3C Verifiable Credentials Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/). This credential attests that the node conforms to `fabric:CoreProfile` and includes a service directory pointing to the node's endpoints. The credential is signed with an [eddsa-jcs-2022](https://www.w3.org/TR/vc-di-eddsa/) Data Integrity proof — JSON Canonicalization Scheme (JCS) + Ed25519, no JSON-LD processing required.

The VC structure matters because it separates the claim ("this node serves SOSA observation data at these endpoints") from the proof ("signed by the node's Ed25519 key at this timestamp"). Agents can verify the signature without trusting the transport layer. When bootstrap-attested credentials arrive (Phase 3), the same VC structure supports multi-proof chaining: the node signs first, then a bootstrap witness co-signs, creating a chain of attestation with no new machinery.

**Content integrity** (D26) — The conformance credential includes a `relatedResource` array (VC Data Model 2.0 §5.3) binding each self-description artifact to its SHA-256 hash:

```json
"relatedResource": [
  {
    "id": "https://bootstrap.cogitarelink.ai/.well-known/void",
    "digestMultibase": "zBKaAuRCu9dMruLbstDUm4WPaRsGggUC8Ei3H47d7B9Sw",
    "digestSRI": "sha256-mVbUgqHTiCiUO3T2jkbHjW2VqvTGrPoFinSPStFcknA=",
    "mediaType": "text/turtle"
  }
]
```

This lets an agent verify that the VoID, SHACL shapes, and SPARQL examples it fetches haven't changed since the credential was issued. The `digestMultibase` format (multibase base58btc prefix `z` + raw SHA-256) follows the conventions used across the DID and VC ecosystem. The `digestSRI` format (Subresource Integrity) follows the W3C SRI specification for browser-compatible verification. Both are computed from the same hash; agents can use whichever format their toolchain supports.

**Linked Data Notifications (LDN)** — Every DID (agent, human, node) advertises an [LDN inbox](https://www.w3.org/TR/ldn/) as a service endpoint. Nodes use `POST /inbox` to deliver JSON-LD notifications (trust gap alerts, catalog updates, delegation requests). The inbox is discoverable via a `Link` header on the DID document, following the LDN specification's discovery mechanism. This replaces custom webhook endpoints with a standard protocol that any LDN-aware client can use.

**Why standards over custom protocols?** Three practical reasons:

1. **Agent transferability.** An agent that learns to resolve a DID, verify a VC signature, and check a `digestMultibase` hash against one fabric node can do the same against any node — or any system outside this project that uses the same standards. Custom protocols create vendor lock-in for agents, not just humans.

2. **Composability.** VC multi-proof chaining, LDN notification delivery, and DID-based service discovery all compose without glue code because they were designed to work together. Adding human-in-the-loop approval (D19) requires no new protocol — it's a second proof on the same credential, delivered via the same inbox.

3. **Edge cases already handled.** DID resolution has defined error codes. VC validation has defined processing rules. Content integrity via `digestMultibase` has defined canonicalization paths (raw bytes now, RDFC-1.0 later). Custom protocols tend to discover these edge cases in production.

## References

- Zhang, A. L., Kraska, T., & Khattab, O. (2025). Recursive Language Models. arXiv:2512.24601v2. https://arxiv.org/abs/2512.24601
- Janowicz, K., Hitzler, P., Adams, B., Kolas, D., & Vardeman II, C. (2014). Five Stars of Linked Data Vocabulary Use. *Semantic Web*, 5(3), 173–176. https://doi.org/10.3233/SW-130175
- Cox, S. J. D., et al. (2021). Ten Simple Rules for Making a Vocabulary FAIR. *PLOS Computational Biology*, 17(6), e1009041. https://doi.org/10.1371/journal.pcbi.1009041
