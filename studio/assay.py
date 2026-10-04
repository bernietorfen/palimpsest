"""Controlled tests of order-specific material memory; run remotely.

The same probe is applied after two differently ordered histories. Displacement,
velocity, and the delay buffer are reset to each material's local rest shape
before probing; retained plastic memory and fatigue are the only differences.
A third arm explicitly erases those retained fields as a causal intervention.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np
import torch

from studio.material import MaterialConfig, PalimpsestMaterial
from studio.score import Gesture
from studio.simulate import source_hashes


def excite(t: float, sequence: tuple[int, ...]) -> np.ndarray:
    f = np.zeros(12, np.float32)
    for i, voice in enumerate(sequence):
        f[voice] += Gesture(i * 4., voice, .4, .6, .8, 1.8).at(t)
    return f


def record(m: PalimpsestMaterial, seconds: float, sequence: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    dt = m.cfg.dt
    pitches, responses = [], []
    for step in range(round(seconds / dt)):
        if step % 4 == 0:
            r = m.readout()
            pitches.append(r["pitch_hz"].cpu().numpy())
            responses.append(r["velocity"].cpu().numpy())
        t = step * dt
        m.step(torch.as_tensor(excite(t, sequence), device=m.device), feedback=.08)
    return np.asarray(pitches), np.asarray(responses)


def relax(m: PalimpsestMaterial, erase: bool = False) -> None:
    if erase:
        m.p.zero_()
        m.z.zero_()
    m.u = m.p.clone()
    m.v.zero_()
    m.delay.zero_()
    m.echo_phase.zero_()
    m.index = 0
    m.steps = 0


def main(args: argparse.Namespace) -> None:
    torch.set_num_threads(2)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    hashes = source_hashes(out / "source")
    started = time.monotonic()
    config = MaterialConfig(size=args.size, device=args.device)
    arms = {}
    histories = {"forward": (0, 4, 2, 7, 3), "reverse": (3, 7, 2, 4, 0),
                 "fresh": ()}
    retained = {}
    for label, history in histories.items():
        m = PalimpsestMaterial(config)
        record(m, 24., history)
        retained[label] = {"memory_rms": float(m.p.square().mean().sqrt()),
                           "fatigue_mean": float(m.z.mean())}
        np.save(out / f"history-{label}.npy", m.fields().cpu().numpy())
        arms[label] = m
    erased = PalimpsestMaterial(config)
    erased.load_state_dict(arms["forward"].state_dict())
    relax(erased, erase=True)
    arms["erased"] = erased
    trajectories = {}
    for label, m in arms.items():
        relax(m)
        pitch, velocity = record(m, 14., (1, 5, 2))
        trajectories[label] = (pitch, velocity)
        np.savez(out / f"probe-{label}.npz", pitch_hz=pitch, velocity=velocity)
    pairs = {}
    for a, b in (("forward", "reverse"), ("forward", "fresh"), ("erased", "fresh")):
        pa, va = trajectories[a]
        pb, vb = trajectories[b]
        pairs[f"{a}_vs_{b}"] = {
            "pitch_rms_difference_hz": float(np.sqrt(np.mean((pa-pb)**2))),
            "pitch_max_difference_hz": float(np.max(np.abs(pa-pb))),
            "velocity_rms_difference": float(np.sqrt(np.mean((va-vb)**2))),
        }
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "question": "Does the order of the same writing gesture multiset change a later identical probe?",
              "controls": "Same parameters, writing gesture multiset, probe and feedback. Reset transient displacement to plastic rest shape, velocity, echo phase and delay to zero; preserve p,z except in erased arm.",
              "history_arms": histories, "retained": retained, "comparisons": pairs,
              "config": asdict(config), "source_sha256": hashes,
              "size": args.size, "dt": config.dt, "elapsed_seconds": time.monotonic()-started,
              "scope": "Evidence about this authored instrument only. u=p removes local elastic strain, but is not necessarily a full static equilibrium because spatial coupling remains. Equal gesture input norms do not imply equal mechanical work. Not a model of biological memory or a universal novelty claim."}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artifacts/studies/memory-assay-002")
    parser.add_argument("--size",type=int,default=128)
    parser.add_argument("--device",default="cuda")
    main(parser.parse_args())
