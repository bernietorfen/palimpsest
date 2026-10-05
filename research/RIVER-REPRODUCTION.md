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
  studio/tests/test_river_camera.py studio/tests/test_river_pickups.py -q
```

The renderer and encoded film are not expected to be byte-identical across GPU,
driver and codec versions. Exact source and data hashes identify the published
production; numerical checks use the stated tolerances.

## Scientific records

Read each protocol before interpreting its results. In a fresh workspace, these
commands generate new records at the canonical paths. They do not replace
verification of the published files.

The release's [complete finite-time study archive](https://github.com/bernietorfen/palimpsest/releases/download/a-river-twice-1/palimpsest-finite-time-studies-001.tar.gz)
retains the raw arrays, failed operational run, frozen producing sources,
tests, protocols and independent reviews. The unchanged result reports and
review JSON files are also retained under `records/river/` in the source
repository, separate from fresh computation outputs. To restore the complete
archive, create an empty `artifacts/` directory in the project and extract the
archive into it. Its `studies/` and `reviews/` members then occupy the canonical
paths used below. Those restored study directories already exist: skip their generation
commands below rather than trying to write over them. To recompute all
studies, use a separate fresh workspace. A new environment-study run can use
restored prerequisite records and its own fresh output directory.

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

The exhibition's listening pair uses two short windows of that same master,
keeping its common gain and stereo. Generate them with the explicit source
receipt; the output records the boundary fades, codec checks and public hashes:

```sh
python -m studio.river_listening_pair \
  --master artwork/river-audio-new/river-full.wav \
  --receipt artwork/river-audio-new/manifest.json \
  --output artwork/river-listening-pair-new
```

## Film

Run the following with Blender 4.5.1 on the rendering host to render the
complete camera edition. It entails thousands of GPU-rendered frames.

```sh
blender -b -t 6 --python-exit-code 1 --python studio/river_sequence.py -- \
  --output artwork/river-master-new --start 0 --duration 240 \
  --fps 24 --width 3840 --height 2160 --samples 24 --detail-sampling \
  --ten-bit --frame-format tiff --full-frame --crf 16 \
  --encode-preset fast --encode-threads 8 --segmented --titles --camera-revision
```

The frame sample limits are 24 for the broader views, 32 for declared intimate
views and 48 for the isolated reference. The camera, source and typography are
frozen before rendering. Each frame records its actual timing, camera, light,
reference selection and sample limit. The renderer streams one temporary
16-bit image and keeps sparse checkpoints instead of thousands of previews.
Closed-GOP twelve-second segments preserve finished sections during production;
the final silent film concatenates those encoded segments without re-encoding.

The camera revision follows connecting fibres during three passages between
136 and 180 seconds. Every other camera interval, the geometry, phase time,
lighting and music retain their original definitions. The production uses a
complete original render plus replacement sections covering 132–180 seconds;
the surrounding unchanged seconds align the replacement to twelve-second
section boundaries. `river_picture_assembly.py` checks both renders and their
absolute model/light records before joining the selected sections. Rendering
the complete edition with `--camera-revision` applies the same camera choices
directly. The published receipts identify the actual production inputs.

The isolated reference geometry returns at film times 0, 104 and 208 seconds.
The controlled comparison uses equal camera and light settings and separately
reports raster differences: mathematically matching shapes do not promise
bit-identical stochastic renderings. Text in the standalone film is a separate
authored layer; the first exact reference frame and the central silence have
no title overlay.

## Delivery and companion

The delivery builder copies the 4K picture into a screening MP4, adds the
stereo soundtrack, and creates a 1080p H.264 viewing edition, poster and captions.
The optional compact edition supplies 720p playback for slower connections.
Pass the exact rendered and synthesized inputs, with their receipts:

```sh
python -m studio.river_delivery \
  --video artwork/river-master-new/river-silent-10bit.mp4 \
  --audio artwork/river-audio-new/river-full.wav \
  --render-receipt artwork/river-master-new/render.json \
  --audio-receipt artwork/river-audio-new/manifest.json \
  --captions research/RIVER-CAPTIONS.vtt \
  --output artwork/river-delivery-new --edition final --crf 20 --compact
```

The builder checks the stream durations, audio format, complete viewing decode
and encoded silence. Independently verify the finished delivery:

```sh
python -m studio.verify_river_delivery \
  --delivery artwork/river-delivery-new \
  --audio artwork/river-audio-new/river-full.wav \
  --output artifacts/reviews/river-delivery-new.json --compact
```

This checks all 5,760 decoded frames in each edition, their 24-fps timestamps
and twelve-second joins, retained AAC packets, source-aligned audio and
caption timing. `river_film_review.py` provides a compact all-frame image
review with declared dark intervals. Browser checks exercise actual media
playback, seeking, native captions, fullscreen, recovery and the observer.
Signal and playback checks are not perceptual listening tests.

`river_notebook.py` builds the illustrated companion from explicitly supplied
plates and admitted scientific records. Generate the controlled reference
and whole views with the same completed geometry. This produces seven 4K
stills, then checks that the camera agrees within each comparison, that the
reference returns within the declared raster tolerance, and that the wider
views differ. These controlled views have their own fixed camera and light;
they are not extracted frames from the moving film.

```sh
blender -b -t 6 --python-exit-code 1 --python studio/river_proofs.py -- \
  --output artwork/river-matched-new --matched --camera-revision \
  --width 3840 --height 2160 --samples 64
python -m studio.river_match_check \
  --proof artwork/river-matched-new --output artwork/river-matched-check-new
```

For the cover, extract the wide view at 03:08 from the completed film. The
comparison inside the book uses the full, equally sized reference images
at 00:00 and 01:44. No separate crop is applied to either comparison image.
Inspect these supplied plates before admitting a final book.

```sh
mkdir artwork/river-book-plates-new
ffmpeg -hide_banner -loglevel error -nostdin -n -ss 188 \
  -i artwork/river-master-new/river-silent-10bit.mp4 \
  -frames:v 1 artwork/river-book-plates-new/wide.png
```

The first three study paths below match the canonical prerequisite records.
The environment-study and review overrides point to the new outputs in the
scientific example above; the notebook's production defaults are different.

```sh
python -m studio.river_notebook \
  --wide artwork/river-book-plates-new/wide.png \
  --macro artwork/river-matched-new/00-local-000.000.png \
  --return-before artwork/river-matched-new/00-local-000.000.png \
  --return-after artwork/river-matched-new/01-local-104.000.png \
  --visual-receipt artwork/river-matched-check-new/comparison.json \
  --film-receipt artifacts/reviews/river-delivery-new.json \
  --audio-receipt artwork/river-audio-new/manifest.json \
  --clock-study artifacts/studies/relational-clock-001 \
  --time-study artifacts/studies/time-ambiguity-001 \
  --operational-study artifacts/studies/operational-time-001/run-002 \
  --environment-study artifacts/studies/clock-environment-new \
  --environment-review artifacts/reviews/clock-environment-new.json \
  --artwork-status final --output artwork/river-notebook-new
```

Use `--artwork-status draft` for unfinished plates. The final setting is
appropriate only for accepted artwork and supplied receipts; it does not
assert a perceptual listening result. The package retains document source,
inputs, layout checks and dependency identities. It copies the installed
DejaVu and Liberation license texts into its `licenses/` directory, covered
by the package manifest. These are separate source-package files, not license
attachments embedded inside the PDF. The public release manifest identifies
the actual finished files and their SHA-256 digests.
