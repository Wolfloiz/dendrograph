<img src="views/logo.svg" alt="" width="64" height="64">

# dendrograph

***English** · [Português](README.pt-br.md)*

**A knowledge graph of what you have built.** Point it at your git repositories and get a
navigable map of Artifacts, Tools, Techniques and time — one that can answer *how long
have I actually used Rust?* with a date instead of a guess.

![A dendrograph graph: Artifacts linked to the Tools and Techniques they use](docs/example-graph.svg)

<sup>A real scan of a public GitHub organisation — 23 repositories, no credential, no
configuration. Regenerate with `python3 tools/render_svg.py <archive>/site/graph.json
docs/example-graph.svg`.</sup>

No server. No database. No account. Python 3.11+ and nothing else — the published site is
a folder you can open from a pen drive with the network unplugged.

```bash
git clone https://github.com/Wolfloiz/dendrograph.git ~/dendrograph
cd ~/dendrograph
python3 cli.py scan github:tinygrad --root ~/my-archive   # any public account
python3 cli.py build --root ~/my-archive
xdg-open ~/my-archive/site/index.html                     # macOS: open · Windows: start
```

**On Windows**, use PowerShell and change two words: `py` instead of `python3`, and
`Select-String` instead of `grep`. Everything else on this page is the same, including the
paths — PowerShell understands `~`.

No credential needed for a public account. The first scan clones full history into a
temporary directory and throws it away — nothing is cached between runs.

`pip install -e .` puts the same commands on your PATH as `dendro`, which is the short name
used elsewhere in this file. Every step below spells out `python3 .../cli.py` so that
nothing you are asked to paste depends on having installed anything.

Or skip the scan and open a real one: [`examples/site/index.html`](examples/site/) is a
published archive of 57 public repositories, committed to this repository. No install, no
account, and it renders with the network unplugged. `examples/README.md` says what the
privacy default kept out of it.

---

## The machine proposes, the Author disposes

This is the rule the rest of the design follows from, and it is worth stating before the
feature list.

dendrograph is **confident about what it observed and deferential about what it
interpreted.** It will tell you a repository's first commit was in March 2019, because it
read that. It will *not* tell you that one project succeeded another — it will notice the
resemblance, print the config line that would say so, and wait. If you never paste the
line, the relationship never exists, and nothing in the archive is blocked waiting for
you.

The same rule, in the places you will meet it:

- `dendro suggest` proposes successions, Collections and identity merges. **It creates
  nothing.**
- `dendro prune` lists what looks like clutter and prints the lines that would hide it.
  **It deletes nothing.** Excluding an Artifact omits it from the graph and leaves it in
  the store; delete the line and it comes back intact. A tool built because memory is
  unreliable must not offer one-command amnesia.
- Identity is overridable. If the tool decides two repositories are one Artifact and you
  disagree, say so in config and you win.
- Epoch Markers — the dated lines across your timeline, like *AI assistants arrive* — are
  declared by you and never inferred.

## Two things it refuses to do

Not "not yet". Refused:

1. **It does not judge your work.** No quality score, no grade, no complexity measure, no
   guess about whether a person or a model wrote something. It records what was built and
   when. A test sweeps every generated file for that vocabulary and fails the build if it
   appears.
2. **It does not overstate.** Where a number could be read two ways, it takes the smaller
   one. A fork you never committed to contributes no dates to your Tool spans, even though
   it sits in your archive — otherwise forking a 2009 project would have you claiming
   seventeen years of C++.

## What the published site contains, and what it does not

The default is `public` mode, and under it the site contains **no private Artifact**: no
name, no description, no URL, no source locator, no Technique evidence path, no content
hash.

That is not a filter you switch on. Private Artifacts are excluded until you opt each one
in by name, one at a time.

| | `public` (default) | `redacted` | `full` |
|---|---|---|---|
| Public Artifacts | yes | yes | yes |
| Private Artifacts | no | no, but counted | yes |
| Aliased Artifacts | node + dates, plus what `reveal` names | same | real name |
| Writes to | `site/` | `site/` | `.dendro-local/` |

`full` writes to a different directory on purpose. It is not a flag that a publish step
has to remember to check — a full build has no path to `site/` at all.

### Publishing private work without naming it

Client work you cannot name is still work you did. An **alias** publishes the node and its
dates under a label you choose (or a generated *Private project 3*), and reveals nothing
further until you name each field:

First scan the private repositories — `login` once, then scan as usual; a private
repository enters the store and stays out of the published site until you say otherwise:

```bash
python3 ~/dendrograph/cli.py login --root .
python3 ~/dendrograph/cli.py scan github:YOUR-ACCOUNT --root .
```

Then find the `id`. It is the store filename, and the name inside says which is which —
the two leading spaces anchor on the Artifact's own name, not a contributor's:

```bash
grep -l '^  "name": "the-project"' store/artifacts/*.json
```

Put that id in `dendrograph.toml` and rebuild:

```toml
[[publish.alias]]
id = "root-a1b2c3..."
label = "Anonymous fintech project"
reveal = ["period", "tools"]        # authorship stays hidden
```

Disclosure is opt-in per field. There is no opt-out redaction, because the failure mode of
opt-out is a field you forgot about. Some things never cross at any setting: the real name,
the description, the URL, source locators, Technique evidence paths, content hashes and
lineage edges.

**This does not make you unidentifiable.** Someone who knows your work may still recognise
a project from its dates and Tools. An alias is for the reader who does not already know —
it is not anonymity against a determined guess. See `docs/adr/0011`.

**One disclosure stated plainly, so it is not left to a guess.** The node keeps its id, and
the id is the repository's root commit SHA (ADR-0003). Anyone holding a clone reproduces it
with `git rev-list --max-parents=0 HEAD` and confirms the match; a private fork of a public
repository has a public root SHA already. The alias hides the project from a reader who does
not have the repository. It does not hide it from one who does — a client, a former
collaborator, a contractor. If that is the reader you are hiding from, do not publish the
Artifact at all. That is the default, and it costs nothing to keep.

## Three steps to your own archive

The tool holds no data of yours. Your Artifacts, your config and your decisions live in an
archive repository that is yours, which can be private while the site it publishes is
public (ADR-0010).

You do not need to read any source file to do this. Each step says what you will see when
it worked, so a failure shows up where it happened instead of at the end.

**1. Take the template.**

```bash
git clone https://github.com/Wolfloiz/dendrograph.git ~/dendrograph  # skip if you have it
cp -r ~/dendrograph/templates/archive ~/my-archive
cd ~/my-archive && git init
```

A copy, not a fork: the archive is yours from its first commit and nothing in it points
back here. It works untouched — an absent config is valid. To keep it on GitHub, private,
`gh repo create my-archive --private --source .` once you have something to commit.

*You should see* a repository with `store/`, `site/` and a `dendrograph.toml` whose every
example is commented out — and every one of them is valid the moment you uncomment it.

**2. Point it at your work.**

```bash
python3 ~/dendrograph/cli.py scan github:YOUR-ACCOUNT --root .
python3 ~/dendrograph/cli.py build --root .
```

`YOUR-ACCOUNT` is your GitHub username or organisation — `octocat`, not an email address
and not a URL. A wrong one is not silent: the scan reports it as unreachable with the HTTP
status, and records it as unreachable rather than as deleted.

No credential is needed for public repositories. `python3 ~/dendrograph/cli.py login` — a
GitHub OAuth device flow, no token to mint or store — adds your private ones to the store,
and they stay out of the published site unless you opt each one in.

Set `[archive].emails` to the addresses you commit under before you build. Without them
there is no "yours" to measure, and every Tool span says so rather than passing a fork's
dates off as your experience.

*You should see* a line saying how many Artifacts were added, one progress line per
repository while it scans, and a `site/` directory afterwards.

**3. Open it, then publish it.**

```bash
xdg-open site/index.html          # macOS: open · Windows: start
```

Or double-click it. It is a plain HTML file: it opens from disk, on any operating system,
with no server and no network.

**Before you publish, this is what the site contains and what it does not.** It is the
only claim in this README that costs something to get wrong:

- **Private Artifacts are not in it.** Not the name, not the description, not the URL, not
  the source locator, not the Technique evidence path. They are in your `store/`, which is
  the repository you can keep private.
- **No contributor's email address is in it.** An Author node is labelled by the name they
  sign commits with, or by the local part of the address when the collector has no name —
  never the address itself (ADR-0012).
- **No path from your machine is in it.** Local source locators do not cross into a
  published build.
- **What is in it**: every repository you scanned that was observed public, its dates, the
  Tools and Techniques inferred from its files with a pointer to the file each came from,
  and the people who committed to it.

If some of your private work should be visible as *shape* without being named, alias it —
see [Publishing private work without naming it](#publishing-private-work-without-naming-it).

```bash
python3 ~/dendrograph/cli.py publish --root .
```

Then serve `site/` with GitHub Pages, or push it to `[publish].target_repository`, or
leave it on disk. It is a folder of static files with no server behind it.

*You should see* `Site ready in site/.` and, once Pages picks it up, your archive at a URL
you can put on a CV.

## What ends up in the archive

`store/artifacts/<id>.json`, one file per Artifact, committed and readable in a diff. That
is the source of truth; `graph.json`, `graph.sqlite`, `llms.txt` and the two views are all
derived from it and regenerated on every build.

**Scans append.** They never rebuild. A drive that dies, an account that closes, a
repository that is deleted — the Artifact stays, and the source is marked unreachable with
the date it was last seen. That is the whole point: the archive outlives the things it was
built from.

An Artifact's identity is the SHA of its root commit, so it survives being cloned, renamed,
re-hosted and moved between disks. A fork shares that SHA and **is** the same Artifact —
which is where free fork detection comes from, and why *how much of it is yours* is a
separate question with a separate answer.

## For programs and agents

Every build writes `llms.txt` — the archive in prose, including what it deliberately does
not contain — alongside `graph.json`, which is self-describing: its `schema` key lists
every node and edge type, so nothing needs this README to read it. `graph.sqlite` holds
the same data as tables.

## Running it

```bash
python3 -m unittest discover -s tests
```

No dependencies to install, and none at runtime either.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: `.specify/memory/constitution.md`
is binding and `docs/adr/` records why each decision was made — work that contradicts
either can still be right, but it has to say so out loud.

## License

MIT. See [LICENSE](LICENSE) and `docs/adr/0006`, which explains why it is not AGPL and asks
that the question not be reopened without new information.
