# Contributing

Thank you for considering it. This file covers the things that are specific to
dendrograph and easy to get wrong; everything else is ordinary.

## The two documents that outrank a pull request

`.specify/memory/constitution.md` is binding, and `docs/adr/` records why each
decision was made. Work that contradicts either can still be right — but it has
to say so explicitly rather than quietly override it. Open the discussion first;
a changed decision is a new ADR, not a changed line.

Read the relevant ADR before working in its area. `CLAUDE.md` carries a one-line
index of all eleven so you always know one exists.

Some decisions are settled and should not be reopened without new information —
the MIT license (ADR-0006) is the clearest example, and it says so in its own
text.

## Constraints that are not negotiable

- **Python 3.11+, standard library only.** No runtime dependencies, ever. If you
  need a library, the answer is usually that the feature is out of scope.
- **`unittest`, not pytest.** It ships with Python; pytest does not.
- **No server, no graph database, no dependency on the published page.** The site
  must open from a `file://` URL on a pen drive with no network (ADR-0004).
- **English public surface, Portuguese comments** (ADR-0001). Identifiers, the
  CLI, file and directory names, the graph schema and the docs are English. Code
  comments are Portuguese. This is deliberate and the tests do not enforce it, so
  please hold the line.

## Two things this tool refuses to do

These are not unimplemented features. They are refusals, and a pull request that
adds either will be declined:

1. **It does not judge.** No quality score, grade, complexity measure, or
   inference about whether a person or a model wrote something (Principle V).
   `tests/test_no_judgement.py` sweeps every generated file for that vocabulary.
2. **It does not decide relationships on the Author's behalf.** The machine
   proposes, the Author disposes (Principle I, ADR-0009). `dendro suggest` prints
   config lines and creates nothing; `dendro prune` prints and deletes nothing. A
   `SUCCEEDS` edge exists because a `[[succession]]` line says so.

## Privacy is the default, and defaults are load-bearing

Private Artifacts are excluded from published output unless the Author opted them
in one by one (Principle IV, ADR-0005, ADR-0011). If you touch anything under
`core/privacy.py`, the publish path, or aliases, assume the test you are about to
skip is the one that matters.

Two related rules:

- Credentials come from the environment only, never from `dendrograph.toml`, and
  never into the store (ADR-0008).
- This repository holds no Author data (ADR-0010). The demo archive under
  `examples/` is public Artifacts only.

## Running the tests

```
python3 -m unittest discover -s tests
```

There are no fixtures to install. Repositories used by tests live as `git bundle`
files under `tests/fixtures/` and are unbundled into a temporary directory;
rebuild them with `tests/fixtures/build.sh` if you change them.

Tests are named as sentences that state what must be true, because the name is
what a reader sees when it fails. Prefer
`test_an_unreachable_source_is_not_a_deletion` over `test_unreachable`.

## Reporting something wrong

The most valuable bug report for this project is **output that asserts something
false** — a date that overstates experience, an edge pointing the wrong way, a
name that should not have been published. Those outrank crashes. Include the
`graph.json` fragment if you can.

## License

By contributing you agree that your contributions are licensed under the MIT
license (ADR-0006).
