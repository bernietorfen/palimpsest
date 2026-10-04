"""Measured second-act figures, assembled from frozen arrays on RunPod."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy import linalg
from studio.preserve import sha256

PAPER='#f1eddf';INK='#293e42';BLUE='#315d6b';OCHRE='#9c6338';MUTED='#74766a'


def style():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':INK,'axes.labelcolor':INK,
        'axes.edgecolor':'#bdb6a7','xtick.color':MUTED,'ytick.color':MUTED,'axes.spines.top':False,'axes.spines.right':False,
        'axes.facecolor':PAPER,'figure.facecolor':PAPER,'savefig.facecolor':PAPER,'grid.color':'#d9d2c3','grid.linewidth':.5})


def save(fig,root,name):
    fig.savefig(root/(name+'.png'),dpi=190,bbox_inches='tight',pad_inches=.18)
    fig.savefig(root/(name+'.pdf'),bbox_inches='tight',pad_inches=.18);plt.close(fig)


def main(args):
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False);style()
    source=root/'source/studio/choir_figures.py';source.parent.mkdir(parents=True);shutil.copy2(__file__,source)
    performance=Path('artifacts/studies/choir-performance-001');study=Path('artifacts/studies/choir-transfer-001');frozen=Path('artifacts/studies/choir-frozen-001')
    protocol=json.loads((performance/'protocol.json').read_text());scene=protocol['scene'];data=np.load(performance/'readouts.npz');t=data['time'];names=[b['name'] for b in scene['bodies']]
    fig,axes=plt.subplots(3,1,figsize=(12,7.4),sharex=True,gridspec_kw={'height_ratios':[1,1,2.2]},layout='constrained')
    for i,color in enumerate([BLUE,OCHRE,'#7b8b66']):axes[0].plot(t[::8],data['contact'][::8,i],color=color,lw=1.1,label=f'B / port {i+1}')
    axes[0].set(ylabel='Writing force');axes[0].legend(ncol=3,frameon=False,loc='upper left',fontsize=8)
    axes[1].plot(t[::8],data['gates'][::8,0],color=BLUE,label='Spokes',lw=1.3);axes[1].plot(t[::8],data['gates'][::8,6],color=OCHRE,label='Outer circle',lw=1.3);axes[1].set(ylabel='Connection',ylim=(-.06,1.2));axes[1].legend(ncol=2,frameon=False,loc='upper left',fontsize=8)
    pitch=data['pitch_hz'].astype(float);drift=np.sqrt(np.mean((pitch-pitch[0])**2,axis=2));colors=[BLUE,'#9e4c36','#477d83','#80865e','#b3ac9a','#99965b','#a56d35']
    for i,color in enumerate(colors):axes[2].plot(t[::8],drift[::8,i],color=color,lw=1.1,label=names[i])
    axes[2].set(ylabel='RMS tuning drift / Hz',xlabel='Performance time / seconds',xlim=(0,288));axes[2].legend(ncol=7,frameon=False,loc='upper left',fontsize=8)
    for ax in axes:
        ax.grid(axis='y');ax.axvspan(5,45,color=OCHRE,alpha=.07);ax.axvspan(248,288,color=OCHRE,alpha=.07);ax.axvline(242,color=INK,ls=':',lw=.8)
    save(fig,root,'the-score')
    state=np.load(performance/'state-228.npz');inscription=state['p'];wear=state['z'];cmap=LinearSegmentedColormap.from_list('inscription',['#9a3a25',PAPER,'#235269'])
    fig,axes=plt.subplots(2,7,figsize=(12,4.0),layout='constrained')
    for i,name in enumerate(names):
        top=axes[0,i].imshow(inscription[i],origin='lower',cmap=cmap,vmin=-.8,vmax=.8,interpolation='nearest');bottom=axes[1,i].imshow(wear[i],origin='lower',cmap='cividis',vmin=0,vmax=1,interpolation='nearest');axes[0,i].set_title(name+(' / source' if i==1 else ''),fontsize=10)
        for row in range(2):axes[row,i].set_xticks([]);axes[row,i].set_yticks([])
    axes[0,0].set_ylabel('Inscription p',fontsize=10);axes[1,0].set_ylabel('Wear z',fontsize=10)
    fig.colorbar(top,ax=axes[0],fraction=.025,pad=.015,ticks=[-.8,0,.8]);fig.colorbar(bottom,ax=axes[1],fraction=.025,pad=.015,ticks=[0,.5,1]);save(fig,root,'seven-retained-fields')
    records=[]
    for path in sorted(study.glob('rate-*/phrase-*/report.json')):
        report=json.loads(path.read_text())
        for outcome in report['outcomes']:records.append({'rate':report['rate'],'phrase':report['phrase'],**outcome})
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for index,receiver in enumerate((1,2)):
        ax=axes[index]
        for rate,marker,color in ((96,'o',BLUE),(192,'s',OCHRE)):
            rows=sorted([r for r in records if r['rate']==rate and r['receiver']==receiver],key=lambda r:r['phrase']);x=np.array([r['phrase'] for r in rows]);y=np.array([r['rms_hz']['connected'] for r in rows]);ax.plot(x,y,color=color,lw=.7,alpha=.8);ax.scatter(x,y,s=40 if rate==96 else 29,marker=marker,facecolors=PAPER if rate==192 else color,edgecolors=color,label=f'{rate} steps / second',zorder=3)
        ax.axhline(.01,color=INK,lw=.8,ls=':',label='Admission / 0.01 Hz');ax.set(title=f'Receiver {receiver}',xlabel='Held-out phrase',ylabel='Retained difference / Hz RMS',xticks=range(12),ylim=(0,None));ax.grid(axis='y');ax.legend(frameon=False,fontsize=8,loc='upper right')
    save(fig,root,'controlled-transfer')
    conditions=['connected','second-link-absent','inscription-erased','wear-erased','both-erased'];labels=['Connected','No second\nlink','p erased','z erased','Both\nerased']
    fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    ablations={}
    for row,rate in enumerate((96,192)):
        for column,receiver in enumerate((1,2)):
            ax=axes[row,column];rows=sorted([r for r in records if r['rate']==rate and r['receiver']==receiver],key=lambda r:r['phrase']);values=np.array([[r['rms_hz'][key] for key in conditions] for r in rows]);ablations[f'{rate}/{receiver}']={key:{'minimum':float(values[:,i].min()),'median':float(np.median(values[:,i])),'maximum':float(values[:,i].max())} for i,key in enumerate(conditions)}
            for i in range(5):
                jitter=(np.arange(12)-5.5)/40;ax.scatter(i+jitter,values[:,i],s=24,facecolors=PAPER if row else BLUE,edgecolors=OCHRE if row else BLUE,lw=.9,zorder=3);ax.plot([i-.23,i+.23],[np.median(values[:,i])]*2,color=INK,lw=1.1)
            ax.set(title=f'Receiver {receiver} / {rate} steps per second',ylabel='Difference from isolated / Hz RMS',xticks=range(5),xticklabels=labels,ylim=(-.06,None));ax.grid(axis='y');ax.tick_params(axis='x',labelsize=8)
    save(fig,root,'what-erasure-removes')
    # Saved matrix checks are independent of the generation report's numbers.
    matrices=np.load(frozen/'matrices.npz');M=matrices['mass'];C=matrices['damping'];H=matrices['hessian'];G=matrices['generator'];T=matrices['step'];P=linalg.block_diag(H,M);zero=np.zeros_like(M)
    identity_error=float(np.max(np.abs(G.T@P+P@G-linalg.block_diag(zero,-2*C))))
    assert identity_error<1e-11
    for matrix in (M,C,H):assert linalg.eigvalsh(matrix,subset_by_index=[0,0])[0]>0
    eig=linalg.eigvals(G);step_eig=linalg.eigvals(T);assert eig.real.max()<0 and np.abs(step_eig).max()<1
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    axes[0].scatter(eig.real,eig.imag,s=9,color=BLUE,alpha=.65);axes[0].axvline(0,color=INK,lw=.8);axes[0].set(xlabel='Real part / 1 second',ylabel='Imaginary part / 1 second',title='Mechanical generator',xlim=(-.23,.015));axes[0].grid()
    theta=np.linspace(-.7,.7,500);axes[1].plot(np.cos(theta),np.sin(theta),color='#b7b0a2',lw=1,label='Unit circle');axes[1].scatter(step_eig.real,step_eig.imag,s=9,color=BLUE,alpha=.65,label='Mechanical step');axes[1].scatter([1],[0],s=90,marker='+',lw=1.6,color=OCHRE,label='Frozen retained block');axes[1].set(xlabel='Real part',ylabel='Imaginary part',title='One 1/96-second step / enlarged',xlim=(.82,1.012),ylim=(-.55,.55));axes[1].grid();axes[1].legend(frameon=False,loc='upper left',fontsize=8)
    save(fig,root,'where-persistence-lives')
    # An actual bridge state: source B is the second endpoint of bridge zero.
    index=228*96;chain=np.r_[data['endpoints'][index,0,1],data['bridge_u'][index,0,::-1],data['endpoints'][index,0,0]]
    fig=plt.figure(figsize=(12,4.6));grid=fig.add_gridspec(1,3,width_ratios=[1,1.7,1],wspace=.35);axes=[fig.add_subplot(grid[i]) for i in range(3)]
    for axis,body,title,point in ((axes[0],1,'Source B',(.22,.5)),(axes[2],0,'Receiver A',(.75,.5))):
        axis.imshow(inscription[body],origin='lower',extent=(0,1,0,1),vmin=-.8,vmax=.8,cmap=cmap,interpolation='nearest');axis.add_patch(plt.Circle(point,.16,edgecolor=OCHRE,facecolor='none',lw=1.4));axis.set(title=title,xlabel='Periodic chart x',ylabel='Periodic chart y',xticks=[0,.5,1],yticks=[0,.5,1])
    axes[1].plot(np.linspace(0,1,18),chain,color=BLUE,lw=1.3);axes[1].scatter(np.linspace(0,1,18)[1:-1],chain[1:-1],s=20,color=BLUE);axes[1].scatter([0,1],chain[[0,-1]],s=40,facecolors=PAPER,edgecolors=OCHRE);axes[1].set(title='Sixteen beads / actual state at 228 s',xlabel='Normalized bridge coordinate',ylabel='Displacement');axes[1].grid(axis='y');save(fig,root,'the-reciprocal-bridge')
    inputs={str(p):sha256(p) for p in (performance/'manifest.json',study/'manifest.json',frozen/'manifest.json')}
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha256(Path(__file__)),'input_manifests':inputs,'receiver_cases':len(records),'ablations':ablations,'frozen_matrix_recheck':{'energy_identity_max_error':identity_error,'largest_generator_real_part':float(eig.real.max()),'step_spectral_radius':float(np.abs(step_eig).max())},
        'files':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(root.iterdir()) if p.is_file()],
        'scope':'Figures of frozen source arrays. The retained plus sign is the structural identity block proved in the frozen-system note; mechanical eigenvalues are from the declared Galerkin reduction. No population error bars or continuum claims.'}
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output':str(root),'files':len(report['files']),'cases':len(records),'matrix_recheck':report['frozen_matrix_recheck']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artwork/choir-figures-001');main(p.parse_args())
