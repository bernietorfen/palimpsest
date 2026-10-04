"""A measured constant gain for the score, preserving its authored dynamics."""
from pathlib import Path
import argparse
import json
import subprocess

import soundfile as sf

from studio.preserve import sha256
from studio.simulate import source_hashes


def loudness(path):
    command=["ffmpeg","-hide_banner","-nostdin","-i",str(path),"-af",
             "loudnorm=I=-18:TP=-2:LRA=21:print_format=json","-f","null","-"]
    result=subprocess.run(command,capture_output=True,text=True,check=True)
    start=result.stderr.rfind("{")
    data=json.loads(result.stderr[start:])
    return {name:float(data[name]) for name in ("input_i","input_tp","input_lra","input_thresh")}


def main(args):
    source=Path(args.input)
    output=Path(args.output)
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError("master output already exists")
    output.parent.mkdir(parents=True,exist_ok=True)
    before=loudness(source)
    gain=min(args.lufs-before["input_i"],args.peak-before["input_tp"])-.05
    partial=output.with_name(output.stem+".partial.wav")
    if partial.exists():
        raise FileExistsError("an unfinished master already exists")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(source),
                    "-af",f"volume={gain:.8f}dB","-c:a","pcm_s24le",str(partial)],check=True)
    after=loudness(partial)
    original,master=sf.info(source),sf.info(partial)
    if (original.frames,original.samplerate,original.channels)!=(master.frames,master.samplerate,master.channels):
        raise ValueError("mastering changed duration, rate, or channels")
    if after["input_tp"]>args.peak+.05:
        raise ValueError("the measured master exceeds the requested true-peak ceiling")
    partial.rename(output)
    report={"input":str(source),"input_sha256":sha256(source),"output_sha256":sha256(output),
            "source_sha256":source_hashes(output.with_suffix("")/"source"),
            "gain_db":gain,"before":before,"after":after,"frames":master.frames,
            "sample_rate":master.samplerate,"channels":master.channels,"subtype":master.subtype,
            "scope":"Constant gain only. No compression, limiting, equalization or timing changes. Loudness is signal measurement; no perceptual audition is claimed."}
    output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="artwork/previews/score-002.wav")
    parser.add_argument("--output",default="artwork/masters/palimpsest-soundtrack.wav")
    parser.add_argument("--lufs",type=float,default=-18.)
    parser.add_argument("--peak",type=float,default=-2.)
    main(parser.parse_args())
