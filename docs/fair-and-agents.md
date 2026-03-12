# FAIR was always about agents

*This essay is part of the [cogitarelink-fabric](../README.md) project documentation.*

**Summary.** The FAIR Guiding Principles (Wilkinson et al., 2016) are commonly read as a checklist for human-accessible data. That reading misses the paper's central argument: FAIR was designed for autonomous computational actors that read structured metadata, reason about what it means, and decide what to query next. LLM-based agents are the machines the FAIR authors were writing for. This project builds and tests the infrastructure FAIR envisioned, with experimental evidence showing measurable consequences for agent performance.

---

The FAIR Guiding Principles (Wilkinson et al., 2016) are often read as a checklist for making data accessible to human researchers. That reading misses the paper's central argument. The authors are explicit:

> "Distinct from peer initiatives that focus on the human scholar, the FAIR Principles put specific emphasis on enhancing the ability of machines to automatically find and use the data, in addition to supporting its reuse by individuals."

Their definition of machine-actionability describes what we would now recognize as an autonomous agent:

> "A continuum of possible states wherein a digital object provides increasingly more detailed information to an autonomously-acting, computational data explorer."

They specify four capabilities this computational explorer needs: (a) identify the type of a digital object by examining its structure and intent, (b) determine utility by interrogating metadata, (c) determine usability by checking licenses, consent, and access protocols, and (d) take appropriate action based on what it learned from (a)–(c). In 2016, the machines that could actually do this — read structured metadata, reason about what it means, and decide what to query next — did not exist. SPARQL reasoners could execute pre-written queries against well-known schemas, but they could not encounter an unfamiliar endpoint and figure out how to use it.

LLM-based agents are the machines the FAIR authors were writing for. An RLM agent encountering a fabric node for the first time does exactly what Wilkinson et al. described: it reads the VoID service description to identify what data exists (a), examines SHACL shapes and TBox ontologies to determine what the data means and how to query it (b), checks credentials and access protocols (c), and writes SPARQL queries to retrieve what it needs (d). The four FAIR capabilities map directly onto the fabric's four-layer KR stack: VoID for discovery, TBox for semantics, SHACL for constraints, SPARQL examples for action patterns.

This project is not extending FAIR to cover a new use case. It is building the system FAIR was designed for — and testing whether the principles, taken seriously as an engineering specification rather than an aspiration, actually produce the machine-navigable infrastructure the authors envisioned. The experimental results (Phase 3: +0.167 score lift from structured metadata for unfamiliar vocabularies) provide the first direct evidence that FAIR's design choices have measurable consequences for autonomous agent performance.

## References

- Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. https://doi.org/10.1038/sdata.2016.18
