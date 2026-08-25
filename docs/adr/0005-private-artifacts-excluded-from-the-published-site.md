# Private Artifacts are excluded from the published site by default

The collector may read private repositories, but GitHub Pages on a public repository
is a world-readable website — so private Artifacts enter the store and are omitted
from the published site unless the Author opts them in one by one. A redacted mode is
available, publishing private Artifacts as aggregate shape with no names ("4 private
repositories, Rust, 2019–2021").

## Consequences

Without this, a tool whose headline promise is privacy would publish the names of a
user's clients, employers and internal systems to the open internet — the kind of
mistake that breaks an NDA. Defaulting to exclusion makes the safe path the lazy path.
Redacted mode exists because it rescues the résumé use case: "four years of Rust" is
the number an interview needs, provable without naming a single client. The README
must not claim that private repositories "never leave your account" without saying
what the published site does and does not contain.
