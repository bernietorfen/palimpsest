# Reproducing PALIMPSEST

Use an authorized Linux GPU host. Production used Python 3.12.3, PyTorch 2.8.0 with CUDA 12.8, an RTX 4090 and NVIDIA's EGL/OpenGL renderer. GPU simulations can vary with hardware and library versions; compare numeric results at stated tolerances rather than assuming universal binary identity.

The release contains the actual scientific record and finished media. Its JSON manifest lists sizes and SHA-256 digests. Verify downloads before extracting the archive into an empty directory. The viewing-room archive expands into `site/`; the scientific record preserves the relative `artifacts/` and `artwork/analysis/` paths used by the production tools.

The publication revision of 4 October 2026 changes editorial text and selected PDF passages. It preserves numerical arrays and finished media. Repackaged archives include `PUBLICATION-REVISION.json`, which maps altered members from their original identities to current digests. Historical generation and test receipts describe the original production; their PDF and source-text hashes can therefore differ from the revised publication. Use the current release checksums and archive inventories to verify downloads.

## Environment

Install a compatible CUDA build of PyTorch on the GPU host, then install `studio/requirements.txt`. System tools are FFmpeg, Poppler and the DejaVu fonts. ModernGL must create an EGL context backed by the NVIDIA device; software rendering is unsuitable for the full film.

```sh
python -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -r studio/requirements.txt
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
python -m pytest studio/tests -q
```

The following commands are ordered by their data dependencies. They refuse to replace existing study directories or media in most production stages. Use a fresh workspace, or choose new output paths and update dependent paths deliberately.

## Material performance and sound

```sh
python -m studio.simulate --output artifacts/studies/performance-002 --duration 432 --save-fields
python -m studio.sound --readouts artifacts/studies/performance-002/readouts.npz --output artwork/previews/score-002.wav
python -m studio.master_sound
```

The simulation records 10,369 frames including the endpoint. Field arrays use channel order displacement, inscription, fatigue, velocity. Saved performance fields are float16 for storage; modal readouts are float32, and selected states and the checkpoint preserve full simulation precision. Rendering reconstructs the stored fields; it does not feed image processing back into the numerical instrument.

The film score and the controlled experiment use different feedback settings. The film follows `Score.controls`; `numerical_assay.record`, reused by the exhaustive history atlas, explicitly applies feedback 0.08. That override is effective even where an older raw configuration report also records the constructor's default of 0.20.

## Controlled experiments and atlas

```sh
python -m studio.assay --output artifacts/studies/memory-assay-002
python -m studio.numerical_assay --output artifacts/studies/numerical-assay-001
python -m studio.history_atlas --output artifacts/studies/history-atlas-001 --rates 96 192
python -m studio.atlas_compare --output artwork/analysis/history-refinement-001
python -m studio.atlas_figures --output artwork/analysis/history-atlas-002
python -m studio.atlas_assets --output artwork/atlas-edition-001
```

Each of the 120 histories receives the same multiset of writing gestures, then the same probe. Before probing, `u=p`, velocity, delay and phase are reset; inscription and fatigue remain. This removes local elastic strain but does not guarantee spatial equilibrium. Equal gesture norms do not imply equal mechanical work.

The audio edition uses 336 recorded controls at 24 Hz. Its excerpt ends at the final available sample, 335/24 seconds. It does not invent a missing endpoint. A fixed gain of 2.5, 0.12-second start fade and 0.8-second end fade apply to every history.

## Film and sculptures

```sh
python -m studio.film --fields artifacts/studies/performance-002/fields.npy \
  --audio artwork/masters/palimpsest-soundtrack.wav \
  --output artwork/masters/palimpsest-film-4k-001.mp4 \
  --width 3840 --height 2160 --samples 128 --area-shadow \
  --shadow-size 4096 --mesh-u 256 --mesh-v 512 \
  --codec h265 --bit-depth 10 --crf 17 --preset medium
python -m studio.export_sculpture --time 0 --output artwork/sculptures/state-000
python -m studio.export_sculpture --time 165 --output artwork/sculptures/state-165
python -m studio.export_sculpture --time 358 --output artwork/sculptures/state-358
python -m studio.plates --output artwork/masters/plates-001
python -m studio.plates --only-diptych --output artwork/masters/diptych-002
```

The master is HEVC Main 10, limited-range BT.709 at 24 fps. Both streams start at zero and last 432 seconds. The glTF files use meters; STL exports use millimeters and a 200 mm maximum extent. Watertightness and winding were checked after export. Physical fabrication, every possible self-intersection, and universal printability have not been established.

## Notebook and exhibition

```sh
python -m studio.analyze_performance
python -m studio.notebook_figures --output artwork/notebook/figures-002
python -m studio.notebook --output artwork/masters/palimpsest-notebook.pdf --edition 'First edition / 4 October 2026'
python -m studio.viewing_assets --output artwork/exhibition-002 --crf 27
python -m studio.stage_site artwork/exhibition-002
python -m studio.stage_site artwork/atlas-edition-001/public
python -m studio.serve_site --port 8083
```

The server binds only to the GPU host's loopback interface. Use an authorized browser on that host. It supports media byte ranges; a server without range support can make Chromium treat the audio as unseekable.

The website uses self-hosted fonts and assets. It needs no accounts, tracking, database, paid API, external model, runtime backend or simulation server. The atlas plays recorded responses; the sculpture viewer renders the exported meshes. Its browser source is ordinary JavaScript and WebGL2.

## Verification

```sh
ffprobe -v error -show_streams -show_format -of json artwork/masters/palimpsest-film-4k-001.mp4
ffmpeg -hide_banner -nostdin -v error -threads 6 -i artwork/masters/palimpsest-film-4k-001.mp4 -map 0:v:0 -map 0:a:0 -f null -
```

The source includes numerical, reconstruction, geometry, preservation and rendering tests. Browser audit functions are supplied for Playwright CLI. Their checks concern visible state, input behavior and media properties; they are not perceptual listening tests.

## Playable edition

The live instrument has no Python or GPU-server dependency at runtime. It uses a fixed-step JavaScript worker, WebGL2 and Web Audio. Its standalone archive includes the original source and the licensed type files; serve that archive over a loopback HTTP server on an authorized computer. Opening the HTML directly as a `file:` URL will not provide the worker and audio-module origin required by browsers.

The film edition and live edition are separate frozen releases. Extract each archive into its own empty directory. Do not unpack an older viewing-room archive over a newer source checkout: it contains the HTML of its own edition.

Node 24 runs the JavaScript equation, phrase-replay, stress and geometry checks. The independent PyTorch and trimesh comparisons run in the studio environment. Complete commands, numeric results and interpretation limits are in [the live edition record](research/LIVE-EDITION.md).

The recovery follow-up adds `node studio/live_recovery_check.mjs` and focused browser functions `audit_live_recovery.js`, `audit_live_storage.js`, `audit_live_storage_denied.js`, `audit_live_navigation.js` and `audit_live_fault.js`. Run each in a fresh browser context unless its instructions explicitly exercise reload or Back. The separate `audit_live_failure_repro.js` records the pre-fix extreme-import defect and is not an expected-to-pass check of the corrected source.

## An imperfect hand

The pressure edition contains both complete experiments, including their original generation-source snapshots, and the two original canonical atlas pitch files needed by their verifiers. Its archive includes a per-file SHA-256 manifest. Extract into an empty directory and add the matching tagged source; avoid overwriting records with a new generation run.

To reproduce from the canonical atlas on the GPU host:

```sh
python -m studio.pressure_study
python -m studio.verify_pressure
python -m studio.check_pressure_reader
python -m studio.pressure_reading
python -m studio.verify_pressure_reading
python -m studio.pressure_summary
python -m studio.pressure_visuals --output artwork/analysis/pressure-reading-003
python -m studio.stage_site artwork/analysis/pressure-reading-003/public
```

The first pressure experiment admits the batched solver against the original scalar implementation and canonical atlas before generating varied cases. The second checks that the admitted material source is unchanged and that its separate algebra check matches the exact reader source. Both experiments refuse to overwrite their output directories. Read `research/PRESSURE-STUDY.md`, `PRESSURE-READING.md` and `PRESSURE-RESULTS.md` for the fixed seeds, sampling rules, controls and interpretation.

The separate `palimpsest-imperfect-hand.zip` opens the interactive study without simulation dependencies. Its `START-HERE.txt` describes a loopback-only static server; all case data and fonts are included. The study's external exhibition and release links require a connection. The figure and browser glyph data are display derivatives; full-precision calculations use the raw scientific archive.

## Registered spatial study and complete notebook

The v1.3.0 continuation includes the complete 71-file spatial study and the exact sampled images used in the 24-page notebook. Its record archive also includes the two canonical atlas pitch files used by the spatial admission checks. The published source supplies the generators and independent verifier.

```sh
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python -m studio.spatial_study
python -m studio.verify_spatial_study
python -m studio.continuation_figures --output artwork/notebook/continuation-001
python -m studio.complete_notebook --output artwork/masters/palimpsest-complete-notebook.pdf
```

Generation refuses to overwrite existing result directories. Run a fresh experiment in a separate checkout, or verify the frozen data without regenerating it. The spatial generator admits the finer grids directly against the scalar implementation and the original grid against the saved canonical atlas. The continuation archive includes `first-dialogue.svg` at `artwork/live-edition-002/` and the pressure display data at `artwork/analysis/pressure-reading-003/public/`, allowing its figures to be regenerated without fetching the earlier releases. It preserves every notebook image at its original path, the required earlier atlas/refinement reports, and the new figure record. These inputs rebuild the book with the matching tagged source. The original film pages and final pages retain the first-edition composition; six new pages connect the playable, pressure and spatial work.

## Portable installation

The v1.4.0 ZIP includes the prepared `site/` directory, all viewing and interaction assets, the complete notebook and the three-grid print PDF. Its `START-HERE.txt` gives a loopback-only static-server command. The browser requires that server; opening HTML directly as `file:` is unsupported. All experiential assets are local. Catalog entries marked Online and external authorship references still require an internet connection.

`studio.prepare_installation` builds the archive from the prepared current site and frozen v1.3.0 book/print inputs. It changes only local links and the portable catalog, and records every file digest. `studio.verify_installation` restores each entry to a new proof directory and checks all file hashes before browser testing. The installation's embedded content manifest records the exact source commit and describes the portable link changes.

## Second act: A choir of absences

The v2.0.0 scientific archive contains the complete seven-body performance,
all three explorations, the locked transfer experiment, the frozen mechanical
calculation, exact image inputs to the second notebook, and the captured source
that produced these records. Extract it into an empty directory and add the
matching tagged source. Verification of frozen data and generation of new data
are separate operations: the generators refuse to overwrite their study roots.

The studio grid is 64 by 64 per body, with 96 steps per second and 24 recorded
field frames per second. The browser uses 32 by 32 at the same timestep. Each
bridge has sixteen bead masses. The first-act equations remain the underlying
body model; `choir_material.py` adds reciprocal ports and old-state bridge forces.

```sh
python -m pytest studio/tests/test_choir.py studio/tests/test_choir_geometry.py studio/tests/test_choir_energy.py -q
python -m studio.choir_transfer_study
python -m studio.verify_choir_transfer
python -m studio.choir_performance
python -m studio.choir_frozen_analysis
python -m studio.choir_figures
```

For a restored scientific record, run the verifier with a new `--output` report
path instead of rerunning the generation commands into its existing directories.
The transfer verifier independently reconstructs the interventions and analysis;
it does not claim an independent implementation of the generating dynamics.
The frozen calculation explicitly uses thirteen Galerkin coordinates per body,
plus all 192 beads. It is not a full-grid eigenvalue calculation.

The original sound and its constant-gain master can be reproduced as follows:

```sh
python -m studio.choir_sound --output artwork/choir-sound-002.wav
ffmpeg -hide_banner -nostdin -i artwork/choir-sound-002.wav \
  -af volume=21.49dB -c:a pcm_s24le artwork/masters/choir-soundtrack.wav
python -m studio.choir_film \
  --output artwork/masters/choir-of-absences-4k.mp4 \
  --audio artwork/masters/choir-soundtrack.wav \
  --width 3840 --height 2160 --fps 24 --samples 32 \
  --nu 128 --nv 192 --shadow 2048 --bits 10 --preset medium --crf 18
```

The film has 6,912 frames. The field record has an additional endpoint frame.
The soundtrack uses continuous synthesis phases, eight partials per voice and
an authored observer mix. The listening piece deliberately removes that mix:
it uses identical phases and one common gain for each forty-second comparison.
E has identical saved synthesis controls and PCM, and both E buttons point to
the same encoded sound. The comparison metric uses the half-open forty-second
window, while interpolation retains the saved endpoint.

```sh
python -m studio.choir_witness --output artwork/choir-witness-002
python -m studio.choir_plates
python -m studio.choir_sculpture --state encounter --output artwork/choir-sculptures/encounter-master
python -m studio.choir_sculpture --state after --output artwork/choir-sculptures/after-master
python -m studio.choir_sculpture --state source --output artwork/choir-sculptures/source-master
python -m studio.choir_notebook --output artwork/masters/a-choir-of-absences-notebook.pdf
```

The sculpture masters use 128 by 192 mesh samples and 256-pixel component
textures. The encounter and after meshes are scaled to a 600 mm maximum extent;
the isolated source uses 200 mm. Browser meshes use smaller resolutions recorded
in their manifests. Exported STL files contain separate closed components;
they do not include physical supports.

The second notebook uses the exact image paths preserved in the scientific
archive. Its PDF generation fixes container metadata for deterministic rebuilding
with the recorded libraries and fonts. The recorded film-source snapshot contains
an overly broad prose claim about matched cameras: the exact matching intervals
are `5 <= t < 28` and `248 <= t < 271`, both 23 seconds. The two widenings have
different durations. The quality record preserves the original source and states
this correction; camera code and rendered frames are unchanged.

The browser equation comparison is `studio/verify_choir_live.mjs`, with its
independent Python reference generator in `studio/verify_choir_live.py`.
`node studio/choir_stress.mjs NEW_REPORT.json` performs the declared 600-second
stress trajectory. Browser checks use Playwright and axe-core installed under
`.tools/browser/node_modules`, with Node 24 on the GPU host. The choir, pointer,
interaction, witness and second-act scripts accept fresh evidence directories;
read each script's positional arguments before invoking it. They check actual
playback and signal generation, not perceptual listening.

`studio.prepare_second_installation` freezes both prepared acts and their local
viewing films into `palimpsest-two-acts.zip`. Its included `serve.py` supports
byte ranges and binds only to loopback. The separate larger masters and research
archives remain optional online links. `studio.verify_installation` can restore
this ZIP with `--manifest two-acts-installation.json --archive palimpsest-two-acts.zip`.
Every restored file is hashed before browser verification.

## Received histories: the four-token follow-up

`RECEIVED-HISTORIES-PROTOCOL.md` fixes all 24 orders of four source contacts,
receiver observations, timesteps and the numerical acceptance gate. The failed
packed-chain admission remains in `received-histories-001`. Read the declared
`RECEIVED-HISTORIES-REVISION-001.md` before interpreting the successful
`received-histories-002`: its writing histories run individually. Neither the
contacts nor the scientific criteria changed. The single-chain admission uses
the reference saved by the first attempt, so that small failed-run directory is
also required for reconstruction.

The full archived result can be checked without generating another trajectory:

```sh
python -m studio.verify_received_histories --output research/received-rechecked.json
python -m studio.received_history_art --output artwork/received-history-art-rebuilt
python -m studio.proof_received_history_art \
  --art artwork/received-history-art-rebuilt --output artwork/received-history-proof-rebuilt
```

The art generator reads `received-histories-002`, uses one common centering and
scale, and creates a vector print, a 6000 by 7500 raster print, two evidence
figures and a four-page companion. It uses the existing NumPy, Matplotlib,
Pillow, ReportLab, DejaVu and Poppler dependencies. The drawing is an authored
projection; the independent verifier uses all full saved trajectories.

To generate new data, start with fresh output paths and follow the protocol and
revision. `studio.received_histories` implements the admitted single-chain
revision. The originally rejected implementation is preserved in the source
snapshot inside `received-histories-001`; the second directory also carries its
own producing snapshot. The separate
research companion preserves the eighteen-page second-act notebook unchanged.
Both PDFs and the received-history print are included in the two-act portable
installation, alongside the first-act notebooks and three-grid print.

## The observer and third timestep

The v2.1.0 observer archive is self-contained for the original 24-order study,
its rejected packing admission, the declared 192/384-step follow-up, both offset
diagnostics and the observer artwork. Its producing snapshots retain the exact
code used in each run. The earlier full-performance archive remains in v2.0.0.

On the restored observer record, use new verification output paths:

```sh
python -m studio.verify_received_histories \
  --study artifacts/studies/received-refinement-001 \
  --output research/refinement-rechecked.json
python -m studio.verify_observer_offset \
  --study artifacts/studies/observer-offset-001 \
  --output research/offset-first-rechecked.json
python -m studio.verify_observer_offset \
  --study artifacts/studies/observer-offset-002 \
  --output research/offset-second-rechecked.json
python -m studio.observer_offset_art --output artwork/observer-art-rebuilt
```

For new generation into an empty study path, `studio.received_histories` accepts
`--rates 192 384 --follow-up-plan research/OBSERVER-REFINEMENT-PLAN.md
--reference-study artifacts/studies/received-histories-002`. It repeats all
192-step arrays and requires their exact agreement with the preserved reference
before beginning 384 steps. The default 96/192 experiment is unchanged. A
nondefault rate pair requires the declared plan and a reference study.

The offset diagnostic uses the complete balanced collection to establish a
common origin. It does not replace the original raw reader or provide a test
of one unknown history. The geometric print uses exact own/rival projections;
its companion explicitly preserves the original six mistaken matches.

The v2.1.0 portable installation also includes the observer companion and print.
Its choir keeps the user's transport intent separate from delayed worker frames,
and importing a saved encounter suspends active sound. Changing the sound
preference while paused leaves the audio context suspended until Resume. The material equations
and saved-state format are unchanged.

## The moving observer

The v2.2.0 moving-observer record contains the original 96/192 near-receiver
trajectories, their offset diagnostic, the compact interaction dataset and a
self-contained copy of the moving-print page. After restoring it beside the
matching source:

```sh
python -m studio.observer_interaction --output artwork/origin-rebuilt
python -m studio.verify_observer_interaction \
  --data artwork/origin-rebuilt/observer-origin-v1.json \
  --output research/origin-rebuilt-verification.json
python -m studio.serve_site --port 8080
```

Open `/observer.html` on the loopback server. The work has no model or rendering
service dependency. Its continuous control evaluates the complete candidate
quadratics; the passage's dwell timing is authored. The displayed six strips
are exact pair-direction projections. All counts use the full trajectories.
The exported SVG embeds fonts, license, current fraction, candidate sets and
source hashes. The supplied specimen is an actual export at the fourth crossing.

The complete two-act portable ZIP includes this work, its fonts and coefficients.
Earlier frozen editions retain their own source identities and files.

## Quiet-choir analytical afterword

The v2.3.0 analytical supplement includes `quiet-choir-record.tar.gz` and its
complete file-hash manifest. Extract it into a new directory. Its two existing
NPZ inputs, scene, proof and source are sufficient for the declared checks;
no earlier large scientific archive is required. With the project's prepared
Python scientific runtime, run from that directory:

```sh
python -m studio.choir_decay_bound --output research/rebuilt-decay.json
python -m studio.choir_decay_figure --output artwork/rebuilt-decay
```

The stored report is `research/choir-decay-bound-003.json`; the figure defaults
to those certified bounds. The first command recomputes all exact certificates,
full-grid checks and nonlinear derivative checks. The second draws analytical
ceilings, not sampled trajectories. Scope and assumptions are in
`research/CHOIR-DECAY.md`.
