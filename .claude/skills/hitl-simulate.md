# /hitl-simulate

Simulate the HitL approval workflow (D19): write to /graph/pending, simulate human signing, verify dual-proof VC.

## Usage
```
/hitl-simulate <agent-did> [--action <description>]
```
Example: `/hitl-simulate did:webvh:ingest-agent.example.org --action "Insert 47 SOSA observations from potentiostat run 2026-02-22"`

## Background (D19)

HitL enforcement uses VC 2.0 multi-proof:
1. IngestCurator writes data + FabricApprovalRequest to /graph/pending
2. Agent's AgentAuthorizationCredential is Proof 1
3. Human (or supervisor agent) reviews → signs FabricApprovalRequest as Proof 2
4. Dual-proof VC structure: `proof` array with `previousProof` chain
5. Fabric accepts data only when Proof 2 present and valid

## Steps

1. **Write FabricApprovalRequest to /graph/pending**:
   ```sparql
   INSERT DATA {
     GRAPH <.../graph/pending> {
       <urn:uuid:{uuid7}> a fabric:FabricApprovalRequest ;
         fabric:requestedBy <{agent-did}> ;
         fabric:targetGraph <.../graph/observations> ;
         rdfs:label "{action-description}" ;
         fabric:status fabric:PendingHumanReview ;
         prov:generatedAtTime "{iso-timestamp}"^^xsd:dateTime .
     }
   }
   ```

2. **Issue Proof 1** (agent authorization, mock or Credo):
   - `/vc-issue AgentAuthorization --subject {agent-did} --mock`

3. **Simulate human review** (print for inspection):
   - Show the FabricApprovalRequest contents
   - Prompt: "Human reviewer would inspect this request"

4. **Issue Proof 2** (human/supervisor approval, mock):
   - FabricDelegationCredential with `previousProof` referencing Proof 1 id

5. **Verify dual-proof structure**:
   - Confirm `proof` is an array (not object)
   - Confirm Proof 2 has `previousProof` pointing to Proof 1's `@id`
   - Confirm both proofs use `eddsa-rdfc-2022` (or mock flag in Phase 1)

6. **Move to /graph/approvals** (simulated acceptance):
   ```sparql
   DELETE { GRAPH <.../graph/pending> { <{request-iri}> ?p ?o } }
   INSERT { GRAPH <.../graph/approvals> { <{request-iri}> ?p ?o ;
               fabric:status fabric:Approved ;
               fabric:approvedAt "{iso-timestamp}"^^xsd:dateTime . } }
   WHERE { GRAPH <.../graph/pending> { <{request-iri}> ?p ?o } }
   ```

7. Report: approval request IRI, dual-proof structure summary, graph transition confirmed
