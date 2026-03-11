"""VoID + DCAT self-description templates (no framework deps).

Pure string constants with {base} placeholders — imported by main.py
(FastAPI) and unit tests (no FastAPI needed).
"""

VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix sd:   <http://www.w3.org/ns/sparql-service-description#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix prov:   <http://www.w3.org/ns/prov#> .

# --- Service Description (D6) ---
<{base}/sparql> a sd:Service, dcat:DataService ;
    sd:supportedLanguage sd:SPARQL12Query, sd:SPARQL12Update ;
    dcat:servesDataset <{base}/dataset/observations> ;
    sd:defaultDataset [
        a sd:Dataset ;
        sd:namedGraph [
            sd:name <{base}/graph/observations> ;
            dct:title "Observations" ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
            fabric:graphPurpose "instances" ;
            rdfs:comment "Instance data: SOSA observations with measurement results. Query with SPARQL SELECT/CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/entities> ;
            dct:title "Entities" ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#EntityShape> ;
            dct:description "Sensor, platform, and observable-property descriptions (sosa:Sensor, sosa:Platform, sosa:ObservableProperty)." ;
            fabric:graphPurpose "instances" ;
            rdfs:comment "Instance data: sensor and platform descriptions. Query with SPARQL SELECT/CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/metadata> ;
            dct:title "Metadata" ;
            dct:description "Node-level metadata, provenance records, and administrative triples." ;
            fabric:graphPurpose "metadata" ;
            rdfs:comment "Administrative metadata and provenance. Query with SPARQL when needed for audit trails." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/sosa> ;
            void:vocabulary <http://www.w3.org/ns/sosa/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/sosa/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C SOSA ontology (cached). Explore structure with JSON-LD via /ontology/sosa or query axioms with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/ssn> ;
            void:vocabulary <http://www.w3.org/ns/ssn/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/ssn/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C SSN ontology (cached). Extends SOSA with System, Deployment, Stimulus, Property classes. Explore with JSON-LD via /ontology/ssn or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/sio> ;
            void:vocabulary <http://semanticscience.org/resource/> ;
            prov:wasDerivedFrom <http://semanticscience.org/resource/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "SIO ontology (cached, 1726 classes). Explore structure with JSON-LD via /ontology/sio or query axioms with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/prov> ;
            void:vocabulary <http://www.w3.org/ns/prov#> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/prov#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C PROV-O ontology (cached). Explore with JSON-LD via /ontology/prov or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/time> ;
            void:vocabulary <http://www.w3.org/2006/time#> ;
            prov:wasDerivedFrom <http://www.w3.org/2006/time#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C OWL-Time ontology (cached). Explore with JSON-LD via /ontology/time or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/fabric> ;
            void:vocabulary <https://w3id.org/cogitarelink/fabric#> ;
            prov:wasDerivedFrom <https://w3id.org/cogitarelink/fabric#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "Cogitarelink Fabric vocabulary (cached). Explore with JSON-LD via /ontology/fabric or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/prof> ;
            void:vocabulary <http://www.w3.org/ns/dx/prof/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/dx/prof/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C Profiles Vocabulary (cached). Explore with JSON-LD via /ontology/prof or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/role> ;
            void:vocabulary <http://www.w3.org/ns/dx/prof/role/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/dx/prof/role/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C PROF role types (cached). Explore with JSON-LD via /ontology/role or query with SPARQL CONSTRUCT." ;
        ] ;
    ] .

# --- VoID Dataset (D6/D9) ---
<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> ;
    void:uriSpace "{base}/entity/" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    void:vocabulary <http://www.w3.org/ns/ssn/> ;
    void:vocabulary <http://www.w3.org/2006/time#> ;
    void:vocabulary <http://www.w3.org/ns/prov#> ;
    void:vocabulary <http://semanticscience.org/resource/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <{base}/graph/observations> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
        fabric:writable true ;
    ] ;
    void:subset [
        a void:Dataset ;
        dct:title "Entities" ;
        dct:description "Sensor, platform, and observable-property descriptions." ;
        void:sparqlGraphEndpoint <{base}/graph/entities> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#EntityShape> ;
        fabric:writable true ;
    ] .

# --- DCAT Dataset Description (D23) ---
# Topic-level metadata for fabric catalog harvesting and agent query routing.
<{base}/dataset/observations> a dcat:Dataset ;
    dct:title "SDL Electrochemical Observations"^^xsd:string ;
    dct:description "SOSA/SSN sensor observations with SIO measurement attributes from automated potentiostat station"^^xsd:string ;
    dcat:theme <http://dbpedia.org/resource/Electrochemistry> ,
               <http://dbpedia.org/resource/Cyclic_voltammetry> ;
    dcat:keyword "electrochemistry", "potentiostat", "cyclic voltammetry", "SDL", "SOSA", "SIO" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ,
                    <http://www.w3.org/ns/ssn/> ,
                    <http://www.w3.org/2006/time#> ,
                    <http://www.w3.org/ns/prov#> ,
                    <http://semanticscience.org/resource/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    dcat:distribution [
        a dcat:Distribution ;
        dcat:accessService <{base}/sparql> ;
        dcat:accessURL <{base}/sparql> ;
        dct:format "application/sparql-results+json"
    ] .
"""

VOID_JSONLD = """\
{{
  "@context": {{
    "void": "http://rdfs.org/ns/void#",
    "sd": "http://www.w3.org/ns/sparql-service-description#",
    "dct": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "fabric": "https://w3id.org/cogitarelink/fabric#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
  }},
  "@graph": [
    {{
      "@id": "{base}/sparql",
      "@type": ["sd:Service", "dcat:DataService"],
      "dcat:servesDataset": {{ "@id": "{base}/dataset/observations" }},
      "sd:defaultDataset": {{
        "@type": "sd:Dataset",
        "sd:namedGraph": [
          {{ "sd:name": {{ "@id": "{base}/graph/observations" }}, "dct:title": "Observations", "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#ObservationShape" }}, "fabric:graphPurpose": "instances", "rdfs:comment": "Instance data: SOSA observations with measurement results. Query with SPARQL SELECT/CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/graph/entities" }}, "dct:title": "Entities", "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#EntityShape" }}, "dct:description": "Sensor, platform, and observable-property descriptions (sosa:Sensor, sosa:Platform, sosa:ObservableProperty).", "fabric:graphPurpose": "instances", "rdfs:comment": "Instance data: sensor and platform descriptions. Query with SPARQL SELECT/CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/graph/metadata" }}, "dct:title": "Metadata", "dct:description": "Node-level metadata, provenance records, and administrative triples.", "fabric:graphPurpose": "metadata", "rdfs:comment": "Administrative metadata and provenance. Query with SPARQL when needed for audit trails." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/sosa" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/ns/sosa/" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/ns/sosa/" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C SOSA ontology (cached). Explore structure with JSON-LD via /ontology/sosa or query axioms with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/ssn" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/ns/ssn/" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/ns/ssn/" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C SSN ontology (cached). Extends SOSA with System, Deployment, Stimulus, Property classes. Explore with JSON-LD via /ontology/ssn or query with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/sio" }}, "void:vocabulary": {{ "@id": "http://semanticscience.org/resource/" }}, "prov:wasDerivedFrom": {{ "@id": "http://semanticscience.org/resource/" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "SIO ontology (cached, 1726 classes). Explore structure with JSON-LD via /ontology/sio or query axioms with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/prov" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/ns/prov#" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/ns/prov#" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C PROV-O ontology (cached). Explore with JSON-LD via /ontology/prov or query with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/time" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/2006/time#" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/2006/time#" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C OWL-Time ontology (cached). Explore with JSON-LD via /ontology/time or query with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/fabric" }}, "void:vocabulary": {{ "@id": "https://w3id.org/cogitarelink/fabric#" }}, "prov:wasDerivedFrom": {{ "@id": "https://w3id.org/cogitarelink/fabric#" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "Cogitarelink Fabric vocabulary (cached). Explore with JSON-LD via /ontology/fabric or query with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/prof" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/ns/dx/prof/" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/ns/dx/prof/" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C Profiles Vocabulary (cached). Explore with JSON-LD via /ontology/prof or query with SPARQL CONSTRUCT." }},
          {{ "sd:name": {{ "@id": "{base}/ontology/role" }}, "void:vocabulary": {{ "@id": "http://www.w3.org/ns/dx/prof/role/" }}, "prov:wasDerivedFrom": {{ "@id": "http://www.w3.org/ns/dx/prof/role/" }}, "fabric:graphPurpose": "schema", "rdfs:comment": "W3C PROF role types (cached). Explore with JSON-LD via /ontology/role or query with SPARQL CONSTRUCT." }}
        ]
      }}
    }},
    {{
      "@id": "{base}/.well-known/void",
      "@type": "void:Dataset",
      "dct:title": "cogitarelink-fabric node",
      "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }},
      "void:uriSpace": "{base}/entity/",
      "void:vocabulary": [
        {{ "@id": "http://www.w3.org/ns/sosa/" }},
        {{ "@id": "http://www.w3.org/ns/ssn/" }},
        {{ "@id": "http://www.w3.org/2006/time#" }},
        {{ "@id": "http://www.w3.org/ns/prov#" }},
        {{ "@id": "http://semanticscience.org/resource/" }}
      ],
      "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#CoreProfile" }},
      "void:subset": [
        {{
          "@type": "void:Dataset",
          "dct:title": "Observations",
          "void:sparqlGraphEndpoint": {{ "@id": "{base}/graph/observations" }},
          "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#ObservationShape" }},
          "fabric:writable": true
        }},
        {{
          "@type": "void:Dataset",
          "dct:title": "Entities",
          "dct:description": "Sensor, platform, and observable-property descriptions.",
          "void:sparqlGraphEndpoint": {{ "@id": "{base}/graph/entities" }},
          "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#EntityShape" }},
          "fabric:writable": true
        }}
      ]
    }},
    {{
      "@id": "{base}/dataset/observations",
      "@type": "dcat:Dataset",
      "dct:title": "SDL Electrochemical Observations",
      "dct:description": "SOSA/SSN sensor observations with SIO measurement attributes from automated potentiostat station",
      "dcat:theme": [
        {{ "@id": "http://dbpedia.org/resource/Electrochemistry" }},
        {{ "@id": "http://dbpedia.org/resource/Cyclic_voltammetry" }}
      ],
      "dcat:keyword": ["electrochemistry", "potentiostat", "cyclic voltammetry", "SDL", "SOSA", "SIO"],
      "void:vocabulary": [
        {{ "@id": "http://www.w3.org/ns/sosa/" }},
        {{ "@id": "http://www.w3.org/ns/ssn/" }},
        {{ "@id": "http://www.w3.org/2006/time#" }},
        {{ "@id": "http://www.w3.org/ns/prov#" }},
        {{ "@id": "http://semanticscience.org/resource/" }}
      ],
      "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#CoreProfile" }},
      "dcat:distribution": {{
        "@type": "dcat:Distribution",
        "dcat:accessService": {{ "@id": "{base}/sparql" }},
        "dcat:accessURL": {{ "@id": "{base}/sparql" }},
        "dct:format": "application/sparql-results+json"
      }}
    }}
  ]
}}
"""
