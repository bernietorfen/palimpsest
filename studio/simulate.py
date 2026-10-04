"""Run only on the authorized RunPod; record the full instrument performance."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from studio.material import MaterialConfig, PalimpsestMaterial
from studio.score import Score


def source_hashes(snapshot: Path | None = None) -> dict[str, str]:
    root = Path(__file__).parent
    hashes = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in (".py", ".frag", ".vert", ".json", ".txt"):
            continue
        relative = p.relative_to(root.parent)
        data = p.read_bytes()
        hashes[str(relative)] = hashlib.sha256(data).hexdigest()
        if snapshot is not None:
            dest = snapshot / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    return hashes


def run(args: argparse.Namespace) -> None:
    torch.set_num_threads(4)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to replace an existing study: {output}")
    output.mkdir(parents=True, exist_ok=True)
    hashes = source_hashes(output / "source")
    print(json.dumps({"source_snapshot": str(output / "source")}), flush=True)
    config = MaterialConfig(size=args.size, device=args.device,
                            buckling=args.buckling, bending=args.bending,
                            memory_tuning=args.memory_tuning, echo_twist=args.echo_twist)
    model = PalimpsestMaterial(config)
    score = Score()
    substeps = round(1 / (args.fps * config.dt))
    if not np.isclose(substeps * config.dt, 1 / args.fps):
        raise ValueError("frame interval must be a multiple of simulation dt")
    frame_count = round(args.duration * args.fps) + 1
    fields = None
    if args.save_fields:
        fields = np.lib.format.open_memmap(output / "fields.npy", mode="w+",
                                          dtype=np.float16,
                                          shape=(frame_count, args.size, args.size, 4))
    readouts = {k: np.zeros((frame_count, 12), np.float32) for k in model.readout()}
    drives = np.zeros((frame_count, 12), np.float32)
    controls = np.zeros((frame_count, 2), np.float32)
    snapshots = [float(t) for t in args.snapshots.split(",") if t]
    saved = set()
    diagnostics = []
    start = time.monotonic()
    for frame in range(frame_count):
        t = frame / args.fps
        if fields is not None:
            fields[frame] = model.fields().cpu().numpy()
        for key, value in model.readout().items():
            readouts[key][frame] = value.cpu().numpy()
        drives[frame] = score.excitation(t)
        ctl = score.controls(t)
        controls[frame] = (ctl["feedback"], ctl["forgetting"])
        for wanted in snapshots:
            if wanted not in saved and t >= wanted:
                np.save(output / f"field-{wanted:06.1f}.npy", model.fields().cpu().numpy())
                saved.add(wanted)
        if frame % (args.fps * 6) == 0 or frame == frame_count - 1:
            info = model.diagnostics()
            info["elapsed_seconds"] = round(time.monotonic() - start, 3)
            diagnostics.append(info)
            print(json.dumps(info), flush=True)
            if not info["finite"]:
                raise FloatingPointError("nonfinite material; render must not proceed")
            if fields is not None:
                fields.flush()
        if frame < frame_count - 1:
            for sub in range(substeps):
                st = t + sub * config.dt
                excitation = torch.as_tensor(score.excitation(st), device=model.device)
                model.step(excitation, **score.controls(st))
    np.savez_compressed(output / "readouts.npz", time=np.arange(frame_count) / args.fps,
                        drive=drives, controls=controls, **readouts)
    torch.save(model.state_dict(), output / "checkpoint.pt")
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(),
            "config": asdict(config), "fps": args.fps, "duration": args.duration,
            "frames_with_endpoint": frame_count,
            "field_channels": ["displacement", "plastic_memory", "fatigue", "velocity"],
            "fields_dtype": "float16" if fields is not None else None,
            "readout_dtype": "float32", "source_sha256": hashes,
            "score": score.manifest(), "diagnostics": diagnostics,
            "elapsed_seconds": time.monotonic() - start,
            "device": torch.cuda.get_device_name() if args.device == "cuda" else "cpu",
            "torch": torch.__version__, "numpy": np.__version__}
    (output / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"complete": True, "output": str(output),
                      "seconds": round(time.monotonic() - start, 3)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/studies/material-001")
    parser.add_argument("--duration", type=float, default=72)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--buckling", type=float, default=0.0)
    parser.add_argument("--bending", type=float, default=0.08)
    parser.add_argument("--memory-tuning", type=float, default=0.65)
    parser.add_argument("--echo-twist", type=float, default=0.018)
    parser.add_argument("--save-fields", action="store_true")
    parser.add_argument("--snapshots", default="18,30,45,60,72,110,160,200,245,278,320,358,395,420")
    run(parser.parse_args())
