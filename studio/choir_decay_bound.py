"""Check the declared full-grid decay bound; perform no new material training."""
import argparse
from datetime import datetime,timezone
import json,math
from fractions import Fraction
from pathlib import Path
import numpy as np
import torch
from studio.material import MaterialConfig,PalimpsestMaterial,laplacian
from studio.choir_material import Port,port_footprint
from studio.preserve import sha256


def constants(mu,gamma,Gamma):
    epsilon=min(2*gamma/3,math.sqrt(mu)/2)
    a=1-epsilon/math.sqrt(mu);b=1+epsilon/math.sqrt(mu)+epsilon*Gamma/mu
    beta=min(2*(gamma-epsilon),epsilon);rate=beta/b;factor=b/a
    return dict(mu=mu,gamma=gamma,Gamma=Gamma,epsilon=epsilon,a=a,b=b,beta=beta,rate_per_second=rate,prefactor=factor,one_percent_energy_bound_seconds=math.log(factor/.01)/rate,energy_fraction_ceiling_at_60_seconds=min(1,factor*math.exp(-60*rate)))


def main(args):
    output=Path(args.output)
    if output.exists():raise FileExistsError(output)
    torch.set_num_threads(2);dtype=torch.float64
    scene=json.loads(Path('site/choir-scene.json').read_text());cfg=MaterialConfig(size=64,device='cpu',dtype='float64',feedback=0.)
    edges=scene['connections'];beads=scene['bridge']['beads'];mass=scene['bridge']['mass'];damping=scene['bridge']['damping'];bodies=len(scene['bodies']);assert bodies==7 and beads==16 and cfg.buckling==0
    assert cfg.damping==.38 and damping==.24, 'The exact rate certificates require the declared damping constants'
    assert cfg.tension>=0 and cfg.bending>=0 and cfg.cubic>=0
    degree=np.zeros(bodies)
    for edge in edges:
        for name in ('first','second'):degree[edge[name][0]]+=mass
    kappa=cfg.stiffness*(1-.58);chain_min=min(3*edge['tension']*(beads+1)/(mass*(beads+2)) for edge in edges);body_min=kappa/(1+degree.max());mu_bound=min(body_min,chain_min)
    assert mu_bound>.20 and kappa>1
    joined=constants(.20,min(cfg.damping,damping),max(cfg.damping,damping));separate=constants(1.,cfg.damping,cfg.damping)
    # Exact rational certificates for readable, conservatively rounded bounds.
    F=Fraction;root_upper=F(2237,1000)
    assert root_upper**2>5 and F(2236,1000)**2<5
    assert F(20)/(163+20*root_upper)>F(96,1000)
    assert (163+20*root_upper)/(125-20*root_upper)<F(259,100)
    assert F(950,5061)>F(187,1000) and F(5061,2800)<F(181,100)
    exact=[]
    for label,prefactor,rate,seconds in [('all-bridges',F(259,100),F(96,1000),60),('separate-bodies',F(181,100),F(187,1000),30)]:
        x=rate*seconds;lower=sum((x**k/F(math.factorial(k)) for k in range(13)),F(0))
        assert lower>100*prefactor
        exact.append({'scene':label,'rounded_prefactor':str(prefactor),'rounded_rate':str(rate),'seconds':seconds,'positive_exponential_series_terms':13,'exponential_lower_numerator':str(lower.numerator),'exponential_lower_denominator':str(lower.denominator),'strictly_below_one_percent':True})
    chain_checks=[]
    for count in (4,16,64):
        order=[0,*range(2,count+2),1];D=np.zeros((count+1,count+2))
        for row,(a,b) in enumerate(zip(order,order[1:])):D[row,a]=-1;D[row,b]=1
        Q=count*(count+2)/3*(D.T@D);Q[0,0]+=count;Q[1,1]+=count;Q[2:,2:]-=np.eye(count)
        minimum=float(np.linalg.eigvalsh(Q).min());assert minimum>=-1e-11
        chain_checks.append({'beads':count,'inequality_matrix_minimum_eigenvalue':minimum})
    rng=np.random.default_rng(202610041415);grid_checks=[]
    for size in (16,32,64):
        ports=[Port(*edge[name],scene['bridge']['port_width']) for edge in edges for name in ('first','second')]
        footprints=torch.stack([port_footprint(port,size,device='cpu',dtype=dtype) for port in ports]).numpy();port_bodies=np.asarray([port.body for port in ports]);spring=np.asarray([edge['tension']*(beads+1) for edge in edges])
        rms_error=float(np.max(np.abs(np.mean(footprints**2,axis=(1,2))-1)));ratios=[];chain_slack=[]
        coordinate=np.arange(size)/size;Y,X=np.meshgrid(coordinate,coordinate,indexing='ij');t=np.arange(1,beads+1)/(beads+1)
        for case in range(12):
            u=np.broadcast_to(rng.normal(size=(bodies,1,1)),(bodies,size,size)).copy()
            if case%3==1:
                u.fill(0)
                for port,f in zip(ports,footprints):u[port.body]+=rng.normal()*f
            if case%3==2:u+=rng.normal(size=(bodies,1,1))*np.cos(2*np.pi*X)+rng.normal(size=(bodies,1,1))*np.sin(2*np.pi*Y)
            ends=np.mean(u[port_bodies]*footprints,axis=(1,2)).reshape(-1,2)
            w=(1-t)*ends[:,:1]+t*ends[:,1:]+rng.normal(size=(len(edges),1))*np.sin(np.pi*t)
            differences=np.diff(np.concatenate((ends[:,:1],w,ends[:,1:]),axis=1),axis=1)
            B=np.sum(np.mean(u*u,axis=(1,2)));S=np.sum(spring*np.sum(differences**2,axis=1));W=mass/beads*np.sum(w*w);ratio=(kappa*B+S)/(B+W);assert ratio>=.20-1e-12;ratios.append(float(ratio))
            left=mass/beads*np.sum(w*w,axis=1);right=mass*np.sum(ends*ends,axis=1)+mass*(beads+2)/3*np.sum(differences**2,axis=1)
            assert np.min(right-left)>=-1e-11;chain_slack.append(float(np.min(right-left)))
        grid_checks.append({'grid':size,'cases':12,'port_rms_squared_max_error':rms_error,'minimum_baseline_hessian_mass_ratio':min(ratios),'minimum_chain_mass_slack':min(chain_slack)})
    # Independently reconstruct the nonlinear reduced potential from full fields.
    saved=np.load('artifacts/studies/choir-frozen-001/matrices.npz');state=np.load('artifacts/studies/choir-performance-001/state-228.npz')
    reference=PalimpsestMaterial(cfg);basis=torch.cat((torch.ones((1,64,64),dtype=dtype),reference.modes));p=torch.tensor(state['p'],dtype=dtype);z=torch.tensor(state['z'],dtype=dtype);stiffness=cfg.stiffness*(1-.58*z)
    assert torch.isfinite(p).all() and torch.isfinite(z).all() and z.min()>=0 and z.max()<=1
    footprints=torch.stack([port_footprint(Port(*edge[name],scene['bridge']['port_width']),64,device='cpu',dtype=dtype) for edge in edges for name in ('first','second')]);port_bodies=torch.tensor([edge[name][0] for edge in edges for name in ('first','second')]);spring=torch.tensor([edge['tension']*(beads+1) for edge in edges],dtype=dtype)
    M=torch.tensor(saved['mass'],dtype=dtype);C=torch.tensor(saved['damping'],dtype=dtype);qstar=torch.tensor(saved['equilibrium'],dtype=dtype);n=len(qstar)
    def potential(q):
        u=torch.einsum('bm,myx->byx',q[:bodies*13].reshape(bodies,13),basis);A=-laplacian(u)*(64/128)**2;d=u-p
        body=(cfg.tension/2*(u*A).mean(dim=(-2,-1))+cfg.bending/2*A.square().mean(dim=(-2,-1))+(.5*stiffness*d*d+cfg.cubic/4*d**4).mean(dim=(-2,-1))).sum()
        ends=(u[port_bodies]*footprints).mean(dim=(-2,-1)).reshape(-1,2);w=q[bodies*13:].reshape(-1,beads);chain=torch.cat((ends[:,:1],w,ends[:,1:]),dim=1)
        return body+(.5*spring*torch.diff(chain,dim=1).square().sum(dim=1)).sum()
    eq=qstar.clone().requires_grad_();Vstar=potential(eq);eq_gradient=torch.autograd.grad(Vstar,eq)[0];eq_error=float(eq_gradient.abs().max());assert eq_error<1e-8;Vstar=Vstar.detach()
    gram=basis.reshape(13,-1)@basis.reshape(13,-1).T/4096
    for body in range(bodies):torch.testing.assert_close(M[body*13:(body+1)*13,body*13:(body+1)*13],gram,atol=2e-15,rtol=2e-15)
    assert np.linalg.eigvalsh(saved['damping']-joined['gamma']*saved['mass']).min()>-1e-12
    assert np.linalg.eigvalsh(joined['Gamma']*saved['mass']-saved['damping']).min()>-1e-12
    trials=[]
    for case in range(26):
        eta=torch.tensor(rng.normal(size=n),dtype=dtype);v=torch.tensor(rng.normal(size=n),dtype=dtype)
        eta*=((.001,.05,.3,1.)[case%4]/torch.sqrt(eta@M@eta));v/=torch.sqrt(v@M@v)
        label='seeded-perturbation'
        if case==0:eta.zero_();v.zero_();v[bodies*13]=1/math.sqrt(mass/beads);label='pure-bead-velocity'
        elif case==1:eta.zero_();v.zero_();v[0]=1;label='pure-body-velocity'
        elif case%5==0:v.zero_();label='displacement-only'
        q=(qstar+eta).detach().requires_grad_();v=v.detach().requires_grad_();eta=q-qstar;U=potential(q)-Vstar;E=.5*v@M@v+U;eps=joined['epsilon'];L=E+eps*(eta@M@v)+eps/2*(eta@C@eta)
        gradient=torch.autograd.grad(U,q,retain_graph=True)[0];Lq,Lv=torch.autograd.grad(L,(q,v));acceleration=torch.linalg.solve(M,-C@v-gradient)
        direct=Lq@v+Lv@acceleration;identity=-v@C@v+eps*(v@M@v)-eps*(eta@gradient)
        scale=max(1.,float(E.detach()));residual=float((direct-identity).abs().detach())/scale
        lower=float((L-joined['a']*E).detach());upper=float((joined['b']*E-L).detach());dissipation=float((-joined['beta']*E-direct).detach());decay=float((-joined['rate_per_second']*L-direct).detach())
        assert residual<3e-12 and min(lower,upper,dissipation,decay)>-3e-12*scale,(case,residual,lower,upper,dissipation,decay)
        trials.append({'case':case,'kind':label,'energy':float(E.detach()),'modified_energy':float(L.detach()),'normalized_derivative_identity_error':residual,'lower_comparison_slack':lower,'upper_comparison_slack':upper,'dissipation_bound_slack':dissipation,'exponential_bound_slack':decay})
    inputs=['site/choir-scene.json','studio/material.py','studio/choir_material.py','studio/choir_decay_bound.py','research/CHOIR-ENERGY.md','research/CHOIR-DECAY.md','research/CHOIR-DECAY-PLAN.md','artifacts/studies/choir-frozen-001/matrices.npz','artifacts/studies/choir-performance-001/state-228.npz']
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'seed':202610041415,'input_sha256':{name:sha256(Path(name)) for name in inputs},'analytical_bounds':{'kappa_min':kappa,'maximum_incident_mass':float(degree.max()),'body_stiffness_bound':float(body_min),'chain_stiffness_bound':float(chain_min),'complete_stiffness_bound':float(mu_bound)},'fully_connected':joined,'separate_bodies':separate,'exact_rational_certificates':exact,'chain_checks':chain_checks,'full_grid_checks':grid_checks,'nonlinear_equilibrium_gradient_residual':eq_error,'nonlinear_checks':trials,'maximum_normalized_derivative_error':max(t['normalized_derivative_identity_error'] for t in trials),'scope':'Conservative analytical bound for frozen unforced continuous-time mechanics, independently checked against chain matrices, full-grid perturbations and the existing nonlinear Galerkin potential. The simple rounded rate and one-percent time certificates use exact rational arithmetic. Other numerical checks are not formal interval proofs, measured decay trajectories, finite-step guarantees or claims about the active artwork.'}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('input_sha256','nonlinear_checks')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='research/choir-decay-bound-001.json');main(parser.parse_args())
