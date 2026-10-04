"""The origin moves: an original geometric print and measured observer companion."""
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
from reportlab.pdfgen import canvas
from studio.notebook import Book,PAPER,INK,MUTED
from studio.received_history_art import fonts
from studio.preserve import sha256

BLUE='#315d6b';RUST='#a64c34';LINE='#c9c1b1'
SOURCES=('studio/observer_offset_art.py','studio/observer_offset.py','studio/verify_observer_offset.py','studio/notebook.py','studio/received_history_art.py','research/OBSERVER-REFINEMENT-PLAN.md','research/OBSERVER-REFINEMENT-RESULTS.md')


def strip_values(item):
    size=item['coarse_pair_squared_hz']
    raw=-(item['common_offset_term_squared_hz']+item['history_specific_term_squared_hz'])/(2*size)
    centered=-item['history_specific_term_squared_hz']/(2*size)
    return raw,centered,float(np.sqrt(size))


def print_work(out,report):
    path=out/'the-origin-moves-print.pdf';c=canvas.Canvas(str(path),pagesize=(1440,1080),pageCompression=1,invariant=True);c.setTitle('The origin moves / Six comparisons, one shared translation');c.setAuthor('Codex')
    c.setFillColor(HexColor(PAPER));c.rect(0,0,1440,1080,fill=1,stroke=0);c.setFillColor(HexColor(INK));c.setFont('Sans',11);c.drawString(72,1024,'PALIMPSEST / THE OBSERVER');c.drawRightString(1368,1024,'CODEX / 2026')
    c.setFont('Serif',52);c.drawString(72,941,'The origin moves.');c.setFont('Sans',17);c.drawString(74,902,'Six comparisons. One shared change of origin.')
    c.setStrokeColor(HexColor(LINE));c.setLineWidth(.6);c.line(72,873,1368,873)
    pairs=report['receivers'][0]['wrong_match_decomposition'];assert len(pairs)==6
    for i,item in enumerate(pairs):
        left=72+(i%2)*672;y=779-(i//2)*204;raw,centered,distance=strip_values(item)
        x=lambda t:left+86+t*420
        c.setFillColor(HexColor(MUTED));c.setFont('Mono',10);c.drawString(left,y+35,f'{i+1:02d}')
        c.setFillColor(HexColor(INK));c.setFont('Serif',19);c.drawString(left+42,y+35,item['actual']+' / '+item['raw_choice'])
        c.setStrokeColor(HexColor(LINE));c.setLineWidth(.6);c.line(x(-.12),y-8,x(1.10),y-8)
        c.setDash(2,3);c.line(x(.5),y-34,x(.5),y+18);c.setDash()
        for value in (0,1):
            c.setStrokeColor(HexColor(INK));c.setFillColor(HexColor(PAPER));c.circle(x(value),y-8,5,stroke=1,fill=1)
        c.setFillColor(HexColor(RUST));c.circle(x(raw),y-8,5.5,stroke=0,fill=1);c.setFont('Sans',9);c.drawCentredString(x(raw),y+6,'Raw reading')
        c.setStrokeColor(HexColor(BLUE));c.setLineWidth(.8);c.line(x(centered)+7,y-8,x(raw)-7,y-8);c.line(x(centered)+7,y-8,x(centered)+13,y-4);c.line(x(centered)+7,y-8,x(centered)+13,y-12)
        c.setFillColor(HexColor(BLUE));c.circle(x(centered),y-8,4,stroke=0,fill=1);c.setFont('Sans',9);c.drawCentredString(x(centered),y-29,'Aligned reading')
        c.setFillColor(HexColor(INK));c.setFont('Mono',11);c.drawCentredString(x(0),y-57,item['actual']);c.drawCentredString(x(1),y-57,item['raw_choice'])
        c.setFillColor(HexColor(MUTED));c.setFont('Sans',8);c.drawCentredString(x(0),y-73,'Own history');c.drawCentredString(x(1),y-73,'Original rival');c.drawCentredString(x(.5),y-48,'Equal-distance boundary')
        c.setFont('Sans',8.5);c.drawString(left+42,y-106,f'Pair separation {distance*1000:.4f} mHz RMS / one unit along this pair direction')
    c.setStrokeColor(HexColor(LINE));c.line(72,195,1368,195);c.setFillColor(HexColor(INK));c.setFont('Serif',22);c.drawString(74,151,'The relations remain. The place from which we compare them changes.')
    c.setFillColor(HexColor(MUTED));c.setFont('Sans',10)
    for i,line in enumerate(('Near receiver / 96 and 192 steps per second. Each axis is the exact projection onto one own-history / rival direction in the full recorded space.',
                             'One common vector aligns the centers of the complete twenty-four-history collections. It preserves every within-rate pair distance.',
                             'The raw result stays 18 of 24. The aligned diagnostic gives 24 of 24, using the complete collection; it is not a test of one unknown history.')):c.drawString(74,115-i*18,line)
    c.save();subprocess.run(['pdftoppm','-png','-singlefile','-scale-to-x','6000','-scale-to-y','4500',str(path),str(out/'the-origin-moves-6000x4500')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    with Image.open(out/'the-origin-moves-6000x4500.png') as image:
        preview=image.copy();preview.thumbnail((1600,1200));preview.save(out/'the-origin-moves.jpg',quality=91)
    return [{'own':item['actual'],'rival':item['raw_choice'],'raw_projection':strip_values(item)[0],'aligned_projection':strip_values(item)[1],'unit_hz':strip_values(item)[2]} for item in pairs]


def figure(out,report):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.facecolor':PAPER,'figure.facecolor':PAPER,'savefig.facecolor':PAPER,'text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':LINE})
    pairs=report['receivers'][0]['wrong_match_decomposition'];fig,ax=plt.subplots(figsize=(12,5.4),layout='constrained')
    for i,item in enumerate(pairs):
        raw,centered,distance=strip_values(item);y=5-i
        ax.plot([0,1],[y,y],color=LINE,lw=.75,zorder=1);ax.scatter([0,1],[y,y],facecolors=PAPER,edgecolors=INK,s=55,lw=1,zorder=3)
        ax.annotate('',xy=(centered,y),xytext=(raw,y),arrowprops={'arrowstyle':'->','color':BLUE,'lw':1.2,'shrinkA':5,'shrinkB':5});ax.scatter(raw,y,color=RUST,s=56,zorder=4);ax.scatter(centered,y,color=BLUE,s=38,zorder=4)
        ax.text(-.20,y+.15,item['actual'],ha='right',va='center',fontsize=11,color=INK);ax.text(-.20,y-.15,f'{distance*1000:.3f} mHz',ha='right',va='center',fontsize=8,color=MUTED);ax.text(1.07,y,item['raw_choice'],va='center',fontsize=10,color=INK)
    ax.axvline(.5,color=MUTED,lw=.8,ls=':');ax.set(ylim=(-.6,5.6),xlim=(-.31,1.22),yticks=[],xticks=[0,.5,1],xticklabels=['Own history','Equal-distance boundary','Original rival']);ax.tick_params(axis='x',length=0,pad=11);[ax.spines[side].set_visible(False) for side in ('top','right','left','bottom')]
    ax.scatter([],[],color=RUST,label='Raw finer-step reply',s=40);ax.scatter([],[],color=BLUE,label='After collection alignment',s=35);ax.legend(loc='lower right',bbox_to_anchor=(1,.99),frameon=False,ncol=2,fontsize=9)
    fig.savefig(out/'six-comparisons.png',dpi=190,bbox_inches='tight',pad_inches=.16);fig.savefig(out/'six-comparisons.pdf',bbox_inches='tight');plt.close(fig)


def table(book,rows,y,widths,size=10):
    x=48
    for row_i,row in enumerate(rows):
        x=48
        for value,width in zip(row,widths):book.text_line(x,y,str(value),size,'SansBold' if row_i==0 else 'Mono');x+=width
        book.c.setStrokeColor(HexColor(LINE));book.c.setLineWidth(.45);book.c.line(48,y-10,816,y-10);y-=37
    return y


def companion(out,first,second,refined):
    book=Book(out/'the-observer-companion.pdf','The observer / A choir of absences / 4 October 2026',invariant=True);book.c.setTitle('The observer / A moving origin and a third timestep')
    book.page('After the first result');book.heading('Six mistakes, one moving origin.')
    book.image(out/'six-comparisons.png',48,185,768,344)
    book.paragraph('The original raw comparison returns eighteen of twenty-four own-history matches at the near receiver. A common shift accounts for 99.1753% of its mean squared timestep discrepancy. Translating the fine collection by that shift returns all twenty-four own matches.',48,158,363,10.5,16)
    book.paragraph('Each row projects the full reply onto its own-history / rival direction. The dashed midpoint is an exact equal-distance boundary for that pair. The arrows use one common vector, expressed along six different axes. The original eighteen-of-twenty-four score is unchanged.',453,158,363,10.5,16)
    book.page('One encounter, three clocks');book.heading('A further halving, with the history held fixed.')
    y=book.paragraph('The third-timestep follow-up was declared after the first result. Before running its new 384-step histories, the repeated 192-step run reproduced all 488 preserved arrays exactly: written fields, probe initial conditions, readouts and distances.',48,523,768,11,17)
    rows=[['Comparison','Near / raw','Far / raw','Near / aligned','Far / aligned']]
    for report in (first,second):
        a,b=report['receivers'];rows.append([f"{report['rates'][0]} to {report['rates'][1]}",f"{a['raw']['own_nearest']} / 24",f"{b['raw']['own_nearest']} / 24",f"{a['translated']['own_nearest']} / 24",f"{b['translated']['own_nearest']} / 24"])
    y=table(book,rows,y-36,[162,141,141,162,162],9.8)
    original=json.loads(Path('artifacts/studies/received-histories-002/summary.json').read_text())
    rows=[['Steps / second','Distant minimum pair separation','Both-erased control']]
    for rate,record in ((96,original),(192,original),(384,refined)):
        values=record['rates'][str(rate)];minimum=values['observations']['connected']['2']['minimum_hz'];error=max(x['both_erased_max_error_hz'] for x in values['controls']);rows.append([rate,f'{minimum:.9f} Hz',f'{error:g} Hz maximum error'])
    y=table(book,rows,y-17,[162,350,256],10)
    book.paragraph('The raw distant-receiver gate '+('passes' if refined['distant_receiver_gate_passed'] else 'does not pass')+' again on 192 / 384: the same 0.001 Hz separation margin, own-history matching, finite-state and erasure conditions apply. Alignment remains a separate diagnostic that uses the complete balanced collection. No spatial-convergence, gesture-noise or audibility claim follows.',48,y-7,768,10,15)
    book.page('The observation');book.heading('A relation survives a shared change of origin.')
    y=book.paragraph('Let each recorded reply be a vector in the space of twelve pitches at 289 times, with the RMS inner product. For each history h, let C_h and F_h be its coarse and fine replies. Their discrepancy splits into a common shift and a history-specific remainder.',48,521,363,11,17)
    book.code(['delta_h = F_h - C_h','mu = mean_h(delta_h)','eta_h = delta_h - mu','','mean ||delta_h||^2','  = ||mu||^2 + mean ||eta_h||^2'],48,y-27,size=11,leading=24)
    book.paragraph('This is the ordinary Euclidean mean decomposition. Translating every member of a collection by the same vector leaves all its pair differences unchanged. Centering chooses the unique zero-mean representative of that collection under shared translation.',48,201,363,10.5,16)
    y=book.paragraph('<b>What the diagnostic explains.</b> In all six original wrong pair comparisons, the common-offset term moves the raw reply across the equal-distance boundary. Removing that term moves it back. Full nearest-history comparisons then choose all twenty-four own histories.',453,521,363,11,17)
    y=book.paragraph('<b>What it does not explain.</b> This does not identify the dynamical cause of timestep bias, prove a general advantage of either receiver, or provide a deployable reader of one unknown history. The complete balanced collection supplies its comparison origin.',453,y-22,363,11,17)
    book.paragraph('<b>The observation.</b> The finite material distinguishes surviving state from what an observer can read. Elementary geometry explains this diagnostic. No recurrence theorem is claimed for the nonlinear artwork.',453,y-22,363,10.5,16)
    assert book.page_number==3;book.c.save();return {'pages':3,'pdf_sha256':sha256(book.path),'embedded_image_sha256':book.assets,'page_inventory':book.records}


def main(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False);fonts();inputs={};reports=[]
    for name in ('observer-offset-001','observer-offset-002'):
        path=Path('artifacts/studies')/name/'report.json';reports.append(json.loads(path.read_text()));inputs[str(path)]=sha256(path)
    path=Path('artifacts/studies/received-refinement-001/summary.json');refined=json.loads(path.read_text());inputs[str(path)]=sha256(path)
    for report in reports:assert len(report['orders'])==24
    sources={}
    for relative in SOURCES:
        target=out/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);sources[relative]=sha256(Path(relative))
    strips=print_work(out,reports[0]);figure(out,reports[0]);book=companion(out,*reports,refined)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'input_sha256':inputs,'source_sha256':sources,'exact_pair_projections':strips,'companion':book,'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(out.iterdir()) if p.is_file()],'scope':'Original vector artwork from exact pair-decision projections, with an explicitly post-result observer analysis and fixed third-timestep follow-up. Raw-reader outcomes are preserved.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output':str(out),'pages':3,'files':len(report['files'])}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artwork/observer-art-002');main(p.parse_args())
