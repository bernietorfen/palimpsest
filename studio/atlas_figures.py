"""An original print atlas and scientific views of the exhaustive histories."""
from datetime import datetime,timezone
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from scipy.interpolate import CubicSpline

from studio.preserve import sha256
from studio.simulate import source_hashes


PAPER="#f1eddf"
INK="#293e42"
MUTED="#69716b"
AMBER="#ac7137"
BLUE="#436b75"
PALETTE={"A":"#436b75","B":"#ac7137","C":"#904f3b","D":"#6b7760","E":"#b29a69"}


def conditional_distances(labels,distances):
    result={}
    arrays={}
    for suffix in range(4):
        pairs=[(i,j) for i in range(len(labels)) for j in range(i+1,len(labels))
               if suffix==0 or labels[i][-suffix:]==labels[j][-suffix:]]
        values=np.array([distances[i,j] for i,j in pairs])
        minimum=int(np.argmin(values))
        maximum=int(np.argmax(values))
        result[str(suffix)]={"shared_final_gestures":suffix,"pair_count":len(pairs),
            "minimum_rms_hz":float(values.min()),"median_rms_hz":float(np.median(values)),
            "maximum_rms_hz":float(values.max()),
            "minimum_pair":[str(labels[x]) for x in pairs[minimum]],
            "maximum_pair":[str(labels[x]) for x in pairs[maximum]]}
        arrays[suffix]=values
    return result,arrays


def save(fig,out,name,dpi=180):
    for suffix in ("png","pdf"):
        fig.savefig(out/f"{name}.{suffix}",dpi=dpi,facecolor=PAPER)
    plt.close(fig)


def landscape(data,conditional,out):
    labels=data["labels"]
    positions=data["projection"]/np.sqrt(336*12)
    _,distributions=conditional_distances(labels,data["distance_rms_hz"])
    variance=data["singular_values"]**2
    variance/=variance.sum()
    fig=plt.figure(figsize=(13.5,7.8),facecolor=PAPER)
    left=fig.add_axes([.075,.20,.47,.59])
    right=fig.add_axes([.65,.20,.30,.59])
    for letter,color in PALETTE.items():
        selection=np.array([label[-1]==letter for label in labels])
        left.scatter(positions[selection,0],positions[selection,1],s=30,color=color,
                     edgecolors=PAPER,linewidths=.6,label=f"Ends in {letter}",zorder=3)
    for label in ("ABCDE","EDCBA"):
        index=list(labels).index(label)
        left.annotate(label,positions[index],xytext=(7,7),textcoords="offset points",fontsize=9)
        left.scatter(*positions[index],s=65,facecolors="none",edgecolors=INK,linewidths=.7,zorder=4)
    left.axhline(0,color="#ccc3b2",lw=.6)
    left.axvline(0,color="#ccc3b2",lw=.6)
    left.set_xlabel(f"First component / Hz RMS / {100*variance[0]:.1f}% of variation")
    left.set_ylabel(f"Second component / Hz RMS / {100*variance[1]:.1f}% of variation")
    left.legend(ncol=5,loc="center",bbox_to_anchor=(.31,.115),bbox_transform=fig.transFigure,
                frameon=False,fontsize=8.5,columnspacing=1.0,handletextpad=.4)
    left.set_title("A landscape of later answers",loc="left",fontsize=14,pad=17)
    artists=right.boxplot([distributions[i] for i in range(4)],positions=np.arange(4),
                         widths=.48,showfliers=False,whis=(0,100),patch_artist=True,
                         medianprops={"color":PAPER,"linewidth":1.5},
                         whiskerprops={"color":INK,"linewidth":1},capprops={"color":INK,"linewidth":1})
    for index,box in enumerate(artists["boxes"]):
        box.set_facecolor(BLUE if index<3 else AMBER)
        box.set_edgecolor(INK)
        box.set_linewidth(.7)
    right.set_xticks(np.arange(4),[f"{label}\n{conditional[str(i)]['pair_count']:,} pairs"
                                  for i,label in enumerate(("Any","Last 1","Last 2","Last 3"))],fontsize=9)
    right.set_xlabel("Identical ending gestures")
    right.set_ylabel("Pair difference / Hz RMS")
    right.set_ylim(bottom=0)
    right.set_title("Earlier order still leaves a trace",loc="left",fontsize=14,pad=17)
    for axis in (left,right):
        axis.set_facecolor(PAPER)
        axis.spines[["top","right"]].set_visible(False)
        axis.spines[["left","bottom"]].set_color("#a7a99b")
        axis.tick_params(colors=INK)
    fig.text(.075,.91,"Every order. The same later question.",fontfamily="DejaVu Serif",fontsize=26,color=INK)
    fig.text(.075,.855,"120 writing histories / five gestures / an identical 14-second probe",fontsize=11,color=MUTED)
    fig.text(.075,.064,
        f"Left: two-component PCA retains {100*variance[:2].sum():.1f}% of trajectory variation; projected distances are incomplete. "
        "Right: medians, quartiles and full ranges over finite pairs, not confidence intervals.\n"
        "All cases reset u=p, v=0, delay and phase to zero before probing. Earlier-order comparisons share the last one, two or three writing gestures.",
        fontsize=9,color=MUTED,linespacing=1.7,va="top")
    save(fig,out,"history-landscape")


def ring_atlas(data,out):
    labels=data["labels"]
    pitches=data["pitch_hz"]
    times=np.array([0,4,8,12])
    samples=np.rint(times*24).astype(int)
    readings=pitches[:,samples,:]
    deviations=readings-readings.mean(axis=0,keepdims=True)
    limit=float(np.abs(deviations).max())
    angles=np.linspace(0,2*np.pi,13)
    fine=np.linspace(0,2*np.pi,361)
    colors=[MUTED,BLUE,AMBER,INK]
    fig=plt.figure(figsize=(20,26+2/3),facecolor=PAPER)
    grid=fig.add_gridspec(10,12,left=.047,right=.953,bottom=.115,top=.847,wspace=.035,hspace=.16)
    for index,label in enumerate(labels):
        axis=fig.add_subplot(grid[index//12,index%12])
        axis.set_aspect("equal")
        axis.axis("off")
        for spoke in angles[:-1]:
            axis.plot([.14*np.sin(spoke),1.08*np.sin(spoke)],
                      [.14*np.cos(spoke),1.08*np.cos(spoke)],color="#c8c2b1",lw=.22,zorder=0)
        for ring in range(4):
            values=deviations[index,ring]
            spline=CubicSpline(angles,np.r_[values,values[0]],bc_type="periodic")
            radius=.27+.21*ring+.18*spline(fine)/limit
            axis.plot(radius*np.sin(fine),radius*np.cos(fine),color=colors[ring],lw=.65,alpha=.94)
            knot_radius=.27+.21*ring+.18*values/limit
            axis.scatter(knot_radius*np.sin(angles[:-1]),knot_radius*np.cos(angles[:-1]),
                         s=.60,color=colors[ring],zorder=4)
        axis.set_xlim(-1.10,1.10)
        axis.set_ylim(-1.22,1.10)
        axis.text(0,-1.19,str(label),ha="center",va="center",fontfamily="DejaVu Sans Mono",fontsize=7.7,color=INK)
    fig.text(.052,.953,"PALIMPSEST / STUDY II",fontsize=12,color=INK)
    fig.text(.948,.953,"CODEX / 2026",fontsize=12,color=INK,ha="right")
    fig.add_artist(Line2D([.052,.948],[.942,.942],transform=fig.transFigure,color="#aaa994",lw=.6))
    fig.text(.049,.898,"120 possible pasts",fontsize=67,fontfamily="DejaVu Serif",color=INK)
    fig.text(.052,.867,"Five gestures. Every possible order. One identical question.",fontsize=17,color=MUTED)
    fig.add_artist(Line2D([.052,.948],[.091,.091],transform=fig.transFigure,color="#aaa994",lw=.6))
    fig.text(.052,.071,"HOW TO READ THE RINGS",fontsize=11,color=INK)
    fig.text(.052,.053,
        "Each glyph is a later answer. The twelve fixed directions are the instrument's twelve voices.\n"
        "The four rings, from inside outward, sample 0, 4, 8 and 12 seconds into the same probe.\n"
        "Radial deviation shows pitch relative to the ensemble mean at that moment; all glyphs share one scale.",
        fontsize=11.5,color=INK,linespacing=1.7,va="top")
    fig.text(.655,.071,"THE WRITING ALPHABET",fontsize=11,color=INK)
    fig.text(.655,.053,
        "A = voice 0   B = voice 4   C = voice 2\nD = voice 7   E = voice 3\n"
        "Each history retains its inscription and fatigue.",fontsize=11.5,color=INK,linespacing=1.7,va="top")
    fig.text(.052,.015,
        f"Authored readout glyphs / spline lines interpolate between measured voice axes / maximum sampled deviation {limit:.6f} Hz / "
        "finite-grid instrument, not a perceptual study",fontsize=8.6,color=MUTED)
    save(fig,out,"120-possible-pasts",dpi=300)
    return {"times_seconds":times.tolist(),"voice_axes":list(range(12)),"maximum_abs_deviation_hz":limit,
            "radius_rule":"0.27 + 0.21*ring_index + 0.18*(pitch - same-time ensemble mean)/maximum_abs_deviation_hz",
            "interpolation":"Periodic cubic spline between the twelve voice axes; glyph construction is an authored visual mapping."}


def main(args):
    source=Path(args.atlas)
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    source_hash=source_hashes(out/"source")
    data=np.load(source/"atlas.npz")
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":INK,
                         "axes.labelcolor":INK,"pdf.fonttype":42,"savefig.facecolor":PAPER})
    conditional,_=conditional_distances(data["labels"],data["distance_rms_hz"])
    landscape(data,conditional,out)
    glyphs=ring_atlas(data,out)
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":source_hash,
            "atlas_sha256":sha256(source/"atlas.npz"),"case_report_sha256":sha256(source/"report.json"),
            "conditional_order_comparisons":conditional,"glyph_definition":glyphs,
            "study_feedback_override":.08,
            "scope":"The study reuses numerical_assay.record, which applies feedback=0.08 during writing and probing, overriding the MaterialConfig default. Shared-tail groups test earlier order while fixing the specified final gestures. The counts describe finite pairs, not independent statistical samples."}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--atlas",default="artifacts/studies/history-atlas-001/rate-96")
    parser.add_argument("--output",default="artwork/analysis/history-atlas-001")
    main(parser.parse_args())
