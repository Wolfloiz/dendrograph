# GitHub access via OAuth device flow, not a personal access token

`dendro login` prints a short code the user approves in their browser and receives a
token — the same mechanism `gh auth login` uses. Public repositories work with no
token at all, and an authenticated `gh` CLI is borrowed as a shortcut when present.

## Consequences

- Device flow needs only a public `client_id` — no client secret and no redirect URI —
  so it requires no server and leaves ADR 0004 intact. It is implementable with stdlib
  `urllib`: one request for the code, then polling until approval.
- Unauthenticated access is the zero-setup default so a stranger sees a graph within a
  minute of forking, at the cost of a 60 request/hour rate limit versus 5,000
  authenticated. Fine for a demo, poor for a 500-repository archive.
- A stored PAT stays supported **for CI only**, because a scheduled Actions run has no
  browser to approve in. This is another reason local runs are the primary mode.
- Actions' built-in `GITHUB_TOKEN` is deliberately not used for discovery: it is scoped
  to the current repository and cannot enumerate the user's other repositories.
