# /shacl-generate

Infer SHACL shapes from sample RDF data; add sh:agentInstruction and sh:intent annotations; output for .well-known/shacl.

## Usage
```
/shacl-generate <data-file-or-graph> [--class <target-class>] [--endpoint <url>]
```
Examples:
- `/shacl-generate ontology/sample-observations.ttl --class sosa:Observation`
- `/shacl-generate https://node.example.org/graph/observations --class sosa:Observation`

## Steps

1. **Load sample data** (file or SPARQL CONSTRUCT from graph)

2. **Profile each target class**:
   ```sparql
   SELECT ?prop ?type (COUNT(*) AS ?count) WHERE {
     ?s a <{target-class}> .
     ?s ?prop ?val .
     OPTIONAL { ?val a ?type }
   } GROUP BY ?prop ?type ORDER BY DESC(?count)
   ```

3. **Infer shape properties** for each property found:
   - `sh:minCount 1` if present in >90% of instances
   - `sh:maxCount 1` if never repeated
   - `sh:datatype` if object is always a literal of the same type
   - `sh:class` if object is always a named individual of the same type
   - `sh:nodeKind sh:IRI` or `sh:Literal`

4. **Add semantic annotations** from ontology knowledge:
   - `sh:agentInstruction`: narrow routing/format hint
   - `sh:intent`: human-readable purpose of the shape
   - Example for sosa:Observation shape:
     ```turtle
     fabric:ObservationShape
         sh:agentInstruction "Use qudt:QuantityValue for hasResult; phenomenonTime must be xsd:dateTime; link to instrument via sosa:madeBySensor" ;
         sh:intent "Validates a sensor observation from an SDL instrument station (D20)" .
     ```

5. **Output Turtle** ready for `.well-known/shacl`:
   - Includes standard SHACL namespace prefix + fabric: prefix
   - One NodeShape per target class
   - All inferred PropertyShapes with counts + types
   - Semantic annotations added

6. **Write to** `shapes/{class-name}-generated.ttl`

7. Report: shape file path, classes covered, properties inferred, annotations added
   Note: generated shapes require human review before serving from `.well-known/shacl`
