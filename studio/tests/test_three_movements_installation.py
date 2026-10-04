"""Synthetic small fixtures only; these tests never substitute for final media."""
from argparse import Namespace
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from studio import prepare_three_movements as package


def put_json(path, value):
    path.write_bytes(package.encoded(value))
    return package.file_digest(path)


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / "inputs"
    source.mkdir()
    files = []
    selection = []
    for target in sorted(package.REQUIRED):
        name = target.removeprefix("site/")
        if name in ("assets/generated/river-viewing.mp4", "assets/generated/river-poster.jpg", "assets/generated/river-notes.vtt"):
            continue
        content = b"synthetic fixture\n"
        if name.endswith(".html"):
            content = b'<p><a href="https://example.org/book.pdf">Book</a></p>'
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
        files.append({"file": name, "size": len(content), "sha256": package.digest_bytes(content)})
        selection.append({"path": target, "input": "site", "source": name})
    (source / "unselected-secret.txt").write_text("Never package directory discoveries")
    site_sha = put_json(tmp_path / "site.json", {"files": files})
    movie = tmp_path / "river"
    movie.mkdir()
    for name in ("river-viewing.mp4", "river-poster.jpg", "river-notes.vtt"):
        (movie / name).write_bytes(b"synthetic delivery bytes, not playable media")
    delivery = {"edition": "final", "viewing_decoded_without_error": True,
                "editions": {"river-viewing.mp4": {"duration": "240", "video": {"width": 1920, "height": 1080}}},
                "files": {name: {"bytes": (movie / name).stat().st_size, "sha256": package.file_digest(movie / name)}
                          for name in ("river-viewing.mp4", "river-poster.jpg", "river-notes.vtt")}}
    delivery_sha = put_json(tmp_path / "delivery.json", delivery)
    for name in ("river-viewing.mp4", "river-poster.jpg", "river-notes.vtt"):
        selection.append({"path": "site/assets/generated/" + name, "input": "river", "source": name})
    plan = {"format": package.FORMAT, "source_commit": "a" * 40,
            "inputs": [{"id": "site", "kind": "site", "receipt": "site.json", "receipt_sha256": site_sha, "directory": "inputs"},
                       {"id": "river", "kind": "delivery", "receipt": "delivery.json", "receipt_sha256": delivery_sha, "directory": "river"}],
            "files": selection,
            "rewrites": {"site/index.html": [{"before": "https://example.org/book.pdf", "after": "/assets/generated/river-companion.pdf", "count": 1}]}}
    path = tmp_path / "plan.json"
    put_json(path, plan)
    args = Namespace(plan=str(path), output=str(tmp_path / "package"), proof=str(tmp_path / "proof"),
                     max_scratch_bytes=package.MAX_SCRATCH, check_only=False)
    return tmp_path, plan, path, args


def test_exact_archive_and_independent_fresh_extraction(fixture):
    root, plan, path, args = fixture
    before = (root / "inputs/index.html").read_bytes()
    report = package.main(args)
    assert report["all_file_hashes_match"]
    assert report["scratch_bytes_before_receipt"] + report["evidence_reserve_bytes"] < report["scratch_bound_bytes"]
    assert (root / "inputs/index.html").read_bytes() == before
    inventory = json.loads((root / "package/installation-content.json").read_text())
    with zipfile.ZipFile(root / "package" / package.ARCHIVE) as archive:
        assert "site/unselected-secret.txt" not in archive.namelist()
        assert "site/vercel.json" not in archive.namelist()
        assert archive.read("installation-content.json") == (root / "package/installation-content.json").read_bytes()
        for item in inventory["files"]:
            extracted = (root / "proof" / item["path"]).read_bytes()
            assert archive.read(item["path"]) == extracted
            assert len(extracted) == item["bytes"]
            assert hashlib.sha256(extracted).hexdigest() == item["sha256"]
    assert b"Online" not in (root / "proof/site/index.html").read_bytes()
    assert b"Book \xc2\xb7 Online" in (root / "proof/site/river.html").read_bytes()
    assert str(root) not in (root / "package/installation-content.json").read_text()
    assert str(root) not in (root / "package/three-movements-installation.json").read_text()


def test_unapproved_source_change_and_receipt_change_are_rejected(fixture):
    root, plan, path, args = fixture
    (root / "inputs/index.html").write_text("changed")
    with pytest.raises(ValueError, match="approved digest|approved size"):
        package.main(args)
    assert not Path(args.output).exists()
    (root / "site.json").write_text("changed receipt")
    with pytest.raises(ValueError, match="receipt digest"):
        package.main(args)


@pytest.mark.parametrize("target", ["site/../private.txt", "/absolute.txt", "site/.env", "site/x\\y.js", "site/vercel.json", "site/river-screening.mp4"])
def test_unapproved_paths_and_large_editions_rejected(fixture, target):
    root, plan, path, args = fixture
    plan["files"][0]["path"] = target
    put_json(path, plan)
    with pytest.raises(ValueError, match="publication path|installation target"):
        package.main(args)


def test_duplicate_targets_and_symlink_sources_rejected(fixture):
    root, plan, path, args = fixture
    plan["files"].append(plan["files"][0])
    put_json(path, plan)
    with pytest.raises(ValueError, match="Duplicate"):
        package.main(args)
    plan["files"].pop()
    put_json(path, plan)
    original = root / "inputs/index.html"
    original.rename(root / "elsewhere.html")
    original.symlink_to(root / "elsewhere.html")
    with pytest.raises(ValueError, match="Symlinks"):
        package.main(args)


def test_draft_is_rejected_even_with_a_pinned_receipt(fixture):
    root, plan, path, args = fixture
    delivery = json.loads((root / "delivery.json").read_text())
    delivery["edition"] = "draft"
    plan["inputs"][1]["receipt_sha256"] = put_json(root / "delivery.json", delivery)
    put_json(path, plan)
    with pytest.raises(ValueError, match="final 1080p"):
        package.main(args)


def test_exact_rewrite_count_and_scratch_cap(fixture):
    root, plan, path, args = fixture
    plan["rewrites"]["site/index.html"][0]["count"] = 2
    put_json(path, plan)
    with pytest.raises(ValueError, match="rewrite count"):
        package.main(args)
    plan["rewrites"]["site/index.html"][0]["count"] = 1
    put_json(path, plan)
    args.max_scratch_bytes = 1000
    with pytest.raises(ValueError, match="scratch bound"):
        package.main(args)
    assert not Path(args.output).exists() and not Path(args.proof).exists()


def test_existing_user_directories_are_preserved(fixture):
    root, plan, path, args = fixture
    Path(args.output).mkdir()
    sentinel = Path(args.output) / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(FileExistsError):
        package.main(args)
    assert sentinel.read_text() == "keep"


def test_clean_legacy_zip_is_selected_by_its_exact_embedded_inventory(fixture):
    root, plan, path, args = fixture
    value = b"approved clean legacy document"
    inventory = {"files": [{"path": "site/assets/generated/legacy-extra.pdf", "bytes": len(value), "sha256": package.digest_bytes(value)}]}
    raw = package.encoded(inventory)
    (root / "legacy-content.json").write_bytes(raw)
    with zipfile.ZipFile(root / "legacy.zip", "w") as archive:
        archive.writestr("installation-content.json", raw)
        archive.writestr("site/assets/generated/legacy-extra.pdf", value)
    plan["inputs"].append({"id": "legacy", "kind": "content", "receipt": "legacy-content.json",
                           "receipt_sha256": package.digest_bytes(raw), "archive": "legacy.zip",
                           "archive_sha256": package.file_digest(root / "legacy.zip")})
    plan["files"].append({"path": "site/assets/generated/legacy-extra.pdf", "input": "legacy", "source": "site/assets/generated/legacy-extra.pdf"})
    put_json(path, plan)
    package.main(args)
    assert (root / "proof/site/assets/generated/legacy-extra.pdf").read_bytes() == value


def test_online_labels_preserve_link_hierarchy_and_skip_hidden_arrow():
    text = '<a href="https://example.org"><span>4K edition</span><span>For screening</span></a>\n<a href="https://example.org/study">Study <span aria-hidden="true">↗</span></a>'
    result = package.portable_text("site/index.html", text.encode(), []).decode()
    assert '<span>For screening · Online</span>' in result
    assert '<span aria-hidden="true">↗</span> · Online</a>' in result
    assert package.portable_text("site/index.html", result.encode(), []).decode() == result


def test_fresh_verification_rejects_tampered_entry(fixture):
    root, plan, path, args = fixture
    package.main(args)
    raw = (root / "package/installation-content.json").read_bytes()
    inventory = json.loads(raw)
    inventory["files"][0]["sha256"] = "0" * 64
    proof = root / "tampered-proof"
    proof.mkdir()
    with pytest.raises(ValueError, match="approved digest"):
        package.verify(root / "package" / package.ARCHIVE, inventory, raw, proof)


def test_poster_cannot_silently_come_from_a_different_receipt(fixture):
    root, plan, path, args = fixture
    item = next(item for item in plan["files"] if item["path"].endswith("river-poster.jpg"))
    source = root / "inputs/assets/generated/river-poster.jpg"
    source.write_bytes((root / "river/river-poster.jpg").read_bytes())
    site = json.loads((root / "site.json").read_text())
    site["files"].append({"file": "assets/generated/river-poster.jpg", "size": source.stat().st_size, "sha256": package.file_digest(source)})
    plan["inputs"][0]["receipt_sha256"] = put_json(root / "site.json", site)
    item.update(input="site", source="assets/generated/river-poster.jpg")
    put_json(path, plan)
    with pytest.raises(ValueError, match="share the final delivery"):
        package.main(args)


def test_preflight_creates_no_installation_or_extraction(fixture):
    root, plan, path, args = fixture
    args.check_only = True
    report = package.main(args)
    assert report["scratch_bound_bytes"] < package.MAX_SCRATCH
    assert not Path(args.output).exists() and not Path(args.proof).exists()
    args.max_scratch_bytes = package.MAX_SCRATCH + 1
    with pytest.raises(ValueError, match="must not exceed"):
        package.main(args)


def test_failed_extraction_cleans_only_new_scratch(fixture, monkeypatch):
    root, plan, path, args = fixture
    def fail(*args):
        raise ValueError("Synthetic extraction failure")
    monkeypatch.setattr(package, "verify", fail)
    with pytest.raises(ValueError, match="Synthetic extraction"):
        package.main(args)
    assert not Path(args.output).exists() and not Path(args.proof).exists()
    assert (root / "inputs/index.html").is_file() and (root / "delivery.json").is_file()
