"""Original modal score synthesis from PALIMPSEST material readouts.

No samples or pretrained models. Each voice uses a continuous phase and smooth
readouts from the instrument; its overtone spread changes with material fatigue.
The room is an authored synthetic impulse response, generated with a fixed seed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import soundfile as sf


SOUND_SEED = 20261003


def smooth_curve(values: np.ndarray, control_time: np.ndarray,
                 sample_time: np.ndarray, sigma_frames: float = 1.2) -> np.ndarray:
    smoothed = gaussian_filter1d(values.astype(np.float64), sigma_frames, mode="nearest")
    return np.interp(sample_time, control_time, smoothed).astype(np.float32)


def make_room(sample_rate: int, seconds: float = 5.2) -> np.ndarray:
    rng = np.random.default_rng(SOUND_SEED)
    n = round(sample_rate * seconds)
    t = np.arange(n, dtype=np.float64) / sample_rate
    ir = np.zeros((n, 2), np.float64)
    taps = ((.027, .22), (.061, -.15), (.113, .125), (.191, .095), (.337, -.06))
    for channel in range(2):
        noise = rng.normal(0, 1, n)
        noise = signal.sosfilt(signal.butter(2, [230, 6100], btype="bandpass",
                                            fs=sample_rate, output="sos"), noise)
        ir[:,channel] = noise * np.exp(-t/1.13) * .0033
        ir[:round(.018*sample_rate),channel] = 0
        for delay, amp in taps:
            index = round((delay + channel * .0061) * sample_rate)
            ir[index,channel] += amp
    return ir.astype(np.float32)


def synthesize(args: argparse.Namespace) -> None:
    began = time.monotonic()
    source = Path(args.readouts)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = np.load(source)
    sr = args.sample_rate
    duration = min(float(data["time"][-1]), args.duration or float(data["time"][-1]))
    n = round(duration * sr)
    t = np.arange(n, dtype=np.float64)/sr
    stereo = np.zeros((n,2), np.float32)
    rng = np.random.default_rng(SOUND_SEED)
    controls = data["time"]
    pans = (-.55,.29,-.12,.58,-.38,.08,.41,-.63,.19,-.23,.68,-.04)
    stats = []
    for voice in range(12):
        pitch = smooth_curve(data["pitch_hz"][:,voice], controls, t)
        fatigue = smooth_curve(data["fatigue"][:,voice], controls, t)
        raw_amplitude = smooth_curve(data["amplitude"][:,voice], controls, t)
        drive = smooth_curve(np.abs(data["drive"][:,voice]), controls, t, .7)
        amplitude = .78*np.tanh(raw_amplitude*4.4) + .22*np.tanh(drive*3.2)
        amplitude = np.maximum(amplitude-.000015,0)
        # A long, smoothly bowed body and a smaller glassy attack share the same
        # continuously accumulated carrier, so there are no phase-reset clicks.
        phase = np.cumsum(pitch.astype(np.float64))*(2*np.pi/sr)
        wave = np.zeros(n, np.float32)
        phase_offset = voice*.713
        for partial in range(1,9):
            ratio = partial * (1 + .0009*(partial*partial-1))
            local_phase = phase*ratio + .014*partial*np.sin(2*np.pi*t*(.19+voice*.007))
            weight = (1/partial**1.9) * (1 if partial%2 else .72)
            shade = np.exp(-fatigue*partial*.21)
            wave += (weight*shade*np.sin(local_phase+phase_offset*partial)).astype(np.float32)
        # A quiet displaced fifth is a material-dependent ringing mode rather
        # than a sampled instrument. Its audibility follows the actual velocity.
        velocity = smooth_curve(np.abs(data["velocity"][:,voice]), controls, t)
        wave += (.075*np.tanh(velocity*7)*np.sin(phase*2.507+voice)).astype(np.float32)
        wave *= amplitude * (.070 if voice < 6 else .043)
        pan = pans[voice]
        stereo[:,0] += wave * np.sqrt((1-pan)/2)
        stereo[:,1] += wave * np.sqrt((1+pan)/2)
        stats.append({"voice":voice,"amplitude_max":float(amplitude.max()),
                      "pitch_min":float(pitch.min()),"pitch_max":float(pitch.max())})
        print(json.dumps({"voice":voice,"seconds":round(time.monotonic()-began,2)}),flush=True)
    # The fine abrasion follows *new* fatigue, not arbitrary visual edits.
    fatigue_rate = np.maximum(np.gradient(data["fatigue"].mean(axis=1), controls),0)
    abrasion = smooth_curve(fatigue_rate,controls,t,2.)
    abrasion = np.tanh(abrasion*45)*.008
    noise = rng.normal(0,1,n).astype(np.float32)
    noise = signal.sosfilt(signal.butter(2,[1300,6500],btype="bandpass",fs=sr,output="sos"),noise)
    stereo[:,0] += (noise*abrasion*.72).astype(np.float32)
    stereo[:,1] += (np.roll(noise,round(.0017*sr))*abrasion*.72).astype(np.float32)
    # Remove inaudible offsets before the room response.
    stereo = signal.sosfilt(signal.butter(2,28,btype="highpass",fs=sr,output="sos"),
                            stereo,axis=0).astype(np.float32)
    room = make_room(sr)
    mid = stereo.mean(axis=1)
    for channel in range(2):
        wet = signal.fftconvolve(mid,room[:,channel],mode="full")[:n]
        stereo[:,channel] += wet*.47
    # Defaults preserve the film's authored envelope. Short probe editions use
    # the same synthesizer with explicitly recorded, shorter boundary fades.
    fade_in = getattr(args,"fade_in",1.5)
    fade_out = getattr(args,"fade_out",7.)
    if fade_in <= 0 or fade_out <= 0:
        raise ValueError("boundary fades must be positive")
    fadein = np.minimum(t/fade_in,1)
    fadeout = np.minimum(np.maximum((duration-t)/fade_out,0),1)
    stereo *= (np.sin(fadein*np.pi/2)**2*np.sin(fadeout*np.pi/2)**2)[:,None]
    peak = float(np.max(np.abs(stereo)))
    fixed_gain = getattr(args,"fixed_gain",None)
    gain = fixed_gain if fixed_gain is not None else min(2.5, 10**(-2.0/20)/max(peak,1e-12))
    if gain <= 0 or not np.isfinite(gain) or peak*gain >= 1:
        raise ValueError("requested audio gain would be invalid or clip")
    stereo *= gain
    if not np.isfinite(stereo).all():
        raise FloatingPointError("nonfinite audio")
    sf.write(output,stereo,sr,subtype="PCM_24")
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"sample_rate":sr,
            "samples":n,"duration_seconds":n/sr,"channels":2,"subtype":"PCM_24",
            "peak_dbfs":20*np.log10(max(float(np.abs(stereo).max()),1e-12)),
            "rms_dbfs":20*np.log10(max(float(np.sqrt(np.mean(stereo**2))),1e-12)),
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "synthesizer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "sound_seed":SOUND_SEED,"normalization_gain":gain,"voices":stats,
            "gain_policy":"fixed across histories" if fixed_gain is not None else "peak-limited up to 2.5",
            "fade_in_seconds":fade_in,"fade_out_seconds":fade_out,
            "seconds_to_synthesize":time.monotonic()-began,
            "scope":"Original additive/modal synthesis; retuning and envelope are instrument readouts. No sampled audio or learned model."}
    output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--readouts",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--sample-rate",type=int,default=48000)
    parser.add_argument("--duration",type=float)
    parser.add_argument("--fade-in",type=float,default=1.5)
    parser.add_argument("--fade-out",type=float,default=7.)
    parser.add_argument("--fixed-gain",type=float)
    synthesize(parser.parse_args())
