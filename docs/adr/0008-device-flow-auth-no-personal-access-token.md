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

## Verified against GitHub's documentation (2026-08-25)

The open question this ADR left — whether device flow needs enabling — is answered, and
the answer is yes:

- **It must be enabled explicitly.** "Before you can use the device flow to authorize and
  identify users, you must first enable it in your app's settings." Registering the OAuth
  App is not enough; the checkbox is a separate step and is on us, once, not on the Author.
- **The failure is named**, so `dendro login` can say what to do instead of failing
  opaquely: the API returns `device_flow_disabled` — "Device flow has not been enabled in
  the app's settings."
- **No client secret**, which is what keeps ADR-0004 intact: "you must pass your app's
  client ID … The `client_secret` is not needed for the device flow."

Source: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
