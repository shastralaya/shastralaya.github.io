# Śāstrālaya

A **free, text-first Sanskrit reading library** at **https://shastralaya.github.io/**. Built as a static site for GitHub Pages. No VPS, subscription, paid domain, database, analytics, advertisements, PDF scans or personal portfolio is required.

## V1.3 collection (after successful publication)

- One Sanskrit **Bhagavad Gītā** digital edition (18 chapters, 701 verse records; pinned to `gita/gita`).
- **Twenty-one Sanskrit IAST digital editions** from the GRETIL-derived corpus, including the original twelve: Brahmabindūpaniṣad, Kaivalyopaniṣad, Kaṭhopaniṣad, Śvetāśvataropaniṣad, Brahmasūtra, Pātañjalayogasūtra, Mukundamālā, Gītagovinda, Bhāgavatapurāṇa, Brahmasaṃhitā (only chapter 5, with Jīva Gosvāmī commentary), Bhaktirasāmṛtasindhu and Laghubhāgavatāmṛta.
- **Nine newly added Sanskrit source editions:** Īśopaniṣad with commentary attributed to Śaṅkara (unproofread commentary), Māṇḍūkyakārikā, Bhagavad Gītā with four named commentaries, Rāmānuja’s Gītābhāṣya, Haribhaktivilāsa (only sections 1–11), Haṃsadūta, Ujjvalanīlamaṇi, Nādabindūpaniṣad, and Garbhopaniṣad. All are individually attributed digital witnesses, not certified collations.
- **Eight historical English editions** from Project Gutenberg: Edwin Arnold's Gītā adaptation; selected Upaniṣads (Paramananda); Viṣṇu Purāṇa (Dutt); Yoga Sūtras (Johnston); *Hindu Law and Judicature*; Harivaṃśa; Sarva-darśana-saṃgraha; and Thibaut's Śaṅkara commentary translation, Vol. I.

**These are 30 source-attributed edition entries, not 30 critically collated bilingual works.** Where English and Sanskrit cover the same work, named companion links connect them at work or section scope without pretending to provide validated verse alignment. The English and Sanskrit records aren't silently aligned, and a technical *reading page* is not passed off as a traditional chapter. SARIT manuscripts that require further editorial decisions remain excluded.

## Reader experience

- Home shelf with instant title filtering and Sanskrit/English categories.
- HTML readers with original book landing pages, readable paragraphs, finite ~8.5k-character reading pages, grouped indexes, numeric page jumps and previous/next links. The original TXT stays available as an archival download, **not** the primary reader.
- Sanskrit Gītā: actual chapters and numbered, copyable verses. Other Sanskrit witnesses: source-faithful IAST text with source-line anchors; readable segments are clearly marked as technical divisions.
- Font size and line-layout choices, focus mode (Escape to exit), reading-width toggle, a subtle scroll-progress line and a locally stored "continue reading" link. Light/dark themes respect OS preference until manually overridden.
- Responsive layouts for 320px phones through large desktops; no external JS or font services.
- Sanskrit search: exact Gītā verse references and the original text lines of the published IAST corpus. **Historical English full-book search is not implemented**; use browser Find on the open reading page and the per-book page list.

## Source, provenance and reuse

- The Gītā data are taken only from the pinned `gita/gita` revision and their complete Git blob hashes are validated. This identifies a digital source; it is not a claim of universal recension agreement or independent manual collation.
- The twenty-one IAST files come from `tokushige-koyasan/gretil-corpus`, pinned at Git revision `b724739ac7dcdec4d81f76b38bd478f84875242f`, with **file size and Git blob SHA-1 verification for each file**. The derived plain-text corpus is attributed to GRETIL/SUB Göttingen, INDOLOGY/GRETIL-mirror, and the extractor. The digital texts carry **CC BY-NC-SA 4.0** notices and require attribution, non-commercial use and ShareAlike. This does not automatically license every modern scholarly edition that may underlie a transcription. Where the source record refers to a modern print or contains editorial material, the actual witness and any rights issues remain explicitly noted. See `sources.json` and each site's Sources section.
- English sources are complete Project Gutenberg **source files**, downloaded by their individual IDs with trusted HTTPS and validated for identity/closing license. Their exact downloaded bytes are retained, including any BOM or CRLF. No modern translations are imported. Project Gutenberg trademark and text notices remain with their originals.
- Manuscript/printed text identity, source byte integrity, correctness of transcription, translation fidelity and redistribution rights are **different questions**. Checksums prove identity of downloads, not textual infallibility. Never silently merge editions or fill missing verses.

## Continuous publishing

GitHub Actions runs on pushes to `main` and on manual dispatch:

1. Unit/regression tests.
2. Download full original source files over verified HTTPS and validate hashes, IDs, notices and declared limits.
3. Build every HTML reader and original download in `_site`.
4. Validate all navigation links and source-line round trips; reject a missing or modified passage.
5. Publish via `actions/deploy-pages`, then **probe the live homepage plus representative Sanskrit and English reading pages**. A rendered README accidentally published instead of the library now fails this live check.

Use V1.3’s `PUSH-UPDATE.ps1` to update a clean checkout at the pinned V1.2.1 Git baseline `5b5c6a9f1cd78e1fd406b64796acd7e67ad40589`. For later development:

```powershell
Set-Location "$HOME\Programs\My_Programs\shastralaya"
py -3 -m unittest discover -s tests -v
git status --short
git add .
git commit -m "Improve Śāstrālaya"
git push origin main
```

The original `Anubhab-Dey/home` portfolio repo and VPS remain separate. Creating and updating Śāstrālaya does not automatically disable the old portfolio; removing it is a separate, domain-scoped operation that must not disrupt unrelated VPS services.

## Limits

GitHub Pages has size, bandwidth and appropriate-use constraints, which must be checked before expanding the library further. The design is deliberately text-only and requires no server APIs. Verify current limits in GitHub's documentation before large imports.

`docs/CCL.md` records decisions, tests, errors, inherited limitations and handoff. The site and its sources are not claimed public domain merely because the GitHub repository is public; each text's individual licence must be honored.


## V1.2.1 portability guard

The first V1.2 PowerShell run stopped before commit because the test's own
text-mode restoration changed UTF-8 HTML newlines on Windows. The generator
already used binary writes and did not need alteration. V1.2.1 corrects the
test to tamper and restore exact bytes and adds a real Windows Python 3.14
GitHub Actions test as a prerequisite to the Ubuntu publish job. The original
source-integrity validation remains strict.

The deploy job also checks out the repository and sets up Python before
executing its live-site verification script. Each Actions job runs in its own
workspace, so this is a mandatory deployment dependency.
