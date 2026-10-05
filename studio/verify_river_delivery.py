"""Verify the finished film's decoded timing and source-to-delivery audio.

Run on the production host. Frame timestamps are read from decoded frames;
container frame counts alone cannot certify the joins between rendered sections.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

import numpy as np
import soundfile as sf


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return {'name': path.name, 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest()}


def inspect_video(path, width, height, codec, pixel_format, *, duration=240, fps=24):
    command = ['ffprobe', '-v', 'error', '-err_detect', 'explode', '-threads', '2',
               '-select_streams', 'v:0', '-show_streams', '-show_frames',
               '-show_entries',
               'stream=codec_name,width,height,pix_fmt,avg_frame_rate,time_base,start_pts,duration_ts,start_time,duration,nb_frames,color_range,color_space,color_transfer,color_primaries:'
               'frame=best_effort_timestamp', '-of', 'json', str(path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    require(not result.stderr.strip(), 'Video decoder reported an error')
    record = json.loads(result.stdout)
    require(len(record['streams']) == 1, 'Expected one selected video stream')
    stream = record['streams'][0]
    for key, expected in {'width': width, 'height': height, 'codec_name': codec,
                          'pix_fmt': pixel_format, 'color_range': 'tv', 'color_space': 'bt709',
                          'color_transfer': 'bt709', 'color_primaries': 'bt709'}.items():
        require(stream.get(key) == expected, f'Unexpected video {key}')
    require(Fraction(stream['avg_frame_rate']) == fps, 'Unexpected frame rate')
    count = duration * fps
    require(int(count) == count, 'Duration must contain a whole number of frames')
    count = int(count)
    require(int(stream['nb_frames']) == count, 'Unexpected container frame count')
    frames = record['frames']
    require(len(frames) == count, 'Unexpected decoded frame count')
    time_base = Fraction(stream['time_base'])
    ticks = Fraction(1, fps) / time_base
    require(ticks.denominator == 1 and ticks > 0, 'Time base cannot represent the requested frame rate')
    ticks = int(ticks)
    timestamps = np.asarray([int(frame['best_effort_timestamp']) for frame in frames], dtype=np.int64)
    require(np.array_equal(timestamps, np.arange(count, dtype=np.int64) * ticks),
            'Decoded presentation cadence changed')
    require(int(stream['duration_ts']) == count * ticks, 'Video duration changed')
    require(int(stream['start_pts']) == 0, 'Video does not begin at zero')
    times = timestamps * float(time_base)
    joins = [round(second * fps) for second in range(12, int(duration), 12)]
    return {'stream': stream, 'decoded_frames': len(frames),
            'first_pts_seconds': float(times[0]), 'last_pts_seconds': float(times[-1]),
            'ticks_per_frame': ticks, 'exact_integer_pts_cadence': True,
            'maximum_pts_error_seconds': 0, 'pts_tolerance_seconds': 0,
            'twelve_second_joins': [{'frame': index, 'pts_seconds': float(times[index]),
                                    'previous_interval_seconds': float(times[index] - times[index - 1])}
                                   for index in joins]}


def audio_payload(path):
    command = ['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2',
               '-i', str(path), '-map', '0:a:0', '-c:a', 'copy', '-f', 'adts', 'pipe:1']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    digest = hashlib.sha256()
    count = 0
    while block := process.stdout.read(1024 * 1024):
        digest.update(block)
        count += len(block)
    detail = process.stderr.read().decode('utf8', errors='replace')
    require(process.wait() == 0 and not detail.strip(), 'Audio packet extraction failed')
    return {'adts_bytes': count, 'adts_sha256': digest.hexdigest()}


def compare_audio(video, source, *, duration=240, silence=(120, 121.8)):
    source_info = sf.info(source)
    count = round(duration * 48000)
    require(source_info.frames == count and source_info.samplerate == 48000
            and source_info.channels == 2, 'Unexpected score master format')
    require(0 <= silence[0] < silence[1] <= duration, 'Invalid silence verification interval')
    native = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                             '-show_streams', '-of', 'json', str(video)],
                            check=True, capture_output=True, text=True)
    require(not native.stderr.strip(), 'Audio stream reader reported an error')
    streams = json.loads(native.stdout)['streams']
    require(len(streams) == 1, 'Expected one selected audio stream')
    audio_stream = streams[0]
    require(audio_stream['codec_name'] == 'aac' and audio_stream['sample_rate'] == '48000'
            and audio_stream['channels'] == 2, 'Unexpected native delivery audio format')
    require(int(audio_stream['start_pts']) == 0, 'Delivered audio does not begin at zero')
    require(Fraction(audio_stream['time_base']) * int(audio_stream['duration_ts']) == Fraction(count, 48000),
            'Delivered audio duration differs from the score')
    command = ['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2',
               '-i', str(video), '-map', '0:a:0',
               '-c:a', 'pcm_f32le', '-f', 'f32le', 'pipe:1']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frames = 0
    square_reference = np.zeros(2)
    square_decoded = np.zeros(2)
    square_difference = np.zeros(2)
    cross = np.zeros(2)
    maximum = np.zeros(2)
    quiet_max = np.zeros(2)
    decoded_hash = hashlib.sha256()
    try:
        with sf.SoundFile(source) as reference:
            while True:
                original = reference.buffer_read(32768, dtype='float32')
                if not len(original):
                    break
                a = np.frombuffer(original, dtype=np.float32).reshape(-1, 2).astype(np.float64)
                data = process.stdout.read(a.shape[0] * 2 * 4)
                require(len(data) == a.shape[0] * 2 * 4, 'Decoded audio ends before the score')
                decoded_hash.update(data)
                b = np.frombuffer(data, dtype='<f4').reshape(-1, 2).astype(np.float64)
                require(np.isfinite(b).all(), 'Nonfinite decoded audio')
                square_reference += np.sum(a * a, axis=0)
                square_decoded += np.sum(b * b, axis=0)
                square_difference += np.sum((a - b) ** 2, axis=0)
                cross += np.sum(a * b, axis=0)
                maximum = np.maximum(maximum, np.max(np.abs(b), axis=0))
                first = max(0, round(silence[0] * 48000) - frames)
                last = min(len(b), round(silence[1] * 48000) - frames)
                if last > first:
                    quiet_max = np.maximum(quiet_max, np.max(np.abs(b[first:last]), axis=0))
                frames += len(b)
        # Some AAC/MP4 decoder paths expose the final padded transform block.
        # Never trim before checking: bound and inspect that tail explicitly.
        allowed_padding = (-count) % 1024
        tail = process.stdout.read((allowed_padding + 1) * 2 * 4)
        require(len(tail) % 8 == 0 and len(tail) // 8 <= allowed_padding,
                'Decoded audio exceeds the score and its possible final AAC padding')
        require(not process.stdout.read(1), 'Decoded audio has further trailing samples')
        tail_values = np.frombuffer(tail, dtype='<f4')
        require(np.isfinite(tail_values).all(), 'Nonfinite AAC padding')
        tail_peak = float(np.max(np.abs(tail_values))) if len(tail_values) else 0.
        require(tail_peak < 1e-5, 'Trailing AAC padding contains audible material')
        decoded_hash.update(tail)
        detail = process.stderr.read().decode('utf8', errors='replace')
        require(process.wait() == 0 and not detail.strip(), 'Audio decoding failed')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    require(frames == count, 'Wrong decoded audio sample count')
    require(np.all(square_reference > 0) and np.all(square_decoded > 0), 'Empty reference or delivered channel')
    correlation = cross / np.sqrt(square_reference * square_decoded)
    signal_to_error = 10 * np.log10(square_reference / np.maximum(square_difference, 1e-30))
    rms_ratio = np.sqrt(square_decoded / square_reference)
    require(np.all(correlation > .99), 'Delivered audio does not match the supplied score')
    require(np.all(np.abs(rms_ratio - 1) <= .01), 'Delivered audio gain differs from the supplied score')
    require(np.all(signal_to_error > 30), 'Delivered audio codec error exceeds the admitted tolerance')
    require(np.all(maximum < 1), 'Decoded audio clips')
    require(np.all(quiet_max < 1e-5), 'The interior of the composed silence is not silent')
    return {'frames_per_channel': frames, 'sample_rate': 48000,
            'decoded_frames_including_padding': frames + len(tail) // 8,
            'trailing_padding_frames': len(tail) // 8, 'allowed_padding_frames': allowed_padding,
            'trailing_padding_peak_linear': tail_peak,
            'native_stream': {key: audio_stream[key] for key in
                              ('codec_name', 'sample_rate', 'channels', 'time_base', 'start_pts', 'duration_ts')},
            'correlation_to_pcm_master': correlation.tolist(),
            'signal_to_error_db': signal_to_error.tolist(),
            'rms_ratio_to_pcm_master': rms_ratio.tolist(),
            'tolerances': {'minimum_correlation': .99, 'maximum_rms_ratio_error': .01,
                           'minimum_signal_to_error_db': 30, 'maximum_silence_or_padding_peak': 1e-5},
            'decoded_peak_linear': maximum.tolist(),
            'silence_interval_seconds': list(silence), 'silence_peak_linear': quiet_max.tolist(),
            'decoded_float32_sha256': decoded_hash.hexdigest(),
            'scope': 'Sample-aligned source correspondence and codec error, not perceived sound quality.'}


def caption_cues(path):
    text = Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    blocks = [block.splitlines() for block in re.split(r'\n[ \t]*\n', text.strip())]
    require(blocks and blocks[0] == ['WEBVTT'], 'Expected the authored WebVTT format')
    stamp = r'(?:\d{2}:)?\d{2}:\d{2}\.\d{3}'
    def milliseconds(value):
        parts = value.split(':')
        hours, minutes, seconds = parts if len(parts) == 3 else ('0', *parts)
        require(int(minutes) < 60 and Fraction(seconds) < 60, 'Invalid caption timestamp')
        return 3600000 * int(hours) + 60000 * int(minutes) + int(Fraction(seconds) * 1000)
    cues = []
    for block in blocks[1:]:
        if block[0] == 'NOTE' or block[0].startswith(('NOTE ', 'NOTE\t')):
            continue
        timing_index = 0 if '-->' in block[0] else 1
        require(len(block) > timing_index + 1, 'Caption cue is missing its timing or text')
        match = re.fullmatch(rf'({stamp}) --> ({stamp})', block[timing_index])
        require(match is not None, 'Unexpected or malformed caption cue')
        payload = '\n'.join(block[timing_index + 1:]).strip()
        require(bool(payload) and '-->' not in payload, 'Empty or malformed caption text')
        cues.append((milliseconds(match[1]), milliseconds(match[2]), payload))
    require(len(cues) == 16, 'Expected all sixteen film notes')
    intervals = [(start, end) for start, end, _ in cues]
    require(all(0 <= start < end <= 240000 for start, end in intervals), 'Caption time outside the film')
    require(all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])),
            'Caption intervals overlap or are out of order')
    require(intervals[-1] == (236400, 240000), 'Closing caption does not match the authored ending')
    return cues


def captions(path, authored=None):
    cues = caption_cues(path)
    if authored is not None:
        require(cues == caption_cues(authored), 'Delivered caption words or times differ from the captured source')
    return {'cues': len(cues), 'last_interval_seconds': [value / 1000 for value in cues[-1][:2]],
            'cue_content_sha256': hashlib.sha256(json.dumps(cues, ensure_ascii=False).encode()).hexdigest(),
            'compared_to_captured_authored_source': authored is not None}


def captured_input(delivery, report, relative, input_key):
    actual = identity(delivery / relative)
    expected = report['inputs'][input_key]
    require(all(actual[key] == expected[key] for key in ('bytes', 'sha256')),
            f'Captured {input_key} differs from the recorded input')
    require(actual == report['files'][relative], f'Captured {input_key} differs from the file inventory')
    return actual


def delivery_editions(delivery, report, *, require_compact=False):
    """A declared compact edition is always verified, even without the CLI flag."""
    editions = [(delivery / 'river-screening.mp4', (3840, 2160), 'hevc', 'yuv420p10le'),
                (delivery / 'river-viewing.mp4', (1920, 1080), 'h264', 'yuv420p')]
    name = 'river-compact.mp4'
    declared = name in report['editions']
    require(declared == (name in report['files']) == ((delivery / name).exists())
            == ('compact' in report), 'Compact edition declaration, inventory or file is inconsistent')
    require(not require_compact or declared, 'The requested compact edition is missing')
    if declared:
        policy = report['compact']
        require(policy['source'] == report['files']['river-screening.mp4'],
                'Compact edition names a different screening source')
        for key, expected in {'resolution': [1280, 720], 'fps': 24, 'video_encoder': 'libx264',
                              'pixel_format': 'yuv420p', 'preset': 'slow', 'crf': 21,
                              'scale_filter': 'lanczos', 'audio': 'packet copy'}.items():
            require(policy.get(key) == expected, f'Unexpected compact edition {key}')
        editions.append((delivery / name, (1280, 720), 'h264', 'yuv420p'))
    return editions


def main(args):
    output = Path(args.output)
    require(not output.exists(), 'Choose a fresh verification output')
    began = time.monotonic()
    delivery = Path(args.delivery)
    report_path = delivery / 'delivery.json'
    report = json.loads(report_path.read_text())
    require(report['edition'] == 'final', 'Only a declared final delivery can be admitted')
    audio = identity(args.audio)
    require(audio == report['inputs']['audio'], 'Supplied score is not the recorded delivery input')
    screening = delivery / 'river-screening.mp4'
    viewing = delivery / 'river-viewing.mp4'
    result = {'format': 'palimpsest-river-delivery-review-v1',
              'delivery_receipt': identity(report_path), 'score': audio, 'editions': {}}
    render_id = captured_input(delivery, report, 'source/render-receipt.json', 'render_receipt')
    render = json.loads((delivery / 'source/render-receipt.json').read_text())
    if 'picture' in render:
        require(render['picture'] == report['inputs']['video'], 'Assembly receipt names a different source picture')
    else:
        require(render['video'] == report['inputs']['video']['name']
                and render['bytes'] == report['inputs']['video']['bytes'],
                'Render receipt names a different source picture')
    result['captured_render_receipt'] = render_id
    result['picture_input_binding'] = ('SHA256 from assembly receipt' if 'picture' in render
                                       else 'Name and byte count from original render receipt; no source-picture hash in that receipt')
    for path, dimensions, codec, pixels in delivery_editions(
            delivery, report, require_compact=bool(getattr(args, 'compact', False))):
        file_id = identity(path)
        require(file_id == report['files'][path.name], 'Delivery bytes differ from the recorded output')
        result['editions'][path.name] = {'identity': file_id,
            'picture': inspect_video(path, *dimensions, codec, pixels),
            'audio': audio_payload(path)}
        require(result['editions'][screening.name]['audio'] == result['editions'][path.name]['audio'],
                f'{path.name} soundtrack differs from screening soundtrack')
    if 'compact' in report:
        result['compact_policy'] = report['compact']
    result['audio_source_comparison'] = compare_audio(viewing, args.audio)
    captured_caption_id = captured_input(delivery, report, 'source/captions-source.vtt', 'captions')
    caption_id = identity(delivery / 'river-notes.vtt')
    require(caption_id == report['files']['river-notes.vtt'], 'Delivered caption bytes differ from the recorded output')
    result['captions'] = {**captions(delivery / 'river-notes.vtt', delivery / 'source/captions-source.vtt'),
                          'identity': caption_id, 'captured_source': captured_caption_id}
    result.update(verified_utc=datetime.now(timezone.utc).isoformat(),
                  elapsed_seconds=time.monotonic() - began,
                  source=identity(__file__), all_passed=True,
                  scope='Decoded timing at every frame, exact audio packet retention, uncropped source-aligned codec comparison and captured caption text/timing. Visual and auditory interpretation require separate review.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'all_passed': True, 'output': str(output),
                      'elapsed_seconds': result['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery', required=True)
    parser.add_argument('--audio', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--compact', action='store_true',
                        help='Require the compact edition; any recorded compact edition is always verified')
    main(parser.parse_args())
