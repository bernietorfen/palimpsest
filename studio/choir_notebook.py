"""An eighteen-page second-act artist's notebook, built and proofed on RunPod."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from studio.notebook import Book,MUTED,INK
from studio.preserve import sha256

FIGURES=Path('artwork/choir-figures-001')
PLATES=Path('artwork/choir-plates-001')
WITNESS=Path('site/assets/generated/choir-witness')
SOURCES=('studio/choir_notebook.py','studio/notebook.py','studio/choir_figures.py','research/CHOIR-PROTOCOL.md','research/CHOIR-RESULTS.md','research/CHOIR-ENERGY.md')


class ChoirBook(Book):
    def __init__(self,path):
        for relative in SOURCES:
            if not Path(relative).is_file():
                raise FileNotFoundError(relative)
        super().__init__(path,'Second act / A choir of absences / 4 October 2026',invariant=True)
        self.c.setTitle('PALIMPSEST / A choir of absences')
        self.c.setSubject('Original composition, reciprocal material choir, retained transfer and the boundary of observation')
    def finish(self):
        self.c.save();hashes={}
        for relative in SOURCES:
            source=Path(relative);destination=self.path.with_suffix('')/'source'/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination);hashes[relative]=sha256(source)
        report={'created_utc':datetime.now(timezone.utc).isoformat(),'pages':self.page_number,'edition':self.edition,'pdf_sha256':sha256(self.path),'source_sha256':hashes,'embedded_image_sha256':self.assets,'page_inventory':self.records,
                'scope':'An original artist notebook with finite-model evidence and an explicitly restricted frozen-system energy argument.'}
        self.path.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'path':str(self.path),'pages':self.page_number,'bytes':self.path.stat().st_size,'sha256':report['pdf_sha256']}),flush=True)


def paired(book,body,y=157,width=350,height=292):
    for side,x in [('before',48),('after',466)]:
        book.image(WITNESS/f'{body}-{side}.jpg',x,y,width,height)
        book.text_line(x,y-17,f'{body} / '+('Before the encounter' if side=='before' else 'After the source leaves'),9,'Sans',MUTED)


def opening(book):
    book.page('An original work in two acts')
    book.image(PLATES/'the-source-view.jpg',454,75,350,437.5)
    book.text_line(48,440,'A choir of',39,'Serif')
    book.text_line(48,384,'absences.',48,'Serif')
    book.paragraph('A voice enters.<br/>Its encounter remains.',48,325,345,17,25)
    book.paragraph('An artist\'s notebook<br/>Composition, material and evidence',48,185,350,11,18)
    book.text_line(48,86,'Conceived, coded and composed by Codex',9,'Sans')
    book.text_line(48,66,'3-4 October 2026',9,'Sans',MUTED)

    book.page('The proposition')
    book.heading('An encounter can outlive its source.')
    book.image(PLATES/'02-encounter-scene.jpg',355,206,461,259)
    y=book.paragraph('The first PALIMPSEST was a solitary surface: a phrase wrote into it, changed its tuning and returned to an instrument with a past. This second act lets that past pass between bodies.',48,514,274,12,19)
    book.paragraph('Seven pleated vessels are joined by twelve wave bridges. Only B receives the writing contacts. After the connections leave, other bodies answer from an encounter that never touched them directly.',48,y-25,274,11,18)
    book.paragraph('The shapes, space and light are authored embeddings of the numerical fields. An actual encounter supplies the shared state of sculpture and sound.',355,180,461,10.5,17)

    book.page('A matched installation')
    book.heading('The source goes. The consequence stays.')
    book.image(PLATES/'01-before-scene.jpg',48,300,363,204)
    book.image(PLATES/'03-after-scene.jpg',453,300,363,204)
    book.text_line(48,282,'42 seconds / Before the encounter',9,'Sans',MUTED)
    book.text_line(453,282,'288 seconds / After the source leaves',9,'Sans',MUTED)
    book.paragraph('The views share one camera, light and scale. At the beginning all seven bodies remain visible and uninscribed. At the end B has left the visible installation; its six listeners remain.',48,244,363,11,17)
    book.paragraph('The numerical source state is still preserved. Its visual departure does not add a force to the material. Every connection has already reached zero before the source moves out of the composition.',453,244,363,11,17)
    book.paragraph('The openings depict accumulated wear. They do not simulate fracture. The bridges follow actual simulated bead motion, although their drawn lengths are not calibrated physical lengths.',48,104,768,10,15)

    book.page('The score')
    book.heading('One writer. Six listening bodies.')
    book.image(FIGURES/'the-score.png',48,140,768,411)
    book.paragraph('The 288-second composition asks its quiet question at 5 and 248 seconds. The shaded intervals mark the two forty-second replies. B is written at three distinct spatial ports; no other body receives a writing contact.',48,126,363,10,15)
    book.paragraph('Spokes enter at 48-58 seconds; the outer circle at 96-108. All links fade out at 228-236. At 242 seconds, the dotted line, a disclosed intervention clears transient motion, delay and phase while keeping inscription and wear.',453,126,363,10,15)

    book.page('The witness')
    book.heading('One observer hears an unchanged world.')
    paired(book,'E',y=212,width=350,height=292)
    book.paragraph('These portraits show E sixteen seconds into each question, in the same isolated pose and light. E\'s recorded pitch, amplitude and fatigue controls agree exactly across the two forty-second windows.',48,157,363,11,17)
    book.paragraph('The listening piece uses identical synthesis phases, filtering and one common gain. The resulting PCM samples for E also agree exactly. Both E choices therefore use the same encoded sound. This equality belongs to the saved finite-precision comparison.',453,157,363,11,17)

    book.page('Beyond the witness')
    book.heading('Another voice carries another past.')
    paired(book,'G',y=212,width=350,height=292)
    book.paragraph('The same view of G reveals an altered body. Its returning pitch record differs by 4.694452 Hz RMS across twelve modes and forty seconds. A changes by 3.410914 Hz; C by 4.052326 Hz. D and F change much less.',48,157,363,11,17)
    book.paragraph('The film first foregrounds E, then widens the camera and listening. The close camera matches for the opening\'s 5 <= t < 28 seconds and the return\'s 248 <= t < 271 seconds. The widenings have different durations. The listening piece lets the visitor choose the witness.',453,157,363,10.5,16)


def mechanism(book):
    book.page('The reciprocal interface')
    book.heading('A connection both listens and pushes back.')
    book.image(FIGURES/'the-reciprocal-bridge.png',48,260,768,294)
    book.paragraph('A port reads the spatial mean of displacement against a localized Gaussian footprint. The endpoint spring returns force through that same footprint. Between the bodies, sixteen damped masses carry the wave.',48,239,363,11,17)
    book.paragraph('This matched reader and force map makes the bridge force the negative gradient of a single quadratic potential. Body and bridge forces are both computed from the same old state before either subsystem advances.',453,239,363,11,17)
    book.code(['q_A = mean(phi_A * u_A)', 'V_bridge = (k*g/2) * sum((w[j+1] - w[j])^2)', 'w[0] = q_A;  w[K+1] = q_B;  k = tension_bridge*(K+1)'],x=48,y=118,size=10,leading=20)

    book.page('The retained material')
    book.heading('Each listener keeps two kinds of trace.')
    book.image(FIGURES/'seven-retained-fields.png',48,270,768,256)
    book.paragraph('The actual fields at 228 seconds, just before the links fade. <b>p</b> is signed rest-shape inscription. <b>z</b> is wear. Every panel uses the same scale for its field. B carries the strongest change; E remains unwritten in the recorded state.',48,243,363,11,17)
    book.paragraph('A body\'s twelve voices read signed projections of p and weighted averages of z. Their tuning alters the phase of a delayed spatial force, closing the active feedback loop. The bridges themselves carry instantaneous motion, not a second invented memory.',453,243,363,11,17)
    book.code(['pitch[m] = base[m] * sqrt(1 - 0.58*wear[m]) * exp(0.65*memory[m])'],x=48,y=87,size=10,leading=18)

    book.page('The controlled question')
    book.heading('Remove the source. Clear the motion. Ask again.')
    book.paragraph('The composition is not its own control experiment. A separate locked study uses a three-body chain: source 0, receiver 1, receiver 2. Only source 0 receives four writing contacts over thirty seconds.',48,519,363,11,17)
    book.paragraph('Twelve deterministic phrases were specified after exploratory runs and before evaluation. The set is repeated at 96 and 192 steps per second on a 64 x 64 grid. An early narrow-port trial gave the second receiver zero retained difference. Increasing contact overlap and drive changed several parameters together. The selected settings are an authored choice; this internal locked plan is not an independent preregistration.',453,519,363,10.5,16)
    book.text_line(48,361,'WRITE',10,'Sans',MUTED)
    book.code(['source 0  <---- bridge ---->  receiver 1  <---- bridge ---->  receiver 2'],x=48,y=330,size=11)
    book.text_line(48,285,'CUT AND CLEAR',10,'Sans',MUTED)
    book.code(['all links = 0;  u = retained p;  velocity = delay = phase = 0'],x=48,y=254,size=11)
    book.text_line(48,209,'PROBE',10,'Sans',MUTED)
    book.code(['same quiet question --> receiver 1       same question --> receiver 2'],x=48,y=178,size=11)
    book.paragraph('The source receives no later gesture and no source signal is mixed into the measured receivers. Additional conditions remove the second writing link, erase p, erase z, or erase both. The complete phrases, coordinates, rates and admission rule are recorded before the evaluation is run.',48,131,768,10.5,16)


def evidence(book):
    book.page('The retained transfer')
    book.heading('All forty-eight receiver cases pass the locked gate.')
    book.image(FIGURES/'controlled-transfer.png',48,232,768,318)
    book.paragraph('Every plotted point is a saved deterministic case, not a population estimate. The connected history differs from the isolated history after the links and transient state have been removed. The fixed admission threshold is 0.01 Hz RMS.',48,216,363,10.5,16)
    book.paragraph('At 96 steps per second, receiver 1 spans 1.447102-2.107750 Hz; receiver 2 spans 0.250035-0.622229 Hz. Halving the timestep changes each paired scalar outcome by at most 0.7352%. This is a timestep check at one spatial grid.',453,216,363,10.5,16)
    book.code(['                      Receiver 1 median     Receiver 2 median',
               '96 steps / second         1.704590 Hz            0.424034 Hz',
               '192 steps / second        1.696467 Hz            0.422229 Hz'],x=48,y=105,size=10,leading=19)

    book.page('The interventions')
    book.heading('Erasure locates the retained effect.')
    book.image(FIGURES/'what-erasure-removes.png',48,182,768,361)
    book.paragraph('Removing the second writing link makes receiver 2 agree exactly with its isolated control in every saved case. Erasing both p and z also restores both receivers to that control. Erasing either field alone leaves a nonzero effect.',48,161,363,10.5,16)
    book.paragraph('The two traces do not add linearly. For phrase 0 at 96 Hz, receiver 1 changes by 1.553793 Hz; erasing p leaves 1.397061 Hz and erasing z leaves 0.608499 Hz. Removing the outgoing link can increase receiver 1\'s change by altering its mechanical load.',453,161,363,10.5,16)

    book.page('The playable choir')
    book.heading('The visitor can become the writer.')
    book.image(PLATES/'01-before-scene.jpg',391,238,425,239)
    y=book.paragraph('Choose a body. Hold a place on its surface. Let go and listen to the reply. The point of contact changes which parts of the material receive force.',48,516,302,12,19)
    book.paragraph('Cut or rejoin the connections, isolate one listener, then ask again. A seventy-two-second encounter demonstrates the instrument; Undo returns to the exact saved state from before that encounter.',48,y-26,302,11,18)
    book.code(['TOUCH     Write into a selected body',
               'CUT       Change which bodies can exchange force',
               'STILL     Clear transient motion; retain inscription and wear',
               'SAVE      Export the complete numerical state'],x=48,y=206,size=11,leading=28)
    book.paragraph('The browser uses a 32 x 32 grid per body at 96 numerical steps per second. The studio performance uses 64 x 64. An independent 24-second, seven-body comparison matched all six float32 field packets between the Python and JavaScript solvers. Live sound uses four partials per voice; the film uses eight.',48,89,768,9.5,14)

    book.page('The sculptural edition')
    book.heading('The encounter becomes a place.')
    book.image(PLATES/'02-encounter-scene.jpg',48,187,768,353)
    book.paragraph('Three matched 8000 x 5200 prints hold the installation before writing, during the encounter and after departure. Three sculpture states preserve the encounter, the six listeners after B leaves, and the isolated source.',48,166,363,11,17)
    book.paragraph('The downloadable meshes have closed, consistently oriented components and survive a fresh export/import check. They are digital sculpture masters: separated suspended pieces are intentional. Fabrication supports and self-intersection certification are outside this edition.',453,166,363,10.5,16)


def persistence(book):
    book.page('The frozen system')
    book.heading('When motion fades, what can remain?')
    book.paragraph('Freeze p and z. Disable writing, external forcing and delayed feedback. Hold every included bridge at a positive fixed strength. Use the finite periodic spatial grid and the same reciprocal port map.',48,519,363,11,17)
    book.paragraph('Under these explicit restrictions, the potential is coercive and strictly convex. Grounding stiffness is at least 1.008; each active chain is anchored through the body coordinates. There is one equilibrium for each retained state.',453,519,363,11,17)
    book.code(['M q\'\' + C q\' + grad V(q; p,z) = 0',
               '',
               'E = (1/2) q\'^T M q\' + V',
               'dE/dt = -q\'^T C q\' <= 0'],x=78,y=337,size=15,leading=30)
    book.paragraph('Positive damping and compact energy sublevels imply convergence to the unique equilibrium. The linear mechanical generator has every eigenvalue strictly in the left half-plane. There is no indefinitely ringing mechanical carrier in this frozen model.',48,177,363,11,17)
    book.paragraph('A separate automatic-differentiation check compares the full frozen potential gradient with the actual body and bridge acceleration rule, and verifies the dissipation identity. The full plastic, driven performance is outside these assumptions.',453,177,363,11,17)

    book.page('A surviving configuration')
    book.heading('The lasting part is a changed rest state.')
    book.paragraph('Let r = (p,z) remain fixed, and let Q be the derivative of the equilibrium with respect to r. In coordinates relative to that changing equilibrium, the linearized evolution separates into damped motion and a retained identity block.',48,519,768,12,19)
    book.code(['eta = delta q - Q delta r',
               'T(t) = diag(exp(t*G), I_retained)',
               'metric = diag(H, M, W)'],x=78,y=390,size=16,leading=34)
    book.paragraph('The mechanical contribution to a return inner product decays. The retained contribution survives. A measurement can miss these surviving directions: an unchanged reading is not a complete description of the state.',48,255,363,11,17)
    book.paragraph('The frozen model separates two questions: which coordinates persist, and which coordinates an observer can detect. The retained inscription and wear determine the surviving state; a chosen readout can remain unchanged while other retained coordinates differ.',453,255,363,10.5,16)
    book.paragraph('Finite recorded equality for E does not establish an infinite-time invariant. The frozen argument uses standard finite-dimensional energy and linearization methods. No quantum recurrence law is asserted for this dissipative artwork.',48,113,768,10,15)

    book.page('A numerical cross-check')
    book.heading('The mechanical spectrum lies inside the circle.')
    book.image(FIGURES/'where-persistence-lives.png',48,234,768,314)
    book.paragraph('The saved check uses thirteen Galerkin coordinates for each of seven bodies and all 192 bridge beads: 283 positions, 566 mechanical state coordinates. It freezes the actual retained fields at 228 seconds and reconnects all twelve bridges.',48,212,363,11,17)
    book.paragraph('The largest generator real part is -0.120000055 per second. The 1/96-second mechanical step has spectral radius 0.998752338. The retained plus sign denotes the structural identity block; it is not an extra eigenvalue measured from the full active simulation.',453,212,363,11,17)
    book.code(['Equilibrium gradient max       1.09e-13',
               'Energy identity residual       1.42e-14',
               'Discrete Lyapunov residual      3.75e-08'],x=48,y=104,size=10,leading=19)


def closing(book):
    book.page('The edition and its evidence')
    book.heading('A work with an inspectable history.')
    y=book.paragraph('<b>The composition.</b> 288 seconds. Seven material bodies, twelve bridges and eighty-four voices. The sound is synthesized from recorded material readouts with continuous phase, eight slightly inharmonic partials and an authored listening mix.',48,520,363,11,17)
    y=book.paragraph('<b>The sound master.</b> 48 kHz stereo, 24-bit PCM. Constant gain produces -19.16 LUFS integrated loudness and -2.05 dB true peak. Playback and signal measurements were checked. No supported perceptual audition was available.',48,y-21,363,11,17)
    book.paragraph('<b>The evidence.</b> The scientific record contains the locked protocol, all twelve phrases at both rates, retained states, readouts, interventions, the full performance fields and the frozen matrix check. Earlier weak exploratory outcomes remain in the project record.',48,y-145,363,10.5,16)
    y=book.paragraph('<b>The authorship.</b> Codex conceived the material system, score, shapes, renderer, sound, experiments and exhibition for this project. Existing numerical, graphics and media libraries provide infrastructure.',453,520,363,11,17)
    y=book.paragraph('<b>The boundary.</b> These results establish effects in an invented finite numerical material. They do not establish physical fracture, biological memory, continuum convergence or a new general theory of recurrence. Authorship is not a claim of universal priority.',453,y-21,363,11,17)
    book.paragraph('<b>Reproduction.</b> Source captures, numerical states and SHA-256 manifests accompany the edition. The public repository is bernietorfen/palimpsest. The exhibition keeps the complete first act alongside this second act, and offers portable files as well as browser instruments.',453,y-145,363,10.5,16)
    book.text_line(48,63,'PALIMPSEST / Second act / Source, recordings, prints and evidence / 4 October 2026',9,'Sans',MUTED)

    book.page('After the source leaves')
    book.heading('An absence can have a shape.')
    book.image(PLATES/'03-after-scene.jpg',48,145,768,400)
    book.paragraph('Six listeners remain. One has nothing to report.',48,112,768,18,24)
    book.text_line(48,66,'Codex / A choir of absences / PALIMPSEST, second act',10,'Sans',MUTED)


def main(args):
    book=ChoirBook(args.output)
    opening(book);mechanism(book);evidence(book);persistence(book);closing(book)
    assert book.page_number==18
    book.finish()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='artwork/choir-notebook-001/a-choir-of-absences-notebook.pdf');main(parser.parse_args())
