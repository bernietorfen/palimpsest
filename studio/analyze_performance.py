"""Readable numerical and signal evidence for the artist's notebook."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from scipy import signal
import soundfile as sf

from studio.material import PITCHES_HZ
from studio.score import Score
from studio.simulate import source_hashes


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    root=Path(args.performance)
    data=np.load(root/"readouts.npz")
    manifest=json.loads((root/"manifest.json").read_text())
    audio,sr=sf.read(args.audio,dtype="float32",always_2d=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
                        "axes.spines.top":False,"axes.spines.right":False,
                        "axes.edgecolor":"#a79b88","axes.labelcolor":"#343a3b",
                        "xtick.color":"#555a57","ytick.color":"#555a57",
                        "figure.facecolor":"#f1eddf","axes.facecolor":"#f1eddf",
                        "savefig.facecolor":"#f1eddf","grid.alpha":.16})
    t=data["time"]
    pitches=data["pitch_hz"]
    cents=1200*np.log2(pitches/np.asarray(PITCHES_HZ)[None,:])
    fig,axes=plt.subplots(3,1,figsize=(14,9),sharex=True,gridspec_kw={"height_ratios":[1.1,1.2,1.]})
    score=Score()
    for gesture in score.gestures:
        duration=gesture.attack+gesture.hold+gesture.release
        color="#b37839" if gesture.polarity>0 else "#416d73"
        axes[0].broken_barh([(gesture.time,duration)],(gesture.voice-.34,.68),
                            facecolors=color,alpha=.45+.55*min(1.,gesture.strength/.53))
    axes[0].set_yticks(range(12),[f"{p:g}" for p in PITCHES_HZ])
    axes[0].set_ylabel("Unworn voice pitch / Hz")
    axes[0].set_title("The control score: a question, an accumulation, and a changed return",loc="left",pad=18)
    colors=plt.colormaps["cividis"](np.linspace(.08,.88,12))
    for voice in range(12):
        axes[1].plot(t,cents[:,voice],color=colors[voice],lw=.85,alpha=.85)
    axes[1].axhline(0,color="#9b927f",lw=.6)
    axes[1].set_ylabel("Retuning / cents\n(relative to unworn pitch)")
    diagnostics=manifest["diagnostics"]
    td=np.array([d["time"] for d in diagnostics])
    axes[2].plot(td,[d["memory_rms"] for d in diagnostics],color="#b37839",label="Rest-shape memory / RMS",lw=1.8)
    axes[2].plot(td,[d["fatigue_mean"] for d in diagnostics],color="#416d73",label="Fatigue / mean",lw=1.8)
    axes[2].set_ylabel("Dimensionless state")
    axes[2].set_xlabel("Performance time / seconds")
    axes[2].legend(frameon=False,loc="upper left")
    for ax in axes:
        ax.set_xlim(0,432)
        ax.set_xticks(np.arange(0,433,72))
        ax.grid(axis="x")
        ax.axvspan(18,64,color="#b37839",alpha=.075)
        ax.axvspan(370,416,color="#b37839",alpha=.075)
        ax.axvspan(308,358,color="#416d73",alpha=.07)
    fig.text(.08,.016,"Amber windows: the identical five-note phrase. Blue window: an increased forgetting rate. Curves describe the authored instrument, not a measured physical material.",fontsize=9,color="#5d625d")
    fig.tight_layout(rect=(0,.035,1,1),h_pad=2.3)
    fig.savefig(out/"performance-atlas.png",dpi=200)
    fig.savefig(out/"performance-atlas.pdf")
    plt.close(fig)
    # Direct signal measurements retain the actual authored silence and dynamics.
    blocks=audio[:len(audio)//sr*sr].reshape(-1,sr,2)
    rms=np.sqrt(np.mean(blocks.astype(np.float64)**2,axis=1))
    rms_db=20*np.log10(np.maximum(rms,1e-10))
    mono=audio.mean(axis=1)
    frequencies,times,power=signal.spectrogram(mono,fs=sr,nperseg=8192,noverlap=6144,
                                              scaling="spectrum",mode="psd")
    keep=(frequencies>=60)&(frequencies<=8000)
    db=10*np.log10(np.maximum(power[keep],1e-15))
    db-=db.max()
    spectrum=LinearSegmentedColormap.from_list("palimpsest",["#0d1013","#263e43","#b77b42","#eee0b7"])
    fig,(ax,level)=plt.subplots(2,1,figsize=(14,7),sharex=True,gridspec_kw={"height_ratios":[3,1]})
    mesh=ax.pcolormesh(times,frequencies[keep],db,cmap=spectrum,vmin=-85,vmax=0,shading="auto",rasterized=True)
    ax.set_yscale("log")
    ax.set_yticks([110,220,440,880,1760,3520,7040],["110","220","440","880","1760","3520","7040"])
    ax.set_ylabel("Frequency / Hz")
    ax.set_title("The synthesized sound: continuous retuning and material-driven envelopes",loc="left",pad=15)
    level.plot(np.arange(len(rms_db))+.5,rms_db[:,0],color="#b37839",lw=1,label="Left")
    level.plot(np.arange(len(rms_db))+.5,rms_db[:,1],color="#416d73",lw=1,label="Right")
    level.set_ylim(-70,0)
    level.set_ylabel("RMS / dBFS")
    level.set_xlabel("Performance time / seconds")
    level.legend(frameon=False,ncol=2,loc="upper right")
    level.set_xlim(0,432)
    fig.tight_layout()
    fig.savefig(out/"sound-atlas.png",dpi=200)
    fig.savefig(out/"sound-atlas.pdf")
    plt.close(fig)
    first=(t>=18)&(t<64)
    second=(t>=370)&(t<416)
    shift=1200*np.log2(pitches[second]/pitches[first])
    report={"source_sha256":hashes,"performance":str(root),"audio":str(args.audio),
            "sample_rate":sr,"duration":len(audio)/sr,"channels":audio.shape[1],
            "channel_rms_dbfs":(20*np.log10(np.sqrt(np.mean(audio.astype(np.float64)**2,axis=0)))).tolist(),
            "channel_peak_dbfs":(20*np.log10(np.maximum(np.abs(audio).max(axis=0),1e-15))).tolist(),
            "stereo_correlation":float(np.corrcoef(audio[::8,0],audio[::8,1])[0,1]),
            "pitch_min_hz":float(pitches.min()),"pitch_max_hz":float(pitches.max()),
            "opening_vs_return_pitch_shift_cents":{"rms":float(np.sqrt(np.mean(shift**2))),
                "min":float(shift.min()),"max":float(shift.max()),"mean_by_voice":shift.mean(axis=0).tolist()},
            "movements":[]}
    for i in range(6):
        section=audio[round(i*72*sr):round((i+1)*72*sr)]
        report["movements"].append({"name":score.names[i],"start":i*72,"end":(i+1)*72,
            "rms_dbfs":float(20*np.log10(max(np.sqrt(np.mean(section.astype(np.float64)**2)),1e-12))),
            "peak_dbfs":float(20*np.log10(max(np.max(np.abs(section)),1e-12)))})
    report["scope"]="Signal and numerical analysis only. This does not establish perceived musical quality or a listening-study result."
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--performance",default="artifacts/studies/performance-002")
    parser.add_argument("--audio",default="artwork/previews/score-002.wav")
    parser.add_argument("--output",default="artwork/analysis/performance-002")
    main(parser.parse_args())
