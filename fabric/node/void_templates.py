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
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

# --- Service Description (D6) ---
<{base}/sparql> a sd:Service, dcat:DataService ;
    sd:supportedLanguage sd:SPARQL12Query, sd:SPARQL12Update ;
    dcat:servesDataset <{base}/dataset/observations> ;
    sd:defaultDataset [
        a sd:Dataset ;
        sd:namedGraph [
            sd:name <{base}/graph/observations> ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/entities> ;
            dct:title "Entities" ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#EntityShape> ;
            dct:description "Sensor, platform, and observable-property descriptions (sosa:Sensor, sosa:Platform, sosa:ObservableProperty)." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/metadata> ;
            dct:title "Metadata" ;
            dct:description "Node-level metadata, provenance records, and administrative triples." ;
        ] ;
    ] .

# --- VoID Dataset (D6/D9) ---
<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> ;
    void:uriSpace "{base}/entity/" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
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
    "fabric": "https://w3id.org/cogitarelink/fabric#"
  }},
  "@graph": [
    {{
      "@id": "{base}/sparql",
      "@type": ["sd:Service", "dcat:DataService"],
      "dcat:servesDataset": {{ "@id": "{base}/dataset/observations" }}
    }},
    {{
      "@id": "{base}/.well-known/void",
      "@type": "void:Dataset",
      "dct:title": "cogitarelink-fabric node",
      "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }},
      "void:uriSpace": "{base}/entity/",
      "void:vocabulary": [
        {{ "@id": "http://www.w3.org/ns/sosa/" }},
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
