"""Prepare two short, un-rebalanced listening windows from the accepted score.

Run on the production host. These are contextual excerpts of the composition,
not isolated instruments, measured sonification or a perceptual experiment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import soundfile as sf

from studio import river_delivery
from studio.river_delivery import identity, probe, stream


WINDOWS = (
    ('river-opening', 0., 'The opening', 'The close plucked voice introduces the call.'),
    ('river-return', 208., 'The changed return', 'The bowed voice carries the call; its original plucked voice remains absent.'),
)
DURATION = 12.
FADE_IN = .025
FADE_OUT = .18
END_SILENCE = .064


def require(condition, message):
    if not condition:
        raise ValueError(message)


def smoothstep(value):
    return value * value * (3. - 2. * value)


def main(args):
    master, receipt, output = Path(args.master), Path(args.receipt), Path(args.output)
    require(not output.exists(), 'Choose a fresh listening-pair directory')
    record = json.loads(receipt.read_text())
    master_id = identity(master)
    require(all(record['outputs'][master.name][key] == master_id[key] for key in ('bytes', 'sha256')),
            'The score master differs from its receipt')
    require(record['mix_name'] == 'spatial-v1' and record['duration'] == 240.,
            'The listening pair requires the accepted full spatial score')
    require(record['withdrawn_role_checks']['felt']['nonzero_samples'] == 0
            and record['withdrawn_role_checks']['felt']['zero_from'] == 118.,
            'The original voice withdrawal is not certified')
    info = sf.info(master)
    require(info.samplerate == 48000 and info.channels == 2 and info.frames == 240 * 48000,
            'Expected the full 48 kHz stereo master')
    output.mkdir(parents=True)
    for directory in ('public', 'pcm', 'source'):
        (output / directory).mkdir()
    shutil.copyfile(__file__, output / 'source' / Path(__file__).name)
    shutil.copyfile(river_delivery.__file__, output / 'source/river_delivery.py')
    shutil.copyfile(receipt, output / 'source/audio-receipt.json')
    count = round(DURATION * info.samplerate)
    enter, leave = round(FADE_IN * info.samplerate), round(FADE_OUT * info.samplerate)
    guard = round(END_SILENCE * info.samplerate)
    exit_start = count - leave - guard
    envelope = np.ones(count, dtype=np.float64)
    envelope[:enter] = smoothstep(np.linspace(0., 1., enter))
    envelope[exit_start:count - guard] = 1. - smoothstep(np.linspace(0., 1., leave))
    envelope[count - guard:] = 0.
    excerpts, checks = [], []
    for name, start, title, description in WINDOWS:
        with sf.SoundFile(master) as source:
            source.seek(round(start * info.samplerate))
            original = source.read(count, dtype='float64', always_2d=True)
        require(original.shape == (count, 2) and np.isfinite(original).all(), 'Incomplete source window')
        edited = original * envelope[:, None]
        pcm = output / 'pcm' / (name + '.wav')
        sf.write(pcm, edited, info.samplerate, subtype='PCM_24')
        stored, rate = sf.read(pcm, dtype='float64', always_2d=True)
        require(rate == info.samplerate and np.array_equal(stored[enter:exit_start], original[enter:exit_start]),
                'Interior samples or common score gain changed')
        require(np.all(stored[[0, -1]] == 0.) and np.max(np.abs(stored)) < 1., 'Invalid boundary or clipping')
        encoded = output / 'public' / (name + '.m4a')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                        '-threads', '2', '-i', str(pcm), '-map_metadata', '-1',
                        '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2',
                        '-metadata', 'title=A River Twice / ' + title,
                        '-metadata', 'artist=Codex', '-movflags', '+faststart', str(encoded)], check=True)
        native = stream(probe(encoded), 'audio')
        require(native['sample_rate'] == '48000' and native['channels'] == 2
                and native['codec_name'] == 'aac' and int(native['start_pts']) == 0
                and native['time_base'] == '1/48000' and int(native['duration_ts']) == count,
                'Encoded excerpt has the wrong native timeline')
        decoded_bytes = subprocess.check_output([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-threads', '2',
            '-i', str(encoded), '-map', '0:a:0', '-c:a', 'pcm_f64le', '-f', 'f64le', 'pipe:1'])
        decoded = np.frombuffer(decoded_bytes, dtype='<f8')
        padding = (-count) % 1024
        require(decoded.size % 2 == 0 and count * 2 <= decoded.size <= (count + padding) * 2
                and np.isfinite(decoded).all(), 'Decoded excerpt has the wrong sample count')
        decoded = decoded.reshape(-1, 2)
        padding_count = len(decoded) - count
        padding_peak = float(np.max(np.abs(decoded[count:]))) if padding_count else 0.
        require(padding_peak < 1e-5, 'Non-silent AAC frame padding')
        decoded = decoded[:count]
        error = decoded - stored
        ratio = float(np.sqrt(np.mean(decoded ** 2) / np.mean(stored ** 2)))
        signal_error = float(10. * np.log10(np.sum(stored ** 2) / max(np.sum(error ** 2), 1e-30)))
        require(abs(ratio - 1.) < .02 and signal_error > 25. and np.max(np.abs(decoded)) < 1.,
                'Excerpt encoding changed gain excessively or introduced clipping')
        excerpts.append({'file': encoded.name, **identity(encoded), 'title': title, 'description': description,
                         'film_start': start, 'film_end': start + DURATION, 'seconds': DURATION})
        checks.append({'file': encoded.name, 'frames_per_channel': count, 'channels': 2,
                       'sample_rate': info.samplerate, 'interior_pcm_samples_identical': True,
                       'endpoint_pcm_samples_zero': True, 'decoded_peak': float(np.max(np.abs(decoded))),
                       'native_duration_frames': count, 'decoded_padding_frames': padding_count,
                       'allowed_padding_frames': padding, 'padding_peak': padding_peak,
                       'decoded_rms_ratio': ratio, 'signal_to_codec_error_db': signal_error,
                       'pcm': identity(pcm)})
    require(identity(master) == master_id, 'The source master changed during preparation')
    provenance = {
        'format': 'palimpsest-river-listening-pair-v1', 'version': 1,
        'title': 'A phrase changes hands', 'source_master': {'file': master.name, **master_id},
        'source_audio_receipt': identity(receipt), 'excerpts': excerpts,
        'edit': {'gain_change_db': 0., 'fade_in_seconds': FADE_IN, 'fade_out_seconds': FADE_OUT,
                 'closing_silence_seconds': END_SILENCE,
                 'fade_shape': 'smoothstep', 'encoding': '320 kbit/s stereo AAC in M4A'},
        'scope': 'Two contextual excerpts from the same original score. Common gain and stereo retained; only boundary fades, a short closing silence and AAC compression are added. No isolated-instrument, sonification or perceptual-test claim.',
    }
    public_record = output / 'public/river-listening-pair.json'
    public_record.write_text(json.dumps(provenance, indent=2) + '\n')
    report = {'format': 'palimpsest-river-listening-pair-review-v1',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': identity(__file__)['sha256'], 'source_master': master_id,
              'helper_source_sha256': identity(output / 'source/river_delivery.py')['sha256'],
              'environment': {'numpy': np.__version__, 'soundfile': sf.__version__,
                              'libsndfile': sf.__libsndfile_version__,
                              'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0]},
              'public': {item.name: identity(item) for item in sorted((output / 'public').iterdir())},
              'checks': checks, 'source_unchanged': True, 'all_passed': True,
              'scope': 'Exact source-window, fade, decoded duration, gain and codec checks. No listening judgment is implied.'}
    (output / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output', required=True)
    main(parser.parse_args())
