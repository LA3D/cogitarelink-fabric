# /sbom-update

Regenerate SPDX 3.0 SBOM for the repo; update codemeta.json if metadata changed.

## Usage
```
/sbom-update [--reason <description>]
```
Example: `/sbom-update --reason "Added pyshacl 0.26 dependency"`

## Steps

1. **Collect current dependencies**:
   - Python: `pip list --format=json` or parse `requirements.txt` / `pyproject.toml`
   - Node/TypeScript: parse `fabric/credo/package.json`
   - Docker images: parse `docker-compose.yml` image references

2. **Read existing SBOM** from `provenance/claude-code-sbom.jsonld`

3. **Update SPDX 3.0 JSON-LD structure**:
   ```json
   {
     "@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld",
     "@type": "SpdxDocument",
     "name": "cogitarelink-fabric",
     "dataLicense": "CC0-1.0",
     "creationInfo": {
       "created": "{iso-timestamp}",
       "createdBy": [
         { "@type": "Tool", "name": "Claude Code (claude-sonnet-4-6)" },
         { "@type": "Person", "externalIdentifier": { "externalIdentifierType": "orcid",
             "identifier": "https://orcid.org/0000-0003-4091-6059" } }
       ]
     },
     "element": [
       { "@type": "ai:AIPackage", "name": "claude-sonnet-4-6",
         "ai:autonomyType": "HumanInTheLoop",
         "supplier": "Anthropic PBC",
         "relationship": [{ "relationshipType": "generatedBy",
             "to": [{ "@id": "cogitarelink-fabric" }] }] },
       /* Python packages, Node packages, Docker images */
     ]
   }
   ```

4. **Update codemeta.json** if package list changed:
   - `softwareRequirements` list
   - `dateModified` to today

5. **Record PROV-O activity** for this SBOM update (call `/fabric-prov`)

6. **Stage and commit**:
   ```bash
   git add provenance/claude-code-sbom.jsonld codemeta.json
   git commit -m "[Agent: Claude] Update SBOM: {reason}

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   ```

7. Report: packages added/removed/updated, SBOM IRI
