# /fabric-prov

Record a PROV-O activity for a development or curation action. Appends to provenance/activities/.

## Usage
```
/fabric-prov "<description of activity>" [--agent <orcid|did>] [--used <file-or-graph>] [--generated <file-or-graph>]
```
Example: `/fabric-prov "Loaded SOSA ontology into /ontology/sosa named graph" --generated https://node.example.org/ontology/sosa`

## Steps

1. Generate UUIDv7 for the activity IRI

2. Construct PROV-O JSON-LD:
   ```json
   {
     "@context": "https://www.w3.org/ns/prov.jsonld",
     "@id": "urn:uuid:{uuid7}",
     "@type": "prov:Activity",
     "prov:startedAtTime": "{iso-timestamp}",
     "prov:wasAssociatedWith": {
       "@id": "https://orcid.org/0000-0003-4091-6059",
       "@type": "prov:Agent"
     },
     "prov:used": [/* list of input IRIs */],
     "prov:generated": [/* list of output IRIs */],
     "rdfs:label": "{description}"
   }
   ```

3. For Claude Code development actions: include agent association with DevelopmentAgent role (D14, D17):
   ```json
   "prov:qualifiedAssociation": {
     "@type": "prov:Association",
     "prov:agent": { "@id": "https://claude.anthropic.com/claude-sonnet-4-6" },
     "prov:hadRole": { "@id": "fabric:DevelopmentAgentRole" }
   }
   ```

4. Determine target file: `provenance/activities/YYYY-MM-DD.jsonld`
   - Append as a new entry in the JSON-LD `@graph` array
   - Create file if it doesn't exist (with `@context` and empty `@graph`)

5. Report: activity IRI + file appended to

## Notes
- ORCID: https://orcid.org/0000-0003-4091-6059 (owner)
- Notre Dame ROR: https://ror.org/00mkhxb43
- Record provenance for all non-trivial file operations per D17
