"""Sheets of the original material, evaluated together on RunPod.

This research implementation preserves the scalar update order. It borrows the
authored patterns from the reference and must pass a scalar comparison before
being used for an experiment. Optional external spatial forces support the
second-act choir; absent those forces, the sheets remain independent. The
frozen first film and live edition retain their original implementations.
"""
import math
import torch

from studio.material import MaterialConfig, PalimpsestMaterial, laplacian


class BatchedMaterial:
    def __init__(self, config: MaterialConfig, count: int):
        if config.buckling != 0 or not 1 <= count <= 256:
            raise ValueError('This experiment supports 1–256 independent unbuckled sheets')
        self.cfg, self.count = config, count
        reference = PalimpsestMaterial(config)
        self.device, self.dtype = reference.device, reference.dtype
        for name in ('modes', 'readout_weights', 'echo_modes', 'echo_quadratures', 'base_pitches'):
            setattr(self, name, getattr(reference, name))
        shape = (count, config.size, config.size)
        for name in ('u', 'v', 'p', 'z'):
            setattr(self, name, torch.zeros(shape, device=self.device, dtype=self.dtype))
        self.delay_steps = reference.delay_steps
        self.delay = torch.zeros((self.delay_steps, count, 12), device=self.device, dtype=self.dtype)
        self.echo_phase = torch.zeros((count, 12), device=self.device, dtype=self.dtype)
        self.index, self.steps = 0, 0

    def project(self, field):
        # The same pointwise product and spatial mean as the scalar reference.
        # Reductions stay inside each independent sheet and voice.
        return (self.modes[None] * field[:, None]).mean(dim=(-2, -1))

    def tuning(self):
        memory = self.project(self.p)
        fatigue = (self.readout_weights[None] * self.z[:, None]).mean(dim=(-2, -1))
        pitch = self.base_pitches * torch.sqrt(1 - .58 * fatigue)
        return memory, fatigue, pitch * torch.exp(self.cfg.memory_tuning * memory)

    @torch.no_grad()
    def step(self, excitation, *, field_force=None):
        if excitation.shape != (self.count, 12):
            raise ValueError('Expected one twelve-voice force per material')
        c, dt = self.cfg, self.cfg.dt
        grid = (c.size / 128) ** 2
        difference = self.u - self.p
        stiffness = c.stiffness * (1 - .58 * self.z)
        lap = laplacian(self.u) * grid
        force = c.force_scale * torch.einsum('bm,mij->bij', excitation, self.modes)
        echo = torch.tanh(self.delay[self.index] / .18)
        force = force + c.feedback * (
            torch.einsum('bm,mij->bij', echo * torch.cos(self.echo_phase), self.echo_modes)
            + torch.einsum('bm,mij->bij', echo * torch.sin(self.echo_phase), self.echo_quadratures))
        if field_force is not None:
            if field_force.shape != self.u.shape:
                raise ValueError('External spatial force must match the material fields')
            force = force + field_force
        acceleration = (c.tension * lap - c.bending * laplacian(lap) * grid
                        - stiffness * difference - c.cubic * difference.pow(3) + force)
        self.v = (self.v + dt * acceleration) / (1 + dt * c.damping)
        self.u = self.u + dt * self.v
        strain = self.u - self.p
        excess = torch.relu(strain.abs() - c.yield_strain * (1 - .35 * self.z))
        write = c.write_rate * excess * torch.tanh(strain / .035)
        capacity = torch.clamp(1 - (self.p / c.memory_limit).square(), min=0)
        self.p = self.p + dt * (write * capacity - c.forgetting * self.p
                               + c.memory_diffusion * laplacian(self.p) * grid)
        self.p.clamp_(-c.memory_limit, c.memory_limit)
        self.z = self.z + dt * (c.fatigue_rate * excess.square() * (1 - self.z)
                               - c.fatigue_recovery * self.z)
        self.z.clamp_(0, 1)
        if c.echo_twist:
            pitch = self.tuning()[2]
            self.echo_phase = torch.remainder(self.echo_phase
                + dt * (2 * math.pi * c.echo_twist) * (pitch - self.base_pitches), 2 * math.pi)
        self.delay[self.index] = self.project(self.v)
        self.index = (self.index + 1) % self.delay_steps
        self.steps += 1

    def reset_transients(self):
        self.u = self.p.clone()
        self.v.zero_(); self.delay.zero_(); self.echo_phase.zero_()
        self.index, self.steps = 0, 0

    def finite(self):
        return all(bool(torch.isfinite(getattr(self, name)).all())
                   for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase'))
