# The tool repository and the Author's archive repository are separate

dendrograph the tool is a public, MIT-licensed repository. An Author's archive — the
committed store, their config and their published site — lives in a *different*
repository that they own and may keep private. The tool is never the place where
anyone's data lives.

## Considered Options

The original model was "fork the tool and run it in your own Actions", which conflated
two things: the program, and the archive it produces. That conflation created a direct
contradiction between ADR-0002 and ADR-0005: the store is committed (so it survives the
death of the drive it came from), while private Artifacts must never reach the open
internet. In a single public repository both cannot hold — the rendered site would
correctly hide private Artifact names while `store/artifacts/*.json` published them in
git history, permanently and in every clone.

Three alternatives were rejected. Splitting the store and gitignoring the private half
destroys the survives-the-dead-drive guarantee for exactly the Artifacts the Author can
least afford to lose. Redacting names at write time keeps the guarantee but permanently
discards data the Author wanted, including locally. Encrypting private entries at rest
adds key management and a crypto dependency to a stdlib-only project.

## Consequences

- The archive repository is created from a template and holds `store/`, config, the
  workflow and the published site. It may be private, and if it is, nothing about
  private work is ever public.
- **GitHub Pages from a private repository requires a paid plan.** Authors on a free
  plan either keep the archive public (and therefore hold no private Artifacts in it)
  or publish the built site to a second, public repository containing no store.
- The tool repository holds no Author data. Its `examples/` demo archive is built from
  public repositories only, which is what the privacy default produces anyway.
- The README's "three-step fork" becomes "create your archive from the template", and
  the tool must be consumable by that archive at a pinned version.
- Any feature that writes Author data into the tool repository is a defect.
