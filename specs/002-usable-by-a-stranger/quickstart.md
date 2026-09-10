# Quickstart — proving v0.2 works

Every check here runs against a real archive, not a fixture. v0.1's three late defects — a
graph that went blank, three things collapsed into one node, and 1,165 contributors'
addresses in a public site — were all invisible to fixtures and obvious against real data.

Assumes an archive at `~/my-archive`. The Author's own test archive is `/mnt/HD/dendro-test`.

## 0. Build

```bash
python3 cli.py build --mode full --root ~/my-archive   # .dendro-local/, never published
python3 cli.py publish --root ~/my-archive             # site/
```

## 1. One screen (US1)

```bash
xdg-open ~/my-archive/site/index.html   # macOS: open · Windows: start
```

- [ ] Both views are reachable from a control on the page, with no document load.
- [ ] Select a node in the graph, switch to the timeline: the same Artifact is highlighted.
- [ ] Reload. The view, the selection and the query come back.
- [ ] `~/my-archive/site/graph.html` and `timeline.html` **do not exist**.

**Offline, the literal test** — this is the claim the whole project rests on:

```bash
nmcli networking off        # or unplug it
xdg-open ~/my-archive/site/index.html   # macOS: open · Windows: start
```

- [ ] Every view works. Nothing is fetched. Switching views does not break.

**The budget** (SC-007). Paste the frame probe from v0.1's T042 into DevTools, drag without
stopping for ten seconds, then `__fps.stop()`:

- [ ] 60fps while panning, at the vsync ceiling, unchanged from v0.1.
- [ ] Switch to the timeline and confirm the graph's loop **stopped** — no frames drawn
      behind it. This is the regression the single screen is most likely to introduce.

## 2. Search (US2)

On the page:

- [ ] A word that appears only in a description, in no name, returns its Artifact.
- [ ] Results appear while typing, under 50 ms per keystroke at 3,000 nodes (SC-005).
- [ ] A visitor who knows a name reaches it in under 15 seconds from opening the archive,
      without scrolling a list (SC-001). Time it with someone who has not seen it.
- [ ] A result says whether it matched a name or a description.
- [ ] Selecting a result moves the current view; the screen is not replaced.
- [ ] A search matching nothing says so and offers no guess.

From the CLI:

```bash
python3 cli.py search melissa --root ~/my-archive
```

- [ ] Returns results from the whole archive, including Artifacts the site withholds.
- [ ] Each row names the kind, the subject and why it matched.

**The privacy check, which is the one that matters.** Pick a word that appears *only* in a
withheld Artifact's description:

```bash
python3 cli.py search <that-word> --root ~/my-archive     # finds it
grep -ril "<that-word>" ~/my-archive/site/                # must find nothing
```

- [ ] The CLI finds it; the published site contains it nowhere.
- [ ] Searching it on the page returns nothing at all — not "1 result hidden".

**No index**: on a Python without FTS5, `dendro search` refuses and says how to fix it. It
never falls back to a scan.

## 3. Tool profile (US3)

Open a Tool that appears in at least one untouched fork.

- [ ] The claimed span, the claimed Artifact count and the untouched count all appear.
- [ ] Untouched rows are marked as contributing no dates, and the marked rows **agree with
      the count** — the R7 question, guarded by a test on the real archive.
- [ ] A Tool used only in untouched forks says it claims no dates, rather than showing an
      empty range.
- [ ] With `[archive].emails` removed from config and a rebuild, every span is labelled as
      observed activity, not the Author's.
- [ ] Address `#tool/tool:something-that-was-withheld` directly: it renders the same *not
      found* as a Tool that never existed.

## 4. The fork path (US4)

The only check that cannot be automated:

- [ ] Hand the README to someone who has never seen the repository. Time them. They reach a
      published archive of their own public repositories in under 10 minutes, asking nothing.
- [ ] They never open a source file.
- [ ] Stopping after step one leaves them with a working thing, not a broken half — build an
      archive of a single Artifact and confirm every view renders it: a graph of one node, a
      one-row timeline, a search with nothing to find. It is the first thing every adopter
      sees, and the only state nothing else in this release exercises.
- [ ] At the point where it first publishes, the README states exactly what the published
      site does and does not contain (Principle IV).

## 4b. Private work under an alias (optional — ADR-0011)

Only if the archive has private Artifacts. Everything above holds without this; nothing
here is required to close v0.2. Skip it and the private work stays out of the site, which
is the default and the safe end of the choice.

```bash
python3 ~/dendrograph/cli.py login --root .          # once; private repos need it
python3 ~/dendrograph/cli.py scan github:YOUR-ACCOUNT --root .
grep -l '^  "name": "the-project"' store/artifacts/*.json    # the id is the filename
```

Put that id in `dendrograph.toml` under `[[publish.alias]]`, then `build` and `publish`.

- [ ] Before the alias: the private Artifact is in `store/` and in **no** published file —
      not its name, not its description, not its URL, not its source locator.
- [ ] After the alias: one node with the label you chose, `aliased: true`, and its dates.
- [ ] `reveal = []` (or absent) publishes the node and its dates and nothing else. Each
      name added to `reveal` adds exactly one field and no other.
- [ ] The real name appears nowhere in `site/`. The only `dendrograph` in a clean archive
      is `generator`, which is the tool naming itself.
- [ ] A Technique published under an alias ships **without** its evidence path — a path
      like `clientname/api/deploy.yml` would destroy the anonymity on its own (ADR-0011).
- [ ] No lineage edge reaches the aliased node.
- [ ] **The published `id` is the Artifact's root commit SHA** (ADR-0003), and it is
      published as-is under an alias. Anyone holding a clone of that repository can run
      `git rev-list --max-parents=0 HEAD` and confirm the match; if the private repository
      is a fork of anything public, the root SHA is public already. Confirm whether this is
      the disclosure you intend before publishing. See the note in ADR-0011.

## 5. Nothing regressed

```bash
python3 -m unittest discover -s tests -q
```

- [ ] All tests pass, and no fewer than at the close of v0.1 — 310 then, more now.
- [ ] `dendro build` requires no rescan to produce everything above (FR-020). Verify by
      building from a store that has not been scanned since v0.1.

## Still owed from v0.1

**SC-008** — a ~500-repository account completing a first full scan unattended within 30
minutes. Projected at 25.5 minutes from measured linearity; never observed. It closes when
an account that size is scanned, or when the criterion is rewritten to state what can
actually be observed. It is not scheduled here, and it has not gone away.
