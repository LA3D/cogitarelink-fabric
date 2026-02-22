# /fabric-sparql

Construct and execute a SPARQL query using endpoint self-description as scaffolding.

## Usage
```
/fabric-sparql "<natural language query>" [--endpoint <url>]
```
Example: `/fabric-sparql "find CV observations for KCl electrode from last 7 days"`

## Steps

1. **Load self-description** (if not cached from `/fabric-discover`):
   - Fetch shapes from `.well-known/shacl` → extract class/property affordances
   - Fetch examples from `.well-known/sparql-examples` → identify matching templates

2. **Identify affordances** from shapes:
   - Which named graph contains the target data?
   - Which properties are available on target class?
   - Any `sh:agentInstruction` routing hints?
   - SSSOM mappings available for vocabulary translation? (`/graph/mappings`)

3. **Select or adapt SPARQL example** closest to the query intent

4. **Construct SPARQL** with:
   - Correct GRAPH clause for the target named graph (D6)
   - Prefix declarations (from sparql-patterns.md)
   - LIMIT clause (default 100 unless full result needed)
   - SERVICE clause for QLever/PubChem federation if chemical identity needed (D20/D21)

5. **Execute** against endpoint `/sparql`

6. **Return bounded result**:
   - Truncate to first 50 rows if larger
   - Include count of total matches if SPARQL supports it
   - Flag if result is partial

## Notes
- Do not guess property names — derive from shapes or examples only
- If query requires vocabulary bridging, check `/graph/mappings` first (D21)
- For PubChem identity chains: use SERVICE <https://qlever.dev/api/pubchem> (D20)
