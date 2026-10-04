"""Draw the analytical ceilings as a standalone vector research figure."""
import argparse
from pathlib import Path
import json
from fractions import Fraction
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from studio.preserve import sha256


def main(args):
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    record=Path(args.report);data=json.loads(record.read_text())
    assert all(item['strictly_below_one_percent'] for item in data['exact_rational_certificates'])
    certificates={item['scene']:item for item in data['exact_rational_certificates']}
    parameters={name:(float(Fraction(item['rounded_prefactor'])),float(Fraction(item['rounded_rate'])),item['seconds']) for name,item in certificates.items()}
    paper='#e9e5dc';ink='#2b3939';blue='#315d6b';rust='#a64c34';muted='#626960'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.hashsalt':'palimpsest-quiet-choir-2026','pdf.fonttype':42,'axes.unicode_minus':False})
    fig=plt.figure(figsize=(11.7,8.3),facecolor=paper);ax=fig.add_axes([.105,.30,.79,.47],facecolor=paper)
    fig.text(.075,.923,'PALIMPSEST / AN ANALYTICAL AFTERWORD',fontsize=8.5,color=muted)
    fig.text(.075,.852,'A clock for the quiet choir.',fontsize=28,fontfamily='DejaVu Serif',color=ink)
    fig.text(.075,.800,'Frozen inscription and wear. No drive or feedback. Fixed connections.',fontsize=10.5,color=muted)
    time=np.linspace(0,65,651)
    joined_prefactor,joined_rate,joined_seconds=parameters['all-bridges'];separate_prefactor,separate_rate,separate_seconds=parameters['separate-bodies']
    ax.plot(time,np.minimum(1,joined_prefactor*np.exp(-joined_rate*time)),color=blue,lw=2.4,label='All twelve bridges held at full strength')
    ax.plot(time,np.minimum(1,separate_prefactor*np.exp(-separate_rate*time)),color=rust,lw=2.4,label='Separate bodies; bridge coordinates omitted')
    ax.axhline(.01,color=muted,lw=.8,ls=(0,(3,4)));ax.text(2,.0127,'1% of initial excess energy',fontsize=9,color=muted)
    for at,color,prefactor,rate,label in [(joined_seconds,blue,joined_prefactor,joined_rate,f'Within {joined_seconds} seconds'),(separate_seconds,rust,separate_prefactor,separate_rate,f'Within {separate_seconds} seconds')]:
        value=prefactor*np.exp(-rate*at);ax.scatter([at],[value],s=28,color=color,zorder=5)
        ax.annotate(label,(at,value),xytext=(-8,-22),textcoords='offset points',ha='right',fontsize=9,color=color,arrowprops={'arrowstyle':'-','color':color,'lw':.7})
    ax.set_yscale('log');ax.set_ylim(1e-5,1.3);ax.set_xlim(0,65);ax.set_xticks([0,15,30,45,60]);ax.set_yticks([1,.1,.01,.001,.0001,.00001],labels=['1','0.1','0.01','0.001','0.0001','0.00001']);ax.minorticks_off()
    ax.set_xlabel('Continuous model time / seconds',labelpad=12,color=ink);ax.set_ylabel('Excess mechanical energy / its initial value',labelpad=12,color=ink)
    ax.tick_params(axis='both',colors=muted,labelsize=9,length=3);ax.spines[['top','right']].set_visible(False)
    for name in ['bottom','left']:ax.spines[name].set_color('#b7b9af')
    ax.grid(axis='y',color='#cfcec3',lw=.45);ax.legend(frameon=False,loc='upper right',fontsize=9,labelcolor=ink)
    fig.text(.075,.139,'Analytical upper bounds',fontfamily='DejaVu Serif',fontsize=15,color=ink)
    fig.text(.075,.101,'The held fields remain fixed by assumption. Each curve bounds settling toward that history’s own equilibrium.',fontsize=9,color=muted)
    fig.text(.075,.077,'The active artwork writes, forgets and receives energy. Its trajectory is outside these frozen assumptions.',fontsize=9,color=muted)
    fig.text(.075,.031,'CODEX / 2026',fontsize=8,color=muted);fig.text(.925,.031,'Proof and exact numerical certificates: research/CHOIR-DECAY.md',ha='right',fontsize=8,color=muted)
    fig.savefig(root/'quiet-choir.svg',metadata={'Date':None,'Creator':'Codex / PALIMPSEST','Description':'Conservative continuous-time excess-energy ceilings for frozen choir mechanics. Fully connected: min(1,2.59 exp(-0.096 t)); separate bodies: min(1,1.81 exp(-0.187 t)). These curves are analytical bounds, not sampled trajectories.'})
    fig.savefig(root/'quiet-choir.pdf',metadata={'CreationDate':None,'ModDate':None,'Creator':'Codex / PALIMPSEST','Title':'A clock for the quiet choir'})
    fig.savefig(root/'review.png',dpi=130);plt.close(fig)
    result={'input_report_sha256':sha256(record),'source_sha256':sha256(Path(__file__)),'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(root.iterdir()) if p.is_file()],'scope':'Original vector figure of the conservatively rounded analytical upper bounds; no simulated or measured decay curve is shown.'}
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',default='research/choir-decay-bound-003.json');p.add_argument('--output',default='artwork/choir-decay-001');main(p.parse_args())
