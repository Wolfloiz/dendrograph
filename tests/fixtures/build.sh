#!/usr/bin/env bash
# Rebuilds the fixture bundles from scratch. Dates and content are fixed, so the
# resulting commit SHAs are stable and tests can assert exact identities.
#
# The "no commits" fixtures are NOT here: `git bundle` requires at least one ref,
# so tests/support/fixtures.py builds those in a temp directory instead.
set -euo pipefail
cd "$(dirname "$0")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

commit() { # commit <repo> <author-name> <author-email> <date> <message>
  git -C "$1" -c user.name="$2" -c user.email="$3" \
    -c commit.gpgsign=false \
    commit -q --date="$4" -m "$5" --author="$2 <$3>"
}
export_env() { export GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1"; }

# --- base: multi-contributor -------------------------------------------------
git init -q -b main "$WORK/base"
cd "$WORK/base"
export_env "2019-03-11T10:00:00+00:00"
printf 'print("hello")\n' > main.py
printf '# project\n\nA thing.\n' > README.md
git add -A; commit "$WORK/base" "Alice" "alice@example.com" "$GIT_AUTHOR_DATE" "root: initial commit"

export_env "2019-06-02T10:00:00+00:00"
printf 'requests==2.31.0\nurllib3==2.2.1\n' > requirements.txt
# Um arquivo substancial (>512 bytes) para o conjunto de linhagem ter o que medir.
python3 - <<'PYGEN' > engine.py
for i in range(60):
    print(f"def step_{i}(value):\n    return value + {i}\n")
PYGEN
mkdir -p .github/workflows; printf 'name: ci\non: [push]\n' > .github/workflows/ci.yml
git add -A; commit "$WORK/base" "Alice" "alice@example.com" "$GIT_AUTHOR_DATE" "add deps and CI"

export_env "2020-01-15T10:00:00+00:00"
printf 'print("hello")\nprint("world")\nprint("again")\n' > main.py
git add -A; commit "$WORK/base" "Bob" "bob@example.com" "$GIT_AUTHOR_DATE" "extend main"

git bundle create -q "$OLDPWD/multi-contributor.bundle" --all
cd "$OLDPWD"

# --- two clones that diverged after the same root ----------------------------
for side in a b; do
  git clone -q "$WORK/base" "$WORK/div-$side"
done
export_env "2021-04-01T10:00:00+00:00"
printf 'side a\n' > "$WORK/div-a/a.txt"
git -C "$WORK/div-a" add -A; commit "$WORK/div-a" "Alice" "alice@example.com" "$GIT_AUTHOR_DATE" "diverge on side a"
git -C "$WORK/div-a" bundle create -q "$PWD/divergent-a.bundle" --all

export_env "2021-05-01T10:00:00+00:00"
printf 'side b\n' > "$WORK/div-b/b.txt"
git -C "$WORK/div-b" add -A; commit "$WORK/div-b" "Bob" "bob@example.com" "$GIT_AUTHOR_DATE" "diverge on side b"
git -C "$WORK/div-b" bundle create -q "$PWD/divergent-b.bundle" --all

# --- a fork the author barely touched ---------------------------------------
git clone -q "$WORK/base" "$WORK/fork"
export_env "2022-02-02T10:00:00+00:00"
printf '\n# typo fix\n' >> "$WORK/fork/README.md"
git -C "$WORK/fork" add -A; commit "$WORK/fork" "Carol" "carol@example.com" "$GIT_AUTHOR_DATE" "fix a typo"
git -C "$WORK/fork" bundle create -q "$PWD/barely-touched-fork.bundle" --all

# --- same content, history rewritten (new root commit) -----------------------
git init -q -b main "$WORK/rewritten"
cp "$WORK/base/main.py" "$WORK/base/README.md" "$WORK/base/requirements.txt" "$WORK/rewritten/"
mkdir -p "$WORK/rewritten/.github/workflows"
cp "$WORK/base/.github/workflows/ci.yml" "$WORK/rewritten/.github/workflows/ci.yml"
export_env "2023-08-08T10:00:00+00:00"
git -C "$WORK/rewritten" add -A
commit "$WORK/rewritten" "Alice" "alice@example.com" "$GIT_AUTHOR_DATE" "squashed import of the whole project"
git -C "$WORK/rewritten" bundle create -q "$PWD/rewritten-history.bundle" --all

echo "bundles rebuilt:"
ls -1 *.bundle
