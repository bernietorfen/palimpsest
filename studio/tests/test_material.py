"""Numerical/behavioral contracts. Execute these tests on RunPod only."""
from dataclasses import replace
import math

import pytest
import torch

from studio.material import MaterialConfig, PalimpsestMaterial, laplacian
from studio.score import Score


def cfg(**kwargs):
    return MaterialConfig(size=32, device="cpu", **kwargs)


def force(model, time):
    a = torch.zeros(12, dtype=model.dtype, device=model.device)
    if time < 2:
        a[2] = .3 * math.sin(math.pi * time / 2) ** 2
    return a


def test_periodic_laplacian_has_correct_fourier_eigenvalue():
    n, k = 32, 3
    x = torch.arange(n, dtype=torch.float64) * (2 * math.pi / n)
    a = torch.cos(k * x)[None].expand(n, -1)
    expected = -4 * math.sin(math.pi * k / n) ** 2 * a
    torch.testing.assert_close(laplacian(a), expected, atol=1e-13, rtol=1e-12)
    assert abs(float(laplacian(a).sum())) < 1e-11


def test_unforced_rest_is_exact_even_with_feedback_and_writing():
    m = PalimpsestMaterial(cfg())
    for _ in range(240):
        m.step(torch.zeros(12))
    assert torch.count_nonzero(m.fields()) == 0
    assert torch.count_nonzero(m.delay) == 0


def test_echo_has_no_effect_before_its_causal_delay():
    a = PalimpsestMaterial(cfg())
    b = PalimpsestMaterial(cfg(feedback=0))
    f = torch.zeros(12)
    f[3] = .3
    for _ in range(a.delay_steps):
        a.step(f)
        b.step(f)
    torch.testing.assert_close(a.fields(), b.fields(), rtol=0, atol=0)
    for _ in range(40):
        a.step(f)
        b.step(f)
    assert float((a.u - b.u).abs().max()) > 1e-6


def test_smaller_time_step_converges_for_unwritten_sheet():
    base = cfg(write_rate=0, fatigue_rate=0, feedback=0, dtype="float64")
    states = []
    for dt in (1 / 48, 1 / 96, 1 / 192):
        m = PalimpsestMaterial(replace(base, dt=dt))
        for k in range(round(4 / dt)):
            m.step(force(m, k * dt))
        states.append(m.u)
    coarse = torch.linalg.vector_norm(states[0] - states[2])
    fine = torch.linalg.vector_norm(states[1] - states[2])
    assert float(fine) < float(coarse) * .55


def test_checkpoint_preserves_delay_and_subsequent_response():
    a = PalimpsestMaterial(cfg())
    for k in range(220):
        a.step(force(a, k * a.cfg.dt))
    b = PalimpsestMaterial(cfg())
    b.load_state_dict(a.state_dict())
    for _ in range(180):
        a.step(torch.zeros(12))
        b.step(torch.zeros(12))
    torch.testing.assert_close(a.fields(), b.fields(), rtol=0, atol=0)
    assert a.index == b.index and a.steps == b.steps


def test_history_changes_pitch_after_excitation_ends():
    m = PalimpsestMaterial(cfg())
    before = m.readout()["pitch_hz"].clone()
    for k in range(500):
        m.step(force(m, k * m.cfg.dt))
    after = m.readout()["pitch_hz"]
    assert float(m.p.square().mean()) > 1e-5
    assert float((after - before).abs().max()) > .1
    assert m.diagnostics()["finite"]


def test_question_and_return_have_identical_excitation_and_controls():
    score = Score()
    for age in (0, .3, 1.4, 7.8, 17.2, 28.1, 40.2, 46):
        torch.testing.assert_close(torch.from_numpy(score.excitation(18 + age)),
                                   torch.from_numpy(score.excitation(370 + age)),
                                   rtol=1e-6, atol=1e-6)
        assert score.controls(18 + age) == score.controls(370 + age)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not present on remote worker")
def test_gpu_and_cpu_agree_on_written_trajectory():
    a = PalimpsestMaterial(cfg())
    b = PalimpsestMaterial(replace(cfg(), device="cuda"))
    for k in range(280):
        a.step(force(a, k * a.cfg.dt))
        b.step(force(b, k * b.cfg.dt))
    torch.testing.assert_close(a.fields(), b.fields().cpu(), rtol=3e-4, atol=5e-6)


def test_variable_tension_flux_is_conservative_and_reduces_to_laplacian():
    from studio.material import tension_force
    x = torch.arange(32, dtype=torch.float64)
    y, x = torch.meshgrid(x, x, indexing="ij")
    a = torch.sin(x * .31) * torch.cos(y * .27)
    constant = torch.full_like(a, 1.7)
    torch.testing.assert_close(tension_force(a, constant), 1.7 * laplacian(a),
                               atol=1e-13, rtol=1e-12)
    variable = torch.sin(x * .27 + y * .41) * 3 - .8
    assert abs(float(tension_force(a, variable).sum())) < 1e-11


def test_compression_variant_remains_finite_after_a_written_history():
    m = PalimpsestMaterial(cfg(buckling=6, bending=1.5))
    m.z.fill_(.8)
    for k in range(600):
        m.step(force(m, k * m.cfg.dt))
    assert m.diagnostics()["finite"]
    assert float(m.u.abs().max()) < 8


def test_signed_memory_distinguishes_opposite_inscriptions_with_equal_fatigue():
    a = PalimpsestMaterial(cfg())
    b = PalimpsestMaterial(cfg())
    a.p = a.modes[3] * .18
    b.p = -a.p
    a.z.fill_(.2)
    b.z.fill_(.2)
    pa = a.readout()["pitch_hz"]
    pb = b.readout()["pitch_hz"]
    assert float(pa[3] - pb[3]) > 25
    torch.testing.assert_close(a.readout()["fatigue"], b.readout()["fatigue"])


def test_retuning_twists_echo_and_changes_later_material_response():
    a = PalimpsestMaterial(cfg())
    b = PalimpsestMaterial(cfg(echo_twist=0))
    for m in (a, b):
        m.p = m.modes[2] * .16
        m.u = m.p.clone()
    for k in range(500):
        a.step(force(a, k * a.cfg.dt))
        b.step(force(b, k * b.cfg.dt))
    assert float(a.echo_phase.abs().max()) > .1
    assert torch.count_nonzero(b.echo_phase) == 0
    assert float((a.u-b.u).square().mean().sqrt()) > .005


def test_checkpoint_rejects_a_different_instrument_configuration():
    a = PalimpsestMaterial(cfg())
    b = PalimpsestMaterial(cfg(memory_tuning=.2))
    with pytest.raises(ValueError, match="memory_tuning"):
        b.load_state_dict(a.state_dict())
