# A published graph never carries a contributor's email address

An Author node is identified by a digest of the commit email and **labelled** by the local
part of that address, with GitHub's numeric prefix removed —
`57202004+kshitija7@users.noreply.github.com` is published as `kshitija7`. The full address
survives only in `full` mode, which `core/build.py` writes to `.dendro-local/` and never
publishes, and in the store, which is the Author's own file on the Author's own disk.

## Considered Options

The defect was not hypothetical. The first real scan — 97 Artifacts, mostly public
repositories including forks — produced a default-public site carrying the readable email
address of **1,165 contributors**, none of whom have heard of this tool. Forks are what make
it large: ADR-0003 keeps a fork as the same Artifact, so every contributor the upstream ever
had arrives with it. `node_id` already digested the address so it would stay out of the id;
the label was simply never given the same thought.

**Publish nothing for an Author** was rejected: the node is the point. An archive that cannot
say who else worked on something cannot answer the question it exists to answer.

**Publish the address, and let the Author redact** was rejected under Principle IV — the safe
path has to be the lazy one, and a control shaped as "remember to remove 1,165 addresses"
makes forgetting the failure mode. It is also not the Author's data to trade away.

**Publish the commit's author name** is the right label and is not available. `Authorship`
records the email alone, because the email is what identity is keyed on. Adding the name
means changing the store schema and rebuilding every Author record, and it belongs to
whoever owns `collectors/git/`. When it lands, it should replace the local part as the label;
this decision is about what must never be published, not about what the best label is.

## Consequences

- **The address never reaches `public` or `redacted`**, in any file — `graph.json`,
  `graph.js`, `graph.sqlite` and `llms.txt` all derive from the same payload.
  `tests/test_no_addresses.py` sweeps every written file for an address-shaped string, and a
  companion test asserts the fixture has addresses to leak, so the sweep cannot pass by
  finding nothing.
- **Two contributors can share a label.** `john@a.example` and `john@b.example` both publish
  as `john`. That is honest — they are two people called john — and the ids stay distinct,
  which is what identity is answered by. The label guard fires on one id with two labels, not
  on two ids with one label.
- **This narrows harvesting, it does not defeat identification.** A local part plus a public
  repository is often enough to find someone; `kshitija7` *is* a GitHub username. The claim
  here is narrow and should be stated narrowly: the site does not hand out a working email
  address. It is the same bargain ADR-0011 records for aliases.
- **`full` still shows addresses**, deliberately. Distinguishing two contributors called
  `john` is a real need for the Author reading their own archive, and that build never
  leaves the machine.
