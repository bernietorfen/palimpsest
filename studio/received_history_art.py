"""An original engraved atlas and four-page companion from received-order data."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from studio.notebook import Book,PAPER,INK,MUTED
from studio.preserve import sha256

ROOT=Path('artifacts/studies/received-histories-002')
SOURCES=('studio/received_history_art.py','studio/notebook.py','research/RECEIVED-HISTORIES-PROTOCOL.md','research/RECEIVED-HISTORIES-REVISION-001.md','research/RECEIVED-HISTORIES-RESULTS.md','studio/verify_received_histories.py')
COLORS={'A':'#a64c34','B':'#69795c','C':'#315d6b','D':'#ac813f'}


def fonts():
    root=Path('/usr/share/fonts/truetype/dejavu')
    for name,file in [('Sans','DejaVuSans.ttf'),('SansBold','DejaVuSans-Bold.ttf'),('Serif','DejaVuSerif.ttf'),('Mono','DejaVuSansMono.ttf')]:pdfmetrics.registerFont(TTFont(name,str(root/file)))


def poster(out,pitch,orders):
    # A common centering does not change any pairwise trajectory distance.
    centered=pitch.astype(np.float64)-pitch.astype(np.float64).mean(axis=0,keepdims=True)
    sample=np.rint(np.linspace(0,288,12)).astype(int);theta=np.linspace(0,2*np.pi,321);modes=np.arange(2,14)
    basis=np.cos(modes[:,None]*theta[None]+np.arange(12)[:,None]*np.pi*(np.sqrt(5)-1))
    deformation=np.einsum('htm,mq->htq',centered[:,sample,:],basis)
    scale=float(np.max(np.abs(deformation)));assert scale>0
    path=out/'received-histories-print.pdf';c=canvas.Canvas(str(path),pagesize=(1440,1800),pageCompression=1,invariant=True);c.setTitle('What arrives / Received histories');c.setAuthor('Codex')
    c.setFillColor(HexColor(PAPER));c.rect(0,0,1440,1800,fill=1,stroke=0)
    c.setFillColor(HexColor(INK));c.setFont('Sans',11);c.drawString(72,1744,'PALIMPSEST / A CHOIR OF ABSENCES');c.drawRightString(1368,1744,'CODEX / 2026')
    c.setFont('Serif',54);c.drawString(72,1658,'What arrives.');c.setFont('Sans',17);c.drawString(74,1618,'Twenty-four orders, received at a distance.')
    c.setFont('Sans',11);c.setFillColor(HexColor(MUTED));c.drawString(74,1580,'Four source gestures. Two wave bridges. The source removed before the question.')
    c.setStrokeColor(HexColor('#c7c0b1'));c.setLineWidth(.65);c.line(72,1554,1368,1554)
    for index,order in enumerate(orders):
        column=index%4;row=index//4;cx=234+324*column;cy=1430-216*row
        c.setStrokeColor(HexColor('#cfc8b9'));c.setLineWidth(.45);c.circle(cx,cy,84,stroke=1,fill=0)
        for ring in range(12):
            radius=80*(.32+.052*ring+.20*deformation[index,ring]/scale)
            x=cx+radius*np.cos(theta);y=cy+radius*np.sin(theta);p=c.beginPath();p.moveTo(float(x[0]),float(y[0]))
            for a,b in zip(x[1:],y[1:]):p.lineTo(float(a),float(b))
            p.close();blend=ring/11;color=np.array([142,118,80])*(1-blend)+np.array([40,77,86])*blend
            c.setStrokeColorRGB(*(color/255));c.setLineWidth(.52 if ring<11 else .9);c.drawPath(p,stroke=1,fill=0)
        for slot,token in enumerate(order):
            x=cx-38+slot*25;c.setFillColor(HexColor(COLORS[token]));c.circle(x,cy-104,3.2,stroke=0,fill=1);c.setFillColor(HexColor(INK));c.setFont('Mono',10);c.drawCentredString(x,cy-122,token)
        c.setFillColor(HexColor(MUTED));c.setFont('Sans',8);c.drawString(cx-95,cy+92,f'{index+1:02d}')
    c.setStrokeColor(HexColor('#c7c0b1'));c.setLineWidth(.65);c.line(72,178,1368,178)
    c.setFillColor(HexColor(INK));c.setFont('Serif',20);c.drawString(74,139,'The distant body keeps an order it never received by touch.')
    c.setFillColor(HexColor(MUTED));c.setFont('Sans',10)
    for i,line in enumerate(('Each mark is an authored harmonic projection of twelve recorded pitch readouts, centered on the mean of the twenty-four histories.',
                             'Twelve nested lines follow the same twelve probe times. One common scale is used throughout. Full trajectories determine the scientific result.',
                             'Receiver 2 / 64 x 64 material / 96 steps per second / A finite numerical study, not a hearing or physical-memory claim.')):c.drawString(74,106-i*17,line)
    c.save();subprocess.run(['pdftoppm','-png','-singlefile','-scale-to-x','6000','-scale-to-y','7500',str(path),str(out/'received-histories-6000x7500')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    with Image.open(out/'received-histories-6000x7500.png') as original:
        preview=original.copy();preview.thumbnail((1600,2000));preview.save(out/'received-histories.jpg',quality=91)
    return {'receiver':2,'rate':96,'centering':'Mean of all 24 connected received trajectories at each time and mode','sample_indices':sample.tolist(),'times_seconds':(sample/24).tolist(),'harmonic_frequencies':modes.tolist(),'phase_rule':'mode_index * pi * (sqrt(5)-1)','normalization_maximum':scale,'common_scale':True,'scope':'Authored projection, not the classification metric or evidence of perceptual separability.'}


def figures(out,data,orders):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.facecolor':PAPER,'figure.facecolor':PAPER,'savefig.facecolor':PAPER,'text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':'#c9c1b1'})
    fig,axes=plt.subplots(1,2,figsize=(12,6.8),layout='constrained')
    for receiver,axis in enumerate(axes,1):
        distances=np.load(ROOT/f'cross-rate-receiver-{receiver}.npz')['rms_hz'];selected=distances.argmin(axis=1);correct=selected==np.arange(24)
        axis.set_facecolor(PAPER);axis.plot([-1,24],[-1,24],color='#c6bfaf',lw=.7,zorder=1)
        for i,j in enumerate(selected):axis.scatter(j,i,s=44,marker='o' if correct[i] else 'x',color='#315d6b' if correct[i] else '#ab4f35',lw=1.6,zorder=3)
        axis.set(xticks=range(24),yticks=range(24),xticklabels=orders,yticklabels=orders,xlim=(-.7,23.7),ylim=(23.7,-.7),xlabel='Nearest history / 96 steps per second',ylabel='Asked history / 192 steps per second',title=('Near receiver' if receiver==1 else 'Distant receiver')+f' / {int(correct.sum())} of 24 own matches')
        axis.tick_params(axis='x',labelrotation=90,labelsize=7);axis.tick_params(axis='y',labelsize=7);axis.set_aspect('equal');axis.grid(color='#ded7c8',lw=.35)
    fig.savefig(out/'who-recognizes-the-order.png',dpi=190,bbox_inches='tight',pad_inches=.16);fig.savefig(out/'who-recognizes-the-order.pdf',bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    a,b=orders.index('CBDA'),orders.index('CDBA');t=np.arange(289)/24
    for rate,color,style in ((96,'#315d6b','-'),(192,'#a3673c','--')):
        values=data[rate]['pitch_hz'];difference=np.sqrt(np.mean((values[a,0,1].astype(float)-values[b,0,1].astype(float))**2,axis=1));axes[0].plot(t,difference*1000,color=color,ls=style,lw=1.3,label=f'{rate} steps / second')
    axes[0].set(title='Closest distant pair / CBDA and CDBA',xlabel='Question time / seconds',ylabel='RMS difference across twelve modes / mHz');axes[0].legend(frameon=False,fontsize=9);axes[0].grid(axis='y',color='#d8d0c0',lw=.5)
    for rate,offset,color in ((96,-.12,'#315d6b'),(192,.12,'#a3673c')):
        distances=np.load(ROOT/f'rate-{rate:03d}/distances.npz')['rms_hz'];indices=np.triu_indices(24,1);minimum=np.array([d[1][indices].min() for d in distances])*1000;axes[1].bar(np.arange(4)+offset,minimum,width=.22,color=color,label=f'{rate} steps / second')
    axes[1].axhline(1,color=INK,lw=.9,ls=':');axes[1].set(title='Minimum distant pair separation',ylabel='mHz RMS',xticks=range(4),xticklabels=['Retained','p erased','z erased','Both erased']);axes[1].tick_params(axis='x',labelsize=9);axes[1].legend(frameon=False,fontsize=9);axes[1].grid(axis='y',color='#d8d0c0',lw=.5);axes[1].set_axisbelow(True)
    fig.savefig(out/'the-smallest-difference.png',dpi=190,bbox_inches='tight',pad_inches=.16);fig.savefig(out/'the-smallest-difference.pdf',bbox_inches='tight');plt.close(fig)


def companion(out):
    book=Book(out/'received-histories-companion.pdf','Received histories / A choir of absences / 4 October 2026',invariant=True);book.c.setTitle('Received histories / A sequence reaches an untouched receiver')
    book.page('The received order');book.heading('A sequence crosses the connections.')
    book.image(out/'received-histories.jpg',470,74,335,419)
    y=book.paragraph('The encounter carries order. All twenty-four permutations of four fixed source gestures leave distinct measured replies at two bodies that the writing contacts never touched.',48,516,372,13,20)
    y=book.paragraph('The source is absent from the later question. Every connection is removed; displacement returns to the retained rest shape, and velocity, delayed feedback and phase are cleared. Only inscription and wear carry the writing history into the probe.',48,y-24,372,11,17)
    y=book.paragraph('The source gestures keep their locations, signed amplitudes and envelopes. Their order changes. This preserves the prescribed ingredients, while the material can do different mechanical work in response.',48,y-22,372,11,17)
    book.paragraph('The accompanying print is an authored projection of the distant receiver\'s actual twelve pitch readouts. The same centering, basis and scale apply to all twenty-four marks. Their full saved trajectories, rather than the drawing, determine every numerical result.',48,y-22,372,10.5,16)
    book.page('Two observers');book.heading('The farther witness gives the steadier reading here.')
    book.image(out/'who-recognizes-the-order.png',48,184,768,358)
    book.paragraph('Each dot asks which coarse-step history lies closest to one fine-step reply. Both receivers separate all twenty-four orders at each rate. The nearer receiver returns eighteen own-history matches; the distant receiver returns all twenty-four.',48,162,363,10.5,16)
    book.paragraph('The six rust crosses remain in the record. This selected comparison does not establish a general advantage of distance: the two bodies also occupy different mechanical roles in the chain. No causal explanation of that difference is claimed.',453,162,363,10.5,16)
    book.page('A small retained difference');book.heading('A numerical distinction has a measured size.')
    book.image(out/'the-smallest-difference.png',48,231,768,307)
    book.paragraph('The closest distant pair is CBDA / CDBA. Its difference is 0.002101487 Hz RMS at 96 steps per second and 0.002121531 Hz at 192. Both exceed the fixed 0.001 Hz numerical gate. These small differences are not a claim about hearing.',48,208,363,11,17)
    book.paragraph('Erasing both retained fields makes every response equal to its fresh control exactly. Erasing either field alone produces another observation; their effects are not additive. The dotted line is the declared gate for the retained condition, not a new admission rule for the partial erasures.',453,208,363,10.5,16)
    book.paragraph('Even pairs with identical final two tokens remain distinct: the smallest distant separation in that twelve-pair subset is 0.005307868 Hz at 96 steps per second and 0.005290206 Hz at 192. Earlier ordering remains in this finite response.',48,91,768,10,15)
    book.page('A reproducible boundary');book.heading('The unsuccessful admission stays with the result.')
    y=book.paragraph('<b>Before evaluation.</b> A written plan fixed the four contacts, all permutations, both timesteps, the reader and the distant-receiver gate. The first attempt packed eight independent chains. Its six-second comparison failed the 2e-6 field tolerance: one bridge-velocity discrepancy was 6.735325e-6. No order results were evaluated in that run.',48,520,363,11,17)
    y=book.paragraph('<b>A declared revision.</b> The packing was rejected. Each three-body writing history then ran alone. The new six-second admission reproduces the preserved single-chain reference exactly, including bridge fields and pitches. The gestures and scientific criteria did not change.',48,y-22,363,11,17)
    book.paragraph('<b>The record.</b> Both producing implementations, the failed admission, every retained state, complete probe initial conditions, all 276 pairwise distances per receiver/condition/rate, and every cross-timestep choice accompany the edition.',48,y-22,363,10.5,16)
    y=book.paragraph('<b>Independent analysis.</b> A separate NumPy verifier hashes 164 files, reconstructs 768 retained-field interventions, verifies u=p with zero velocity, delay, phase and clock at each probe, and recomputes every distance matrix. The saved matrix discrepancy is zero.',453,520,363,11,17)
    y=book.paragraph('<b>The limits.</b> These are all orders in one selected four-token universe. The metric reads all twelve modal pitches, including modes that the probe does not directly excite. It establishes neither human audibility nor pressure/noise robustness, physical memory capacity, continuum convergence or infinite-time arithmetic rank.',453,y-22,363,11,17)
    book.paragraph('<b>The observer.</b> This follow-up asks a finite question in the numerical material. A changed state, a distinguishable numerical reply and a perceptible sound remain different claims.',453,y-22,363,10.5,16)
    assert book.page_number==4;book.c.save()
    return {'pages':4,'pdf_sha256':sha256(book.path),'embedded_image_sha256':book.assets,'page_inventory':book.records}


def main(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False);fonts();source_hashes={}
    for relative in SOURCES:
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);source_hashes[relative]=sha256(Path(relative))
    data={rate:np.load(ROOT/f'rate-{rate:03d}/readouts.npz') for rate in (96,192)};orders=data[96]['orders'].tolist();assert data[192]['orders'].tolist()==orders
    glyph=poster(out,data[96]['pitch_hz'][:,0,1],orders);figures(out,data,orders);book=companion(out)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source_hashes,'study_manifest_sha256':sha256(ROOT/'manifest.json'),'glyph':glyph,'companion':book,
        'files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.iterdir()) if p.is_file()],
        'scope':'Original data-derived engraving and measured research companion. The drawing is an authored projection; classification uses every full-precision pitch trajectory. No perceptual discrimination claim.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output':str(out),'files':len(report['files']),'pages':4}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artwork/received-history-art-001');main(p.parse_args())
