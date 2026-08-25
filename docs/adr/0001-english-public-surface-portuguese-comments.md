# Public surface in English, code comments in Portuguese

dendrograph is written by a Brazilian author but aims at an open source audience,
so every surface another person or machine touches is English: node and edge
identifiers, the CLI, file and directory names, docs and README. Code comments
stay in Portuguese as the author's signature. Documentation in both languages.

## Consequences

The seam is "anything anyone else reads is English" — which puts the **graph schema
on the English side**, because it ships inside `graph.json`, `graph.sqlite` and
`llms.txt`, all of which exist to be consumed by other people and by machines.
The original Portuguese schema (`artefato`, `USA_FERRAMENTA`, `DA_COLECAO`) is
therefore translated, not kept. See `CONTEXT.md` for the resulting vocabulary.
