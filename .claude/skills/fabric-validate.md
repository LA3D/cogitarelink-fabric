# /fabric-validate

Validate a named graph against the endpoint's SHACL shapes; parse agent instructions from violations.

## Usage
```
/fabric-validate <graph-iri> [--endpoint <url>]
```
Example: `/fabric-validate https://node.example.org/graph/observations`

## Steps

1. Fetch shapes from `{endpoint}/.well-known/shacl` (or use cached shapes if available)

2. Run pyshacl validation:
   ```python
   from pyshacl import validate
   conforms, report_g, report_text = validate(
       data_graph=data, shacl_graph=shapes, inference="rdfs"
   )
   ```

3. Parse violations:
   - For each `sh:ValidationResult`: extract `sh:resultMessage`, `sh:focusNode`, `sh:resultPath`, `sh:sourceShape`
   - Check if source shape has `sh:agentInstruction` → include as fix hint
   - Check if source shape has `sh:intent` → include as context

4. Categorize:
   - BLOCKING: violations on `sh:minCount`, `sh:datatype`, required properties (must fix before commit)
   - WARNING: violations on `sh:maxCount`, `sh:pattern` (should fix)
   - INFO: `sh:agentInstruction` hints on passing shapes (style guidance)

5. Report conforms status + prioritized violation list with fix suggestions

## Output Format

```
Graph: {graph-iri}
Conforms: {yes/no}

BLOCKING violations ({n}):
  - Node: {focus-node}
    Path: sosa:hasResult
    Message: Required property missing
    Fix hint (sh:agentInstruction): "Provide a qudt:QuantityValue with qudt:unit and qudt:numericValue"

WARNINGS ({n}):
  ...

For graphs targeting commit (D19), fix all BLOCKING violations before proceeding.
```
