# PALIMPSEST

**An instrument that becomes its own score.**

A phrase presses into an invented material. The impression it leaves changes the material's tuning. Those changed voices return as a different force. Later, the phrase comes back to an instrument that has already lived through it.

Conceived, coded and composed by Codex, 3–4 October 2026.

[Enter the exhibition](https://site-inky-eight-42.vercel.app) · [Play the material](https://site-inky-eight-42.vercel.app/instrument.html) · [Explore 120 possible pasts](https://site-inky-eight-42.vercel.app/atlas.html) · [Download the film edition](https://github.com/bernietorfen/palimpsest/releases/tag/v1.0.0)

## The work

The edition includes a seven-minute, twelve-second 4K film and original stereo soundtrack; three 8000 × 10000 prints; a matched first/return diptych; three textured glTF/STL sculptures; an 18-page illustrated notebook; and an audible atlas of all 120 orders of five writing gestures.

The exhibition lets you compare the first and returning phrase, turn the actual sculptures in an original WebGL viewer, and choose two histories from the exhaustive atlas. Its media loads on request.

The live edition lets you write your own phrase into the material and ask it again. Its original JavaScript solver, WebGL surface and AudioWorklet voices run in the browser. Keep the timing and pressure of a phrase, compare its changing replies, export a measured vector drawing, save the complete material state, or take a closed STL sculpture from your performance. [Download the standalone instrument](https://github.com/bernietorfen/palimpsest/releases/tag/v1.1.0), or read [the live edition record](research/LIVE-EDITION.md) for its equations, checks and limits.

The material coupling, score, synthesis, sculpture geometry, shaders, camera sequence, glyph system and experiments are authored here. The project does not import an artificial-life system, procedural presets, meshes, photographs, sampled music or trained-model output. Established ingredients and neighboring artistic practices are acknowledged in [the provenance record](research/ORIGINALITY.md).

## The instrument

Four fields describe a periodic sheet: displacement, velocity, retained rest-shape inscription and fatigue. Twelve authored spatial patterns connect that sheet to twelve voices. Signed inscription and fatigue alter pitch; altered pitch changes the phase of a delayed spatial force. The repeated phrase therefore encounters an instrument changed by its own history.

The rolled, open sculpture is an artistic mapping of the recorded fields. Its apertures represent wear; they do not simulate physical fracture. The model is an invented instrument, not a claim about biological memory or a calibrated material.

## The experiment

All 120 permutations of five writing gestures receive the same later 14-second probe after their displacement, velocity, phase and delay transients are reset. Their two retained fields remain.

| Observation | Recorded result |
|---|---:|
| Smallest difference among 7,140 pairs, timestep 1/96 s | 0.171444 Hz RMS |
| Smallest difference at timestep 1/192 s | 0.175995 Hz RMS |
| Finer-step histories closest to their own coarse-step record | 120 / 120 |
| Smallest difference when the last three writing gestures are identical, 1/96 s | 0.298446 Hz RMS |
| Fully erased probe versus fresh control | Exactly equal |

The metric spans all twelve pitch readouts and 336 times, including voices not currently excited. These numeric results do not establish that every pair can be distinguished by ear. The refinement comparison holds the spatial grid fixed; it is not a continuum convergence proof or a noise-robust memory-capacity estimate.

The audible atlas renders the actual recorded controls with the original synthesizer. Every history uses the same gain, room, seed and boundary fades. The fresh and erased PCM sound masters match byte for byte.

## Source and reproduction

- [Model and update order](research/MODEL.md)
- [Reproduction guide](REPRODUCE.md)
- [Authorship and prior context](research/ORIGINALITY.md)
- [Verification record](VERIFICATION.md)

The implementation is organized under `studio/`; the static exhibition and original browser renderers are under `site/`. The release contains the finished media, checksums, a complete viewing-room bundle and the scientific record. Source is kept separate from generated media.

Production used an NVIDIA RTX 4090 on RunPod. No simulation, rendering, synthesis, model execution or browser testing ran on the authoring laptop.

The work claims an original construction and composition. It does not claim to be the first artwork about hysteresis, feedback, memory or sound sculpture. Sound was measured for duration, loudness, peak and signal structure; a supported perceptual audition path was unavailable to the authoring assistant.
