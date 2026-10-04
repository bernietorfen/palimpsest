"""Figures made from the actual score and controlled experiment records."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
from matplotlib.patches import FancyArrowPatch,FancyBboxPatch
import numpy as np
from PIL import Image,ImageDraw

from studio.material import PITCHES_HZ
from studio.simulate import source_hashes


PAPER="#f1eddf"
INK="#293e42"
AMBER="#ac7137"
BLUE="#476f78"


def save(fig,out,name):
    fig.savefig(out/f"{name}.png",dpi=220,facecolor=PAPER)
    fig.savefig(out/f"{name}.pdf",facecolor=PAPER)
    plt.close(fig)


def main(output):
    out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
        "figure.facecolor":PAPER,"axes.facecolor":PAPER,"axes.spines.top":False,
        "axes.spines.right":False,"axes.edgecolor":"#a89e8b","axes.labelcolor":INK,
        "xtick.color":INK,"ytick.color":INK,"text.color":INK,"grid.alpha":.15})
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    diverging=LinearSegmentedColormap.from_list("signed-memory",["#234c5a",PAPER,"#a9582f"])
    fatigue=LinearSegmentedColormap.from_list("accumulated-wear",[PAPER,"#c59750","#453f35"])
    fig,axes=plt.subplots(3,3,figsize=(10,10),layout="constrained")
    for row,t in enumerate((30,165,358)):
        f=fields[t*24].astype(np.float32)
        for col,channel in enumerate((0,1,2)):
            kwargs=dict(cmap=fatigue,vmin=0,vmax=1) if col==2 else dict(cmap=diverging,vmin=-.8,vmax=.8)
            image=axes[row,col].imshow(f[:,:,channel],origin="lower",interpolation="bilinear",**kwargs)
            axes[row,col].set_xticks([]);axes[row,col].set_yticks([])
            if row==0:
                axes[row,col].set_title(("Displacement / u","Rest-shape inscription / p","Fatigue / z")[col],pad=12)
            if col==0:
                axes[row,col].set_ylabel(f"{t:03d} seconds",labelpad=14)
            if row==2:
                bar=fig.colorbar(image,ax=axes[:,col],orientation="horizontal",fraction=.025,pad=.03)
                bar.set_label("Dimensionless field")
    save(fig,out,"material-fields")

    root=Path("artifacts/studies/numerical-assay-001")
    report=json.loads((root/"report.json").read_text())
    forward=np.load(root/"dt-96-forward.npz")
    reverse=np.load(root/"dt-96-reverse.npz")
    delta=forward["pitch_hz"]-reverse["pitch_hz"]
    t=np.arange(len(delta))/24
    fig,(ax,below)=plt.subplots(2,1,figsize=(11,6.7),gridspec_kw={"height_ratios":[3,1.2]},layout="constrained")
    heat=ax.imshow(delta.T,origin="lower",aspect="auto",extent=(0,14,-.5,11.5),
                   cmap=diverging,norm=TwoSlopeNorm(vmin=-2.7,vcenter=0,vmax=2.7))
    ax.set_yticks(range(12),[f"{p:g}" for p in PITCHES_HZ])
    ax.set_ylabel("Unworn voice pitch / Hz")
    ax.set_xlabel("Time within identical probe / seconds")
    ax.set_title("The same five writing gestures, in a different order",loc="left",pad=15)
    bar=fig.colorbar(heat,ax=ax,fraction=.03,pad=.025)
    bar.set_label("Forward minus reverse / Hz")
    below.plot(t,np.sqrt(np.mean(delta**2,axis=1)),color=AMBER,lw=1.7)
    below.set_xlim(0,14);below.set_ylim(0,1.25)
    below.set_ylabel("Across-voice RMS\ndifference / Hz")
    below.set_xlabel("Time within identical probe / seconds")
    below.grid()
    save(fig,out,"order-memory")

    fig,axes=plt.subplots(2,1,figsize=(11,7.4),layout="constrained",gridspec_kw={"height_ratios":[2,1]})
    colors={"intact":INK,"erase_p":AMBER,"erase_z":BLUE,"erase_both":"#7d8275"}
    labels={"intact":"Both fields retained","erase_p":"Inscription erased; fatigue retained",
            "erase_z":"Fatigue erased; inscription retained","erase_both":"Both erased"}
    fresh=np.load(root/"probe-fresh.npz")["pitch_hz"]
    for arm,color in colors.items():
        pitch=np.load(root/f"probe-{arm}.npz")["pitch_hz"]
        difference=np.sqrt(np.mean((pitch-fresh)**2,axis=1))
        axes[0].plot(t,difference,color=color,label=labels[arm],lw=1.6)
    axes[0].set_xlim(0,14);axes[0].set_ylim(bottom=-.2)
    axes[0].set_ylabel("Pitch RMS difference\nfrom fresh instrument / Hz")
    axes[0].set_xlabel("Time within identical probe / seconds")
    axes[0].legend(frameon=False,fontsize=9,loc="center left",bbox_to_anchor=(.01,.38))
    axes[0].set_title("Erasing an inscription leaves a different material",loc="left",pad=15)
    rates=(96,192,384)
    values=[report["time_step_sensitivity"][str(rate)]["forward_vs_reverse"]["pitch_hz"]["rms"] for rate in rates]
    axes[1].bar(range(3),values,color=["#d0b998",AMBER,INK],width=.46)
    for i,value in enumerate(values):
        axes[1].text(i,value+.025,f"{value:.4f} Hz",ha="center",fontsize=10)
    axes[1].set_xticks(range(3),[f"1/{r} s" for r in rates])
    axes[1].set_ylim(0,1.2)
    axes[1].set_ylabel("Order-effect RMS / Hz")
    axes[1].set_xlabel("Integration timestep, with the same 128 x 128 grid")
    save(fig,out,"interventions-and-timestep")

    fig,ax=plt.subplots(figsize=(11,6.5))
    ax.set_xlim(0,11);ax.set_ylim(0,6.5);ax.axis("off")
    def box(x,y,w,h,title,body,color=INK):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.12,rounding_size=.05",linewidth=.9,edgecolor=color,facecolor=PAPER))
        ax.text(x+.17,y+h-.25,title,fontsize=13,color=color,va="top")
        ax.text(x+.17,y+h-.72,body,fontsize=10,va="top",linespacing=1.6)
    def arrow(a,b,label,curvature=0):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=12,color=AMBER,lw=1.3,
                                    connectionstyle=f"arc3,rad={curvature}"))
        if label:
            ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.12,label,ha="center",fontsize=9,color=AMBER)
    box(.4,4.45,2.6,1.4,"The score","Twelve force shapes\nSmooth, signed envelopes")
    box(4.05,4.25,3.,1.65,"The material","u, v: motion\np: rest-shape inscription\nz: retained fatigue")
    box(8.0,4.45,2.5,1.4,"The voice","Signed memory projection\nFatigue-weighted tuning")
    box(4.05,1.25,3.,1.55,"The reply","Delayed velocity readout\nPitch drift turns the\nspatial echo phase",color=AMBER)
    box(8.0,.7,2.5,2.0,"The artwork","Additive stereo synthesis\nFolded sheet and pigment\nWear mapped to openings\nAuthored camera and light",color=BLUE)
    arrow((3.15,5.1),(3.9,5.1),"force")
    arrow((7.2,5.1),(7.85,5.1),"readout")
    arrow((9.15,4.28),(7.2,2.5),"pitch drift",-.1)
    arrow((5.15,2.96),(5.15,4.1),"",0)
    ax.text(4.78,3.45,"force returns",ha="right",fontsize=9,color=AMBER)
    arrow((9.7,4.28),(9.7,2.86),"",0)
    ax.text(.45,1.7,"The sheet remembers two things:\nwhat was written,\nand what writing cost.",fontsize=12,linespacing=1.7,color=INK)
    fig.tight_layout(pad=.5)
    save(fig,out,"instrument-loop")
    images=sorted(out.glob("*.png"))
    contact=Image.new("RGB",(1200,2*650),PAPER)
    for i,path in enumerate(images):
        image=Image.open(path).convert("RGB")
        image.thumbnail((590,610),Image.Resampling.LANCZOS)
        x,y=(i%2)*600,(i//2)*650
        contact.paste(image,(x+(600-image.width)//2,y))
        ImageDraw.Draw(contact).text((x+12,y+622),path.stem,fill=INK)
    contact.save(out/"contact.jpg",quality=87)
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"figures":[p.name for p in images],
        "data":"performance-002 and numerical-assay-001; no synthetic example curves"},indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artwork/notebook/figures-002")
    main(parser.parse_args().output)
