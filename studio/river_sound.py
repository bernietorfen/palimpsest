"""Deterministic original instrumental synthesis for A River Twice. RunPod only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
from scipy import signal
import soundfile as sf

from studio.river_score import NoteEvent, get_score


# Mix automation is separate from the immutable performance score. Pan changes
# are sampled at each attack; gain/send curves are continuous role-bus controls.
# No delay is applied to the direct voice to manufacture stereo width.
SPATIAL_MIX = {
    "name": "spatial-v1",
    "purpose": "A close source, a shared field, an empty interval, and a redistributed inheritance.",
    "pan_rule": "clip(original event pan * scale + offset, -0.78, 0.78); equal-power direct gains",
    "room_rule": "Original deterministic reflection responses; time-varying sends before convolution",
    "gain_rule": "Smooth role-bus dB automation before room sends; one common constant master gain",
    "scope": "Authored spatial staging and balance, not physical acoustics or measured sonification. No perceptual audition is claimed.",
    "roles": {
        "felt": {
            "pan_scale": [[0, .5], [240, .5]],
            "pan_offset": [[0, -.20], [240, -.20]],
            "gain_db": [[0, 0], [240, 0]],
            "send": [[0, .075], [20, .14], [48, .22], [88, .25], [110, .18], [118, .08], [240, .08]],
        },
        "breath": {
            "pan_scale": [[0, 1.0], [20, 1.6], [32, 1.9], [88, 1.8], [112, 1.4], [122.2, 2.0], [156, 2.3], [240, 2.3]],
            "pan_offset": [[0, .05], [20, .03], [88, .02], [112, .06], [122.2, .02], [156, 0], [240, 0]],
            "gain_db": [[0, 0], [119.6, 0], [122.2, .3], [136, .3], [149, 0], [156, -.8], [164, 0], [240, 0]],
            "send": [[0, .19], [21.4, .28], [48, .38], [88, .42], [112, .30], [122.2, .21], [138, .29], [156, .33], [188, .48], [208, .43], [228, .50], [240, .50]],
        },
        "bow": {
            "pan_scale": [[0, .6], [240, .6]],
            "pan_offset": [[0, 0], [240, 0]],
            "gain_db": [[0, 0], [148, 0], [156, -.6], [188, -.9], [208, -1.0], [228, -.6], [240, -.6]],
            "send": [[0, .14], [88, .16], [122.2, .11], [156, .12], [208, .14], [228, .16], [240, .16]],
        },
        "glass": {
            "pan_scale": [[0, 1.4], [32, 1.8], [112, 1.8], [122.2, 2.0], [156, 1.8], [240, 1.8]],
            "pan_offset": [[0, 0], [240, 0]],
            "gain_db": [[0, 0], [118, 0], [122.2, 1.6], [134, 1.6], [149, 0], [240, 0]],
            "send": [[0, .30], [32, .40], [88, .48], [118, .15], [122.2, .24], [138, .28], [156, .37], [188, .55], [208, .48], [240, .52]],
        },
        "pulse": {
            "pan_scale": [[0, 1.7], [240, 1.7]],
            "pan_offset": [[0, 0], [240, 0]],
            "gain_db": [[0, 0], [156, 0], [164, 1.2], [188, 1.2], [208, 1.0], [228, 0], [240, 0]],
            "send": [[0, .04], [240, .04]],
        },
        "thread": {
            "pan_scale": [[0, 1.0], [240, 1.0]],
            "pan_offset": [[0, -.22], [156, -.22], [180, -.33], [208, -.35], [240, -.35]],
            "gain_db": [[0, 0], [155, 0], [156.25, 3.0], [164, 2.2], [180, 2.2], [196, 2.8], [216, 2.8], [228, 1.2], [240, 1.2]],
            "send": [[0, .20], [156, .22], [180, .31], [208, .40], [228, .48], [240, .48]],
        },
    },
}


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3.-2.*x)


def control_at(points, time_value):
    if time_value <= points[0][0]:
        return float(points[0][1])
    for (start, left), (end, right) in zip(points, points[1:]):
        if time_value <= end:
            return float(left+(right-left)*smooth((time_value-start)/(end-start)))
    return float(points[-1][1])


def control_curve(points, count, sr):
    value=np.full(count,points[-1][1],dtype=np.float32)
    for (start,left),(end,right) in zip(points,points[1:]):
        first=max(0,round(start*sr));last=min(count,round(end*sr))
        if last > first:
            position=(np.arange(first,last,dtype=np.float64)/sr-start)/(end-start)
            value[first:last]=left+(right-left)*smooth(position)
    return value


def frequency(pitch):
    return 440.*2.**((pitch-69.)/12.)


def envelope(t, event):
    value = smooth(t/event.attack)
    value *= 1.-smooth((t-event.duration)/event.release)
    return value


def colored_noise(rng, count, sr, low, high):
    raw = rng.standard_normal(count)
    filtered = signal.sosfilt(signal.butter(2, [low, high], btype="bandpass", fs=sr, output="sos"), raw)
    std = max(float(filtered.std()), 1e-9)
    return filtered/std


def synthesize(event: NoteEvent, sr: int, seed: int):
    count = round((event.duration+event.release)*sr)+1
    t = np.arange(count, dtype=np.float64)/sr
    rng = np.random.default_rng(seed)
    base = frequency(event.pitch)*2.**(event.detune_cents/1200.)
    env = envelope(t, event)
    brightness = event.brightness
    wave = np.zeros(count, dtype=np.float64)
    if event.instrument == "felt":
        # Frequency settles by less than a cent; decaying partials carry the attack.
        phase = base*(t+.00009*(1.-np.exp(-t/.07)))
        for partial in range(1, 14):
            ratio = partial*math.sqrt(1.+.000025*partial*partial)
            if base*ratio > sr*.45:
                continue
            weight = (1. if partial % 2 else .74)/partial**(1.5+.6*(1.-brightness))
            decay = np.exp(-t*(.52+.15*partial**1.16)/(1.15-.15*brightness))
            wave += weight*decay*np.sin(2*np.pi*phase*ratio+event.phase)
        attack = colored_noise(rng, count, sr, 260., 2800.+brightness*2500.)
        wave += .024*attack*np.exp(-t/.024)
        scale = .25
    elif event.instrument == "breath":
        vibrato = .0016*smooth((t-.25)/.65)*np.sin(2*np.pi*4.65*t)
        phase = 2*np.pi*base*np.cumsum(1.+vibrato)/sr
        drift = 1.+.035*np.sin(2*np.pi*.71*t+.6)+.014*np.sin(2*np.pi*2.2*t)
        for partial in range(1, 23):
            hz = partial*base
            if hz > sr*.44:
                continue
            formant = .45+1.1*np.exp(-.5*((hz-740.)/490.)**2)+.30*np.exp(-.5*((hz-2200.)/650.)**2)
            weight = formant*np.exp(-hz/(2100.+2400.*brightness))/partial**1.36
            wave += weight*np.sin(partial*phase+.14*partial)*(.93+.07*np.sin(2*np.pi*.39*t+partial))
        breath = colored_noise(rng, count, sr, 560., 4600.)
        wave = wave*drift+.022*breath*(.7+.3*np.sin(np.pi*np.minimum(t/2.,1.)))
        scale = .175
    elif event.instrument == "bow":
        vibrato = .0012*smooth(t/.9)*np.sin(2*np.pi*4.1*t+.3)
        phase = 2*np.pi*base*np.cumsum(1.+vibrato)/sr
        for partial in range(1, 23):
            if base*partial > sr*.44:
                continue
            weight = (1. if partial % 2 else .65)/partial**1.30
            weight *= math.exp(-base*partial/(1250.+brightness*1800.))
            wave += weight*np.sin(partial*phase+.18*partial)
        friction = colored_noise(rng, count, sr, 180., 2100.)
        wave = wave*(1.+.035*np.sin(2*np.pi*.83*t))+.020*friction
        scale = .205
    elif event.instrument == "glass":
        for ratio, weight in ((1.,1.), (2.012,.40), (2.756,.15), (4.071,.08), (5.433,.025)):
            if base*ratio > sr*.44:
                continue
            decay = np.exp(-t*(.40+.23*ratio))
            wave += weight*decay*np.sin(2*np.pi*base*ratio*t+.06*ratio)
        wave += .012*colored_noise(rng, count, sr, 1800., 8000.)*np.exp(-t/.012)
        scale = .205
    elif event.instrument == "pulse":
        low = base*.47
        phase = 2*np.pi*low*(t+.013*(1.-np.exp(-t/.035)))
        wave = np.sin(phase)*np.exp(-t/.047)
        wave += .20*colored_noise(rng, count, sr, 370., 2400.)*np.exp(-t/.016)
        scale = .21
    elif event.instrument == "thread":
        # A bowed strand rather than another pluck: two close harmonic strings
        # share a shaped pressure gesture. Its added role is absent in the miniature.
        vibrato=.0026*smooth((t-.18)/.75)*np.sin(2*np.pi*5.05*t+.2)
        phase=2*np.pi*base*np.cumsum(1.+vibrato)/sr
        bow_pressure=.77+.23*np.sin(np.pi*np.clip(t/max(event.duration,.1),0.,1.))
        for partial in range(1,25):
            hz=base*partial
            if hz > sr*.44:
                continue
            body=.73+.50*math.exp(-.5*((hz-1400.)/640.)**2)
            weight=body*math.exp(-hz/(1850.+2800.*brightness))/partial**1.17
            detuning=2*np.pi*base*partial*.00055*t
            wave+=weight*(.69*np.sin(partial*phase+.11*partial)+
                          .31*np.sin(partial*phase+detuning+.11*partial))
        friction=colored_noise(rng,count,sr,420.,3400.)
        wave=wave*bow_pressure+.017*friction*(.65+.35*bow_pressure)
        scale=.155
    else:
        raise ValueError(event.instrument)
    mono = (wave*env*scale*event.velocity).astype(np.float32)
    mono[0] = mono[-1] = 0.
    assert np.isfinite(mono).all()
    return mono


def room_response(sr: int, seed: int, role: str):
    """Original sparse-reflection room with a deterministic filtered tail."""
    duration = 2.25 if role in {"glass", "breath"} else 1.55
    count = round(duration*sr)
    rng = np.random.default_rng(seed)
    response = np.zeros((count, 2), dtype=np.float64)
    # Channels share early structure; slightly different reflections create width.
    for channel in range(2):
        for k, (delay, gain) in enumerate(((.023,.25),(.047,.18),(.081,.13),(.137,.10),(.211,.065))):
            index = round((delay+channel*(.0017+.0004*k))*sr)
            response[index,channel] += gain
        t = np.arange(count)/sr
        noise = signal.sosfilt(signal.butter(2, 3100., fs=sr, output="sos"), rng.standard_normal(count))
        tail = noise*np.exp(-t/(duration/6.5))*smooth((t-.061)/.11)
        tail /= max(np.sqrt(np.sum(tail*tail)), 1e-12)
        response[:,channel] += tail*.11
    return response.astype(np.float32)


def gate(score, count, sr):
    t = np.arange(count, dtype=np.float64)/sr
    value = smooth(t/.04)*(1.-smooth((t-(score.duration-2.3))/2.3))
    start, end = score.silence
    # No abrupt mute: a 0.7 s composed room fade leads into the exact silence.
    before = 1.-smooth((t-(start-.7))/.7)
    after = smooth((t-end)/.16)
    value *= np.where(t<start, before, after)
    value[(t>=start)&(t<end)] = 0.
    value[-1] = 0.
    return value.astype(np.float32)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_metrics(value, sr, score):
    precise = value.astype(np.float64)
    peak = float(np.max(np.abs(precise)))
    mono = precise.mean(axis=1)
    rms = float(np.sqrt(np.mean(precise*precise)))
    mono_rms = float(np.sqrt(np.mean(mono*mono)))
    left, right = precise.T
    correlation = float(np.corrcoef(left, right)[0,1])
    # Four-times polyphase reconstruction is an estimate, separately from FFmpeg.
    true_peak = max(float(np.max(np.abs(signal.resample_poly(value[:,c],4,1)))) for c in range(2))
    sections=[]
    for start, end, name in score.sections:
        piece = precise[round(start*sr):round(end*sr)]
        sections.append({"start":start,"end":end,"name":name,
                         "rms":float(np.sqrt(np.mean(piece*piece))),
                         "peak":float(np.max(np.abs(piece)))})
    boundaries=[]
    for at in sorted({score.silence[0]-.7,*score.silence,score.source_leaves,*[x[0] for x in score.sections]}):
        index=round(at*sr)
        piece=precise[max(0,index-96):min(len(value),index+96)]
        boundaries.append({"time":at,"maximum_adjacent_sample_step":float(np.max(np.abs(np.diff(piece,axis=0))))})
    quiet=precise[round(score.silence[0]*sr):round(score.silence[1]*sr)]
    return {"samples":len(value),"sample_rate":sr,"duration":len(value)/sr,
            "channels":2,"finite":bool(np.isfinite(value).all()),"sample_peak":peak,
            "four_times_true_peak_estimate":true_peak,"rms":rms,"mono_rms":mono_rms,
            "mono_to_stereo_energy_db":float(20*np.log10(max(mono_rms,1e-15)/max(rms,1e-15))),
            "stereo_correlation":correlation,"silence_nonzero_samples":int(np.count_nonzero(quiet)),
            "maximum_adjacent_sample_step":float(np.max(np.abs(np.diff(precise,axis=0)))),
            "sections":sections,"boundary_checks":boundaries}


def spatial_window_metrics(stems, master, sr):
    windows=((0,8,"first call"),(8,21.4,"answer"),(32,56,"interlock"),
             (88,112,"first crest"),(122.2,138,"inheritance"),
             (156,180,"new collective"),(180,208,"second rise"),
             (208,228,"recognition"),(228,240,"release"))
    results=[]
    for start,end,name in windows:
        a=round(start*sr);b=round(end*sr)
        piece=master[a:b].astype(np.float64);mid=piece.mean(axis=1);side=(piece[:,0]-piece[:,1])*.5
        mid_energy=float(np.mean(mid*mid));side_energy=float(np.mean(side*side))
        energy={role:float(np.mean(value[a:b].astype(np.float64)**2)) for role,value in stems.items()}
        total=max(sum(energy.values()),1e-30)
        results.append({"start":start,"end":end,"name":name,
                        "mix_rms_dbfs":float(10*np.log10(max(float(np.mean(piece*piece)),1e-30))),
                        "side_to_mid_db":float(10*np.log10(max(side_energy,1e-30)/max(mid_energy,1e-30))),
                        "stereo_correlation":float(np.corrcoef(piece.T)[0,1]),
                        "isolated_role_energy_fraction":{role:e/total for role,e in energy.items()}})
    return results


def main(args):
    if args.mix != "reference" and args.preset != "full":
        raise ValueError("The spatial mix is authored for the full score only; the miniature keeps its original mix")
    output=Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    (output/"stems").mkdir(); (output/"dry").mkdir(); (output/"source").mkdir()
    score=get_score(args.preset); sr=args.sample_rate; count=round(score.duration*sr)
    mix=SPATIAL_MIX if args.mix == "spatial-v1" else None
    prefix="river-miniature" if args.preset=="miniature" else "river-full"
    (output/"score.json").write_text(json.dumps(score.manifest(),indent=2)+"\n")
    if mix:
        automation={"mix":mix,"interpolation":"Smoothstep between declared breakpoints; direct pan sampled at note onset", "sample_rate":sr,
                    "performance_score_sha256":sha256(output/"score.json"),"event_pan":[],"curves_at_one_second":{}}
        for event in score.events:
            definition=mix["roles"][event.instrument]
            pan=float(np.clip(event.pan*control_at(definition["pan_scale"],event.start)+control_at(definition["pan_offset"],event.start),-.78,.78))
            automation["event_pan"].append({"event":event.id,"start":event.start,"score_pan":event.pan,"mixed_pan":pan})
        for role,definition in mix["roles"].items():
            automation["curves_at_one_second"][role]=[{"time":t,**{key:control_at(points,t) for key,points in definition.items()}} for t in range(round(score.duration)+1)]
        (output/"mix-automation.json").write_text(json.dumps(automation,indent=2)+"\n")
    sources={}
    for name in ("studio/river_score.py","studio/river_sound.py","research/RIVER-SCORE.md"):
        target=output/"source"/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(name,target);sources[name]=sha256(target)
    began=time.monotonic(); boundary=gate(score,count,sr); stems={}; note_checks=[]; dry_hashes={}; support_checks={}
    for role_index,role in enumerate(score.instruments):
        dry=np.zeros((count,2),dtype=np.float32)
        for event_index,event in enumerate(score.events):
            if event.instrument!=role:
                continue
            sound=synthesize(event,sr,score.seed+event_index*101)
            note_checks.append({"event":event.id,"first_sample":float(sound[0]),
                                "last_sample":float(sound[-1]),"peak":float(np.max(np.abs(sound)))})
            start=round(event.start*sr);length=min(len(sound),count-start)
            pan=event.pan
            if mix:
                definition=mix["roles"][role]
                pan=float(np.clip(pan*control_at(definition["pan_scale"],event.start)+control_at(definition["pan_offset"],event.start),-.78,.78))
            gains=(math.sqrt((1.-pan)/2.),math.sqrt((1.+pan)/2.))
            for channel in range(2):
                dry[start:start+length,channel]+=sound[:length]*gains[channel]
        # Consistent low-frequency cleanup, without processing silence through a filter afterward.
        dry=signal.sosfilt(signal.butter(2,26.,btype="highpass",fs=sr,output="sos"),dry,axis=0).astype(np.float32)
        room=room_response(sr,score.seed+2000+role_index,role)
        processed_dry=dry
        if mix:
            definition=mix["roles"][role]
            gain_curve=10.**(control_curve(definition["gain_db"],count,sr)/20.)
            processed_dry=dry*gain_curve[:,None]
        mid=processed_dry.mean(axis=1)
        wet=np.empty_like(dry)
        wet_amount={"felt":.23,"breath":.37,"bow":.20,"glass":.43,"pulse":.08,"thread":.29}[role]
        if mix:
            send=mid*control_curve(definition["send"],count,sr)
            for channel in range(2):
                wet[:,channel]=signal.fftconvolve(send,room[:,channel],mode="full")[:count]
            first_onset=min(round(event.start*sr) for event in score.events if event.instrument==role)
            # Restore strict causal support lost only to FFT floating-point roundoff.
            # This is far below audibility in the baseline; no threshold gate is used.
            wet[:first_onset]=0.
            support_checks[role]={"first_scored_onset":first_onset/sr,"pre_onset_nonzero_samples":int(np.count_nonzero(processed_dry[:first_onset])+np.count_nonzero(wet[:first_onset]))}
        else:
            for channel in range(2):
                wet[:,channel]=signal.fftconvolve(mid,room[:,channel],mode="full")[:count]*wet_amount
        value=(processed_dry+wet)*boundary[:,None]
        dry*=boundary[:,None]
        if role in score.withdrawn_roles:
            value[round(score.silence[0]*sr):]=0.;dry[round(score.silence[0]*sr):]=0.
        if role in score.mute_after:
            mute_time=score.mute_after[role]
            role_gate=(1.-smooth((np.arange(count)/sr-(mute_time-.35))/.35)).astype(np.float32)
            value*=role_gate[:,None];dry*=role_gate[:,None]
            value[round(mute_time*sr):]=0.;dry[round(mute_time*sr):]=0.
        sf.write(output/"dry"/(role+".wav"),dry,sr,subtype="FLOAT")
        dry_hashes[role]=hashlib.sha256(dry.tobytes()).hexdigest()
        stems[role]=value
        print(json.dumps({"role":role,"notes":sum(e.instrument==role for e in score.events),
                          "peak":float(np.max(np.abs(value))),"seconds":time.monotonic()-began}),flush=True)
    unmastered=sum(stems.values(),start=np.zeros((count,2),dtype=np.float32))
    peak=float(np.max(np.abs(unmastered)))
    gain=10.**(-2.5/20.)/peak
    master=unmastered*gain
    sf.write(output/f"{prefix}-unmastered.wav",unmastered,sr,subtype="FLOAT")
    sf.write(output/f"{prefix}.wav",master,sr,subtype="PCM_24")
    sf.write(output/f"{prefix}-float.wav",master,sr,subtype="FLOAT")
    sf.write(output/f"{prefix}-mono.wav",master.mean(axis=1),sr,subtype="PCM_24")
    reconstructed=np.zeros_like(master)
    for role,value in stems.items():
        delivered=value*gain
        sf.write(output/"stems"/(role+".wav"),delivered,sr,subtype="FLOAT")
        readback,_=sf.read(output/"stems"/(role+".wav"),dtype="float32")
        reconstructed+=readback
    metrics=audio_metrics(master,sr,score)
    metrics["stem_sum_maximum_error"]=float(np.max(np.abs(reconstructed-master)))
    metrics["master_gain_db"]=float(20*np.log10(gain))
    metrics["master_processing"]="One common constant gain; no limiter or compressor. Exact silence and boundary fades are part of the composed mix."
    metrics["mix_name"]=args.mix
    metrics["mix_treatment"]=mix or {"name":"reference","description":"Original event pans, fixed role sends and original deterministic rooms."}
    metrics["score_sha256"]=sha256(output/"score.json")
    metrics["dry_stem_scope"]="Original synthesized notes, chosen direct panning and 26 Hz cleanup, before role-bus gain automation and room; composed silence/withdrawal gates retained."
    metrics["dry_decoded_sample_sha256"]=dry_hashes
    metrics["causal_support_checks"]=support_checks
    metrics["spatial_windows"]=spatial_window_metrics(stems,master,sr) if args.preset=="full" else []
    metrics["note_boundaries"]=note_checks
    metrics["withdrawn_role_checks"]={
        role:{"zero_from":score.mute_after.get(role,score.silence[0]),
              "nonzero_samples":int(np.count_nonzero(stems[role][round(score.mute_after.get(role,score.silence[0])*sr):]))}
        for role in score.withdrawn_roles}
    assert metrics["finite"] and metrics["silence_nonzero_samples"]==0
    assert metrics["four_times_true_peak_estimate"] < .95
    assert metrics["stem_sum_maximum_error"] < 2e-6
    assert metrics["mono_to_stereo_energy_db"] > -4
    assert all(x["first_sample"]==x["last_sample"]==0 for x in note_checks)
    assert all(x["nonzero_samples"]==0 for x in metrics["withdrawn_role_checks"].values())
    assert all(x["pre_onset_nonzero_samples"]==0 for x in support_checks.values())
    if shutil.which("ffmpeg"):
        encode=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-threads","2","-i",str(output/f"{prefix}.wav"),
                "-threads","2","-c:a","libmp3lame","-b:a","192k",str(output/f"{prefix}.mp3")]
        subprocess.run(encode,check=True)
        meter=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-threads","2","-i",str(output/f"{prefix}.wav"),
                              "-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True,check=True)
        (output/"loudness.txt").write_text(meter.stderr)
    metrics["source_sha256"]=sources
    metrics["created_utc"]=datetime.now(timezone.utc).isoformat()
    metrics["seconds_to_render"]=time.monotonic()-began
    metrics["listening_scope"]="Technical audio checks and authored musical design. No supported perceptual audition is claimed by the rendering program."
    metrics["outputs"]={str(p.relative_to(output)):{"bytes":p.stat().st_size,"sha256":sha256(p)}
                         for p in sorted(output.rglob("*")) if p.is_file()}
    (output/"manifest.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps({k:metrics[k] for k in ("duration","sample_peak","four_times_true_peak_estimate",
                                           "stereo_correlation","mono_to_stereo_energy_db","silence_nonzero_samples",
                                           "stem_sum_maximum_error","master_gain_db","seconds_to_render")},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--sample-rate",type=int,default=48000)
    parser.add_argument("--preset",choices=("miniature","full"),default="miniature")
    parser.add_argument("--mix",choices=("reference","spatial-v1"),default="reference")
    args=parser.parse_args()
    if args.sample_rate not in {44100,48000}:
        raise ValueError("Use a production audio sample rate")
    main(args)
