"""The frozen energy gradient must reproduce both actual integrator forces."""
import torch
from studio.material import MaterialConfig,laplacian
from studio.choir_material import MaterialChoir,Bridge,Port


def test_frozen_total_potential_gradient_matches_actual_body_and_bead_update():
    config=MaterialConfig(size=16,device='cpu',dtype='float64',feedback=0,write_rate=0,
                          forgetting=0,memory_diffusion=0,fatigue_rate=0,fatigue_recovery=0)
    links=(Bridge(Port(0,.21,.37,.16),Port(1,.72,.53,.16),tension=1.6),
           Bridge(Port(1,.58,.50,.16),Port(2,.71,.53,.16),tension=1.04))
    choir=MaterialChoir(config,3,links,beads=16);choir.set_connections([.6,.85]);m=choir.material;w=choir.wave
    rng=torch.Generator().manual_seed(202610040935)
    random=lambda shape,scale:torch.randn(shape,generator=rng,dtype=torch.float64)*scale
    m.u=random((3,16,16),.25);m.v=random(m.u.shape,.12);m.p=random(m.u.shape,.08)
    m.z=torch.rand(m.u.shape,generator=rng,dtype=torch.float64)*.85
    w.u=random(w.u.shape,.11);w.v=random(w.v.shape,.07)
    body=m.u.clone().requires_grad_();beads=w.u.clone().requires_grad_()
    A=-laplacian(body)*(16/128)**2;d=body-m.p;kappa=config.stiffness*(1-.58*m.z)
    potential=(config.tension/2*(body*A).mean(dim=(-2,-1))+config.bending/2*A.square().mean(dim=(-2,-1))
               +(.5*kappa*d.square()+config.cubic/4*d.pow(4)).mean(dim=(-2,-1))).sum()
    ends=(body[w.body_indices]*w.footprints).mean(dim=(-2,-1)).reshape(2,2)
    chain=torch.cat((ends[:,:1],beads,ends[:,1:]),dim=1)
    potential=potential+(.5*w.spring*choir.gates*torch.diff(chain,dim=1).square().sum(dim=1)).sum()
    grad_body,grad_beads=torch.autograd.grad(potential,(body,beads))
    expected_body=-grad_body*16**2;expected_beads=-grad_beads/w.mass[:,None]
    old_body_v=m.v.clone();old_bead_v=w.v.clone();p=m.p.clone();z=m.z.clone()
    choir.step(torch.zeros((3,12),dtype=torch.float64))
    actual_body=(m.v*(1+config.dt*config.damping)-old_body_v)/config.dt
    actual_beads=(w.v*(1+config.dt*w.damping[:,None])-old_bead_v)/config.dt
    torch.testing.assert_close(actual_body,expected_body,atol=3e-13,rtol=3e-13)
    torch.testing.assert_close(actual_beads,expected_beads,atol=3e-12,rtol=3e-13)
    assert torch.equal(m.p,p) and torch.equal(m.z,z)
    energy_rate=(grad_body*old_body_v).sum()+(grad_beads*old_bead_v).sum()
    energy_rate+=((expected_body-config.damping*old_body_v)*old_body_v).mean(dim=(-2,-1)).sum()
    energy_rate+=(w.mass[:,None]*(expected_beads-w.damping[:,None]*old_bead_v)*old_bead_v).sum()
    dissipation=config.damping*old_body_v.square().mean(dim=(-2,-1)).sum()+(w.mass*w.damping*old_bead_v.square().sum(dim=1)).sum()
    torch.testing.assert_close(energy_rate,-dissipation,atol=3e-13,rtol=3e-13)
