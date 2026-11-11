# Śāstrālaya - a text-first Śāstra library

This is a **new, separate website** for free GitHub Pages hosting at
`https://shastralaya.github.io/`, in the GitHub organization `shastralaya`, administered by the personal account `Anubhab-Dey`.
It deliberately contains **no personal portfolio, résumé, contact details, or
old Caddy / VPS configuration**. The previous `Anubhab-Dey/home` repository is
not changed by this release.

## What is actually published

- One **Sanskrit** Bhagavad Gītā digital transcription, 18 chapters and 701
  verse records, with chapter/verse navigation, verse search, copyable Sanskrit,
  source notes and permanent links.
- Eight **historical English editions** retained from the source records of the
  earlier website. They are labelled translation, adaptation or commentary,
  not falsely paired verse-by-verse with the Sanskrit.
- No scanned PDFs. No SARIT texts claimed cleared. No external services,
  analytics, advertising or JavaScript frameworks.

The Gītā is attributed to the `gita/gita` dataset, pinned at Git commit
`c6fce39595445768876ddbb8d1268a9c935e1d2b`, with **both upstream Git blob
hashes verified** before the build. The repository's stated licence is
Unlicense; read the source attribution at `sources.json`. The 701-record
count belongs to this digital edition, not a claim about all traditional
recensions. No commentary or translation bundled with the upstream dataset is
copied. The exact Sanskrit bytes and structural checks pass at build time.

The English editions use Project Gutenberg source IDs 2388, 3283, 66208,
2526, 21918, 61937, 34125, 16295. These downloads are validated for identity,
title, closing marker, and full Gutenberg licence and are preserved without
stripping their original notices. Checksums are recorded per built release.
**Unlike the Sanskrit Gītā Git blobs, these Gutenberg bytes are not pinned to a
pre-recorded checksum.** Their identity checks are necessary, but do not prove
manual collation or textual infallibility.

## Publish to GitHub Pages (Git only, no GitHub CLI)

Prerequisites: Windows PowerShell 7, Python 3 (`py -3`), Git, Windows OpenSSH
with a key authenticated to the **personal** `Anubhab-Dey` account, and the
ability to create a public repository in the GitHub website.

Use the existing **public, empty** organization repository <https://github.com/shastralaya/shastralaya.github.io>. Do not initialize it with README,
`.gitignore` or licence. Then run top-level `INSTALL.ps1` from the release ZIP
(see top-level `START-HERE.md`). The installer tests the sources, verifies the organization repository is publicly accessible, and verifies the
personal SSH identity, creates the permanent local source workspace
`$HOME\Programs\My_Programs\shastralaya`, commits and pushes through
`git` alone. It refuses remote history it did not create or already verify.

After pushing, open repository **Settings > Pages > Build and deployment >
Source > GitHub Actions**. If the initial build failed before the setting was
ready, re-run it in the **Actions** tab. The `pages.yml` workflow downloads
and verifies real sources, builds all 30 HTML pages, checks the text and links,
then deploys. Confirm that both `build` and `deploy` passed and visit
<https://shastralaya.github.io/> and `/gita/2/` before claiming publication.

All pages have light/dark themes: system setting is used by default before CSS
paints, while a manual toggle is saved in local storage. The toggle remains
accessible without storage; system changes are followed unless overridden.

The old portfolio/VPS are untouched by this release. An old public website does
not disappear when a new Pages site is created.

### Future site updates

Edit in the persistent local working directory, run:

```powershell
Set-Location "$HOME\Programs\My_Programs\shastralaya"
py -3 -m unittest discover -s tests -v
git add .
git commit -m "Improve Śāstrālaya"
git push origin main
```

GitHub Actions automatically rebuilds and redeploys after the push. When
adding a work to `sources.json`, the build and reader must also be extended
with explicit source, verified edition bounds, and rights metadata. **Never
copy text under a guessed or generic licence.**

### Local full build (optional)

With internet access and trusted TLS certificates:

```powershell
py -3 scripts/fetch.py --dest _sources
py -3 scripts/build.py --source-dir _sources --out _site
py -3 scripts/check.py --site _site
py -3 -m http.server 8080 --directory _site
```

Visit `http://localhost:8080/`. Windows Python TLS verification occasionally
fails with specific corporate certificate stores. Do **not** disable certificate
verification. GitHub Actions' Linux runner performs the publication build,
while local Windows can use the repository to edit and test the source.

## Moving off the old portfolio

The new repository does not contain the portfolio, and it **does not** alter
`Anubhab-Dey/home`, the existing `anubhabdey.in` domain, Cloudflare or VPS.
The old site may still be publicly accessible even after this site is live.
Take it down in a **separate, domain-scoped operation after verifying Pages**;
do not cancel the shared VPS or delete its web root without auditing unrelated
hosted services. If complete GitHub-source privacy is also desired, decide
whether to make the existing portfolio repo private after checking dependencies
(the old public Git history is not erased simply by deploying a new site).

## Limits and responsibility

GitHub Pages is free for public repos on GitHub Free, with limits such as a
published site no larger than 1 GB and soft 100 GB/month bandwidth. It provides
no server-side database; this site needs none. See GitHub's current docs.

Texts are editorial historical sources, not endorsements of every historical
medical, legal, cosmological or philosophical claim. Distinguish mūla,
translation, commentary, and the claims of a specific digital recension.

The repository contains no licence grant over original UI/website code beyond
what applies by law, unless the owner adds one. Each included external text
has its own source terms on the sources page. The Sanskrit dataset's Unlicense
and the Gutenberg licences are separate; do not impose one on the other.
