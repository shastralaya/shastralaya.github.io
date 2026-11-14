# Causal Continuity Ledger: Śāstrālaya V1.2

**Parent state:** Organization `shastralaya`; repo `shastralaya/shastralaya.github.io`; `main` at `9d51e2f2da5471c7fef4f07963f9c964eb482385` before this change. GitHub Pages uses GitHub Actions. User uses Windows 11, PowerShell 7, Git and personal SSH. The old portfolio is deliberately excluded. GitHub connection here is read-only: this work cannot push on behalf of the personal account.

## Cause -> choice -> operation -> evidence

1. **User goal:** substantially more real Sanskrit e-texts, not merely another build of nine established editions. **Choice:** twelve source-attributed IAST Sanskrit digital editions from a published CC BY-NC-SA 4.0 GRETIL-derived corpus; pin exact upstream commit, file size and Git blob hash, mark excerpt/recension boundaries. **Action:** `sources.json`, `scripts/gretil.py`, `scripts/fetch.py`, generators, source credits. **Limit:** exact bytes and stated licence do not prove independent print collation or third-party modern editorial rights. Do not imply alignment with translations.
2. **User experience failure:** Project Gutenberg `.txt` was the main practical interface, with a giant preformatted page. **Choice:** real HTML book index and per-page readers, usable spacing and navigation, archival TXT as a secondary download. **Action:** `scripts/build.py`, `src/assets/style.css`, `src/assets/app.js`; preservation of one-to-one source-line DOM nodes; technical segments clearly labelled rather than invented chapters.
3. **Integrity domino:** converting text to readable paragraphs could silently lose line breaks. **Choice:** retain raw codepoints in source-line elements; derive visual paragraphs solely from source blank lines; compare reconstructed text of all generated HTML pages to the original. **Action:** `scripts/check.py`, tests, tamper rejection. Real raw Gutenberg UTF-8 BOM and CRLF are retained byte-for-byte in downloads; generated HTML is written as UTF-8 bytes without Windows newline conversion.
4. **Mobile defect:** the Devanagari `श्री` glyph's visible ink, not the element box, was vertically high within the homepage rings. **Choice:** font-size-proportional optical adjustment after rendering in Chromium, with responsive 320-1360 checks. **Action:** CSS hero art alignment; no raster image dependency.
5. **Reading continuity:** source navigation was cumbersome. **Choice:** adjustable text, original line layout toggle, reading width, focus mode with keyboard Escape, progress indicator, local last-page link, clear next/previous links. **Action:** shared browser JavaScript and reader toolbars; no accounts, tracking, or external dependencies.
6. **Deployment truth:** initial Pages launch mistakenly ended on an automatic README/Jekyll artifact despite successful custom build. **Choice:** post-deploy live probes of five generated URLs, including non-README reader pages. **Action:** `.github/workflows/pages.yml`, `scripts/live_smoke.py`, regression tests. **Limit:** the live probe is exercised only when GitHub Actions runs against the actual public domain.
7. **Authentication and scope:** this environment lacks a personal GitHub push permission. **Choice:** release one guarded PowerShell update command, requiring exact clean HEAD and remote, checking package bytes, running tests before commit and push, preserving the original files on pre-commit failure. No `gh` dependency, no changes to `Anubhab-Dey/home` or the VPS.

## Verification state

- `python -m unittest discover -s tests -v`: **10 tests passed** (including complete synthetic library build, round-trip reader text, tamper rejection, UTF-8/CRLF source preservation, hashes and live-probe semantics).
- Synthetic `_site`: **21 editions**, 701 Gītā verse records, 12 extra IAST editions, 8 historical English editions; source reconstruction and link integrity passed.
- Chromium in-memory rendering of generated HTML/CSS/JS at **320, 360, 390, 768, 1024, 1360**: no horizontal overflow or JS errors; shelf filter, Sanskrit search, font controls, width toggle, focus/Escape, theme switch and English paragraph rendering passed. Direct localhost/file browser navigation is blocked in test runtime; this was not misreported as real production navigation.
- Actual pinned GRETIL file blobs and per-file catalogue licence metadata inspected on GitHub. **Full real-source build and subsequent live deployment pending CI push.** Synthetic fixtures never ship to the website.

## Handoff

- Apply against clean, unchanged `main` at `9d51e2f2da5471c7fef4f07963f9c964eb482385` and push to `shastralaya/shastralaya.github.io` only.
- Verify GitHub workflow's complete build/deploy/live-probe steps, then actual public Gītā/English/IAST readers, dark/light mode and mobile art.
- If a new source check fails, diagnose the **first source-specific error** rather than disable integrity gates. If live probe fails, inspect Pages source settings and competing workflows; never claim the site is live simply because a job has a green check.
- Separate next priorities: comprehensive textual collation and review, edition-specific scholarly rights, better book/chapter structure when real text witnesses support it, and optional historical English full-book search.

## V1.2.1 Windows regression correction (2026-11-11)

- **Observed result:** On Windows 11 / Python 3.14, V1.2 `test_full_offline_build_has_no_portfolio_and_all_verses` passed its first `check.check(out)` (line 138) and its deliberate corruption check, but failed at line 154 **after the test restored a generated HTML page using `Path.write_text()`**. The replacement text-mode write translated original LF characters into Windows CRLF. The *test* caused the source mismatch. The generator already used `write_bytes()` and the integrity checker correctly detected it. The first diagnostic guess that the generator used text-mode writes was wrong and was corrected after inspecting the actual release and traceback positions.
- **Root fix:** The test now snapshots the original HTML with `read_bytes`, tampers with UTF-8 bytes, restores the snapshot in a `finally` using `write_bytes`, asserts identical restored bytes, then rechecks the full output. The production generator and fail-closed checker are unchanged.
- **Regression guards:** Added a dedicated mixed-LF/CRLF Unicode byte-restoration test and gated the Ubuntu source build and Pages deployment on a `windows-latest` job using Python 3.14. Thus Windows portability is checked in CI before publication rather than only on the user's PC.
- **Verification:** The new synthetic suite has 12 passing tests on Linux; ZIP content and manifest to be checked independently before handoff. The Windows CI job and the full real-source download/build remain unexecuted until the next push. No user repository, GitHub branch, Pages deployment, or VPS changes were made by the failed V1.2 pre-commit run.
- **Next:** Apply this full V1.2.1 replacement to clean baseline `9d51e2f2da5471c7fef4f07963f9c964eb482385`, then check the Windows compatibility job, Ubuntu source build, Pages deploy, and live-probe steps in that order. If any gate fails, leave the earlier published site intact and inspect the first specific error.

- **Deployment dependency caught in final preflight:** GitHub Actions jobs have isolated workspaces. The V1.2 deploy job attempted `python scripts/live_smoke.py` without `actions/checkout`, which would have failed despite a successful deploy. V1.2.1 adds checkout and Python setup to that job, before deploy and probe; a regression asserts their ordering.


## V1.3 (2026-11-12): source expansion and bounded reading

- Cause: request to expand beyond 21 book-edition entries; user requires trusted, identified Sanskrit, commentary/translation companions, and finite reading pages instead of endless TXT scrolling.
- Source decision: append 9 pinned GRETIL-derived CC BY-NC-SA 4.0 texts with file-specific Git blob SHA-1 and exact byte lengths. Total intended source entries 30 = Sanskrit Gītā + 21 IAST Sanskrit e-texts + 8 complete Project Gutenberg English editions. Original six SARIT works still held separately.
- Provenance warning: GRETIL Īśā/Śaṅkara commentary specifically warns commentary is not proofread. Four-commentary Gītā includes Śrīdhara, Madhusūdana, Viśvanātha, Baladeva as distinct historical interpretive voices; not a homogeneous theological text or verified English translation.
- Design: chunk original source lines at a target of 8,500 characters (preserve an oversize whole line) and independently reconstruct every source byte/character from HTML. Show at most 24 pages directly; larger works offer twenty-page collapsible groups and a guarded numeric page jump. Previous/next and original downloads remain.
- Translation choice: historical Swami Paramananda (PG 3283) is already in the site. Identify exact section headings for Īśā and Kaṭha and link Sanskrit landing pages directly to corresponding English sections. No automatic verse alignment: different editorial witnesses and interpretations must not be conflated. Additional cross-edition links are labelled by their authors and genres.
- Deployment preflight: local Python tests, source patch application, exact remote and Git HEAD check, Node syntax if present; GitHub Windows+Linux tests, pinned source verification, build, complete HTML/source round-trip, deploy and live-URL probe.
- Tests: 16 offline unit/integration cases green on Linux, source fixture is synthetic, actual new source bytes have not been downloaded by this build environment. Further tests on Windows and real-source Actions are required before calling this release live.
- Recovery: on precommit failure restore touched files from backup; after commit, avoid blanket git reset; inspect commit and push state. No repository/VPS writes made from this environment.


## 2026-11-14 - Paged reading navigation, whole existing Śāstrālaya

- **Before:** GitHub `shastralaya/shastralaya.github.io` public `main`,
  HEAD `0a77329c98c63589b7a2723f7424a598e5e3aff3`; last GitHub Actions
  publishing workflow succeeded. Existing text editions are already paged,
  but their reader pages have only footer next/previous links and a jump form;
  the page inventory lives on a separate book landing page. Gītā has a
  chapter select but no visible chapter list in the left panel.
- **Trigger:** User wants left-panel page lists and Left/Right Arrow navigation.
  This is a navigational improvement, not a request to alter any Śāstra text.
- **Decision and reason:** Add bounded server-rendered left-side link lists
  (20 per group), a non-navigating range selector for other groups, and a
  native collapsed `<details>` mobile menu. Highlight the current page with
  `aria-current="page"`. Gītā renders its actual 18 chapter names. Preserve
  existing footer links and numeric page-jump forms as non-JavaScript fallbacks.
  Keyboard navigation is limited to valid adjacent routes and excluded from
  form controls, interactive elements, modifier shortcuts, repeated key events,
  and active text selections. No browser storage needed for navigation.
- **Changes:** `scripts/build.py`, `src/assets/style.css`, `src/assets/app.js`,
  `tests/test_reader_navigation.py`, `.github/workflows/pages.yml`, `README.md`, and this ledger.
  `sources.json`, `fetch.py`, original source bytes, licences, and upstream
  references are untouched.
- **Verification:** All 21 Python tests pass (including new sidebar boundary,
  page group, access semantics, first/last page and source preservation tests).
  Node JavaScript syntax check passes. Offline full synthetic build passes.
  Chromium in-memory rendering at 320, 390, 768 and 1360 px has no JS errors
  or horizontal overflow; responsive menu collapses on small devices; desktop
  panel is physically left of the reading text. Tested real keyboard handlers
  for English page navigation, Gītā chapters 1 and 18, a long IAST Sanskrit
  work, input focus, Ctrl+Arrow and range selector synchronisation.
- **After / outstanding:** The distribution package can be applied to the
  exact Git baseline with a guarded `git`-only Windows updater. The user still
  needs to run it and let GitHub Actions build the real source-backed website;
  Windows PowerShell execution and production push are not claimed as tested
  in this environment. No remote repository or VPS changes were made here.
