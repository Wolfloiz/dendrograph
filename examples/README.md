# A real published archive

`site/` is not a mock-up. It is the output of `dendro publish` run against the author's own
GitHub account, with nothing configured beyond `[archive].emails` — the privacy default and
nothing else.

Open it with no server, no install and no account:

```bash
xdg-open examples/site/index.html   # or open the file however your desktop does
```

Unplug the network first if you want to check the claim. Everything the page needs —
the graph, the fonts, the stylesheet — is in this folder.

## What is in it

57 Artifacts spanning 2013 to 2026, and 2,432 nodes in all: 1,183 Dependencies, 1,165
Authors, 14 Periods, 10 Tools, 3 Techniques. The Author count is the surprise, and it is
ADR-0003 working as designed — a fork is the same Artifact, so every contributor the
upstream ever had arrives with it.

`graph.json` is the whole graph, `graph.js` the same payload wrapped so a `file://` page can
load it without a fetch, `graph.sqlite` the queryable form, and `llms.txt` the prose summary
for a model reading the archive instead of a person. Together they are 3.2 MB; a demo built
from real data costs what real data costs.

## What is not in it, and why

- **Private repositories, and anything whose visibility was never observed.** 40 of the 97
  Artifacts in the source archive are withheld here, because a local scan cannot tell that a
  folder is meant to be public and `unknown` is not `public` (ADR-0005).
- **Contributor email addresses.** Author nodes are labelled by the local part of the commit
  address — `kshitija7`, not `57202004+kshitija7@users.noreply.github.com` (ADR-0012).
- **Paths on the author's machine.** Local locators never cross into a published build.

The store that produced this is not here either. It lives in the author's own archive
repository, which is a separate repository from this tool by decision (ADR-0010).

## Making your own

```bash
python3 cli.py scan github:<your-account> --root ~/my-archive
python3 cli.py publish --root ~/my-archive
```

Nothing above needs a credential to read public repositories. `python3 cli.py login` adds
your private ones to the archive — and they stay out of `site/` unless you opt each one in.

## Regenerating this one

It is a snapshot, not a build artifact: nothing regenerates it on commit, and it will drift
from the author's account until someone republishes and copies `site/` back over this one.
