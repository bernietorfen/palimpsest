"""Create and restore checksum-verified, size-bounded production archives.

Execute on RunPod. This module never reads .env, caches, credentials, or files
outside the selected project paths. GitHub upload is a separate authenticated
transfer; a local archive is not itself evidence of remote preservation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile


EXCLUDED = {".env", ".git", ".venv", "__pycache__", ".pytest_cache", ".vercel", ".vercel-agent", ".DS_Store"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class ChunkWriter:
    def __init__(self, directory: Path, name: str, limit: int):
        self.directory, self.name, self.limit = directory, name, limit
        self.current = None
        self.parts = []
        self.digest = None
        self.count = 0

    def finish_part(self):
        if self.current is not None:
            self.current.close()
            self.parts.append({"name":self.current.name.rsplit("/",1)[-1],
                               "bytes":self.count,"sha256":self.digest.hexdigest()})
            self.current = None

    def write(self, data):
        original = len(data)
        view = memoryview(data)
        while view:
            if self.current is None:
                path = self.directory / f"{self.name}.tar.gz.part{len(self.parts):03d}"
                self.current = path.open("xb")
                self.digest = hashlib.sha256()
                self.count = 0
            amount = min(len(view), self.limit-self.count)
            block = view[:amount]
            self.current.write(block)
            self.digest.update(block)
            self.count += amount
            view = view[amount:]
            if self.count == self.limit:
                self.finish_part()
        return original

    def close(self):
        self.finish_part()


class HashedReader:
    def __init__(self, source):
        self.source = source
        self.digest = hashlib.sha256()

    def read(self, amount=-1):
        data = self.source.read(amount)
        self.digest.update(data)
        return data


class JoinedReader(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                try:
                    self.current = next(self.paths).open("rb")
                except StopIteration:
                    return 0
            amount = self.current.readinto(buffer)
            if amount:
                return amount
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()


def selected_files(root: Path, includes: list[str]):
    found = set()
    for include in includes:
        path = root / include
        if not path.resolve().is_relative_to(root) or not path.exists():
            raise ValueError(f"invalid or missing project path: {include}")
        for p in ([path] if path.is_file() else path.rglob("*")):
            relative = p.relative_to(root)
            if any(part in EXCLUDED or part.startswith(".env.") for part in relative.parts):
                continue
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError(f"symlinks and external paths are excluded: {relative}")
            if p.is_file() and p.suffix != ".pyc":
                found.add(relative)
    return sorted(found)


def pack(root: Path, output: Path, name: str, includes: list[str],
         chunk_bytes: int = 1_800_000_000) -> Path:
    root = root.resolve()
    if not name or Path(name).name != name or chunk_bytes < 1024:
        raise ValueError("archive name and chunk size are invalid")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / f"{name}.manifest.json"
    if manifest_path.exists() or list(output.glob(f"{name}.tar.gz.part*")):
        raise FileExistsError(f"archive already exists: {name}")
    paths = selected_files(root, includes)
    if not paths:
        raise ValueError("no files selected")
    writer = ChunkWriter(output, name, chunk_bytes)
    inventory = []
    try:
        with tarfile.open(fileobj=writer, mode="w|gz", compresslevel=1) as archive:
            for relative in paths:
                p = root / relative
                before = p.stat()
                info = archive.gettarinfo(str(p), arcname=str(relative))
                with p.open("rb") as source:
                    reader = HashedReader(source)
                    archive.addfile(info, reader)
                after = p.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise RuntimeError(f"file changed during backup: {relative}")
                inventory.append({"path":str(relative),"bytes":before.st_size,
                                  "sha256":reader.digest.hexdigest()})
    finally:
        writer.close()
    manifest = {"created_utc":datetime.now(timezone.utc).isoformat(),"name":name,
                "format":"concatenated gzip tar stream; concatenate parts in listed order",
                "parts":writer.parts,"files":inventory,
                "excluded":"credentials, environment files, runtime caches, symlinks"}
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    checksum_lines = [f"{p['sha256']}  {p['name']}" for p in writer.parts]
    checksum_lines.append(f"{sha256(manifest_path)}  {manifest_path.name}")
    (output/f"{name}.sha256").write_text("\n".join(checksum_lines)+"\n")
    print(json.dumps({"manifest":str(manifest_path),"files":len(inventory),"parts":writer.parts}),flush=True)
    return manifest_path


def verify(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text())
    paths = []
    for part in manifest["parts"]:
        if Path(part["name"]).name != part["name"]:
            raise ValueError("unsafe part name")
        path = manifest_path.parent / part["name"]
        if not path.is_file() or path.stat().st_size != part["bytes"] or sha256(path) != part["sha256"]:
            raise ValueError(f"missing or corrupt archive part: {part['name']}")
        paths.append(path)
    return manifest, paths


def restore(manifest_path: Path, destination: Path):
    manifest, paths = verify(manifest_path)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("restore destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    with io.BufferedReader(JoinedReader(paths)) as source:
        with tarfile.open(fileobj=source, mode="r|gz") as archive:
            archive.extractall(destination, filter="data")
    for item in manifest["files"]:
        path = destination / item["path"]
        if not path.resolve().is_relative_to(destination.resolve()) or sha256(path) != item["sha256"]:
            raise ValueError(f"restored content does not match: {item['path']}")
    print(json.dumps({"restored":len(manifest["files"]),"destination":str(destination)}),flush=True)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command",required=True)
    p = commands.add_parser("pack")
    p.add_argument("--root",type=Path,default=Path("."))
    p.add_argument("--output",type=Path,default=Path("backups"))
    p.add_argument("--name",required=True)
    p.add_argument("paths",nargs="+")
    v = commands.add_parser("verify")
    v.add_argument("manifest",type=Path)
    r = commands.add_parser("restore")
    r.add_argument("manifest",type=Path)
    r.add_argument("destination",type=Path)
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.root,args.output,args.name,args.paths)
    elif args.command == "verify":
        manifest,_ = verify(args.manifest)
        print(json.dumps({"verified_parts":len(manifest["parts"]),"manifest":str(args.manifest)}))
    else:
        restore(args.manifest,args.destination)


if __name__ == "__main__":
    main()
