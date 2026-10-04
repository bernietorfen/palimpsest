"""An authored hysteretic membrane with delayed modal feedback.

This is a speculative instrument, not a calibrated physical material. A toroidal
sheet carries displacement u, velocity v, plastic rest shape p, and fatigue z.
Sound-envelope forces change the sheet; modal readouts of the changed sheet
retune the sound and return as delayed forces. All constants belong to the score.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import torch


@dataclass(frozen=True)
class MaterialConfig:
    size: int = 128
    dt: float = 1 / 96
    stiffness: float = 2.4
    tension: float = 1.2
    bending: float = 0.08
    buckling: float = 0.0
    damping: float = 0.38
    cubic: float = 0.7
    yield_strain: float = 0.095
    write_rate: float = 0.32
    memory_limit: float = 0.8
    memory_diffusion: float = 0.035
    forgetting: float = 0.0008
    fatigue_rate: float = 0.26
    fatigue_recovery: float = 0.001
    feedback: float = 0.20
    feedback_delay: float = 0.79
    memory_tuning: float = 0.65
    echo_twist: float = 0.018
    force_scale: float = 1.6
    device: str = "cuda"
    dtype: str = "float32"

    def __post_init__(self) -> None:
        if self.size < 16 or self.dt <= 0 or self.dt > 1 / 24:
            raise ValueError("size >= 16 and 0 < dt <= 1/24 are required")
        if self.memory_limit <= 0 or self.yield_strain <= 0:
            raise ValueError("memory and yield scales must be positive")
        if self.feedback_delay < self.dt:
            raise ValueError("feedback must have a positive causal delay")
        if not 0 <= self.memory_tuning <= 2 or not 0 <= self.echo_twist <= .1:
            raise ValueError("tuning and echo twist are outside the supported parameter range")
        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable; do not fall back silently")


# These nonseparable force/readout shapes and their phase offsets are authored
# for this instrument. They are not taken from a cellular-automaton catalog.
MODE_PAIRS = ((1, 0), (1, 1), (2, 1), (3, 1), (2, 3), (4, 1),
              (3, 3), (5, 2), (4, 3), (5, 4), (6, 5), (7, 3))
PITCHES_HZ = (110.0, 137.5, 146.6666667, 165.0, 183.3333333, 220.0,
              247.5, 275.0, 293.3333333, 330.0, 366.6666667, 440.0)


def laplacian(a: torch.Tensor) -> torch.Tensor:
    """Five-point periodic Laplacian, with unit grid spacing."""
    return (torch.roll(a, 1, -1) + torch.roll(a, -1, -1)
            + torch.roll(a, 1, -2) + torch.roll(a, -1, -2) - 4 * a)


def tension_force(a: torch.Tensor, tension: torch.Tensor) -> torch.Tensor:
    """Symmetric edge fluxes for a sheet with spatially varying tension.

    A negative edge coefficient is compressive. The bending and cubic terms in
    the material equation oppose the resulting short-wave buckling instability.
    """
    out = torch.zeros_like(a)
    for axis in (-2, -1):
        for shift in (-1, 1):
            neighbor = torch.roll(a, shift, axis)
            edge = (tension + torch.roll(tension, shift, axis)) * 0.5
            out = out + edge * (neighbor - a)
    return out


class PalimpsestMaterial:
    """Deterministic sheet; no random state and no external data are required."""

    def __init__(self, config: MaterialConfig = MaterialConfig()) -> None:
        self.cfg = config
        self.dtype = getattr(torch, config.dtype)
        self.device = torch.device(config.device)
        coord = torch.arange(config.size, dtype=self.dtype, device=self.device)
        coord = coord * (2 * math.pi / config.size)
        y, x = torch.meshgrid(coord, coord, indexing="ij")
        modes, quadratures = [], []
        for i, (a, b) in enumerate(MODE_PAIRS):
            phase = i * math.pi * (3 - math.sqrt(5))
            f = (torch.cos(a * x + b * y + phase)
                 + 0.31 * torch.sin((a + 1) * x - (b + 1) * y - phase)
                 + 0.17 * torch.cos((b + 2) * x + (a + 1) * y + 0.7 * phase))
            f = f - f.mean()
            modes.append(f / f.square().mean().sqrt())
            q = (-torch.sin(a * x + b * y + phase)
                 + 0.31 * torch.cos((a + 1) * x - (b + 1) * y - phase)
                 - 0.17 * torch.sin((b + 2) * x + (a + 1) * y + 0.7 * phase))
            q = q - q.mean()
            quadratures.append(q / q.square().mean().sqrt())
        self.modes = torch.stack(modes)
        self.readout_weights = self.modes.square()
        self.readout_weights /= self.readout_weights.mean(dim=(-2, -1), keepdim=True)
        self.u = torch.zeros_like(x)
        self.v = torch.zeros_like(x)
        self.p = torch.zeros_like(x)
        self.z = torch.zeros_like(x)
        self.delay_steps = max(1, round(config.feedback_delay / config.dt))
        self.delay = torch.zeros((self.delay_steps, len(MODE_PAIRS)),
                                 dtype=self.dtype, device=self.device)
        self.index = 0
        self.steps = 0
        self.base_pitches = torch.tensor(PITCHES_HZ, dtype=self.dtype, device=self.device)
        self.echo_phase = torch.zeros_like(self.base_pitches)
        # Shifted response shapes mean an echo does not simply redraw its source.
        self.echo_modes = torch.roll(self.modes, (config.size // 7, config.size // 11), (-2, -1))
        self.echo_quadratures = torch.roll(torch.stack(quadratures),
                                           (config.size // 7, config.size // 11), (-2, -1))

    def _project(self, a: torch.Tensor) -> torch.Tensor:
        return (self.modes * a[None]).mean(dim=(-2, -1))

    def _tuning(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # Signed projection retains the orientation of an inscription. Squared
        # weights describe fatigue independently of that orientation.
        memory = self._project(self.p)
        fatigue = (self.readout_weights * self.z[None]).mean(dim=(-2, -1))
        pitch = self.base_pitches * torch.sqrt(1 - 0.58 * fatigue)
        pitch = pitch * torch.exp(self.cfg.memory_tuning * memory)
        return memory, fatigue, pitch

    @torch.no_grad()
    def step(self, excitation: torch.Tensor, *, feedback: float | None = None,
             forgetting: float | None = None) -> None:
        c = self.cfg
        if excitation.shape != (len(MODE_PAIRS),):
            raise ValueError(f"excitation must have shape ({len(MODE_PAIRS)},)")
        dt = c.dt
        rate = c.forgetting if forgetting is None else forgetting
        gain = c.feedback if feedback is None else feedback
        d = self.u - self.p
        stiffness = c.stiffness * (1 - 0.58 * self.z)
        grid_scale = (c.size / 128) ** 2
        lap = laplacian(self.u) * grid_scale
        tension = c.tension * lap
        if c.buckling:
            tension = tension_force(self.u, c.tension - c.buckling * self.z) * grid_scale
        force = c.force_scale * torch.einsum("m,mij->ij", excitation, self.modes)
        echo = torch.tanh(self.delay[self.index] / 0.18)
        force = force + gain * (
            torch.einsum("m,mij->ij", echo * torch.cos(self.echo_phase), self.echo_modes)
            + torch.einsum("m,mij->ij", echo * torch.sin(self.echo_phase), self.echo_quadratures))
        accel = (tension - c.bending * laplacian(lap) * grid_scale
                 - stiffness * d - c.cubic * d.pow(3) + force)
        self.v = (self.v + dt * accel) / (1 + dt * c.damping)
        self.u = self.u + dt * self.v
        strain = self.u - self.p
        excess = torch.relu(strain.abs() - c.yield_strain * (1 - 0.35 * self.z))
        write = c.write_rate * excess * torch.tanh(strain / 0.035)
        # Smoothly close the writing window at the authored memory capacity.
        capacity = torch.clamp(1 - (self.p / c.memory_limit).square(), min=0)
        self.p = self.p + dt * (write * capacity - rate * self.p
                              + c.memory_diffusion * laplacian(self.p) * grid_scale)
        self.p.clamp_(-c.memory_limit, c.memory_limit)
        self.z = self.z + dt * (c.fatigue_rate * excess.square() * (1 - self.z)
                              - c.fatigue_recovery * self.z)
        self.z.clamp_(0, 1)
        if c.echo_twist:
            # Pitch drift turns the spatial location of a later echo. The scale
            # maps audible Hz to slow geometric phase; it is an authored rule,
            # not an attempt to resolve audio-rate vibrations at this timestep.
            _, _, pitch = self._tuning()
            self.echo_phase = torch.remainder(self.echo_phase
                + dt * (2 * math.pi * c.echo_twist) * (pitch - self.base_pitches), 2 * math.pi)
        self.delay[self.index] = self._project(self.v)
        self.index = (self.index + 1) % self.delay_steps
        self.steps += 1

    @torch.no_grad()
    def readout(self) -> dict[str, torch.Tensor]:
        position = self._project(self.u)
        velocity = self._project(self.v)
        strain = self._project(self.u - self.p)
        memory, fatigue, pitch = self._tuning()
        # This is a deliberately designed modal mapping, not an eigenvalue solve.
        amplitude = torch.sqrt(velocity.square() + 0.55 * strain.square() + 1e-12)
        return {"position": position, "velocity": velocity, "strain": strain, "memory": memory,
                "fatigue": fatigue, "pitch_hz": pitch, "amplitude": amplitude,
                "echo_phase": self.echo_phase.clone()}

    def fields(self) -> torch.Tensor:
        """u, p, fatigue, velocity, in a documented image-channel order."""
        return torch.stack((self.u, self.p, self.z, self.v), dim=-1)

    def state_dict(self) -> dict[str, Any]:
        return {"config": asdict(self.cfg), "steps": self.steps, "index": self.index,
                **{name: getattr(self, name).clone().cpu()
                   for name in ("u", "v", "p", "z", "delay", "echo_phase")}}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        for key, value in asdict(self.cfg).items():
            if key not in ("device", "dtype") and state["config"].get(key) != value:
                raise ValueError(f"checkpoint configuration differs at {key}")
        for name in ("u", "v", "p", "z", "delay", "echo_phase"):
            a = state[name].to(device=self.device, dtype=self.dtype)
            if a.shape != getattr(self, name).shape:
                raise ValueError(f"incompatible {name} shape")
            setattr(self, name, a.clone())
        self.steps, self.index = int(state["steps"]), int(state["index"])

    @torch.no_grad()
    def diagnostics(self) -> dict[str, float]:
        d = self.u - self.p
        gx = self.u - torch.roll(self.u, 1, -1)
        gy = self.u - torch.roll(self.u, 1, -2)
        energy = (0.5 * self.v.square() + 0.5 * self.cfg.stiffness * (1 - 0.58 * self.z) * d.square()
                  + self.cfg.cubic * d.pow(4) / 4
                  + self.cfg.tension * (gx.square() + gy.square()) / 2).mean()
        return {"time": self.steps * self.cfg.dt, "energy_proxy": float(energy),
                "max_displacement": float(self.u.abs().max()),
                "memory_rms": float(self.p.square().mean().sqrt()),
                "fatigue_mean": float(self.z.mean()),
                "finite": bool(torch.isfinite(self.fields()).all())}
