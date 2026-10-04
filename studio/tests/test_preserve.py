"""Exercise actual archive restoration, including splitting and corruption."""
import json
import random

import pytest

from studio.preserve import pack, restore, verify


def test_split_archive_restores_every_byte_and_excludes_environment_files(tmp_path):
    project = tmp_path/"project"
    project.mkdir()
    (project/".env").write_text("TEST_SECRET=do-not-archive\n")
    data = random.Random(20261003).randbytes(62000)
    (project/"field.bin").write_bytes(data)
    (project/"readme.txt").write_text("A material that remembers.\n")
    manifest = pack(project,tmp_path/"backups","trial",["."],chunk_bytes=8192)
    info = json.loads(manifest.read_text())
    assert len(info["parts"]) > 5
    assert all(p["bytes"] <= 8192 for p in info["parts"])
    assert {p["path"] for p in info["files"]} == {"field.bin","readme.txt"}
    restored = tmp_path/"restored"
    restore(manifest,restored)
    assert (restored/"field.bin").read_bytes() == data
    assert (restored/"readme.txt").read_text() == (project/"readme.txt").read_text()
    assert not (restored/".env").exists()
    with pytest.raises(FileExistsError):
        restore(manifest,restored)


def test_corrupt_part_fails_before_restoring_anything(tmp_path):
    root = tmp_path/"project"
    root.mkdir()
    (root/"data.txt").write_text("one preserved inscription"*300)
    manifest = pack(root,tmp_path/"backups","trial",["data.txt"])
    info = json.loads(manifest.read_text())
    part = manifest.parent/info["parts"][0]["name"]
    part.write_bytes(b"corrupted")
    with pytest.raises(ValueError,match="corrupt"):
        verify(manifest)
    target = tmp_path/"restore"
    with pytest.raises(ValueError,match="corrupt"):
        restore(manifest,target)
    assert not target.exists()
