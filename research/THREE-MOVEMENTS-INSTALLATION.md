# The three-movement offline edition

The portable edition contains the three viewing films and their browser
experiences. The 4K screening editions, lossless audio, source and complete
scientific archives remain optional online downloads. It is a viewing and
interaction package, not a duplicate of the production workspace.

`studio/prepare_three_movements.py` accepts an explicit input plan. It never
discovers package contents by collecting a directory. Every selected source
entry must appear in a pinned publication receipt with its exact size and
SHA256. The earlier package builders and editions remain unchanged.

## Inputs

The private operational plan uses format
`palimpsest-three-movements-plan-v1`, the clean public source commit, an `inputs`
array, a `files` array and optional exact `rewrites`. All filesystem input
paths are relative to the plan unless explicitly absolute. They are not copied
into the public installation records.

Each input supplies `id`, `kind`, `receipt`, `receipt_sha256`, and either
`directory` or an approved content ZIP's `archive` and `archive_sha256`.

| Kind | Receipt entries | Purpose |
|---|---|---|
| `site` | `files: [{file, size, sha256}]` | Approved final website files |
| `content` | `files: [{path, bytes, sha256}]` | Clean legacy installation entries, from a directory or its exact published ZIP |
| `delivery` | `files: {name: {bytes, sha256}}` plus final delivery checks | New film, poster and captions from one final receipt |
| `files` | `files: [{name or path, bytes, sha256}]`, or a name-keyed object | Companion and other separately approved small publication assets |

An input from a ZIP must have the exact embedded `installation-content.json`.
Its entry set must agree with that receipt and its complete ZIP digest must
match the supplied published digest. Entries are streamed directly from the
ZIP; a second legacy extraction is unnecessary.

The new film, poster and captions must all come from the same `delivery`
input. That receipt must declare `edition: final`, a fully decoded viewing
file, 1920 by 1080 dimensions and a 240-second duration. A draft receipt is
rejected. The builder does not repeat the delivery encoder's full audiovisual
decoding; it verifies the exact approved bytes and runs a separate offline
browser check afterward.

Every selected archive entry has this shape:

```json
{
  "path": "site/assets/generated/river-viewing.mp4",
  "input": "river",
  "source": "river-viewing.mp4"
}
```

`path` is the new ZIP destination; `source` is the exact key in that input's
receipt. The complete selection must include the new entry and alias, all
older routes, their actual runtime assets, the three viewing films and books.
An explicit required minimum catches an omitted movement early; real offline
workflow checks establish the full runtime closure.

Use the cleaned public v2.2.0 installation as the legacy authority, not a
private original recovery with similarly named PDFs. Its published ZIP is
150,459,893 bytes with SHA256
`4887c6824ef41f94a04b414ad4bad4c2e9ffc1bca32bfd17e7c22757afa6fb41`;
its 39,146-byte content receipt has SHA256
`4cc531eb89bbf9f88c8251fe9a8c33c1a1f0ee8f9b2e42a2e5fcf3a27028c1c9`.
These existing inputs remain immutable.

## Portable presentation

The plan's `rewrites` object maps a selected target to a list of
`{before, after, count}` literal replacements. Each exact occurrence count is
checked before modifying an in-memory copy. This localizes older book/media
links and the second-act sculpture download template. A changed source cannot
silently produce an incomplete rewrite.

After those replacements, external HTML links receive a visible `Online`
suffix within their existing text hierarchy. The two download catalogs mark
external entries `Online / ...`. Local film/book links stay local. No
production HTML, CSS, script, inventory or approved media file is modified.

The package has a `START-HERE.txt` and the existing standalone range-aware
server as `serve.py`. The consumer runs:

```sh
python3 serve.py --site site --port 8080
```

The server binds only to `127.0.0.1`. Opening the HTML directly through `file:`
does not satisfy browser origin rules. Sound still requires an explicit
interaction. The new observer example keeps the same calculated state and
time when its selected readings change.

## Space and integrity

The hard ceiling is 1,500,000,000 bytes for package output plus a fresh
verification extraction and reserved browser evidence. The plan can set a
smaller ceiling but cannot raise it. There is no prepared site copy on disk:
approved files stream directly into the ZIP, while small modified text stays
in memory. Entries are stored without recompressing existing media; an exact
size bound includes both ZIP payload and fresh extraction, conservative ZIP
headers, receipts and 16 MB for browser evidence.

Preflight verifies every chosen source and rejects unsafe or duplicate paths,
symlinks, missing receipts, changed sizes/digests, unselected rewrite targets,
unsupported large movie editions and an over-budget selection. Binary inputs
are checked again while being written, so changes between preflight and
archiving fail. Archive paths, hashes, input receipt hashes and the public
source commit are recorded; local operational paths are omitted.

A fresh extraction verifies the exact entry set, entry metadata, sizes and
hashes. Both output directories must be new. Failure removes only directories
created by that invocation. Existing approved inputs and existing output
directories are preserved.

```sh
python -m studio.prepare_three_movements --plan PLAN.json \
  --output artwork/three-movements-installation-001 \
  --proof artwork/three-movements-proof-001 --check-only

python -m studio.prepare_three_movements --plan PLAN.json \
  --output artwork/three-movements-installation-001 \
  --proof artwork/three-movements-proof-001
```

## Verification boundaries

`studio/tests/test_three_movements_installation.py` uses small synthetic
fixtures. It checks the packaging contract, provenance guards, exact
rewrites, non-destructive failures, space limits and fresh extraction. Its
synthetic media is never a candidate installation or a playback proof.

`studio/three_movements_offline_check.mjs` launches the extracted server on a
random loopback port. A dead external proxy and request interception isolate
the test. It first rechecks the extracted file hashes, then exercises the
three actual viewing films, local captions/books, the returning-readings
example, preserved sculpture viewers, both live instruments and paused
recovery, recorded witness/atlas playback and vector export. It checks that
the external network really remains unavailable, saves bounded evidence and
closes its temporary server. Browser invocation and all packaging run on the
authorized production host.

```sh
node studio/three_movements_offline_check.mjs \
  --proof artwork/three-movements-proof-001 \
  --out artwork/three-movements-offline-001 --engine chromium
```

Successful source/fixture checks do not mean a final installation exists.
Final packaging waits for the pinned final site, companion and film receipts;
the fresh package must then pass the actual offline workflow. Playback and
signal checks remain separate from perceptual listening or emotional effect.
