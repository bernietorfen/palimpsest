"""PALIMPSEST's original material choir, connected by reciprocal wave bridges.

Run on RunPod. Each bridge is a finite mass-and-spring chain. Its endpoint
coordinates are spatial projections of the two materials; the matching force
footprints make body and bridge coupling derive from one quadratic potential.
This does not imply passivity of the complete active, plastic instrument.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch

from studio.batched_material import BatchedMaterial
from studio.material import MaterialConfig


@dataclass(frozen=True)
class Port:
    body: int
    x: float
    y: float
    width: float = .12

    def __post_init__(self):
        if not isinstance(self.body, int) or self.body < 0:
            raise ValueError('A port needs a nonnegative body index')
        if not all(math.isfinite(v) for v in (self.x, self.y, self.width)):
            raise ValueError('Non-finite port geometry')
        if not (0 <= self.x < 1 and 0 <= self.y < 1 and .04 <= self.width <= .3):
            raise ValueError('Port coordinates or width are outside the supported chart')


@dataclass(frozen=True)
class Bridge:
    first: Port
    second: Port
    tension: float = 1.2
    mass: float = .65
    damping: float = .24

    def __post_init__(self):
        if self.first.body == self.second.body:
            raise ValueError('A bridge must join two different bodies')
        if not all(math.isfinite(v) for v in (self.tension, self.mass, self.damping)):
            raise ValueError('Non-finite bridge constants')
        if not (.02 <= self.tension <= 8 and .1 <= self.mass <= 4 and 0 <= self.damping <= 4):
            raise ValueError('Bridge constants are outside the explored operating range')


def port_footprint(port: Port, size: int, *, device, dtype):
    coordinate = torch.arange(size, device=device, dtype=dtype) / size
    y, x = torch.meshgrid(coordinate, coordinate, indexing='ij')
    dx = torch.remainder(x - port.x + .5, 1) - .5
    dy = torch.remainder(y - port.y + .5, 1) - .5
    footprint = torch.exp(-(dx.square() + dy.square()) / (2 * port.width ** 2))
    return footprint / footprint.square().mean().sqrt()


class WaveBridges:
    def __init__(self, config: MaterialConfig, bodies: int, bridges: tuple[Bridge, ...], beads: int = 16):
        if not 4 <= beads <= 64 or not 1 <= bodies <= 32:
            raise ValueError('The choir supports 1–32 bodies and 4–64 beads per bridge')
        if any(max(edge.first.body, edge.second.body) >= bodies for edge in bridges):
            raise ValueError('A bridge names a body outside the choir')
        if len(bridges) > 96:
            raise ValueError('The bridge inventory exceeds the supported scene size')
        self.config, self.bodies, self.bridges, self.beads = config, bodies, tuple(bridges), beads
        self.device, self.dtype = torch.device(config.device), getattr(torch, config.dtype)
        self.count = len(bridges)
        self.u = torch.zeros((self.count, beads), device=self.device, dtype=self.dtype)
        self.v = torch.zeros_like(self.u)
        self.spring = torch.tensor([e.tension * (beads + 1) for e in bridges], device=self.device, dtype=self.dtype)
        self.mass = torch.tensor([e.mass / beads for e in bridges], device=self.device, dtype=self.dtype)
        self.damping = torch.tensor([e.damping for e in bridges], device=self.device, dtype=self.dtype)
        # Conservative explicit bound on a free bridge's highest angular frequency.
        # Endpoint/material modes are separately checked by numerical admission.
        if self.count and float((4 * self.spring / self.mass).sqrt().max()) * config.dt >= 1.5:
            raise ValueError('The bridge lattice is too stiff for the selected timestep')
        n = config.size
        self.ports = tuple(port for edge in bridges for port in (edge.first, edge.second))
        if self.ports:
            self.footprints = torch.stack([port_footprint(p, n, device=self.device, dtype=self.dtype) for p in self.ports])
        else:
            self.footprints = torch.empty((0, n, n), device=self.device, dtype=self.dtype)
        self.body_indices = torch.tensor([p.body for p in self.ports], device=self.device, dtype=torch.long)
        # A dense, tiny port map avoids nondeterministic CUDA index-add atomics.
        self.force_map = torch.zeros((bodies, n, n, len(self.ports)), device=self.device, dtype=self.dtype)
        for i, port in enumerate(self.ports):
            self.force_map[port.body, :, :, i] = self.footprints[i]
        self.force_map = self.force_map.reshape(bodies * n * n, len(self.ports))
        self.zeros = torch.zeros((bodies, n, n), device=self.device, dtype=self.dtype)

    def coordinates(self, field):
        return (field[self.body_indices] * self.footprints).mean(dim=(-2, -1)).reshape(self.count, 2)

    def evaluate(self, body_u, gates):
        """Forces from a single old state; caller then advances both subsystems."""
        if gates.shape != (self.count,):
            raise ValueError('One connection strength is required per bridge')
        endpoints = self.coordinates(body_u)
        chain = torch.cat((endpoints[:, :1], self.u, endpoints[:, 1:]), dim=1)
        k = self.spring * gates
        acceleration = (chain[:, :-2] - 2 * chain[:, 1:-1] + chain[:, 2:]) * (k / self.mass)[:, None]
        endpoint_force = torch.stack((self.u[:, 0] - endpoints[:, 0], self.u[:, -1] - endpoints[:, 1]), dim=1) * k[:, None]
        force = (self.force_map @ endpoint_force.reshape(-1)).reshape_as(body_u) if self.count else self.zeros
        return force, acceleration, endpoints, endpoint_force

    def advance(self, acceleration):
        dt = self.config.dt
        self.v = (self.v + dt * acceleration) / (1 + dt * self.damping[:, None])
        self.u = self.u + dt * self.v

    def energy(self, body_u, gates):
        endpoints = self.coordinates(body_u)
        chain = torch.cat((endpoints[:, :1], self.u, endpoints[:, 1:]), dim=1)
        potential = .5 * self.spring * gates * torch.diff(chain, dim=1).square().sum(dim=1)
        kinetic = .5 * self.mass * self.v.square().sum(dim=1)
        return {'potential': potential, 'kinetic': kinetic,
                'dissipation_rate': self.mass * self.damping * self.v.square().sum(dim=1)}

    def reset_motion(self, body_u):
        endpoints = self.coordinates(body_u)
        t = torch.arange(1, self.beads + 1, device=self.device, dtype=self.dtype) / (self.beads + 1)
        self.u = endpoints[:, :1] * (1 - t) + endpoints[:, 1:] * t
        self.v.zero_()


class MaterialChoir:
    def __init__(self, config: MaterialConfig, bodies: int, bridges: tuple[Bridge, ...] = (), *, beads: int = 16):
        self.config, self.bodies = config, bodies
        self.material = BatchedMaterial(config, bodies)
        self.wave = WaveBridges(config, bodies, tuple(bridges), beads)
        self.gates = torch.ones(len(bridges), device=self.material.device, dtype=self.material.dtype)
        self.last_endpoint_force = torch.zeros((len(bridges), 2), device=self.material.device, dtype=self.material.dtype)

    @property
    def time(self):
        return self.material.steps * self.config.dt

    def set_connections(self, values):
        value = torch.as_tensor(values, device=self.material.device, dtype=self.material.dtype)
        if value.shape != self.gates.shape or not bool(torch.isfinite(value).all()) or bool(((value < 0) | (value > 1)).any()):
            raise ValueError('Connection strengths must lie between zero and one')
        self.gates = value.clone()

    @torch.no_grad()
    def step(self, excitation, *, contact_force=None):
        force, acceleration, _, endpoint_force = self.wave.evaluate(self.material.u, self.gates)
        if contact_force is not None:
            if contact_force.shape != force.shape:
                raise ValueError('Contact forces must match all body fields')
            force = force + contact_force
        # Both force calculations precede either subsystem's state update.
        self.material.step(excitation, field_force=force if self.wave.count or contact_force is not None else None)
        self.wave.advance(acceleration)
        self.last_endpoint_force = endpoint_force

    def fields(self):
        m = self.material
        return torch.stack((m.u, m.p, m.z, m.v), dim=-1)

    def readout(self):
        m = self.material
        memory, fatigue, pitch = m.tuning()
        position, velocity = m.project(m.u), m.project(m.v)
        strain = position - memory
        return {'memory': memory, 'fatigue': fatigue, 'pitch_hz': pitch,
                'position': position, 'velocity': velocity, 'strain': strain,
                'amplitude': torch.sqrt(velocity.square() + .55 * strain.square() + 1e-12)}

    def reset_transients(self, *, reset_clock=True):
        steps, index = self.material.steps, self.material.index
        self.material.reset_transients()
        if not reset_clock:
            self.material.steps, self.material.index = steps, index
        self.wave.reset_motion(self.material.u)
        self.last_endpoint_force.zero_()

    def diagnostics(self):
        m = self.material
        return {'time': self.time, 'finite': m.finite() and bool(torch.isfinite(self.wave.u).all()) and bool(torch.isfinite(self.wave.v).all()),
                'memory_rms': m.p.square().mean(dim=(-2, -1)).sqrt().cpu().tolist(),
                'fatigue_mean': m.z.mean(dim=(-2, -1)).cpu().tolist(),
                'max_displacement': m.u.abs().amax(dim=(-2, -1)).cpu().tolist(),
                'bridge_peak': float(self.wave.u.abs().max()) if self.wave.count else 0.,
                'bridge_energy': {key: value.cpu().tolist() for key, value in self.wave.energy(m.u, self.gates).items()}}

    def state_dict(self):
        m = self.material
        return {'format': 'palimpsest-choir', 'version': 1, 'config': asdict(self.config),
                'bodies': self.bodies, 'bridges': [asdict(e) for e in self.wave.bridges], 'beads': self.wave.beads,
                'steps': m.steps, 'index': m.index,
                'material': {name: getattr(m, name).detach().cpu().clone() for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase')},
                'bridge_u': self.wave.u.detach().cpu().clone(), 'bridge_v': self.wave.v.detach().cpu().clone(),
                'gates': self.gates.detach().cpu().clone()}

    def load_state_dict(self, state):
        if state.get('format') != 'palimpsest-choir' or state.get('version') != 1:
            raise ValueError('Unsupported choir state')
        expected = self.state_dict()
        for key in ('config', 'bodies', 'bridges', 'beads'):
            if state.get(key) != expected[key]:
                raise ValueError(f'Choir configuration differs at {key}')
        if not isinstance(state.get('steps'), int) or state['steps'] < 0 or not isinstance(state.get('index'), int) or not 0 <= state['index'] < self.material.delay_steps:
            raise ValueError('Invalid material clock')
        staged = {}
        for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase'):
            value = state['material'][name].to(device=self.material.device, dtype=self.material.dtype)
            if value.shape != getattr(self.material, name).shape or not bool(torch.isfinite(value).all()):
                raise ValueError(f'Invalid saved material field: {name}')
            staged[name] = value.clone()
        wave_values = {}
        for key, reference in (('bridge_u', self.wave.u), ('bridge_v', self.wave.v), ('gates', self.gates)):
            value = state[key].to(device=self.material.device, dtype=self.material.dtype)
            if value.shape != reference.shape or not bool(torch.isfinite(value).all()):
                raise ValueError(f'Invalid saved bridge field: {key}')
            wave_values[key] = value.clone()
        if bool((staged['p'].abs() > self.config.memory_limit).any()) or bool(((staged['z'] < 0) | (staged['z'] > 1)).any()) or bool(((wave_values['gates'] < 0) | (wave_values['gates'] > 1)).any()):
            raise ValueError('Retained state or connection strength is out of bounds')
        for name, value in staged.items():
            setattr(self.material, name, value)
        self.wave.u, self.wave.v, self.gates = wave_values['bridge_u'], wave_values['bridge_v'], wave_values['gates']
        self.material.steps, self.material.index = state['steps'], state['index']
        self.last_endpoint_force.zero_()


def ring_choir(tension=1.2):
    """An authored seven-body score topology, including a central voice."""
    bridges = []
    for i in range(6):
        a = i * math.tau / 6
        bridges.append(Bridge(Port(0, .5 + .25 * math.cos(a), .5 + .25 * math.sin(a)),
                              Port(i + 1, .22, .5), tension=tension))
    for i in range(6):
        bridges.append(Bridge(Port(i + 1, .7, .28), Port((i + 1) % 6 + 1, .7, .72), tension=tension * .65))
    return tuple(bridges)
