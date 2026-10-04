"""Mechanical and causal admission of the new choir. Execute on RunPod."""
import torch
import pytest

from studio.batched_material import BatchedMaterial
from studio.choir_material import Bridge, MaterialChoir, Port, WaveBridges
from studio.material import MaterialConfig


def config(**options):
    return MaterialConfig(size=32, device='cpu', dtype='float64', feedback=.08, **options)


def edge():
    return Bridge(Port(0, .19, .37), Port(1, .71, .53), tension=1.2)


def test_disconnected_choir_preserves_original_trajectory():
    c = config()
    original = BatchedMaterial(c, 2)
    choir = MaterialChoir(c, 2, (edge(),), beads=8)
    choir.set_connections([0])
    for step in range(240):
        drive = torch.zeros((2, 12), dtype=torch.float64)
        drive[0, step // 60] = .4
        drive[1, (step // 40 + 3) % 12] = -.27
        original.step(drive)
        choir.step(drive)
    for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase'):
        assert torch.equal(getattr(original, name), getattr(choir.material, name)), name


def test_bridge_forces_are_negative_gradient_of_one_potential():
    c = config()
    bridge = WaveBridges(c, 2, (edge(),), beads=8)
    rng = torch.Generator().manual_seed(2026100408)
    body = (torch.randn((2, 32, 32), generator=rng, dtype=torch.float64) * .1).requires_grad_()
    bridge.u = (torch.randn((1, 8), generator=rng, dtype=torch.float64) * .04).requires_grad_()
    gates = torch.tensor([.7], dtype=torch.float64)
    force, acceleration, _, _ = bridge.evaluate(body, gates)
    potential = bridge.energy(body, gates)['potential'].sum()
    body_gradient, bridge_gradient = torch.autograd.grad(potential, (body, bridge.u))
    # The material kinetic energy and work use a spatial mean, not a sum.
    torch.testing.assert_close(force, -body_gradient * 32 ** 2, rtol=1e-13, atol=2e-14)
    torch.testing.assert_close(acceleration * bridge.mass[:, None], -bridge_gradient, rtol=1e-13, atol=2e-14)


def test_bridge_power_balances_for_arbitrary_body_and_chain_motion():
    c = config()
    bridge = WaveBridges(c, 2, (edge(),), beads=8)
    rng = torch.Generator().manual_seed(2026100409)
    u = torch.randn((2, 32, 32), generator=rng, dtype=torch.float64) * .1
    v = torch.randn((2, 32, 32), generator=rng, dtype=torch.float64) * .2
    bridge.u = torch.randn((1, 8), generator=rng, dtype=torch.float64) * .04
    bridge.v = torch.randn((1, 8), generator=rng, dtype=torch.float64) * .06
    gates = torch.tensor([.6], dtype=torch.float64)
    force, acceleration, ends, _ = bridge.evaluate(u, gates)
    end_speed = bridge.coordinates(v)
    chain = torch.cat((ends[:, :1], bridge.u, ends[:, 1:]), dim=1)
    speed = torch.cat((end_speed[:, :1], bridge.v, end_speed[:, 1:]), dim=1)
    potential_rate = (bridge.spring * gates * (torch.diff(chain, dim=1) * torch.diff(speed, dim=1)).sum(dim=1)).sum()
    body_power = (force * v).mean(dim=(-2, -1)).sum()
    bridge_power = (acceleration * bridge.mass[:, None] * bridge.v).sum()
    assert abs(float(potential_rate + body_power + bridge_power)) < 2e-14
    assert float(bridge.energy(u, gates)['dissipation_rate'].sum()) > 0


def test_a_wave_cannot_skip_the_bridge_in_one_step():
    choir = MaterialChoir(config(feedback_delay=.1), 2, (edge(),), beads=4)
    drive = torch.zeros((2, 12), dtype=torch.float64)
    drive[0, 0] = .5
    for _ in range(5):
        choir.step(drive)
        assert torch.count_nonzero(choir.material.u[1]) == 0
        assert torch.count_nonzero(choir.material.p[1]) == 0
    choir.step(drive)
    assert torch.count_nonzero(choir.material.u[1]) > 0
    assert torch.count_nonzero(choir.material.u[0]) > 0


def test_checkpoint_continues_every_body_and_bridge_exactly():
    c = config()
    first = MaterialChoir(c, 2, (edge(),), beads=8)
    drive = torch.zeros((2, 12), dtype=torch.float64)
    drive[0, 2] = .43
    for _ in range(160):
        first.step(drive)
    first.set_connections([.36])
    second = MaterialChoir(c, 2, (edge(),), beads=8)
    second.load_state_dict(first.state_dict())
    for _ in range(40):
        first.step(drive)
        second.step(drive)
    for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase'):
        assert torch.equal(getattr(first.material, name), getattr(second.material, name)), name
    assert torch.equal(first.wave.u, second.wave.u)
    assert torch.equal(first.wave.v, second.wave.v)
    assert first.time == second.time


def test_bad_checkpoint_cannot_partly_replace_an_existing_choir():
    choir = MaterialChoir(config(), 2, (edge(),), beads=8)
    drive = torch.zeros((2, 12), dtype=torch.float64)
    drive[0, 1] = .3
    for _ in range(20):
        choir.step(drive)
    old = choir.state_dict()
    bad = choir.state_dict()
    bad['material']['u'].zero_()
    bad['bridge_v'][0, 0] = float('nan')
    with pytest.raises(ValueError):
        choir.load_state_dict(bad)
    assert torch.equal(old['material']['u'], choir.material.u)
    assert torch.equal(old['bridge_v'], choir.wave.v)
