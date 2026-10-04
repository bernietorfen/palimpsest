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

## Recovery follow-up

The live follow-up keeps a single recovery entry in the browser's session storage. It replaces that entry every five seconds while playing and when paused; it does not retain a growing history or send state to a service. An entry is capped at 1,500,000 JSON characters. A crash or immediate navigation can recover the last completed copy, so an actively played material may return a few seconds behind. File export remains the durable way to keep a material across tabs and browser sessions.

Saved documents now optionally include the last two completed reply trajectories. Their length, sample-step sequence and twelve finite pitch values are validated before any existing material is replaced. Original version-one documents without replies remain accepted. Recovery restores the paired drawing as well as the fields and kept phrase.

A real Chromium Back-navigation check initially returned to a zero state. With recovery enabled, the paused material's time, inscription and wear were restored exactly. A separate reload check compared the complete numerical state, phrase and both reply trajectories and found them identical; its one recovery entry contained 404,354 characters. New material replaced that entry and reload did not resurrect the discarded state. These are specific browser checks, not a guarantee that every browser preserves session storage after a tab is closed.

A forced WebGL context loss now pauses the instrument and rebuilds its graphics resources after restoration. The material remains in its worker. One 64 KB field copy restores the displayed surface without accumulating frames. Chromium and iPhone-sized WebKit checks recovered an identical complete material state and an identical paused camera image, then continued the simulation.

A finite but extreme imported displacement previously produced a non-finite trajectory and repeatedly re-entered the pause handler. The reproduction was stopped by its test harness after eight pause requests. The worker now reports a numerical fault once, stops scheduling frames, and requires a fresh or opened material before continuing. A test-only injection of one NaN at step 42 confirmed a single fault and a single pause, no subsequent message loop, and successful writing after New material. The invalid state is not retained as an undo target or offered for export.

File admission also bounds displacement to ±16, velocity and delayed projection to ±64, and echo phase to [0, 2π). These are broad file-validation limits, separate from the unchanged evolution equations. They are not a stability theorem or clamps applied during simulation. The recorded ordinary trajectories fit inside them.

The subsequent Chromium and WebKit file checks saved a material with two completed replies, cleared the tab's recovery storage, reloaded to an empty instrument, and opened the downloaded JSON. The complete numerical state, phrase, both replies and paired drawing returned exactly. Their one-entry recovery copies contained 408,969 and 404,843 characters respectively. A browser with deliberately denied session-storage access continued to play and offered normal file saving.
