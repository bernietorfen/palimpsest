# Reproducing PALIMPSEST

Use an authorized Linux GPU host. Production used Python 3.12.3, PyTorch 2.8.0 with CUDA 12.8, an RTX 4090 and NVIDIA's EGL/OpenGL renderer. GPU simulations can vary with hardware and library versions; compare numeric results at stated tolerances rather than assuming universal binary identity.

The release contains the actual scientific record and finished media. Its JSON manifest lists sizes and SHA-256 digests. Verify downloads before extracting the archive into an empty directory. The viewing-room archive expands into `site/`; the scientific record preserves the relative `artifacts/` and `artwork/analysis/` paths used by the production tools.

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
