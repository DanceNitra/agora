#!/usr/bin/env bash
# Publish the site to GitHub Pages WITHOUT GitHub Actions.
#
# We deploy from the `gh-pages` branch (Pages source = gh-pages / root), which holds ONLY the website
# files (index.html + public/ + .nojekyll) — not the hundreds of MB of game assets in main's root
# that made the legacy "deploy from main" build fail. Run this after changing index.html or public/:
#
#   bash tools/deploy_pages.sh
#
# It rebuilds gh-pages from main's current site files via an isolated worktree (never touches the
# running main checkout), force-pushes it, and requests a Pages build. ~1-2 min to go live.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="DanceNitra/agora"
WT="$HOME/_ghp_build"

echo "[deploy] staging gh-pages from main's index.html + public/ …"
git worktree remove --force "$WT" 2>/dev/null || true
git worktree prune 2>/dev/null || true
git worktree add -B gh-pages "$WT" HEAD >/dev/null
(
  cd "$WT"
  git rm -r --cached . >/dev/null 2>&1 || true
  touch .nojekyll
  git add -f index.html public .nojekyll
  git commit -q -m "Pages: site-only deploy $(date -u +%Y-%m-%dT%H:%MZ)" || { echo "[deploy] nothing changed"; }
  git push -f origin gh-pages >/dev/null 2>&1
)
git worktree remove --force "$WT" 2>/dev/null || true
git worktree prune 2>/dev/null || true

echo "[deploy] requesting a Pages build …"
gh api -X POST "repos/$REPO/pages/builds" >/dev/null 2>&1 || true
echo "[deploy] done — live in ~1-2 min at https://dancenitra.github.io/agora/"
