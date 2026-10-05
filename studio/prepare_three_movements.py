"""Build a bounded offline edition from explicitly pinned publication inputs.

No directory discovery supplies package contents. The private input plan selects
every file; public receipts contain relative archive paths and hashes only.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile


FORMAT = "palimpsest-three-movements-plan-v1"
MAX_SCRATCH = 1_500_000_000
EVIDENCE_RESERVE = 16_000_000
TEXT_LIMIT = 8_000_000
ARCHIVE = "palimpsest-three-movements.zip"
ALLOWED = {".html", ".css", ".js", ".json", ".svg", ".jpg", ".jpeg", ".png",
           ".webp", ".woff2", ".txt", ".mp4", ".m4a", ".glb", ".pdf", ".vtt",
           ".bin", ".vert", ".frag"}
FILMS = {"river-viewing.mp4", "river-compact.mp4", "choir-viewing.mp4", "palimpsest-viewing.mp4",
         "phrase-first.mp4", "phrase-return.mp4"}
REQUIRED = {"site/" + name for name in (
    "index.html", "river.html", "movements.html", "first-act.html", "instrument.html",
    "choir.html", "witness.html", "observer.html", "atlas.html", "pressure.html",
    "credits.html", "river.css", "river.js", "assets/relational-clock-core.js",
    "assets/data/relational-clock.json", "assets/generated/river-viewing.mp4",
    "assets/generated/river-compact.mp4", "assets/generated/river-opening.m4a",
    "assets/generated/river-return.m4a", "assets/generated/river-listening-pair.json",
    "assets/generated/river-poster.jpg", "assets/generated/river-notes.vtt",
    "assets/generated/river-local-000.jpg", "assets/generated/river-local-104.jpg",
    "assets/generated/river-local-208.jpg", "assets/generated/river-wide-000.jpg",
    "assets/generated/river-wide-104.jpg", "assets/generated/river-wide-208.jpg",
    "assets/generated/river-controlled-views.json",
    "assets/generated/river-companion.pdf", "assets/generated/choir-viewing.mp4",
    "assets/generated/palimpsest-viewing.mp4", "assets/generated/palimpsest-complete-notebook.pdf",
    "assets/generated/a-choir-of-absences-notebook.pdf", "assets/generated/font-license.txt")}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def safe(name):
    if not isinstance(name, str):
        raise ValueError("Invalid relative publication path")
    path = PurePosixPath(name)
    if (not name or str(path) != name or path.is_absolute()
            or any(part.startswith(".") for part in path.parts)
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)):
        raise ValueError("Invalid relative publication path")
    return name


def checked_stream(stream, expected, destination=None):
    digest, size = hashlib.sha256(), 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(block)
        if size > expected["bytes"]:
            raise ValueError("Input exceeds its approved size")
        digest.update(block)
        if destination is not None:
            destination.write(block)
    if size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        raise ValueError("Input differs from its approved digest")


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(size, digest):
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError("Invalid approved file size")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid approved file digest")
    return {"bytes": size, "sha256": digest}


class Input:
    def __init__(self, spec, base, stack):
        self.identifier = spec["id"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", self.identifier):
            raise ValueError("Invalid input identifier")
        receipt = (base / spec["receipt"]).resolve()
        if receipt.stat().st_size > TEXT_LIMIT:
            raise ValueError("Publication receipt exceeds the bounded text budget")
        raw = receipt.read_bytes()
        if len(raw) > TEXT_LIMIT or digest_bytes(raw) != spec["receipt_sha256"]:
            raise ValueError("Publication receipt digest differs")
        data = json.loads(raw)
        self.public = {"id": self.identifier, "kind": spec["kind"],
                       "receipt_sha256": spec["receipt_sha256"]}
        kind = spec["kind"]
        if kind == "site":
            items = [(r["file"], r["size"], r["sha256"]) for r in data["files"]]
        elif kind == "content":
            items = [(r["path"], r["bytes"], r["sha256"]) for r in data["files"]]
        elif kind in ("files", "delivery"):
            values = data["files"]
            items = ([(name, r["bytes"], r["sha256"]) for name, r in values.items()]
                     if isinstance(values, dict) else
                     [(r.get("name", r.get("path")), r["bytes"], r["sha256"]) for r in values])
            if kind == "delivery":
                viewing = data["editions"]["river-viewing.mp4"]
                if (data["edition"] != "final" or not data["viewing_decoded_without_error"]
                        or viewing["video"]["width"] != 1920 or viewing["video"]["height"] != 1080
                        or abs(float(viewing["duration"]) - 240) > .05):
                    raise ValueError("A verified final 1080p river delivery is required")
                if not spec.get("verification") or not spec.get("verification_sha256"):
                    raise ValueError("The independent final delivery verification is required")
                review_path = base / spec["verification"]
                if review_path.stat().st_size > TEXT_LIMIT:
                    raise ValueError("Delivery verification exceeds the bounded text budget")
                review_raw = review_path.read_bytes()
                if digest_bytes(review_raw) != spec["verification_sha256"]:
                    raise ValueError("Delivery verification digest differs")
                review = json.loads(review_raw)
                if (review.get("format") != "palimpsest-river-delivery-review-v1"
                        or review.get("all_passed") is not True
                        or review["delivery_receipt"]["sha256"] != spec["receipt_sha256"]
                        or review["delivery_receipt"]["bytes"] != len(raw)):
                    raise ValueError("Delivery verification does not bind the approved final receipt")
                for name, width, height in (("river-viewing.mp4", 1920, 1080),
                                             ("river-compact.mp4", 1280, 720)):
                    edition = data["editions"].get(name)
                    verified = review["editions"].get(name)
                    if (not edition or not verified
                            or edition["video"]["width"] != width or edition["video"]["height"] != height
                            or abs(float(edition["duration"]) - 240) > .05
                            or verified["identity"] != data["files"][name]
                            or verified["picture"]["decoded_frames"] != 5760
                            or verified["picture"]["exact_integer_pts_cadence"] is not True
                            or verified["audio"] != review["editions"]["river-screening.mp4"]["audio"]):
                        raise ValueError("Both final playback editions need matching decoded timing and soundtrack verification")
                self.public["verification_sha256"] = spec["verification_sha256"]
        else:
            raise ValueError("Unsupported publication receipt kind")
        self.files = {}
        for name, size, digest in items:
            name = safe(name)
            if name in self.files:
                raise ValueError("Duplicate receipt entry")
            self.files[name] = record(size, digest)
        self.archive = None
        self.root = None
        if "archive" in spec:
            if "directory" in spec or kind != "content":
                raise ValueError("Only content inventories accept a ZIP input")
            archive_path = base / spec["archive"]
            if archive_path.is_symlink() or file_digest(archive_path) != spec["archive_sha256"]:
                raise ValueError("Publication archive digest differs")
            self.archive = stack.enter_context(zipfile.ZipFile(archive_path))
            names = self.archive.namelist()
            if len(set(names)) != len(names) or set(names) != set(self.files) | {"installation-content.json"}:
                raise ValueError("Publication archive inventory differs")
            if self.archive.read("installation-content.json") != raw:
                raise ValueError("Embedded publication receipt differs")
            for item in self.archive.infolist():
                safe(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("Symlinks are not publication inputs")
            self.public["archive_sha256"] = spec["archive_sha256"]
        else:
            self.root = base / spec["directory"]
            if self.root.is_symlink() or not self.root.is_dir():
                raise ValueError("Publication directory is missing or linked")
            self.root = self.root.resolve()

    def open(self, name):
        safe(name)
        if name not in self.files:
            raise ValueError("Selected file is absent from its publication receipt")
        if self.archive is not None:
            return self.archive.open(name)
        path = self.root
        for part in PurePosixPath(name).parts:
            path /= part
            if path.is_symlink():
                raise ValueError("Symlinks are not publication inputs")
        if not path.is_file() or not path.resolve().is_relative_to(self.root):
            raise ValueError("Publication input is missing or escapes its directory")
        return path.open("rb")


class OnlineLabels(HTMLParser):
    """Add visible labels while preserving all original markup and attributes."""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in text.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.anchor = None
        self.spans = []
        self.insertions = []
        self.feed(text)

    def position(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a":
            self.anchor = {"external": attrs.get("href", "").startswith(("https://", "http://")),
                           "span": None, "text": ""}
            self.spans = []
        elif tag == "span" and self.anchor is not None:
            self.spans.append(attrs.get("aria-hidden") == "true")

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["text"] += data

    def handle_endtag(self, tag):
        if self.anchor is None:
            return
        if tag == "span" and self.spans:
            if not self.spans.pop():
                self.anchor["span"] = self.position()
        elif tag == "a":
            if self.anchor["external"] and not re.search(r"\bOnline\b", self.anchor["text"]):
                self.insertions.append(self.anchor["span"] or self.position())
            self.anchor = None


def portable_text(target, raw, rewrites):
    text = raw.decode("utf-8")
    for rewrite in rewrites:
        before, after, count = rewrite["before"], rewrite["after"], rewrite["count"]
        if not before or before == after or not isinstance(count, int) or count < 1:
            raise ValueError("Invalid exact portable rewrite")
        if text.count(before) != count:
            raise ValueError(f"Portable rewrite count differs for {target}")
        text = text.replace(before, after)
    if target.endswith(".html"):
        for position in reversed(OnlineLabels(text).insertions):
            text = text[:position] + " · Online" + text[position:]
    elif target in ("site/edition.json", "site/choir-edition.json"):
        catalog = json.loads(text)
        for item in catalog["downloads"]:
            if item["url"].startswith(("https://", "http://")) and not item["detail"].startswith("Online / "):
                item["detail"] = "Online / " + item["detail"]
        return encoded(catalog)
    return text.encode()


def startup(commit):
    return f"""PALIMPSEST / THREE MOVEMENTS
An original collection of films and instruments by Codex, 2026.

Extract into an empty directory on an authorized computer. From that directory:

  python3 serve.py --site site --port 8080

Open http://127.0.0.1:8080/ on the same computer. Stop with Ctrl+C.
The server listens only on loopback and supports seeking with byte ranges.
Direct file: opening is unsupported by browser origin rules.

A RIVER TWICE / 4:00
The 1080p viewing film and smaller 720p option share the same soundtrack and
native controls. Optional captions, two short listening excerpts, companion
and calculated phase-clock experiment are included. Return the fragment,
then open its surroundings at the same moment.

EARLIER MOVEMENTS / movements.html
A choir of absences (4:48), its playable choir, matched listening piece,
observer, sculptures and books; the first film (7:12), playable material,
120 histories, pressure explorer, sculptures and notebooks.

All three viewing films and the browser experiences use included files.
Sound begins only after interaction. Live instruments need WebGL2 and Web Audio.
Use Save to retain a material state. No user state is uploaded.

Links marked Online are optional: 4K screenings, lossless sound, source,
complete scientific records and external references need a connection.
The film and PDF books can also be opened separately.

The geometry and music are authored interpretations. A River Twice's closed
calculated state continues through its composed silence. This is not a
demonstration of uniquely quantum behavior or a universal account of time.
Playback and signal checks are not claims of perceptual audition.

Source: https://github.com/bernietorfen/palimpsest/tree/{commit}
Exact included files: installation-content.json.
Website type license: site/assets/generated/font-license.txt.
""".encode()


def prepare(plan, base, stack):
    if plan.get("format") != FORMAT or not re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"]):
        raise ValueError("Expected a pinned installation plan and source commit")
    inputs = {}
    for spec in plan["inputs"]:
        source = Input(spec, base, stack)
        if source.identifier in inputs:
            raise ValueError("Duplicate input identifier")
        inputs[source.identifier] = source
    selected, records, prepared = {}, [], {}
    rewrites = plan.get("rewrites", {})
    for item in plan["files"]:
        target = safe(item["path"])
        if (target in selected or not target.startswith(("site/", "licenses/"))
                or PurePosixPath(target).suffix not in ALLOWED
                or target in ("site/vercel.json", "site/assets/generated/edition.json")
                or (target.endswith(".mp4") and PurePosixPath(target).name not in FILMS)):
            raise ValueError("Duplicate or unapproved installation target")
        source, name = inputs[item["input"]], safe(item["source"])
        expected = source.files.get(name)
        if expected is None:
            raise ValueError("Selected file is absent from its publication receipt")
        selected[target] = (source, name)
        text = target.endswith(".html") or target in ("site/edition.json", "site/choir-edition.json") or target in rewrites
        with source.open(name) as stream:
            buffer = io.BytesIO() if text else None
            if text and expected["bytes"] > TEXT_LIMIT:
                raise ValueError("Portable text exceeds the bounded text budget")
            checked_stream(stream, expected, buffer)
        if text:
            prepared[target] = portable_text(target, buffer.getvalue(), rewrites.get(target, []))
            actual = record(len(prepared[target]), digest_bytes(prepared[target]))
        else:
            actual = expected
        records.append({"path": target, **actual, "input": source.identifier,
                        "source": name, "source_sha256": expected["sha256"]})
    if not REQUIRED.issubset(selected):
        raise ValueError("Required three-movement content is missing")
    if set(rewrites) - set(selected):
        raise ValueError("Portable rewrites refer to unselected files")
    river_input, _ = selected["site/assets/generated/river-viewing.mp4"]
    for name in ("river-viewing.mp4", "river-compact.mp4", "river-poster.jpg", "river-notes.vtt"):
        source, source_name = selected["site/assets/generated/" + name]
        if source is not river_input or source.public["kind"] != "delivery" or source_name != name:
            raise ValueError("The new playback editions, poster and captions must share the final delivery receipt")
    pair_source, pair_name = selected["site/assets/generated/river-listening-pair.json"]
    with pair_source.open(pair_name) as stream:
        pair = json.load(stream)
    if (pair.get("format") != "palimpsest-river-listening-pair-v1"
            or [item["file"] for item in pair["excerpts"]] != ["river-opening.m4a", "river-return.m4a"]):
        raise ValueError("The approved listening-pair record is required")
    for item in pair["excerpts"]:
        source, name = selected["site/assets/generated/" + item["file"]]
        if source.files[name] != record(item["bytes"], item["sha256"]):
            raise ValueError("A listening excerpt differs from its provenance record")
    prepared["START-HERE.txt"] = startup(plan["source_commit"])
    server = Path(__file__).with_name("serve_site.py").read_bytes()
    prepared["serve.py"] = server.replace(b"Viewing room on RunPod loopback port", b"Viewing room on loopback port")
    for name in ("START-HERE.txt", "serve.py"):
        records.append({"path": name, "bytes": len(prepared[name]), "sha256": digest_bytes(prepared[name]),
                        "generated": "portable launcher"})
    records.sort(key=lambda item: item["path"])
    inventory = {"title": "PALIMPSEST / Three movements", "source_commit": plan["source_commit"],
                 "files": records, "input_receipts": [item.public for item in inputs.values()],
                 "portable_changes": "Explicit approved files only; exact declared text rewrites; external HTML/catalog links marked Online; loopback range server; three viewing films, no 4K masters or stems."}
    raw = encoded(inventory)
    total = sum(item["bytes"] for item in records) + len(raw)
    # Stored ZIP entries cannot expand. Reserve ample headers, receipts and
    # bounded browser evidence; no prepared site copy is created on disk.
    bound = 2 * total + 4096 * (len(records) + 1) + 1_000_000 + EVIDENCE_RESERVE
    return inputs, selected, prepared, inventory, raw, total, bound


def verify(archive_path, inventory, raw, proof):
    expected = {item["path"]: item for item in inventory["files"]}
    expected["installation-content.json"] = record(len(raw), digest_bytes(raw))
    if not proof.is_dir() or any(proof.iterdir()):
        raise ValueError("Verification requires a fresh empty proof directory")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Installation archive entries differ")
        for name in names:
            safe(name)
            info = archive.getinfo(name)
            if stat.S_ISLNK(info.external_attr >> 16) or info.file_size != expected[name]["bytes"]:
                raise ValueError("Installation archive metadata differs")
            destination = proof / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, destination.open("xb") as target:
                checked_stream(source, expected[name], target)


def main(args):
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text())
    limit = args.max_scratch_bytes
    if not 0 < limit <= MAX_SCRATCH:
        raise ValueError("Scratch limit must not exceed 1.5 GB")
    with ExitStack() as stack:
        inputs, selected, prepared, inventory, raw, total, bound = prepare(plan, plan_path.parent, stack)
        if bound > limit:
            raise ValueError(f"Installation scratch bound {bound} exceeds {limit}")
        report = {"files": len(inventory["files"]) + 1, "uncompressed_bytes": total,
                  "scratch_bound_bytes": bound, "scratch_limit_bytes": limit,
                  "plan_sha256": file_digest(plan_path), "source_commit": plan["source_commit"]}
        if args.check_only:
            print(json.dumps({"preflight_passed": True, **report}))
            return report
        output, proof = Path(args.output), Path(args.proof)
        if output.exists() or proof.exists() or output.resolve() == proof.resolve():
            raise FileExistsError("Use fresh separate installation and proof directories")
        if output.resolve().is_relative_to(proof.resolve()) or proof.resolve().is_relative_to(output.resolve()):
            raise ValueError("Installation and proof directories must not contain one another")
        output_created = proof_created = False
        try:
            output.mkdir(parents=True)
            output_created = True
            proof.mkdir(parents=True)
            proof_created = True
            archive_path = output / ARCHIVE
            with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_STORED) as archive:
                for item in inventory["files"] + [{"path": "installation-content.json", "bytes": len(raw), "sha256": digest_bytes(raw)}]:
                    name = item["path"]
                    metadata = zipfile.ZipInfo(name, (2026, 10, 4, 0, 0, 0))
                    metadata.external_attr = (stat.S_IFREG | 0o644) << 16
                    with archive.open(metadata, "w") as target:
                        if name == "installation-content.json":
                            target.write(raw)
                        elif name in prepared:
                            target.write(prepared[name])
                        else:
                            source, source_name = selected[name]
                            with source.open(source_name) as stream:
                                checked_stream(stream, item, target)
            (output / "installation-content.json").write_bytes(raw)
            (output / "START-HERE.txt").write_bytes(prepared["START-HERE.txt"])
            verify(archive_path, inventory, raw, proof)
            actual = sum(p.stat().st_size for folder in (output, proof) for p in folder.rglob("*") if p.is_file())
            if actual + EVIDENCE_RESERVE > limit:
                raise ValueError("Actual installation scratch exceeds its limit")
            report.update(archive_sha256=file_digest(archive_path), archive_bytes=archive_path.stat().st_size,
                          all_file_hashes_match=True, scratch_bytes_before_receipt=actual,
                          evidence_reserve_bytes=EVIDENCE_RESERVE,
                          scope="Freshly extracted exact archive; browser workflow and perceptual checks are separate.")
            (output / "three-movements-installation.json").write_bytes(encoded(report))
            print(json.dumps(report))
            return report
        except BaseException:
            # Both paths were absent on entry; no approved source is removed.
            if output_created and output.exists():
                shutil.rmtree(output)
            if proof_created and proof.exists():
                shutil.rmtree(proof)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--proof", required=True)
    parser.add_argument("--max-scratch-bytes", type=int, default=MAX_SCRATCH)
    parser.add_argument("--check-only", action="store_true")
    main(parser.parse_args())
