"""A landscape artist's notebook assembled and proofed entirely on RunPod."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from studio.preserve import sha256
from studio.simulate import source_hashes


PAPER="#f1eddf"
INK="#293e42"
AMBER="#ac7137"
MUTED="#69716b"
DARK="#0b1013"
CREAM="#e8deca"


class Book:
    width,height=864,648
    margin=48

    def __init__(self,path,edition,*,invariant=None):
        self.path=Path(path)
        if self.path.exists():
            raise FileExistsError(self.path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fonts=Path("/usr/share/fonts/truetype/dejavu")
        for name,file in (("Sans","DejaVuSans.ttf"),("SansBold","DejaVuSans-Bold.ttf"),
                          ("Serif","DejaVuSerif.ttf"),("Mono","DejaVuSansMono.ttf")):
            pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
        pdfmetrics.registerFontFamily("Sans",normal="Sans",bold="SansBold",italic="Sans",boldItalic="SansBold")
        self.c=canvas.Canvas(str(self.path),pagesize=(self.width,self.height),pageCompression=1,invariant=invariant)
        self.c.setTitle("PALIMPSEST - Artist's notebook")
        self.c.setAuthor("Codex")
        self.c.setSubject("An authored material instrument, original audiovisual composition and numerical evidence")
        self.c.setCreator("PALIMPSEST / ReportLab")
        self.edition=edition
        self.page_number=0
        self.assets={}
        self.records=[]

    def page(self,label,dark=False):
        if self.page_number:
            self.c.showPage()
        self.page_number+=1
        self.dark=dark
        self.c.setFillColor(HexColor(DARK if dark else PAPER))
        self.c.rect(0,0,self.width,self.height,fill=1,stroke=0)
        self.color=CREAM if dark else INK
        self.text_line(48,615,"PALIMPSEST",8.5,"Sans",self.color)
        self.text_line(816,615,label.upper(),8.5,"Sans",self.color,right=True)
        self.c.setStrokeColor(HexColor("#334046" if dark else "#ccc3b2"))
        self.c.setLineWidth(.45)
        self.c.line(48,42,816,42)
        self.text_line(48,25,self.edition,7.5,"Sans",CREAM if dark else MUTED)
        self.text_line(816,25,f"{self.page_number:02d}",8,"Mono",self.color,right=True)
        self.records.append({"page":self.page_number,"label":label,"images":[]})

    def text_line(self,x,y,text,size=11,font="Sans",color=None,right=False):
        self.c.setFont(font,size)
        self.c.setFillColor(HexColor(color or self.color))
        if right:
            self.c.drawRightString(x,y,text)
        else:
            self.c.drawString(x,y,text)

    def heading(self,title,kicker=None):
        self.text_line(48,571,title,27,"Serif")
        if kicker:
            self.text_line(48,548,kicker,10,"Sans",CREAM if self.dark else MUTED)

    def paragraph(self,text,x=48,y=520,width=350,size=11,leading=16,color=None):
        style=ParagraphStyle("body",fontName="Sans",fontSize=size,leading=leading,
                             textColor=HexColor(color or self.color),allowWidows=0,allowOrphans=0)
        paragraph=Paragraph(text,style)
        _,height=paragraph.wrap(width,1000)
        if y-height<51:
            raise ValueError(f"paragraph overflows page {self.page_number}: {text[:60]}")
        paragraph.drawOn(self.c,x,y-height)
        return y-height

    def image(self,path,x,y,width,height):
        path=Path(path)
        self.c.drawImage(str(path),x,y,width=width,height=height,preserveAspectRatio=True,anchor="c",mask="auto")
        self.assets[str(path)]=sha256(path)
        self.records[-1]["images"].append(str(path))

    def code(self,lines,x=48,y=505,size=10,leading=18):
        for line in lines:
            if pdfmetrics.stringWidth(line,"Mono",size)>768:
                raise ValueError("a code line exceeds the page width")
            self.text_line(x,y,line,size,"Mono")
            y-=leading
        return y

    def finish(self):
        self.c.save()
        report={"pages":self.page_number,"edition":self.edition,"pdf_sha256":sha256(self.path),
                "source_sha256":source_hashes(self.path.with_suffix("")/"source"),
                "embedded_image_sha256":self.assets,"page_inventory":self.records}
        self.path.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({"path":str(self.path),"pages":self.page_number,"bytes":self.path.stat().st_size,
                          "sha256":report["pdf_sha256"]}),flush=True)


def opening_pages(book,plates,diptych,figures):
    book.page("An original computational work",dark=True)
    book.image(plates/"02-inscription-view.jpg",404,62,412,515)
    book.text_line(48,446,"PALIMPSEST",38,"Serif")
    book.paragraph("An instrument that becomes<br/>its own score.",48,410,340,17,25)
    book.paragraph("Artist's notebook<br/>Composition, material, evidence",48,226,330,11,18)
    book.text_line(48,91,"Codex / 3-4 October 2026",10,"Sans")

    book.page("Intention")
    book.heading("Writing changes the surface.")
    y=book.paragraph("A question arrives at a surface that can remember it. Each gesture leaves an inscription, but also changes how the material will answer the next gesture. A later interval lets the inscription fade. Some of the wear remains.",48,523,342,12,19)
    y=book.paragraph("PALIMPSEST is a seven-minute, twelve-second portrait of this instrument. A five-note phrase appears near the beginning and returns near the end. Its envelopes, strengths and timing repeat. The instrument carries a different history into the return.",48,y-20,342,11,17)
    y=book.paragraph("The material is invented. Its behavior follows explicit rules, and the same recorded state supplies both the sound and the sculpture. Camera, color, lighting and the mapping of wear into openings are composed choices.",48,y-20,342,11,17)
    book.paragraph("The work comprises an original score, numerical instrument, renderer, film, print series and closed sculpture geometry. This notebook makes their construction inspectable.",48,y-20,342,10.5,16)
    book.image(plates/"01-impression-view.jpg",535,316,176,220)
    book.image(plates/"03-remnant-view.jpg",535,70,176,220)
    book.text_line(535,303,"30 seconds / Impression",8.5,"Mono",MUTED)
    book.text_line(535,57,"358 seconds / Remnant",8.5,"Mono",MUTED)

    book.page("The returning question",dark=True)
    book.heading("The same phrase arrives at a changed instrument.")
    book.image(diptych/"question-first-view.jpg",73,92,330,412.5)
    book.image(diptych/"question-return-view.jpg",461,92,330,412.5)
    book.text_line(80,77,"First question / 30 seconds",10,"Sans")
    book.text_line(468,77,"Returning question / 382 seconds",10,"Sans")
    book.paragraph("Both portraits occur twelve seconds into the phrase and use identical camera and light settings.",80,62,710,8.5,10)

    book.page("The instrument")
    book.heading("An impression becomes a reply.")
    book.image(figures/"instrument-loop.png",48,102,768,454)
    book.paragraph("The voice reads signed inscription and fatigue. Its pitch drift changes the phase of a delayed force pattern, which acts on the material again. The audible carriers are synthesized separately from these slow material dynamics.",48,89,768,10,14)

    book.page("The retained state")
    book.heading("Two kinds of memory.")
    y=book.paragraph("<b>u</b> is current displacement. It moves as the material is driven.<br/><br/><b>p</b> is the rest-shape inscription. Signed deformation accumulates above the writing threshold.<br/><br/><b>z</b> is fatigue. It changes the writing threshold and the audible tuning.",48,512,245,11,17)
    y=book.paragraph("In the forgetting interval, the inscription becomes faint while substantial fatigue remains. Their different time scales give the return its changed condition.",48,y-25,245,11,17)
    book.paragraph("These are the actual recorded fields, with shared scales across time. They are dimensionless values on a periodic numerical grid.",48,y-25,245,10,15)
    book.image(figures/"material-fields.png",322,65,482,482)

    book.page("The composition")
    book.heading("A question, an accumulation, a changed return.")
    book.image("artwork/analysis/performance-002/performance-atlas.png",79,92,706,454)
    book.paragraph("The first and returning five-note phrases begin at 18 and 370 seconds. The blue interval increases the forgetting rate. The middle movements use authored fragments, overlapping replies and a deliberate rise in gesture density.",48,79,768,9.5,13)


def evidence_pages(book,figures):
    book.page("The sound")
    book.heading("Twelve voices share one changing material.")
    book.image("artwork/analysis/performance-002/sound-atlas.png",48,157,768,384)
    book.paragraph("The score uses continuous-phase additive voices, slightly inharmonic partials, fatigue-dependent spectral shading and a synthetic room. New fatigue controls a quiet abrasion layer. Every sound is synthesized from the authored instrument.",48,145,360,10,14)
    book.paragraph("The delivery master is 48 kHz stereo PCM24, measured at -18.07 LUFS and -2.67 dBTP after constant gain. The plot shows the earlier synthesis level. No supported perceptual audition was available; signal measurements do not establish listening quality.",450,145,366,10,14)

    book.page("Controlled history")
    book.heading("The order of writing changes a later answer.")
    book.image(figures/"order-memory.png",61,100,742,452)
    book.paragraph("Five writing gestures are played in forward and reverse order. The same new probe follows, after transient state is reset. Retained inscription and fatigue are the remaining differences. Pitch difference is 0.933236 Hz RMS across voices and probe time.",48,87,768,9.5,13)

    book.page("Intervention and sensitivity")
    book.heading("The two retained fields have different effects.")
    book.image(figures/"interventions-and-timestep.png",87,89,690,464)
    book.paragraph("Erasing both fields reproduces the fresh control exactly. Erasing either one alone leaves a difference. The order effect persists with smaller timesteps on the same grid; delay-buffer length is rounded separately at each timestep. This is a sensitivity check, not a convergence proof.",48,80,768,9.2,12.5)

    book.page("The material rule")
    book.heading("Move. Write. Retain the consequence.")
    book.paragraph("The production update uses h = 1/96 s on a periodic 128 x 128 grid. Lap is the five-point periodic Laplacian. Fields are dimensionless. The motion step precedes writing and fatigue.",48,529,768,11,16)
    book.code([
        "d = u - p",
        "a = 1.2*Lap(u) - 0.08*Lap(Lap(u)) - 2.4*(1-0.58*z)*d - 0.7*d^3 + F",
        "v_next = (v + h*a) / (1 + 0.38*h)",
        "u_next = u + h*v_next",
        "",
        "s = u_next - p",
        "excess = max(abs(s) - 0.095*(1-0.35*z), 0)",
        "write = 0.32*excess*tanh(s/0.035)*max(1-(p/0.8)^2, 0)",
        "p_next = clip(p + h*(write - lambda*p + 0.035*Lap(p)), -0.8, 0.8)",
        "z_next = clip(z + h*(0.26*excess^2*(1-z) - 0.001*z), 0, 1)",
    ],y=463,size=10,leading=19)
    book.paragraph("<b>The inscription.</b> Writing begins beyond a fatigue-dependent threshold. A finite capacity bounds the rest shape. Diffusion smooths it and a controllable forgetting rate lets it recede.",48,231,355,11,17)
    book.paragraph("<b>The wear.</b> Fatigue grows with excess strain and recovers on a slower time scale. The forgetting interval therefore leaves a changed material. Wear is persistent during this performance, rather than mathematically permanent.",452,231,364,11,17)
    book.paragraph("The selected film uses the non-buckling configuration. Exact operation order, spatial scaling, patterns and parameter definitions accompany this edition in research/MODEL.md and studio/material.py.",48,97,768,9.5,14)

    book.page("Tuning and feedback")
    book.heading("A voice reads the surface, then changes it.")
    book.paragraph("For each authored force pattern psi_j, the instrument reads signed inscription and weighted fatigue. It maps them to an audible frequency; it does not solve for physical eigenfrequencies.",48,529,768,11,16)
    book.code([
        "m_j = mean(p * psi_j)",
        "q_j = mean(z * psi_j^2) / mean(psi_j^2)",
        "f_j = f0_j * sqrt(1 - 0.58*q_j) * exp(0.65*m_j)",
        "theta_j = (theta_j + h*2*pi*0.018*(f_j-f0_j)) modulo (2*pi)",
    ],y=461,size=12,leading=26)
    book.paragraph("<b>The reply.</b> Delayed velocity readouts set the amplitude of shifted force patterns. Each phase combines a pattern and its authored quadrature. Pitch drift thus changes the next force applied to the material.",48,327,357,11,17)
    book.paragraph("<b>Two time scales.</b> The coefficient 0.018 maps audible pitch differences to slow geometric phase. Audible oscillations are synthesized at 48 kHz; the material update does not resolve them directly. The nominal delay uses 76 buffer slots at the production timestep.",452,327,364,11,17)
    book.text_line(48,187,"UNWORN CARRIER FREQUENCIES / HZ",9,"Sans",MUTED)
    pitches=("110","137.5","146.6667","165","183.3333","220",
             "247.5","275","293.3333","330","366.6667","440")
    for index,pitch in enumerate(pitches):
        book.text_line(48+(index%6)*128,156-(index//6)*25,pitch,12,"Mono")
    book.paragraph("The twelve mean-zero, RMS-normalized patterns are mixtures of Fourier components. They are authored force/readout shapes and are not asserted to be orthogonal normal modes.",48,93,768,9.5,14)


def atlas_pages(book,atlas,comparison):
    base=json.loads((atlas/"report.json").read_text())
    result=json.loads((comparison/"report.json").read_text())
    matching=result["matching"]
    coarse=result["coarse_rate"]
    fine=result["fine_rate"]
    count=matching["total"]
    book.page("An exhaustive history atlas")
    book.heading("120 possible pasts.","Five writing gestures. One common probe.")
    y=book.paragraph("Five writing gestures can be arranged in 120 orders. Each history begins on a fresh sheet. After 24 seconds, transient motion, delay and phase are reset while inscription and fatigue remain. The same three-gesture, 14-second probe then follows.",48,517,355,11,17)
    y=book.paragraph(f"All {count} histories give distinct pitch trajectories at both tested timesteps. The closest pair differs by {base['summaries'][str(coarse)]['minimum_pair_rms_hz']:.3f} Hz RMS at 1/{coarse} second, and {base['summaries'][str(fine)]['minimum_pair_rms_hz']:.3f} Hz RMS at 1/{fine} second.",48,y-21,355,11,17)
    y=book.paragraph(f"For each finer-step trajectory, a direct lookup selects the nearest coarse-step trajectory. It identifies {matching['correct']} of {count} histories correctly. This uses the complete later pitch response; no classifier is trained.",48,y-21,355,11,17)
    book.paragraph("This checks one numerical refinement on a fixed grid. It does not establish human audibility or robustness to noise, new writing histories or spatial refinement.",48,y-21,355,10,15)
    book.image("artwork/analysis/history-atlas-002/120-possible-pasts-view.jpg",468,63,348,464)
    book.paragraph("Each glyph samples twelve voices at four probe times, using one shared scale. The full 6000 x 8000 print and its vector PDF accompany the edition.",48,96,355,9.5,14)

    book.page("Earlier order and a common ending")
    book.heading("An earlier order survives the same ending.")
    book.image("artwork/analysis/history-atlas-002/history-landscape.png",48,96,768,444)
    old=result["shared_tail_results"][str(coarse)]["3"]
    new=result["shared_tail_results"][str(fine)]["3"]
    book.paragraph(f"Fixing the last three writing gestures leaves {old['pair_count']} paired comparisons. All remain distinct: the smallest difference is {old['minimum_rms_hz']:.3f} Hz RMS at 1/{coarse} second and {new['minimum_rms_hz']:.3f} Hz RMS at 1/{fine} second. The plot shows the first timestep; the source includes both.",48,84,768,9.2,12.5)


def closing_pages(book,plates):
    book.page("The sculpture")
    book.heading("A continuous chart becomes an open sheet.")
    book.image(plates/"02-inscription-view.jpg",48,145,335,419)
    y=book.paragraph("A two-dimensional chart rolls through two turns. Displacement and retained inscription emboss its radius. Fatigue clips openings into the chart, and front, back and boundary walls close the resulting geometry.",430,524,386,11,17)
    y=book.paragraph("The openings are a visual encoding of wear. The numerical grid remains intact. The apparent fragments do not behave as a fracture-mechanics simulation or as free rigid bodies.",430,y-18,386,11,17)
    y=book.paragraph("The exported states are actual meshes in textured glTF and STL. Reopening them checks triangle counts, bounds, watertightness and winding. The authored export has a 200 mm maximum extent; fabrication and universal printability have not been tested.",430,y-18,386,11,17)
    book.text_line(48,116,"STATE",9,"Sans",MUTED)
    book.text_line(213,116,"TRIANGLES",9,"Sans",MUTED)
    book.text_line(420,116,"CONNECTED PIECES",9,"Sans",MUTED)
    book.text_line(655,116,"STL ROUNDTRIP",9,"Sans",MUTED)
    for i,(state,triangles,pieces) in enumerate(((0,294908,1),(165,259772,1),(358,105564,45))):
        y=96-i*17
        book.text_line(48,y,f"{state:03d} seconds",9.5,"Mono")
        book.text_line(213,y,f"{triangles:,}",9.5,"Mono")
        book.text_line(420,y,str(pieces),9.5,"Mono")
        book.text_line(655,y,"Closed, consistent",9.5,"Sans")

    book.page("Reproduction")
    book.heading("The record can be reconstructed.")
    y=book.paragraph("The source contains the instrument, original control score, synthesizer, geometry, shaders, camera score, preservation tools and notebook generator. Each substantial study also preserves the exact source snapshot that produced it.",48,525,360,11,17)
    y=book.paragraph("The production performance records the four material fields at 24 frames per second, modal readouts in float32, selected full-precision states, a complete checkpoint and a parameter manifest. Image reconstruction and artistic mappings remain separate from the numerical record.",48,y-20,360,11,17)
    book.paragraph("Large artifacts are preserved in size-bounded archives with per-file and archive-part SHA-256 hashes. A real 64-file performance archive was restored and checked against every recorded file digest. Uploaded GitHub assets are checked independently for size, state and digest.",48,y-20,360,11,17)
    book.paragraph("Use an authorized GPU host. Production simulation, synthesis, rendering, analysis and testing ran on RunPod. The commands below illustrate the tool sequence; the supplied manifests and README define the exact paths and settings for each edition.",453,525,363,11,17)
    book.code([
        "python -m studio.simulate --output artifacts/studies/new-performance --duration 432 --save-fields",
        "python -m studio.sound --readouts READOUTS.npz --output score.wav",
        "python -m studio.film --fields FIELDS.npy --audio score.wav \\",
        "  --output film.mp4 --width 3840 --height 2160 --area-shadow \\",
        "  --samples 128 --shadow-size 4096 --mesh-u 256 --mesh-v 512 \\",
        "  --codec h265 --bit-depth 10 --crf 17",
    ],x=48,y=194,size=9.3,leading=18)
    book.paragraph("For archive recovery: python -m studio.preserve restore MANIFEST.json EMPTY_DESTINATION. Verification of all archive parts precedes extraction; every restored file is then checked.",48,81,768,9.2,12.5)

    book.page("Authorship and context")
    book.heading("What was made here, and what came before.")
    y=book.paragraph("<b>Authored for PALIMPSEST.</b> The specific material coupling, signed-memory tuning, phase-dependent delayed force patterns, score gestures, synthesis decisions, rolled-sheet geometry, pigment, rendering code, camera sequence, print compositions and numerical experiments were written for this work.",48,526,360,11,17)
    y=book.paragraph("The project uses no borrowed organisms, procedural presets, mesh assets, photographs, music samples or trained-model outputs. ",48,y-19,360,11,17)
    y=book.paragraph("<b>Established ingredients.</b> Wave dynamics, plastic rest shapes, hysteresis, Fourier analysis, additive synthesis, feedback music and sound sculpture all have prior histories. The work claims an original implementation and composition. It does not claim universal scientific priority.",48,y-19,360,11,17)
    book.paragraph("<b>Infrastructure.</b> Python, PyTorch, NumPy, SciPy, ModernGL/OpenGL, Pillow, FFmpeg, Matplotlib, trimesh and ReportLab provide general computation and production tools. Typography uses DejaVu Serif and DejaVu Sans. Their implementations and type designs belong to their respective authors.",48,y-19,360,10,15)
    y=book.paragraph("<b>Contextual precedents</b><br/><br/>Tom Mudd, <i>Following the Material: Hysteresis, Intermittency and Timing-dependent Behaviour in Musical Interactions</i>, ECHO. The article examines history and timing in musical feedback interactions.",453,526,363,11,17)
    y=book.paragraph('<link href="https://echo.orpheusinstituut.be/article/following-the-material" color="#476f78">echo.orpheusinstituut.be/article/following-the-material</link>',453,y-10,363,8.5,13)
    y=book.paragraph("Alan Ahued Naime, <i>Plasticity of Sound</i>. An earlier practice connecting sound, sculpture and the experience of time.",453,y-25,363,11,17)
    y=book.paragraph('<link href="https://www.alanahuednaime.com/plasticity-of-sound" color="#476f78">alanahuednaime.com/plasticity-of-sound</link>',453,y-10,363,8.5,13)
    book.paragraph("These references establish neighboring practices. No code, imagery, recordings or compositions from them were imported into PALIMPSEST. The source and records distinguish the authored construction from the broader ideas it shares with earlier work.",453,y-25,363,10.5,16)

    book.page("Reading the evidence")
    book.heading("What the numbers can support.")
    y=book.paragraph("<b>A finite-grid result.</b> The controlled experiment detects an order-specific difference in this instrument. The effect persists under the tested timestep refinements. Spatial convergence, global stability and a general theorem about memory are outside the result.",48,526,360,11,17)
    y=book.paragraph("<b>A defined intervention.</b> Resetting u=p removes local elastic strain. It does not ensure full spatial equilibrium. Erasing the two retained fields is an explicit operation on a mathematical state, not a model of amnesia or material healing.",48,y-22,360,11,17)
    book.paragraph("<b>A composed comparison.</b> The film's repeated phrase differs by about 466 cents RMS across voice and time readouts. Its history and transients continue naturally. This comparison inside the composition is distinct from the smaller, controlled order experiment.",48,y-22,360,11,17)
    y=book.paragraph("<b>An inspected image.</b> Geometry closure, rendered crops, paired framing and complete video decoding are checkable. They do not establish that every possible parameter state is printable or that the visual mapping describes real fracture.",453,526,363,11,17)
    y=book.paragraph("<b>A measured soundtrack.</b> Duration, sample rate, peak, loudness and signal structure are documented. A supported audio-perception path was unavailable to the authoring assistant. Listening quality has not been established by a claimed audition or audience study.",453,y-22,363,11,17)
    book.paragraph("<b>An original work.</b> The code and composition were authored for this work. A world-first claim would require a different standard of historical and scientific evidence. This notebook preserves enough of the construction for the work to be examined on its own terms.",453,y-22,363,11,17)
    book.paragraph("Detailed equations and boundaries: research/MODEL.md. Originality record: research/ORIGINALITY.md. Verification and preservation records accompany the source edition.",48,99,768,9.5,14)

    book.page("What remains",dark=True)
    book.image(plates/"03-remnant-view.jpg",417,63,397,496)
    book.paragraph("The question returns.<br/>The material answers<br/>from its history.",48,420,360,24,37)
    book.text_line(48,107,"PALIMPSEST",15,"Serif")
    book.text_line(48,82,"Codex / 2026",10,"Sans")


def main(args):
    book=Book(args.output,args.edition)
    plates=Path(args.plates)
    figures=Path(args.figures)
    opening_pages(book,plates,Path(args.diptych),figures)
    evidence_pages(book,figures)
    atlas_pages(book,Path(args.atlas),Path(args.comparison))
    closing_pages(book,plates)
    book.finish()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="output/pdf/palimpsest-notebook-proof-001.pdf")
    parser.add_argument("--edition",default="Studio proof / 3 October 2026")
    parser.add_argument("--plates",default="artwork/masters/plates-001")
    parser.add_argument("--diptych",default="artwork/masters/diptych-002")
    parser.add_argument("--figures",default="artwork/notebook/figures-002")
    parser.add_argument("--atlas",default="artifacts/studies/history-atlas-001")
    parser.add_argument("--comparison",default="artwork/analysis/history-refinement-001")
    main(parser.parse_args())
