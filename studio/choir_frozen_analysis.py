"""Equilibrium and contraction checks in a declared modal Galerkin reduction.

Run on RunPod. Thirteen body coordinates (constant plus our twelve patterns)
and all 192 bridge beads are retained. This is not a full-grid spectral result.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from scipy import linalg,optimize
import torch
from studio.material import MaterialConfig,PalimpsestMaterial,laplacian
from studio.choir_material import port_footprint
from studio.choir_scene import load_scene,bridge_specs
from studio.preserve import sha256


def main(args):
    torch.set_num_threads(2);root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    sources=('studio/choir_frozen_analysis.py','studio/material.py','studio/choir_material.py','studio/choir_scene.py','research/CHOIR-ENERGY.md','site/choir-scene.json')
    hashes={}
    for relative in sources:
        target=root/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    scene=load_scene();cfg=MaterialConfig(size=64,device='cpu',dtype='float64',feedback=0.)
    reference=PalimpsestMaterial(cfg)
    basis=torch.cat((torch.ones((1,64,64),dtype=torch.float64),reference.modes),dim=0)
    B=basis.reshape(13,-1).numpy().T;AB=(-laplacian(basis)*(64/128)**2).reshape(13,-1).numpy().T
    gram=B.T@B/4096;linear=cfg.tension*(B.T@AB)/4096+cfg.bending*(AB.T@AB)/4096
    state=np.load(args.state);p=state['p'].astype(np.float64).reshape(7,-1);z=state['z'].astype(np.float64).reshape(7,-1)
    kappa=cfg.stiffness*(1-.58*z);beads=16;body_count=7*13;count=body_count+12*beads
    M=np.zeros((count,count));C=np.zeros_like(M);K=np.zeros_like(M)
    for body in range(7):
        s=slice(body*13,(body+1)*13);M[s,s]=gram;C[s,s]=gram*cfg.damping;K[s,s]=linear
    incidence=[];stiffness=[]
    for edge_index,edge in enumerate(bridge_specs(scene)):
        def endpoint(port):
            f=port_footprint(port,64,device='cpu',dtype=torch.float64).numpy().ravel();a=np.zeros(count);a[port.body*13:(port.body+1)*13]=f@B/4096;return a
        chain=[endpoint(edge.first)]
        for bead in range(beads):
            index=body_count+edge_index*beads+bead;a=np.zeros(count);a[index]=1;chain.append(a);M[index,index]=edge.mass/beads;C[index,index]=edge.mass/beads*edge.damping
        chain.append(endpoint(edge.second))
        for a,b in zip(chain[:-1],chain[1:]):incidence.append(b-a);stiffness.append(edge.tension*(beads+1))
    D=np.asarray(incidence);spring=D.T@(np.asarray(stiffness)[:,None]*D);K+=spring
    def energy(q):
        result=.5*q@K@q
        for body in range(7):
            d=B@q[body*13:(body+1)*13]-p[body];result+=np.mean(.5*kappa[body]*d*d+cfg.cubic/4*d**4)
        return float(result)
    def gradient(q):
        result=K@q
        for body in range(7):
            s=slice(body*13,(body+1)*13);d=B@q[s]-p[body];result[s]+=B.T@(kappa[body]*d+cfg.cubic*d**3)/4096
        return result
    def hessian(q):
        result=K.copy()
        for body in range(7):
            s=slice(body*13,(body+1)*13);d=B@q[s]-p[body];result[s,s]+=B.T@((kappa[body]+3*cfg.cubic*d*d)[:,None]*B)/4096
        return result
    seed=np.zeros(count)
    for body in range(7):seed[body*13:(body+1)*13]=linalg.solve(gram,B.T@p[body]/4096,assume_a='pos')
    solved=optimize.minimize(energy,seed,method='trust-exact',jac=gradient,hess=hessian,options={'gtol':1e-10,'maxiter':100})
    q=solved.x;H=hessian(q);residual=float(np.max(np.abs(gradient(q))));assert residual<1e-8,(solved.message,residual)
    I=np.eye(count);zero=np.zeros_like(I);MiH=linalg.solve(M,H,assume_a='pos');MiC=linalg.solve(M,C,assume_a='pos')
    G=np.block([[zero,I],[-MiH,-MiC]]);P=linalg.block_diag(H,M)
    identity=G.T@P+P@G-linalg.block_diag(zero,-2*C);identity_error=float(np.max(np.abs(identity)));assert identity_error<1e-11
    frequencies=linalg.eigvalsh(H,M);eigenvalues=linalg.eigvals(G);assert frequencies.min()>0;assert eigenvalues.real.max()<0
    h=1/96;decay=linalg.solve(I+h*MiC,I)
    T=np.block([[I-h*h*decay@MiH,h*decay],[-h*decay@MiH,decay]])
    spectral_radius=float(np.max(np.abs(linalg.eigvals(T))));assert spectral_radius<1
    # The finite integrator has its own contraction metric. Do not substitute
    # the continuous mechanical energy metric for this discrete assertion.
    Pd=linalg.solve_discrete_lyapunov(T.T,np.eye(2*count),method='bilinear')
    discrete_error=float(np.max(np.abs(T.T@Pd@T-Pd+np.eye(2*count))));minimum_metric=float(linalg.eigvalsh(Pd,subset_by_index=[0,0])[0])
    assert discrete_error<1e-6;assert minimum_metric>0
    rng=np.random.default_rng(20261004);direction=rng.normal(size=count);direction/=np.linalg.norm(direction);at=q+.2*direction;epsilon=1e-5
    finite_gradient=(energy(at+epsilon*direction)-energy(at-epsilon*direction))/(2*epsilon)
    gradient_error=abs(finite_gradient-gradient(at)@direction);assert gradient_error<1e-8
    np.savez_compressed(root/'matrices.npz',equilibrium=q,mass=M,damping=C,hessian=H,generator=G,step=T,discrete_metric=Pd,eigenvalues=eigenvalues,generalized_stiffness=frequencies)
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'state':args.state,'state_sha256':sha256(Path(args.state)),'source_sha256':hashes,
            'bodies':7,'body_coordinates_each':13,'bridge_beads':192,'position_coordinates':count,'mechanical_state_dimension':2*count,
            'equilibrium_max_gradient':residual,'energy_gradient_directional_error':float(gradient_error),
            'generalized_stiffness_minimum':float(frequencies.min()),'generalized_stiffness_maximum':float(frequencies.max()),
            'generator_largest_real_part':float(eigenvalues.real.max()),'continuous_energy_identity_max_error':identity_error,
            'step_seconds':h,'discrete_spectral_radius':spectral_radius,'discrete_lyapunov_max_residual':discrete_error,'discrete_metric_min_eigenvalue':minimum_metric,
            'scope':'Declared 13-mode-per-body Galerkin reduction at the 228-second retained fields, with every bridge reconnected at full strength, feedback/drive disabled, and p,z frozen. Algebraic continuous-energy identity and independently constructed discrete contraction metric. Not a full-grid spectrum, a claim about active plastic dynamics, or a universal recurrence theorem.'}
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inventory=[{'path':str(path.relative_to(root)),'bytes':path.stat().st_size,'sha256':sha256(path)} for path in sorted(root.rglob('*')) if path.is_file()]
    (root/'manifest.json').write_text(json.dumps({'files':inventory},indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--state',default='artifacts/studies/choir-performance-001/state-228.npz');parser.add_argument('--output',default='artifacts/studies/choir-frozen-001');main(parser.parse_args())
