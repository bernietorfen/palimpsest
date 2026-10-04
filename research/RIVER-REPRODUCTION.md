# Reproducing A River Twice

The new movement uses its own phase model, meshes, camera score and synthesizer.
It does not require the earlier material simulations to render the film or run
its scientific studies. Use an authorized Linux compute host for execution.
Keep output directories new: production tools refuse to overwrite their records.

## Environment

Production uses Python 3.12, NumPy, SciPy, mpmath, Pillow, Matplotlib, ReportLab,
SoundFile and PyMuPDF, plus FFmpeg 6.1.1, Blender 4.5.1, Liberation fonts and
DejaVu fonts. The film renders with Cycles on an NVIDIA RTX 5090. Each study or
media package captures the source, parameters and relevant dependency versions
used for that output. Those receipts, rather than a current package index,
describe the recorded environment.

Install the Python dependencies from `studio/requirements.txt` in the compute
host's environment. Production used mpmath 1.3.0, threadpoolctl 3.7.0, PyMuPDF
1.28.2 and ReportLab 5.0.1 for the scientific/document path. Blender and FFmpeg
are separate applications, with the two font packages available to both.

The scientific calculations are small CPU workloads. Limit BLAS threads; they
need no GPU or machine-learning framework. Film rendering uses the GPU. The
soundtrack uses deterministic numerical synthesis on the CPU.

```sh
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
python -m pytest studio/tests/test_relational_clock.py \
  studio/tests/test_time_ambiguity.py studio/tests/test_operational_time.py \
  studio/tests/test_clock_environment.py \
  studio/tests/test_river_camera.py -q
```

The renderer and encoded film are not expected to be byte-identical across GPU,
driver and codec versions. Exact source and data hashes identify the published
production; numerical checks use the stated tolerances.

## Scientific records

Read each protocol before interpreting its results. In a fresh workspace, these
commands generate new records at the canonical paths. They do not replace
verification of the published files.

```sh
python -m studio.relational_clock --output artifacts/studies/relational-clock-001
python -m studio.time_ambiguity --output artifacts/studies/time-ambiguity-001
python -m studio.operational_time --output artifacts/studies/operational-time-001/run-002
python -m studio.clock_environment --output artifacts/studies/clock-environment-new
python -m studio.verify_clock_environment \
  --study artifacts/studies/clock-environment-new \
  --output artifacts/reviews/clock-environment-new.json
```

The first record checks the phase model, observation graph and noise bound.
The second checks finite-resolution ambiguity, its local expansion and the
declared finite scan. The third preserves an exact integer certificate and
independent high-precision and density-operator calculations for cycle 4109.
The scientific archive includes the failed first operational-study execution
and the corrected run; the scientific criteria were unchanged.

The fourth study checks six declared times and three preparations of a finite
two-state environment. Its generator verifies that the three earlier records
exist under their recorded canonical paths and remain unchanged. If they have
already been restored from the publication, skip generating them again. The
fourth command's output may be any new directory. Its independent verifier imports no generator module
and reconstructs all eighteen cases using 80-digit operators in the exact
stroboscopic group subspace.

The browser's clock specification is data, not a screenshot of those results.
Its JavaScript module computes both coherence quadratures and the declared
observation metrics from the selected model time. Changing the observer leaves
the state unchanged. The browser verification checks this distinction.

## Original score

```sh
python -m studio.river_sound --preset full --mix spatial-v1 \
  --sample-rate 48000 --output artwork/river-audio-new
```

`river_score.py` defines the note events. `river_sound.py` defines the six
synthesis roles, deterministic reflection response and spatial automation.
The output retains the original score, role stems, float mix and a common-gain
24-bit stereo master. The master is 240 seconds long. Its interior silence
spans 119.6–122.2 seconds; the source role stays absent after 118 seconds.
No limiter or compressor supplies the final gain.

## Film

Run the following with Blender 4.5.1 on the rendering host. This is the full
production command, so it entails thousands of GPU-rendered frames.

```sh
blender -b -t 6 --python-exit-code 1 --python studio/river_sequence.py -- \
  --output artwork/river-master-new --start 0 --duration 240 \
  --fps 24 --width 3840 --height 2160 --samples 24 --detail-sampling \
  --ten-bit --frame-format tiff --full-frame --crf 16 \
  --encode-preset fast --encode-threads 8 --segmented --titles
```

The frame sample limits are 24 for the broader views, 32 for declared intimate
views and 48 for the isolated reference. The camera, source and typography are
frozen before rendering. Each frame records its actual timing, camera, light,
reference selection and sample limit. The renderer streams one temporary
16-bit image and keeps sparse checkpoints instead of thousands of previews.
Closed-GOP twelve-second segments preserve finished sections during production;
the final silent film concatenates those encoded segments without re-encoding.

The isolated reference geometry returns at film times 0, 104 and 208 seconds.
The controlled comparison uses equal camera and light settings and separately
reports raster differences: mathematically matching shapes do not promise
bit-identical stochastic renderings. Text in the standalone film is a separate
authored layer; the first exact reference frame and the central silence have
no title overlay.

## Delivery and companion

The delivery builder copies the 4K picture into a screening MP4, adds the
stereo soundtrack, and creates a 1080p H.264 viewing edition, poster and captions.
Pass the exact rendered and synthesized inputs, with their receipts:

```sh
python -m studio.river_delivery \
  --video artwork/river-master-new/river-silent-10bit.mp4 \
  --audio artwork/river-audio-new/river-full.wav \
  --render-receipt artwork/river-master-new/render.json \
  --audio-receipt artwork/river-audio-new/manifest.json \
  --captions research/RIVER-CAPTIONS.vtt \
  --output artwork/river-delivery-new --edition final
```

The builder checks the stream durations, audio format, complete viewing decode
and encoded silence. `river_film_review.py` provides a compact all-frame image
review with declared dark intervals. Browser checks then exercise actual media
playback, seeking, native captions, fullscreen, recovery and the observer.
Signal and playback checks are not perceptual listening tests.

`river_notebook.py` builds the illustrated companion from explicitly supplied
plates and scientific records. Supply `--wide`, `--macro`, the controlled return
pair and the actual media receipts. `--artwork-status final` is appropriate only
for accepted final artwork. The package retains the document source, font
licenses, inputs, layout checks and dependency identities. The public release
manifest identifies the actual finished files and their SHA-256 digests.
