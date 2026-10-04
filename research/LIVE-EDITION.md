# PALIMPSEST: the playable material

The live edition lets a visitor write into the material, hear its changing voices, keep a phrase, and ask it again. A captured phrase preserves the pressure envelopes on the simulation clock. It can be replayed against the current material or a fresh one. The two recorded replies become a paired vector drawing. A material can also be saved, reopened, or exported as a closed STL sculpture.

## Numerical scope

`site/live-material.js` expresses the original material equations in JavaScript. The interactive grid is 64 × 64, the fixed timestep is 1/96 second, and the internal arrays use double precision. The studio performance uses a 128 × 128 grid and single precision. These are distinct editions; the live response is not advertised as the identical film trajectory.

The port was compared against a double-precision PyTorch reference using the same grid, forcing, forgetting schedule and update order. Three 24-second cases cover 64-grid timesteps of 1/96 and 1/192 second, plus a 128-grid 1/96-second case. The maximum absolute field or phase error was below 3 × 10⁻¹³. See `live-material-001.json`.

Three additional 600-second trajectories exercise the maximum twelve-voice chord, alternating writing and forgetting, and seeded changing gestures at the UI pressure limit. All remained finite, with inscription bounded by ±0.8 and fatigue by [0, 1]. These are tested trajectories, not a formal stability proof. See `live-stress-001.json`.

## A phrase and its return

`site/live-score.js` stores changes to the target envelopes at material-step indices, together with the initial envelope state. Capture lasts at most 24 seconds, followed by two seconds of release. Replaying uses the same fixed-step envelope update. No animation-frame timestamps are substituted for the material clock.

The implementation check captured seven gesture events over 7.208333 seconds. Replaying from a fresh material reproduced every force envelope, complete material state and sampled pitch readout exactly. Repeating on the changed material produced a 3.605929 Hz RMS difference across 173 samples and twelve voices. This is an implementation check, not an audibility result. See `live-score-001.json`.

The live comparison includes displacement, velocity, inscription, fatigue, echo phase and delayed feedback present at the start of a reply. Unlike the controlled 120-history experiment, it does not reset transients to isolate the two retained fields.

The four glyph rings sample the response at approximately 10%, 37%, 64% and 91% of its recorded duration. Angular positions identify the twelve voices. Radial deviations from each faint circle encode departures from the original tuning. Both drawings share the same maximum-deviation scale. The standalone SVG includes the complete compared trajectories and metric as metadata.

## Sound and sculpture

The AudioWorklet calculates twelve continuously phased voices with eight inharmonic partials and a smaller displaced ringing mode. Control smoothing is causal. The live synthetic room is shorter than the studio room, and a bounded waveshaper plus a compressor precedes the user volume control. No audio samples are loaded. Browser playback and signal meters are checked; no perceptual audition is claimed.

The surface uses the same authored chart coordinates, deformation and aperture rule as the studio sculpture. The live renderer samples the 64-grid fields directly. The STL exporter clips chart triangles, shares cut vertices and closes every boundary with a wall between the two sheet faces. It scales the largest extent to 200 mm.

Four live states were exported in JavaScript and independently reopened with trimesh. All were watertight with consistent winding and nondegenerate faces. Their sampled chart positions and aperture values agreed with the studio equations to below 10⁻⁶. Later states can contain separate fragments. These checks do not certify self-intersection freedom, structural adequacy or physical printability. See `live-geometry-001.json`.

## Browser state and resources

The worker runs only after an explicit start. Leaving the tab pauses the material and sound. Fixed-step catch-up is capped; a slow device slows the material clock instead of accumulating a backlog or changing the integration step. Render data uses a transferred buffer returned to the worker. There is no frame history.

At most one phrase, the last two completed reply trajectories, one current reply, and one undo material are retained. Geometry is built only on export. Graphics use one field texture, one indexed mesh and one shadow texture. Generated download URLs are revoked after use. The source has no analytics, accounts, external runtime library or server-side session.

The actual browser file round trip preserves every field, delay value, echo phase and clock value exactly. A saved phrase is validated before it can replace the current material. Fresh-material reset has one-step undo. The Chromium and iPhone-sized WebKit checks cover gestures, audible signal generation, pause, real file download/import, continued evolution and horizontal layout. See `live-file-roundtrip-001.json` and the browser audit records.

## Reproduction

Use Node 24 for the standalone JavaScript checks, and the studio Python environment for the independent reference checks. Run these on the authorized compute host:

```sh
node studio/live_material_check.mjs 64
python -m studio.verify_live_material --node /path/to/node
node studio/live_score_check.mjs
node studio/live_stress_check.mjs
node studio/live_geometry_check.mjs
python -m studio.verify_live_geometry
```

The geometry check writes a new output directory and refuses to overwrite it. Browser audit scripts under `studio/audit_live*.js` run through Playwright against `studio.serve_site` on loopback port 8083. Generated media and test artifacts stay on the compute host and are preserved through verified GitHub release assets.
