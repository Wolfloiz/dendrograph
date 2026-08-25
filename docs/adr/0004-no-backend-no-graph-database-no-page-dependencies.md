# No backend, no graph database, no external dependencies on the page

dendrograph runs in the user's own GitHub Actions and publishes to the user's own
GitHub Pages: no server to host, authenticate, pay for, or become a data processor
on behalf of. No graph database, because an archive of 500 repositories is roughly
3,000 nodes — under 1 MB, which a browser holds and draws without effort, the same
bet Obsidian's graph view makes. No CDN and no graph library on the page: the force
simulation is about 90 lines against a 2D canvas.

## Consequences

The page works offline, from a pen drive, and on Pages with no configuration, and
private repositories are never transmitted to a third party. If the project ever
needs to aggregate many archives into one corpus, `graph.json` imports into Neo4j in
an afternoon — the door stays open, but it is not walked through now. The Python
implementation uses the standard library only, so a fork installs nothing.
