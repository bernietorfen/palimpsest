# A River Twice: a woven view of recurrence

The film uses an original procedural architecture of 32 folded bands, arranged
as four interleaved families of eight around an asymmetric opening. Its meshes,
fibres, materials, lights and camera are authored in source. No existing mesh,
photograph, environment image or generated-model footage is used.

The underlying state is the 32-level finite unitary family in
`RELATIONAL-CLOCK-PROTOCOL.md`. Film seconds map to model time by
`t_model = 2*pi*t_film/104`. Within-family phase relations return at film times
104 and 208 seconds. The full state generally differs at those instants.

Both real and imaginary components of phase relations affect the folds. The
reference family's shape depends only on its internal phase differences. The
surrounding families also encode their phase relative to the reference mode.
Short joining fibres encode cross-family coherence in two spatial directions.
All geometry is invariant to a common global phase. This is an artistic
embedding, not a physical material simulation or an image of quantum matter.

An isolated reference view at 0, 104 and 208 offers a matched visual comparison;
the camera then opens onto the changed surroundings. Camera moves, visibility
and lighting are composed observations. The state continues evolving through
the authored 119.6–122.2-second blackout. Removing a voice from the separate
musical score does not erase a component of this unitary model.

The film is a human interpretation of a precise distinction: recognizing a
familiar part does not settle whether its relationships have returned. Neither
the calculation nor the composition establishes a result about human memory,
a thermodynamic arrow or the metaphysical nature of time.

Production uses Blender Cycles with original procedural surfaces and lighting.
Each sequence captures its exact source and camera score before rendering.
Frames stream into the encoder through one temporary image; sparse checkpoints
and numerical geometry checks are retained. Resolution, samples, durations,
source hashes and actual rendering time are recorded by the producing program.
Final delivery specifications belong to the final receipt, not this plan.

After the silence, three camera passages follow the centre of actual joining
fibres. At 136–148 seconds, a copper connection becomes the subject between
two banks of folded material. At 160–172 seconds, another woven connection
stays legible as the new bowed voice develops. The cut at 172 seconds opens
outward into upright ribs before the wider view at 180 seconds. These authored
changes of attention preserve the phase state, geometry, lighting and score.
The quieter arch between them gives the two fibre studies room to differ.

## The standalone film

Sparse typography supplies the title without covering the recurring stitch.
The first exact reference frame remains untouched; the title appears between
2.5 and 7.3 seconds. The final observer rests from 222 seconds while the shape
continues changing. From 235 to 236.2 seconds, the authored view fades to black.
The closing lines read “The phrase returns. / The voice does not.” They refer
to the musical carrier that remains absent, not erasure in the unitary model.
The central 119.6–122.2-second silence has no burned-in text.

`river_typography.py` records the exact timing, fonts and filter expressions.
Liberation Serif and DejaVu Sans are existing open fonts; their files, hashes
and license notices accompany a titled render. Typography is applied to the
high-bit-depth displayed image before video encoding. The independently
computed geometry and its controlled comparison images do not include titles.

## Viewing compression

Two completed twelve-second 4K sections were encoded at H.264 CRF 18, 20 and 22
with the same 1080p Lanczos conversion. CRF20 retained the fine surface structure
in inspected native-size crops while using approximately one quarter fewer
bytes than CRF 18 in those sections. Their full-image SSIM scores were 0.987242
and 0.989121 at CRF 20. These finite comparisons support the viewing edition's
chosen compression setting; they are not perceptual scores for the film.
The screening edition retains the 4K 10-bit picture stream without re-encoding.
