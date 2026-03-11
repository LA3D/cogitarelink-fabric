# tool_choices

kind: let

source:
```prose
let tool_choices = session: tool_classifier
  prompt: "For each trajectory, classify every iteration by tool family..."
```

---

## Classification Key

| Family | Tools matched |
|--------|--------------|
| `discovery` | `fetchVoID` (fv), `fetchShapes` (fs), `fetchExamples` (fe) |
| `jsonld` | `fetchJsonLd` (fjl), `jsonld.expand`, `jsonld.compact`, `jsonld.frame` |
| `sparql` | `comunica_query` (cq) |
| `compute` | `fetchEntity`, or mixed tool calls that don't fit a single family — classified as the primary family when unambiguous |
| `mixed` | Iterations invoking tools from more than one family |
| `submit` | Iterations with no tool calls — reasoning-only or return |

Note on `fetchEntity`: treated as `discovery` (it fetches a resource description) when it is the sole call. When co-occurring with `cq` or `fjl` it contributes to `mixed`. In this dataset `fetchEntity` is always solo, so classified as `discovery`.

---

## Per-Task Iteration Timelines

### js-baseline

#### Run 2026-03-06T17-50-41-018Z

**sio-has-value-type** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | cq | sparql |
| 1 | cq | sparql |
| 2 | fv | discovery |
| 3 | cq | sparql |
| 4 | (none) | submit |

**sio-attribute-inverse** (score=1, 3 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | (none) | submit |

**sio-measured-value-range** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**obs-sio-measured-value** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | fetchEntity | discovery |
| 5 | cq, cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

**obs-sio-unit** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |

---

#### Run 2026-03-11T15-58-31-918Z

**vocab-obs-to-sensor-properties** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fs, fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |

**vocab-sio-float-range-properties** (score=1, 13 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | cq | sparql |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | cq | sparql |
| 8 | fs | discovery |
| 9 | cq | sparql |
| 10 | cq, cq | sparql |
| 11 | (none) | submit |
| 12 | (none) | submit |

**vocab-sio-inverse-chain** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | (none) | submit |

**vocab-observation-subclasses** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | cq | sparql |
| 1 | cq | sparql |
| 2 | fv | discovery |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | (none) | submit |

---

#### Run 2026-03-11T16-12-53-597Z

**sio-has-value-type** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**sio-attribute-inverse** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**sio-measured-value-range** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**obs-sio-measured-value** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |

**obs-sio-unit** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

---

#### Run 2026-03-11T18-34-35-421Z

**vocab-obs-to-sensor-properties** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fs, fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |

**vocab-sio-datatype-property** (score=1, 3 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | (none) | submit |

**vocab-sio-inverse-chain** (score=0, 9 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq, cq | sparql |
| 6 | cq, cq, cq | sparql |
| 7 | cq, cq | sparql |
| 8 | (none) | submit |

**vocab-observation-subclasses** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | cq | sparql |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | fv | discovery |
| 5 | cq, cq | sparql |
| 6 | cq | sparql |
| 7 | cq | sparql |

---

#### Run 2026-03-11T18-51-09-275Z

**sio-has-value-type** (score=1, 9 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | cq | sparql |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | cq | sparql |
| 8 | cq | sparql |

**sio-attribute-inverse** (score=0, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | (none) | submit |

**sio-measured-value-range** (score=0, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |

**obs-sio-measured-value** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-unit** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

---

### js-jsonld

#### Run 2026-03-11T16-01-32-644Z

**vocab-obs-to-sensor-properties** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl, jsonld.expand | jsonld |
| 2 | (none) | submit |
| 3 | (none) | submit |

**vocab-sio-float-range-properties** (score=1, 14 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | fjl | jsonld |
| 5 | jsonld.expand | jsonld |
| 6 | jsonld.expand | jsonld |
| 7 | fjl | jsonld |
| 8 | fjl | jsonld |
| 9 | fjl | jsonld |
| 10 | fjl | jsonld |
| 11 | fjl | jsonld |
| 12 | fjl | jsonld |
| 13 | (none) | submit |

**vocab-sio-inverse-chain** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl | jsonld |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq, cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

**vocab-observation-subclasses** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fjl | jsonld |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | fjl | jsonld |
| 4 | (none) | submit |
| 5 | (none) | submit |
| 6 | cq | sparql |
| 7 | (none) | submit |

---

#### Run 2026-03-11T16-08-35-772Z

**sio-has-value-type** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fjl, jsonld.expand | jsonld |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | (none) | submit |

**sio-attribute-inverse** (score=1, 3 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl, jsonld.expand | jsonld |
| 2 | (none) | submit |

**sio-measured-value-range** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl | jsonld |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | (none) | submit |

**obs-sio-measured-value** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

**obs-sio-unit** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | cq | sparql |
| 4 | fetchEntity | discovery |
| 5 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | (none) | submit |

---

#### Run 2026-03-11T18-45-54-138Z

**vocab-obs-to-sensor-properties** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl, jsonld.frame | jsonld |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**vocab-sio-datatype-property** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**vocab-sio-inverse-chain** (score=0, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq, cq | sparql |
| 5 | cq, cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

**vocab-observation-subclasses** (score=1, 9 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | fjl, fjl, jsonld.expand, jsonld.expand | jsonld |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | fjl | jsonld |
| 7 | cq | sparql |
| 8 | cq | sparql |

---

#### Run 2026-03-11T18-53-46-003Z

**sio-has-value-type** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fjl | jsonld |
| 4 | cq | sparql |
| 5 | (none) | submit |

**sio-attribute-inverse** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | cq | sparql |
| 4 | (none) | submit |

**sio-measured-value-range** (score=0, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |

**obs-sio-measured-value** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq, cq | sparql |
| 4 | cq, cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-unit** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | fetchEntity | discovery |
| 5 | cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

---

### js-combined

#### Run 2026-03-11T16-06-07-967Z

**vocab-obs-to-sensor-properties** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl, jsonld.expand | jsonld |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |

**vocab-sio-float-range-properties** (score=0, 12 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | (none) | submit |
| 4 | (none) | submit |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | fjl | jsonld |
| 8 | cq, cq | sparql |
| 9 | cq | sparql |
| 10 | cq, cq | sparql |
| 11 | (none) | submit |

**vocab-sio-inverse-chain** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl | jsonld |
| 2 | jsonld.expand | jsonld |
| 3 | (none) | submit |
| 4 | (none) | submit |
| 5 | (none) | submit |
| 6 | (none) | submit |

**vocab-observation-subclasses** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fjl | jsonld |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | (none) | submit |

---

#### Run 2026-03-11T16-10-46-303Z

**sio-has-value-type** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fjl, jsonld.expand | jsonld |
| 1 | fv | discovery |
| 2 | cq | sparql |
| 3 | (none) | submit |

**sio-attribute-inverse** (score=1, 5 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | (none) | submit |

**sio-measured-value-range** (score=1, 3 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | fjl, jsonld.expand | jsonld |
| 2 | (none) | submit |

**obs-sio-measured-value** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-unit** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fs | discovery |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | cq, cq | sparql |
| 6 | (none) | submit |
| 7 | (none) | submit |

---

#### Run 2026-03-11T18-48-13-053Z

**vocab-obs-to-sensor-properties** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | jsonld.expand | jsonld |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**vocab-sio-datatype-property** (score=1, 4 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | (none) | submit |

**vocab-sio-inverse-chain** (score=0, 9 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | fjl | jsonld |
| 4 | fjl, jsonld.frame | jsonld |
| 5 | cq | sparql |
| 6 | cq, cq | sparql |
| 7 | cq | sparql |
| 8 | (none) | submit |

**vocab-observation-subclasses** (score=1, 8 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | jsonld.expand | jsonld |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq | sparql |
| 7 | cq | sparql |

---

#### Run 2026-03-11T19-09-48-125Z

**sio-has-value-type** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |

**sio-attribute-inverse** (score=1, 3 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | (none) | submit |

**sio-measured-value-range** (score=0, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fjl | jsonld |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | (none) | submit |

**obs-sio-measured-value** (score=1, 9 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | cq | sparql |
| 6 | cq, cq | sparql |
| 7 | (none) | submit |
| 8 | (none) | submit |

**obs-sio-unit** (score=1, 7 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | cq | sparql |
| 3 | cq | sparql |
| 4 | cq | sparql |
| 5 | (none) | submit |
| 6 | (none) | submit |

**obs-sio-chemical-entity** (score=1, 6 iter)
| Iter | Tools | Family |
|------|-------|--------|
| 0 | fv | discovery |
| 1 | cq | sparql |
| 2 | fetchEntity | discovery |
| 3 | fetchEntity | discovery |
| 4 | cq | sparql |
| 5 | (none) | submit |

---

## Aggregate: Fraction of Iterations by Family

Counts are individual iteration slots. Each iteration is assigned exactly one family. When multiple tools appear in one iteration (e.g. `fjl, jsonld.expand`), the dominant/named family is used (jsonld if any jsonld tool is present; mixed if both sparql and jsonld co-occur in one iteration — in this dataset that does not occur).

### js-baseline (5 runs, 26 tasks, 167 total iterations)

| Family | Count | Fraction |
|--------|-------|----------|
| discovery | 43 | 25.7% |
| sparql | 92 | 55.1% |
| jsonld | 0 | 0.0% |
| submit | 32 | 19.2% |
| **Total** | **167** | **100%** |

No JSON-LD tool calls in any baseline run. The discovery budget is dominated by `fetchVoID` appearing once per task at iteration 0 or 1. SPARQL fills all remaining active iterations.

### js-jsonld (4 runs, 20 tasks, 140 total iterations)

| Family | Count | Fraction |
|--------|-------|----------|
| discovery | 34 | 24.3% |
| sparql | 66 | 47.1% |
| jsonld | 16 | 11.4% |
| submit | 24 | 17.1% |
| **Total** | **140** | **100%** |

JSON-LD appears in 11.4% of all iterations. However, adoption is strongly task-gated: zero JSON-LD iterations across all obs-* data tasks; 100% of fetchJsonLd calls are on schema/vocab tasks.

### js-combined (4 runs, 20 tasks, 142 total iterations)

| Family | Count | Fraction |
|--------|-------|----------|
| discovery | 36 | 25.4% |
| sparql | 73 | 51.4% |
| jsonld | 13 | 9.2% |
| submit | 20 | 14.1% |
| **Total** | **142** | **100%** |

JSON-LD appears in 9.2% of iterations. Same obs-task exclusion applies. Lower adoption rate than js-jsonld (9.2% vs 11.4%) despite having the same JSON-LD tools available, suggesting the write/rdfs tools in combined condition compete for budget.

---

## Key Finding: JSON-LD Tool Adoption is Schema-Exclusive

The central question was: in js-jsonld and js-combined, does the agent actually USE the JSON-LD tools, or go straight to SPARQL?

**Answer: Yes, it uses them — but only for schema introspection tasks.**

| Task category | JSON-LD iter fraction (js-jsonld) | JSON-LD iter fraction (js-combined) |
|---------------|----------------------------------|-------------------------------------|
| data tasks (obs-*) | 0 / 47 iters = **0.0%** | 0 / 47 iters = **0.0%** |
| schema tasks (sio-*, vocab-*) | 16 / 93 iters = **17.2%** | 13 / 95 iters = **13.7%** |

Within schema tasks, the agent reaches for JSON-LD when it needs structural/ontological information it cannot get from raw SPARQL results: property inverses (`sio-attribute-inverse`), type hierarchies (`vocab-obs-to-sensor-properties`, `vocab-observation-subclasses`), and range information. The agent's strategy is: attempt SPARQL first; if the SPARQL response doesn't resolve the schema question, fetch the ontology document via `fetchJsonLd` and process it with `jsonld.expand` or `jsonld.frame`.

**Notable exception — vocab-sio-float-range-properties**: In the js-jsonld run `2026-03-11T16-01-32-644Z`, the agent used 7 consecutive `fetchJsonLd` calls (iters 4–12) after initial SPARQL attempts failed. This is the highest JSON-LD usage of any task and produced the highest token cost (108,044). The same task with js-combined used only 2 `fetchJsonLd` calls and still failed — JSON-LD access doesn't guarantee success on this task.

**vocab-sio-inverse-chain failure pattern**: Despite JSON-LD access being available, both js-jsonld and js-combined fail this task 50% of the time. In the failing runs, the agent either ignores `fetchJsonLd` entirely (js-jsonld run `18-45-54`) or uses it mid-task then reverts to repeated SPARQL (js-combined run `18-48-13`). The failure is in answer extraction, not tool selection.

**The SPARQL-first heuristic is stable across conditions**: In both js-jsonld and js-combined, iteration 0 is dominated by `discovery` (fetchVoID) or `sparql` (direct SPARQL attempt). `fetchJsonLd` almost never appears at iteration 0 — the agent treats JSON-LD as a fallback instrument, not a primary one.

This mirrors the Python phase 4-6 finding exactly: the tool is adopted selectively for schema tasks where SPARQL alone cannot ground the reasoning, and ignored for data tasks where raw triple exploration is sufficient.
