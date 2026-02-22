# /fabric-discover

Discover and summarize the capabilities of a fabric endpoint via progressive disclosure (D9 four-layer KR).

## Usage
```
/fabric-discover <endpoint-url>
```
Example: `/fabric-discover http://localhost:8080`

## Steps

1. **L1 — Service Description + VoID**: Fetch `{url}/.well-known/void`
   - Parse vocabulary declarations (`void:vocabulary` → ontology IRIs)
   - Extract `dct:conformsTo` → profile link(s)
   - List named graphs (`void:namedGraph` entries)
   - Note SPARQL endpoint URL

2. **L2 — TBox cache (via profile)**: Follow `dct:conformsTo` to `fabric:CoreProfile`
   - Fetch `role:schema` artifacts (ontology IRIs)
   - Fetch `role:constraints` artifacts (standard SHACL shapes)
   - Load into working graph summary

3. **L3 — Endpoint-specific shapes**: Fetch `{url}/.well-known/shacl`
   - List `sh:NodeShape` names + `sh:intent` descriptions
   - Extract `sh:agentInstruction` annotations (routing hints)
   - Note `sh:targetClass` for each shape

4. **L4 — SPARQL examples**: Fetch `{url}/.well-known/sparql-examples`
   - List `sh:SPARQLExecutable` instances with `rdfs:label`
   - Show `schema:target` endpoint bindings
   - Note which named graphs each query covers

## Output Format

```
Endpoint: {url}
Profile: {profile-iri} (dct:conformsTo)

Named graphs:
  - /graph/observations  (sosa:Observation instances)
  - /graph/entities      (sosa:FeatureOfInterest, instruments)
  ...

Vocabularies (TBox):
  - sosa: (SOSA/SSN)
  - qudt: (QUDT)
  - prov: (PROV-O)

Endpoint shapes ({n} shapes):
  - FabricObservationShape — targets sosa:Observation
    agentInstruction: "Use qudt:unit for hasResult; phenomenonTime is xsd:dateTime"
  ...

SPARQL examples ({n} examples):
  - "Find observations by feature of interest" → /sparql
  ...

Routing summary:
  - Observations: query /graph/observations with sosa:Observation shapes
  - Vocabulary alignment: /graph/mappings (SSSOM)
```
