# A River Twice: score contract

This is a composed soundtrack for an original film about return, observation and what an encounter leaves behind. Musical writing, instrument design, spatialization and dramatic timing are authored. A recognizable motif and a disappearing voice carry the human relation. The soundtrack is not a quantum measurement, reconstruction of physical sound, or claim about biological memory.

## Composition versions

A complete 66-second miniature establishes an intimate call, a distinct reply, a developing counterpoint, a brief crest, a decisive removal, true silence and an altered return. Its exact event list, dramatic cues and individual role stems are preserved. The 240-second full score develops this language through separately written phrases and a second orchestral arc.

All synthesis and analysis run on the production GPU server, using CPU synthesis while graphics renders use the GPU. No audio samples, trained models, external music services or borrowed music are used. Compact listening copies accompany the lossless masters and isolated stems.

## Musical identity

The call is D–F–E–A–D, initially D4–F4–E4–A4–D5. Its uneven spacing has a breath: two close steps, a longer reach to A, then a delayed high D. The recognizable interval/rhythm relation survives when its register, carrier and harmony change. This is an original short motif, not a claim that no similar five-note sequence has ever existed.

The tonal world begins in D with open fifths and an added ninth, moves through B-flat and G, and gathers on an A suspension. Harmonic motion is sparse but deliberate. Upper voices must not merely double every bass change. The crest grows through counterpoint, register and attack density before gain. The return retains the motif while the original felt/plucked source remains absent.

## Instrument roles

| Role | Audible identity by design | Synthesis | Dramatic job |
|---|---|---|---|
| `felt` | Warm, close, quick felted/plucked attack with a darker long body | Phase-consistent modal sum with frequency-dependent decay, a short filtered original-noise exciter and a slight downward settling of pitch | The identifiable source; states the call and is removed at the loss |
| `breath` | Sustained, rounded harmonic voice with an audible soft intake and modest organic motion | Harmonic/formant weighting, deterministic filtered noise, slow amplitude and pitch modulation, soft attack/release | Answers, then inherits the motif after the source leaves |
| `bow` | Low, grainy support that swells rather than striking | Warm odd/even harmonic bank, slow colored-noise bowing component and separately written envelopes | Supplies changing harmonic ground and weight; never an unbroken drone |
| `glass` | Sparse high clear strikes with a short contact and long, thin decay | Authored inharmonic resonant ratios, frequency-dependent decay, quiet excitation noise | Fleeting phase/clock accents and isolated highlights, not constant sparkle |
| `pulse` | Small dry wooden/skin-like impacts, pitched loosely to harmonic roots | Decaying low oscillator plus original filtered-noise contact | Makes the braid move; absent from opening and return |

No instrument is a sampled or modeled imitation of a named performer or existing instrument library. Labels are qualitative synthesis descriptions. Sustain timbres have distinct envelopes and register roles; a shared reverb must not erase their differences.

## Miniature timeline

| Interval | Name | Main event | Intended contrast |
|---|---|---|---|
| 0–9 s | A first mark | Close felt call, very little accompaniment | Intimate, legible, dry |
| 9–19 s | Someone answers | Breath reply, isolated high echo, gentle harmonic change | A second identity enters |
| 19–34 s | What passes between | Shorter exchanged fragments, a growing pulse and bass movement | More direction and interlock, not just louder |
| 34–43.1 s | The almost-return | Register opens; a held upper response meets the completed source call | Brief maximum density and harmonic suspension |
| 43.1–45.4 s | The source leaves | Original source is removed; a fragile residual tail remains | Audible absence of a known role |
| 45.4–47.05 s | No answer | Exact zero samples in every public stem and mix after a smooth preceding release | Actual silence, not a quiet pad |
| 47.05–61.8 s | The familiar question, elsewhere | Motif returns distributed through breath, bow and glass; felt and pulse stay absent | Recognition with a missing carrier |
| 61.8–66 s | What remains | Final open D/A resonance decays | A changed world remains after motion ends |

The silence is an authored edit to the musical room as well as the dry events. Reverb is explicitly brought to zero before it, so an apparently silent clip does not retain inaudible tails. No abrupt discontinuity is permitted at its edges.

## Event and cue data model

Each `NoteEvent` has a stable `id`, `instrument`, `start`, `duration`, MIDI `pitch`, `velocity` in [0,1], `pan` in [-1,1], `brightness` in [0,1], `attack`, `release`, optional `detune_cents`, optional harmonic `phase` in radians and a semantic `phrase` label. `duration` is the audible note envelope before its release tail. The score manifest includes total duration, sample rate, declared original motif, sections, exact silence interval, dramatic cue timestamps, instrument descriptions, deterministic random seed and an ordered complete event list.

Each `Cue` contains `time`, `name`, `description` and the related event IDs where relevant. Film alignment can use semantic cues without reverse-engineering waveforms. Notes remain musical events, while cues describe visual/narrative opportunities.

A later optional control table may map normalized material or phase observables to small bounded changes in brightness, stereo width or breath. Such a mapping must be named and exported. It must not silently quantize measured pitches into musical notes and present the result as strict sonification. The first proof is fully composed and deterministic; no scientific controls are attached yet.

## Rendering and preservation

`studio/river_score.py` owns the event/cue model and score. `studio/river_sound.py` owns synthesis, room, mix, mastering and checks. Each role is rendered separately to 48 kHz stereo floating-point WAV before a common documented master gain. Preserve dry/source stems, delivery stems whose sum matches the delivered mix, the original float mix, a PCM24 listening master, a compact MP3 proof, manifest and exact score JSON under a new immutable output directory. A small mono listening proof helps detect stereo cancellation. Avoid dumping spectrograms or per-note WAVs.

The room consists only of authored deterministic delays and filtered decays. Panning uses equal-power gains. The center information remains present in mono. Source silence is meaningful: the `felt` stem has no new notes after the source leaves and is exactly zero from the silence onward.

## Acceptance checks

- Every sample is finite; channel count, rate and exact duration agree with the manifest.
- Master peak retains headroom. Report true-peak estimate and integrated/short-time loudness when FFmpeg is available; constant gain and any dynamics are stated.
- Event attack and release envelopes start/end at zero; inspect maximum adjacent-sample difference and peak behavior at phrase/silence boundaries, without pretending these meters prove musicality.
- The exact silence interval has zero samples in every delivered stem, including room return.
- Source `felt` and pulse roles remain absent after the loss.
- Delivered stems reconstruct the mix within floating-point storage tolerance.
- Report stereo correlation and mono/stereo energy ratio, with per-section RMS to confirm contrast and avoid a continuously maximal master.
- Keep a compact event map and musical/technical critique. Actual listening judgment is separate from objective measurements. If no supported audio perception path is available, say so.

## Full film score: 240-second development

The 66-second miniature remains an unchanged proof preset. The full score is a separately authored composition, not a timing stretch. Its first contact occurs at 1.1 seconds, a distinct breath answer begins at 10.25 seconds and the first shared phrase begins at 21.4 seconds.

The full score uses the same original call but changes what the surrounding harmony makes of it. The first half inhabits D minor, with B-flat and G moving toward A and a first D-minor crest. The second rise begins in a warmer F-major/B-flat/C field; D–F–E–A–D then has a different harmonic place. No pitch sequence alone is claimed as universal novelty.

| Interval | Musical work |
|---|---|
| 0–32 | Intimate call and tangible answer; sustained ground enters only when useful. A shared fragment reveals the relation before 22 seconds. |
| 32–88 | Interlocking phrases, short cells, held counterlines, displaced accents and occasional rests; the score grows through changing roles rather than a continuous arpeggio. |
| 88–112 | First broad crest, followed by an unsettled thinning. The source can still carry the whole call. |
| 112–119.6 | Withdrawal. Felt's last incomplete statement loses its final answer. Both its dry sound and synthetic-room contribution are fully zero by 118 seconds. |
| 119.6–122.2 | Exact zero in every delivered stem and mix. |
| 122.2–156 | The familiar call is augmented and distributed among surviving roles. A sparsely scored gap lets the changed timbres register. |
| 156–208 | A new `thread` voice leads a warmer collective rise. This is a soft, friction-bearing harmonic string synthesis with distinct attack, spectral weighting and bow-shaped envelope; no string samples are used. It enters as a new participant rather than impersonating the removed felt voice. The pulse returns quietly as a shared motion, while felt remains absent. |
| 208–228 | The recognizable call returns in the new harmonic context. The collective response is fuller without restoring the original source. |
| 228–240 | No new attack after 228 seconds. Open D/A resonance, with a remembered E, dies into the held final image. |

Withdrawal is an authored choice of musical voice and visibility. The film's separate finite unitary scientific model does not destroy information irreversibly. Musical absence must not be described as a quantum loss process or evidence of thermodynamic irreversibility.

The full score manifest declares its title and preset, the roles permanently withdrawn after the loss, and an exact per-role mute time. These controls distinguish the full film's return of pulse from the miniature, where both felt and pulse remain absent. Every role uses the same master gain, so delivered stems retain their relation and sum to the master. The new `thread` role is absent from the original proof preset.

## First full-score rendering record

The first full draft contains 312 explicit events: 85 felt, 71 breath, 41 low bow, 25 glass, 42 pulse and 48 thread events. The last felt dry envelope ends at 117.28 seconds; its delivered stem, including synthetic room, is exactly zero from 118 seconds. The final new attack is at 227.8 seconds.

The 240-second 48 kHz stereo PCM24 master measures -18.0 LUFS integrated loudness, 10.0 LU loudness range and -2.5 dBTP. It uses one constant +5.098 dB master gain, without compression or limiting. The declared silence contains zero nonzero samples. Summed delivery stems reproduce the float master within 1.20e-7; mono energy is 0.065 dB below the mean stereo energy.

The first crest's 88–96-second window measures -15.6 dBFS RMS. The collective second arc grows from -22.6 dBFS RMS at 156–164 seconds to -18.3 at 204–212 seconds. It reaches recognition through a new carrier, register and harmonic setting, while remaining gentler than the first crest. These are signal measurements, not perceptual findings.

A preservation check rebuilt the 66-second preset with the expanded synthesizer: its score JSON and MP3 remain byte-identical and every decoded WAV sample is identical. Floating-point WAV container metadata can vary with write time. The original proof remains intact; temporary regression audio was removed after comparison.

The full score, role stems, exact cues, source snapshot and checks are preserved with the rendering. Audio perception was not available in the production review environment. The documented conclusions concern authored composition and acoustic checks; emotional effectiveness remains a listening judgment.

## Second mix: changing the shared space

The selectable `spatial-v1` mix preserves all 312 score events, pitches, note envelopes, cues and synthesized instrument waveforms. It changes direct panning, smooth role-bus levels and sends into the original deterministic room. Pan is chosen at each note attack; level and send curves use smoothstep interpolation. The exact curves and every resulting note pan are exported in `mix-automation.json`. The default `reference` mix remains available, and the miniature retains its original treatment.

The source is close and consistently left of center before withdrawal. The answering voices occupy a progressively wider field. The inherited glass fragment receives a brief 1.6 dB lift; the new bowed thread receives a shaped 2.2–3 dB lift, with a small reduction in the low support. The thread enters near the departed source's side, then opens farther into the shared space. These are composed balance and spatial choices, not measurements of physical propagation. Direct voices are not delayed or phase-inverted to manufacture width.

The second 240-second master measures -17.7 LUFS integrated, 9.9 LU loudness range and -2.5 dBTP. One common +5.296 dB master gain is applied, with no compressor or limiter. The first crest remains stronger than the second rise: their complete 88–112 and 180–208-second windows measure -16.63 and -19.74 dBFS RMS. The final release is not raised uniformly with the ensemble.

Compared with the reference, the 180–208-second window's left/right correlation changes from 0.972 to 0.874 and side-to-mid energy from -18.23 to -11.67 dB, while its RMS rises by 0.41 dB. The opening becomes drier and more correlated. Side energy also includes stable lateral placement, so it must not be read as a pure measure of room size. The second rise's isolated thread share increases from about 16% to 29%; these fractions omit inter-stem cross terms and do not prove auditory masking or emotional clarity. Whole-program mono energy loss is 0.172 dB; the tested section windows remain within 0.286 dB.

Both masters are preserved. Their score JSON and score source are byte-identical. The original master hashes are unchanged. The new delivered stems reproduce its float master within 1.20e-7. The PCM24 master, float master and all delivered stems retain exact zero samples from 119.6 to 122.2 seconds, and felt remains zero from 118 seconds. Dry stems precede the new role gains and room; processed stems include the common master gain. Approximately level-matched excerpts apply one fixed -0.3 dB adjustment to the second mix, preserving relative section dynamics. No listening judgment is claimed.

## Listening pair

The exhibition offers two twelve-second windows from the chosen spatial mix:
0–12 seconds and 208–220 seconds. They retain the full musical context, original
common gain and stereo image. They are excerpts of the composition, not
isolated instruments or measured sonification.

The preparation applies a 25 ms entry fade and a 180 ms closing fade followed
by 64 ms of silence. The short silent ending contains AAC's transform tail.
Outside those boundaries, the PCM samples match the source master exactly.
The 48 kHz stereo AAC files retain native twelve-second timelines; their decoded
RMS ratios to the edited PCM are 0.999681 and 0.999601, with signal-to-codec-error
ratios of 50.75 and 47.96 dB. The extra decoded half-frame of AAC padding is
exactly silent. These checks concern delivery fidelity, not a listening verdict.

The first MP3 attempt was rejected because its encoder reduced the excerpt's
RMS to approximately 0.97004 of the source. An initial AAC attempt exposed a
small transform tail beyond the presentation interval. Both attempts remain
in the production record; the accepted excerpts use the explicit silent
boundary guard. The original full score and its mix were never changed.

`studio/river_listening_pair.py` captures the exact source master, edit recipe,
producer, helper source and codec environment. Its public provenance record
identifies both small listening files. Native controls let a visitor compare
them at their own pace; their original balance is kept rather than normalized
separately.
