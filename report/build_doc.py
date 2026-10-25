"""Builds the Unit 1 and 2 individual project report as a .docx file."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = "Times New Roman"
BLACK = RGBColor(0, 0, 0)
BODY, LEAD = 11, 1.02
TBL = 8

doc = Document()
for s in doc.sections:
    s.top_margin = Inches(0.75)
    s.bottom_margin = Inches(0.75)
    s.left_margin = Inches(0.95)
    s.right_margin = Inches(0.85)

normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(BODY)
normal.font.color.rgb = BLACK
normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = LEAD

_pending = [False]


def _run(r, size=BODY, bold=False, italic=False, font=None):
    f = font or FONT
    r.font.name = f
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = BLACK
    r._element.rPr.rFonts.set(qn("w:eastAsia"), f)
    return r


def _new(align="just", space_after=5, line=LEAD, before=0):
    p = doc.add_paragraph()
    p.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = line
    if _pending[0]:
        p.paragraph_format.page_break_before = True
        _pending[0] = False
    return p


def para(text="", size=BODY, bold=False, italic=False, align="just", space_after=5,
         line=LEAD, before=0):
    p = _new(align, space_after, line, before)
    if text:
        _run(p.add_run(text), size, bold, italic)
    return p


def heading(text, level=1):
    sizes = {0: 13, 1: 11.5, 2: 11}
    p = _new("left", space_after=4, line=1.03, before={0: 15, 1: 8, 2: 6}[level])
    _run(p.add_run(text), sizes[level], bold=True)
    return p


def bullet(text, size=BODY):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.1
    _run(p.add_run(text), size)
    return p


def _shade(cell, hexval="D9D9D9"):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hexval)
    cell._tc.get_or_add_tcPr().append(el)


def _cell(cell, text, size, bold):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    _run(p.add_run(str(text)), size, bold)


def table(headers, rows, widths=None, size=TBL, after=4):
    if _pending[0]:
        para("", space_after=0, line=1.0)
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for i, h in enumerate(headers):
        _cell(t.rows[0].cells[i], h, size, True)
        _shade(t.rows[0].cells[i])
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            _cell(cells[i], val, size, False)
    if widths:
        for r in t.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(after)
    return t


def kv_table(rows, widths, size=10):
    if _pending[0]:
        para("", space_after=0, line=1.0)
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            _cell(cells[i], val, size, i % 2 == 0)
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def caption(text, size=9):
    p = _new("center", space_after=6, line=1.0, before=1)
    _run(p.add_run(text), size, bold=True)
    return p


def code(lines, size=9, left=0.22):
    """Monospace block for commands and formulae."""
    for i, ln in enumerate(lines):
        p = _new("left", space_after=(5 if i == len(lines) - 1 else 0), line=1.0,
                 before=(5 if i == 0 else 0))
        p.paragraph_format.left_indent = Inches(left)
        _run(p.add_run(ln if ln else " "), size, font="Courier New")


def figure(path, width, cap):
    p = _new("center", space_after=1, line=1.0, before=3)
    p.add_run().add_picture(path, width=Inches(width))
    caption(cap)


def page_break():
    _pending[0] = True

# ------------------------------------------------------------------ cover
para("ATLAS uGDX", 11, align="center", space_after=1, line=1.05)
para("School of Technology", 11, align="center", space_after=1, line=1.05)
para("B. Tech in CS AI and ML", 11, align="center", space_after=1, line=1.05)
para("Academic Year 2026 to 2027", 11, align="center", space_after=14, line=1.05)
para("BTECH CAP 501", 12.5, bold=True, align="center", space_after=1, line=1.05)
para("PROJECT LIFE CYCLE MANAGEMENT", 12.5, bold=True, align="center", space_after=1, line=1.05)
para("PROJECT REPORT", 12.5, bold=True, align="center", space_after=16, line=1.05)
para("Autonomous Drone Obstacle Avoidance Using Monocular Depth Estimation",
     14.5, bold=True, align="center", space_after=4, line=1.15)
para("Unit 1 and Unit 2. Project Initiation, Feasibility, and Requirements",
     11.5, italic=True, align="center", space_after=16, line=1.15)
kv_table([["Branch / Section", "B. Tech CS AI and ML", "Academic Year", "2026 to 2027"],
          ["Project Title", "Autonomous Drone Obstacle Avoidance Using Monocular "
           "Depth Estimation", "Project Domain", "Robotics and Computer Vision"],
          ["Faculty Mentor", "", "Date of Submission", "11 September 2026"]],
         widths=[1.25, 2.35, 1.2, 1.3])
para("Project Team", 11.5, bold=True, align="center", space_after=3, line=1.05)
table(["Sr. No.", "Name of Student", "App ID", "Role Held in the Project"],
      [["1", "Siddharth Lama", "2407926",
        "Simulation environment, avoidance policy, evaluation harness"],
       ["2", "Manit Aravind", "2409933", "Depth model integration and benchmarking"],
       ["3", "Sahil Asopa", "2404698", "Airframe design, electronics and bill of materials"],
       ["4", "Riyaan Sheth", "2409365",
        "Requirements, documentation and responsible AI analysis"]],
      widths=[0.62, 1.55, 0.85, 3.28], size=10)
page_break()

# ------------------------------------------------------------------ front matter
heading("DEDICATION", 1)
para("This report is dedicated to every person on the ground who never agreed to have an "
     "aircraft fly above them. Small drones are becoming ordinary in delivery, surveying "
     "and agriculture, and the people most affected by a failure are almost never the "
     "people who chose to operate the machine. A project about obstacle avoidance is "
     "really a project about not hurting somebody, and we have tried to keep that at the "
     "front of our minds rather than treating it as a paragraph added at the end.")
para("It is also dedicated to our families, who have tolerated a great deal of talk about "
     "depth maps at the dinner table, and to our faculty, who pushed us to report what we "
     "measured rather than what we hoped for.")

heading("ABSTRACT", 1)
para("Small autonomous aircraft used for inspection, delivery and agriculture must avoid "
     "obstacles while carrying as little weight as possible. Stereo cameras and laser "
     "scanners measure distance reliably but add mass, cost and power that a light "
     "airframe can rarely afford. A single ordinary camera is the cheapest sensor "
     "available and weighs almost nothing. The difficulty is that one photograph contains "
     "no distance information. A small object close to the lens and a large object far "
     "away produce the same pixels.")
para("This project asks whether a neural network can supply the missing distance well "
     "enough to fly. We integrate MiDaS, a pretrained monocular depth model, into a "
     "perception and control loop, convert its output into a steering command using a "
     "transparent reactive policy, and place a non learned safety stop layer underneath. "
     "The work is carried out in simulation, where perfectly accurate depth is available "
     "for comparison, and is intended to move onto a fixed wing vertical take off and "
     "landing airframe the team is designing in parallel.")
para("The central measurement is an ablation. The same aircraft flies the same courses "
     "three times, using perfect depth from the simulator, depth estimated from a single "
     "image, and no depth at all. The difference between the first two results is the "
     "price of replacing a measuring instrument with a prediction.")
para("The simulation environment, seeded course generator, reactive policy, safety layer, "
     "batch evaluation harness and the depth model itself are all working. The aircraft "
     "now flies on depth estimated by MiDaS from a single camera image, and the three arm "
     "ablation runs end to end. Using perfect depth on fifty courses "
     "never used during tuning, the aircraft completes 76 per cent of routes and 66 per "
     "cent with no contact at moderate obstacle density. Those numbers form the ceiling "
     "against which estimated depth will be judged. They are below the 90 per cent target "
     "originally set, and Chapter 4 treats that honestly rather than adjusting the target "
     "afterwards.")

heading("ACKNOWLEDGEMENTS", 1)
para("We are grateful to our faculty mentor for insisting that feasibility be argued with "
     "evidence rather than asserted, and for pressing us on the difference between a "
     "number we tuned and a number we can defend. That distinction changed how we ran our "
     "experiments and appears throughout Chapter 4.")
para("We thank the Intel Intelligent Systems Lab for releasing the MiDaS models under a "
     "permissive licence, and the maintainers of MuJoCo, PX4, NumPy and OpenCV. This "
     "project has a hardware budget of nothing and exists only because that software is "
     "free to use and free to study. We also thank the teams behind the NYU Depth V2 and "
     "KITTI datasets, on which our depth benchmarking depends entirely.")
para("Finally the four of us acknowledge one another. The work divided into simulation, "
     "perception, hardware and documentation, and every part turned out harder than it "
     "looked at the start of the semester.")

heading("PREFACE", 1)
para("This report covers Units 1 and 2 of the Project Life Cycle Management course. It is "
     "an initiation document rather than a results document. Its purpose is to define the "
     "problem, map the people affected, establish whether the project is feasible on four "
     "counts, write requirements that can be tested, and describe where the data comes "
     "from and how it is tracked.")
para("A complete implementation is not required at this stage. We have included "
     "measurements from the working simulation anyway, for two reasons. The course asks "
     "us to avoid generic answers and connect every section to our own project, and real "
     "numbers make that easier to do honestly. Several of our early assumptions also "
     "turned out to be wrong once measured, and a feasibility chapter that hid that would "
     "be a worse document.")
para("On scope, the graded deliverable is the simulation. In parallel the team is "
     "designing a fixed wing vertical take off and landing airframe and has produced an "
     "electronics bill of materials. That build is a stretch goal reusing the same "
     "perception and avoidance code. Assumptions are stated where they are used rather "
     "than collected at the end.")

# ------------------------------------------------------------------ index
heading("INDEX", 1)
table(["Sr. No.", "Content", "Page No."],
      [["", "FIRST PAGE. Project title and student details", "i"],
       ["", "DEDICATION and ABSTRACT", "ii"],
       ["", "ACKNOWLEDGEMENTS and PREFACE", "ii"],
       ["", "INDEX", "iii"], ["", "LIST OF FIGURES and LIST OF TABLES", "iv"],
       ["I", "Project Overview and Problem Scoping", "1"],
       ["1.1", "Project Title", "1"], ["1.2", "Background and Context", "1"],
       ["1.3", "Problem Statement", "1"], ["1.4", "Proposed AI and ML Solution", "2"],
       ["1.5", "Success Criteria", "2"],
       ["II", "AI and ML Project Life Cycle and Difference from Conventional Software", "3"],
       ["2.1", "Proposed Life Cycle of Our Project", "4"],
       ["2.2", "Why Our Project Is an AI and ML Project", "4"],
       ["2.3", "ML Project Compared With an ML Pipeline", "5"],
       ["III", "AI Project Life Cycle Frameworks", "6"],
       ["3.1", "CRISP-DM Mapping", "6"], ["3.2", "Microsoft TDSP Mapping", "6"],
       ["3.3", "Google ML Life Cycle and Pipeline Perspective", "7"],
       ["3.4", "Final Framework Choice and Justification", "7"],
       ["IV", "Problem Scoping and Feasibility Analysis", "7"],
       ["4.1", "Technical Feasibility", "7"], ["4.2", "Economic Feasibility", "9"],
       ["4.3", "Operational Feasibility", "11"], ["4.4", "Ethical Feasibility", "11"],
       ["V", "Requirements Engineering for AI", "13"],
       ["5.1", "Functional Requirements", "13"],
       ["5.2", "Non Functional Requirements", "13"], ["5.3", "Data Requirements", "14"],
       ["VI", "Stakeholder Management in AI", "15"],
       ["6.1", "Stakeholder Identification", "15"],
       ["6.2", "Stakeholder Categories Considered", "16"],
       ["6.3", "Stakeholder Conflict Analysis", "16"],
       ["6.4", "Data Subjects and Affected Communities", "16"],
       ["6.5", "Adversarial Stakeholders", "17"],
       ["VII", "Dataset Overview", "18"],
       ["7.1", "Data Required for the Project", "18"], ["7.2", "Data Provenance", "18"],
       ["7.3", "Data Lineage Diagram", "19"], ["7.4", "Data Transformation Log", "19"],
       ["VIII", "Final Project Initiation Summary", "20"],
       ["IX", "Preliminary Next Steps", "21"],
       ["X", "References", "23"], ["XI", "Appendix", "24"]],
      widths=[0.62, 4.9, 0.72], size=7.5)

heading("LIST OF FIGURES", 1)
table(["Figure No.", "Title", "Page No."],
      [["1", "Proposed project life cycle showing feedback loops", "4"],
       ["2", "System architecture from camera to actuators", "1"],
       ["3", "Data lineage from source to final dataset", "19"],
       ["4", "Simulation environment with chase view, camera and ground truth depth", "8"],
       ["5", "Collision free completion against obstacle density", "9"]],
      widths=[0.8, 4.7, 0.72], size=8)

heading("LIST OF TABLES", 1)
table(["Table No.", "Title", "Page No."],
      [["1", "Success criteria input and output definition", "3"],
       ["2", "Technical and practical success criteria", "3"],
       ["3", "Characteristics of the project as an AI and ML project", "5"],
       ["4", "Automated pipeline activities against human decisions", "5"],
       ["5", "CRISP-DM phase mapping", "6"],
       ["6", "Microsoft TDSP stage mapping", "6"],
       ["7", "Google ML life cycle pipeline stages", "7"],
       ["8", "Technical feasibility analysis", "8"],
       ["9", "Measured performance using perfect depth", "8"],
       ["10", "Economic feasibility analysis", "10"],
       ["11", "Electronics bill of materials for the physical airframe", "11"],
       ["12", "Operational feasibility analysis", "11"],
       ["13", "Ethical feasibility analysis", "12"],
       ["14", "Functional requirements", "13"],
       ["15", "Non functional requirements", "14"],
       ["16", "Data requirements", "15"],
       ["17", "Stakeholder identification", "15"],
       ["18", "Stakeholder conflict analysis", "16"],
       ["19", "Adversarial stakeholders and mitigations", "17"],
       ["20", "Data required for the project", "18"],
       ["21", "Data provenance", "19"],
       ["22", "Data transformation log", "20"],
       ["23", "Final project initiation summary", "21"],
       ["24", "Simulator command line options", "25"],
       ["25", "Effect of the preprocessing fault on depth quality", "27"],
       ["26", "The two alignment arms", "27"],
       ["27", "Measured depth model performance", "28"],
       ["28", "Policy parameter reference", "29"]],
      widths=[0.8, 4.7, 0.72], size=8)
page_break()

# ================================================================== CHAPTER 1
heading("CHAPTER I. PROJECT OVERVIEW AND PROBLEM SCOPING", 0)
heading("1.1 Project Title", 1)
para("Autonomous Drone Obstacle Avoidance Using Monocular Depth Estimation. In full, a "
     "reactive obstacle avoidance system for a small fixed wing vertical take off and "
     "landing aircraft, driven by depth estimated from a single camera and evaluated "
     "against perfect depth in simulation.")

heading("1.2 Background and Context", 1)
para("Small uncrewed aircraft have moved out of hobby use into commercial work. They "
     "inspect transmission towers and turbines, survey construction sites, monitor crops "
     "and carry small parcels. Almost all of this happens close to structures, close to "
     "vegetation and often close to people. An aircraft that cannot detect what is in "
     "front of it is limited to open sky, which removes most of the value.")
para("Detecting obstacles requires knowing distance, and every established way of "
     "measuring it costs something the aircraft cannot spare. A laser scanner gives "
     "excellent range but is heavy, expensive and draws steady power. A stereo pair is "
     "lighter but needs two synchronised sensors, a rigid baseline, calibration that "
     "survives vibration, and continuous computation. Ultrasonic and infrared range "
     "finders are cheap but measure a single point at short range, which is not enough to "
     "steer around anything. On a small airframe the real currency is mass, because every "
     "gram of sensor is a gram not spent on battery and battery is flight time.")
para("A single ordinary camera sits at the opposite end of that trade. It weighs a few "
     "grams, costs very little and draws almost no power. What it does not do is measure "
     "distance, because projection destroys depth and no geometry recovers it from one "
     "image. What has changed is that this no longer has to be solved geometrically. "
     "Photographs of the real world are highly structured. Distant surfaces appear "
     "smaller, sit higher in the frame, lose contrast and are hidden by nearer surfaces. "
     "Those relationships can be learned. Monocular depth models such as MiDaS take a "
     "single colour image and return a dense depth map, and they generalise to scenes "
     "they were never trained on, which is what makes them usable on an aircraft flying "
     "somewhere nobody has surveyed.")
para("Our team works in two parallel tracks. The graded track is a full simulation in "
     "which an aircraft flies procedurally generated indoor courses. The second, a "
     "stretch goal, is a physical fixed wing vertical take off and landing airframe for "
     "which an electronics bill of materials already exists. The perception and avoidance "
     "software is identical across both because it depends on the camera and not the "
     "airframe. A multirotor hovers well but has poor range, a fixed wing has excellent "
     "range but cannot hover or stop, and the vertical take off and landing configuration "
     "does both at the cost of a considerably harder control problem.")
figure("figures/fig2_architecture.png", 3.1,
       "Figure 2. System architecture from camera to actuators. Only depth estimation "
       "is learned.")

heading("1.3 Problem Statement", 1)
para("A small aircraft carrying only a single forward facing colour camera must travel "
     "from a start position to a sequence of specified positions inside a cluttered space "
     "without striking anything, using no distance sensor, no prior map and no external "
     "positioning infrastructure.")
para("Three properties make this hard and they fail in different ways. First, the "
     "distance is predicted rather than measured, and a prediction can be confidently "
     "wrong. A laser range finder reporting two metres is either correct or detectably "
     "broken. A network reporting two metres may be producing a plausible looking map "
     "with a large error in exactly the region that matters, and nothing in the output "
     "announces this.")
para("Second, the prediction has no units. The model is trained in a way that "
     "deliberately ignores absolute scale, so its output says which things are nearer "
     "than which but not that the wall is three metres away. Any rule of the form stop "
     "when something is closer than a given distance needs a separate source of scale.")
para("Third, the sensor sees a wedge while the aircraft occupies an area. A camera covers "
     "perhaps ninety degrees ahead. An aircraft with a one metre wingspan sweeps a full "
     "circle when it turns. Anything leaving the frame becomes invisible immediately and "
     "the wingtip does not care that it is no longer observed. This was the dominant cause "
     "of collisions in our own measurements and is evidenced in Chapter 4. The problem is "
     "therefore not only to estimate depth but to build a control loop that behaves safely "
     "while its only source of distance is unreliable, unscaled and incomplete.")

heading("1.4 Proposed AI and ML Solution", 1)
para("The system is split so that exactly one stage learns anything and no stage "
     "affecting safety does. The learned stage is perception. A pretrained MiDaS model "
     "receives one colour image and returns a depth map. We do not train it and collect "
     "no data to train it. It answers one narrow question, how far away each pixel is, "
     "and has no notion of an obstacle, a goal or an aircraft.")
para("Everything after that is ordinary engineering a person can read and check. The "
     "depth map is filtered so only surfaces at the aircraft's own flying height count, "
     "which removes floor and ceiling. Each image column is reduced to the nearest "
     "surface in it. Every obstacle is widened sideways by the angle the wing needs to "
     "clear it at that distance, so a gap only counts if the aircraft fits through. Each "
     "candidate heading is scored on free space against how far it points from the next "
     "target, and the best becomes the steering command.")
para("Underneath sits a safety layer with a single rule. If anything at flying height is "
     "closer than a set distance ahead, forward motion is refused and the aircraft turns "
     "on the spot. This layer contains no learned component, which is the entire reason it "
     "can be trusted. A guardrail that is four lines of arithmetic can be argued correct. "
     "A guardrail that is a neural network cannot.")
para("A short term memory of recent obstacles addresses the third difficulty above. It "
     "records how far the nearest surface was in each direction, carries that forward "
     "through the aircraft's own motion and lets it decay. It builds no map and localises "
     "nothing, so it does not turn this into a mapping problem. Its only purpose is to "
     "stop the aircraft rotating a wingtip into something that has just left the frame.")
para("The measurement that justifies the project is an ablation. The identical aircraft "
     "flies identical courses under three depth sources. Perfect depth from the simulator "
     "sets the ceiling. Depth estimated by MiDaS is the real system. No depth at all "
     "confirms the task is not trivially easy. The gap between the first two is the price "
     "of replacing a measuring instrument with a prediction, measured with everything else "
     "held constant.")

heading("1.5 Success Criteria", 1)
table(["Question", "Project Specific Answer"],
      [["What is the input?",
        "One colour image, 320 by 240 pixels, from a forward facing camera, plus the "
        "bearing to the next target position from the flight controller."],
       ["What is the expected output?",
        "A steering command of forward speed, yaw rate and climb rate at least ten times "
        "per second, plus a flag stating whether the safety layer has stopped forward "
        "motion."],
       ["Who will use the output?",
        "The flight controller consumes it directly. The supervising operator sees the "
        "same information and holds a manual override at all times."],
       ["How will the output help solve the problem?",
        "It lets a small aircraft fly through cluttered space without a distance sensor, "
        "removing the mass, cost and power a laser scanner or stereo pair would add."]],
      widths=[1.6, 4.65], size=9)
caption("Table 1. Success criteria input and output definition.")
table(["Type", "Success Criterion", "How It Will Be Measured"],
      [["Technical", "Depth accuracy of the pretrained model",
        "Proportion of pixels within a factor of 1.25 of true depth, with absolute "
        "relative error, on the NYU and KITTI test splits after aligning scale and shift "
        "by least squares."],
       ["Technical", "Perception rate",
        "At least ten depth maps per second in the chosen serving configuration, reported "
        "as a distribution over a run rather than a best case."],
       ["Technical", "Camera to command latency",
        "Not more than one hundred milliseconds at the simulated cruise speed of two "
        "metres per second."],
       ["Technical", "Route completion",
        "Proportion of held out seeded courses on which every target is reached, with a "
        "confidence interval."],
       ["Technical", "Collision free completion",
        "Proportion of held out courses completed with zero contact events. This is the "
        "headline number."],
       ["Technical", "Value of the perception stage",
        "Difference in collision free completion between perfect depth, estimated depth "
        "and no depth on identical courses."],
       ["Practical", "Safety layer integrity",
        "Zero contacts across twenty runs with the steering policy switched off and only "
        "the stop rule active."],
       ["Practical", "Reproducibility",
        "Any team member reproduces the headline number from a clean checkout in under an "
        "hour, because courses come from integer seeds."],
       ["Practical", "Cost",
        "The simulation costs nothing. The optional physical build stays inside a budget "
        "the team can fund without institutional support."],
       ["Practical", "Honest reporting",
        "The published headline is always the estimated depth result on held out courses, "
        "never the perfect depth result and never a number obtained on tuning courses."]],
      widths=[0.8, 1.75, 3.7], size=9)
caption("Table 2. Technical and practical success criteria.")
para("The last criterion was added part way through the semester rather than at the "
     "start. Section 4.1 explains why, and the reason is not a comfortable one.")

# ================================================================== CHAPTER 2
heading("CHAPTER II. AI AND ML PROJECT LIFE CYCLE AND DIFFERENCE FROM "
        "CONVENTIONAL SOFTWARE", 0)
heading("2.1 Proposed Life Cycle of Our Project", 1)
para("Our life cycle runs through eight stages. Written as a list it looks linear, which "
     "is misleading, so the feedback paths are drawn in Figure 1 and described after it. "
     "The stages are problem scoping and stakeholder analysis, requirements and "
     "feasibility, simulation environment and course generation, data acquisition and "
     "exploration, depth model integration, avoidance policy and safety layer, evaluation "
     "and ablation, and finally deployment profiling and monitoring.")
figure("figures/fig1_lifecycle.png", 3.2,
       "Figure 1. Proposed project life cycle showing the two feedback loops that matter "
       "most.")
para("Two feedback paths matter more than the others. The first runs from evaluation back "
     "to data and modelling. If the ablation shows estimated depth performing far worse "
     "than perfect depth, the correct response is not to adjust the steering policy. It is "
     "to return to perception and ask whether depth is being aligned correctly, whether "
     "the input resolution is too low, or whether simulator imagery differs from the "
     "photographs the model was trained on. We have used this loop already. An early "
     "evaluation produced results so poor that we went back and found the depth reaching "
     "the policy was dominated by the floor rather than by obstacles.")
para("The second runs from monitoring back to scoping. If scenes encountered in service "
     "stop resembling those used in development, because of fog, low sun or dust, the "
     "model has not broken but the problem definition has moved. The response is lower "
     "speed and a larger stop distance rather than immediate retraining, because a safety "
     "related system should become more cautious when its inputs become less trustworthy.")
para("This is the clearest difference from conventional software. There a defect is a "
     "mistake in the code and the fix is a change to the code. Here a fall in performance "
     "can come from the model, the data, a shift in the environment, or a threshold "
     "calibrated under conditions that no longer hold. Diagnosis has to precede repair, "
     "and the life cycle has to make room for that.")

heading("2.2 Why Our Project Is an AI and ML Project", 1)
para("It is fair to ask whether this is a machine learning project at all, given that the "
     "steering logic is hand written and we train nothing. The answer is that the entire "
     "system rests on a learned component, and every property distinguishing machine "
     "learning engineering from ordinary engineering follows from that dependence.")
table(["Aspect", "Our AI and ML Project"],
      [["Primary input",
        "A single colour image from one camera. No distance sensor and no second camera, "
        "so depth is inferred and never measured."],
       ["Expected behaviour",
        "The network returns a plausible estimate rather than a guaranteed value. Two "
        "visually similar scenes can give noticeably different depth, and the output "
        "carries no indication of when it should be doubted."],
       ["Role of data",
        "Data determines the perception stage entirely. We write no rules for judging "
        "distance. The model learned them from a mixture of public datasets, so its blind "
        "spots are inherited rather than authored by us."],
       ["Testing and evaluation",
        "There is no correct output to assert against. Testing is statistical. We measure "
        "depth error against reference datasets and flight outcomes across many seeded "
        "courses, reporting distributions and intervals rather than pass or fail."],
       ["Changes after deployment",
        "The code can be frozen and performance can still fall, because lighting, "
        "surfaces, weather and scene content change. This cannot happen to a sorting "
        "routine and is the defining risk of a deployed model."],
       ["Monitoring requirement",
        "Scene statistics such as brightness, depth map entropy and near field pixel "
        "fraction are tracked against a reference. A significant shift lowers speed and "
        "raises the stop distance. Retraining is only a second line response."]],
      widths=[1.35, 4.9], size=9)
caption("Table 3. Characteristics of the project as an AI and ML project.")
para("One difference is easy to overlook. The model runs on each frame independently "
     "with no memory, so a stationary camera on a stationary scene still produces a depth "
     "map that flickers. The control loop must tolerate that, which is why the chosen "
     "heading is smoothed over time rather than taken from the newest frame.")

heading("2.3 ML Project Compared With an ML Pipeline", 1)
para("A pipeline is the part of the work that runs without a person present. The project "
     "is the larger activity around it, including every decision somebody must be "
     "accountable for. Separating the two honestly matters here, because this system can "
     "cause physical harm and it is tempting to describe more of it as automated than "
     "really is.")
table(["Possible Automated Pipeline Activities", "Human Decisions and Accountability"],
      [["Generating courses from integer seeds and exporting paired colour and true depth "
        "frames.",
        "Deciding what obstacle density and geometry represent a fair test rather than one "
        "chosen because the aircraft performs well on it."],
       ["Running the depth model over a benchmark split and computing accuracy and error.",
        "Deciding what accuracy justifies flying at all, and stating the conditions under "
        "which the answer would be no."],
       ["Running the policy across many seeded courses and logging completion, contacts, "
        "time and minimum clearance.",
        "Deciding which seeds are used for tuning and which are held back, and committing "
        "to that split before results are seen."],
       ["Searching the policy parameters for values that score best.",
        "Deciding whether an improvement found on tuning seeds is real or an artefact of a "
        "small sample, and choosing which number gets reported."],
       ["Measuring inference latency across serving stacks and producing the comparison.",
        "Choosing the deployment configuration and accepting the latency budget it implies "
        "at the intended flight speed."],
       ["Comparing live scene statistics against a reference and raising an alert on "
        "divergence.",
        "Deciding what the aircraft does about it. Our answer is slow down and increase "
        "the stop distance, which is a safety judgement rather than a computation."],
       ["Running unit tests and a short headless flight as a quality gate before any "
        "change is accepted.",
        "Deciding the aircraft is fit to fly near people, which no automated gate is "
        "qualified to certify."]],
      widths=[3.1, 3.15], size=9)
caption("Table 4. Automated pipeline activities against human decisions.")
para("The pattern is consistent. Measurement automates well and judgement does not. Every "
     "row on the right involves either a value judgement about acceptable risk or a "
     "decision requiring a named person to be answerable. For a system that can strike a "
     "person that separation is not a formality.")

# ================================================================== CHAPTER 3
heading("CHAPTER III. AI PROJECT LIFE CYCLE FRAMEWORKS", 0)
heading("3.1 CRISP-DM Mapping", 1)
table(["CRISP-DM Phase", "How This Phase Applies to Our Project"],
      [["Business Understanding",
        "Establishing that the objective is reducing sensor mass and cost, not producing "
        "depth maps for their own sake. Success is collision free completion of a route, "
        "and the acceptable failure rate is a safety decision."],
       ["Data Understanding",
        "Examining the paired colour and true depth frames from the simulator and the NYU "
        "and KITTI splits. Depth distributions, camera parameters, and how far simulated "
        "imagery sits from real photographs."],
       ["Data Preparation",
        "Resizing and normalising, and the critical step of aligning the unscaled model "
        "output by fitting both a scale and an offset. Getting this wrong invalidates "
        "every downstream number."],
       ["Modelling",
        "Integration rather than training. The pretrained model is brought into the loop, "
        "exported to a portable format and checked for parity. Policy parameters are "
        "fitted here, which is optimisation rather than learning."],
       ["Evaluation",
        "Depth accuracy against benchmarks and flight outcomes across held out seeded "
        "courses under each depth source. This feeds the ablation and is where the project "
        "demonstrates its claim or does not."],
       ["Deployment",
        "Packaging perception and policy so they run identically on a laptop and a "
        "companion computer, profiling speed, and choosing a serving configuration against "
        "the latency budget."]],
      widths=[1.3, 4.95], size=9)
caption("Table 5. CRISP-DM phase mapping.")

heading("3.2 Microsoft TDSP Mapping", 1)
table(["TDSP Stage", "Application to Our Project"],
      [["Business Understanding",
        "The same scoping work with more emphasis on named roles. TDSP expects each "
        "deliverable to have an owner, which suits a team of four with divided "
        "responsibilities."],
       ["Data Acquisition and Understanding",
        "Setting up the course generator, exporting the dataset with a manifest recording "
        "every seed, and obtaining benchmark splits with licence terms recorded."],
       ["Modelling",
        "Depth integration, scale and offset alignment, and the policy parameter search. "
        "The feature and model report TDSP asks for maps onto our depth benchmark and "
        "ablation results."],
       ["Deployment",
        "A container holding perception and policy, run alongside the simulator, arranged "
        "as a companion computer would host it."],
       ["Customer Acceptance",
        "No external customer exists. The nearest equivalent is faculty review and the "
        "internal decision on whether the system is safe to fly outdoors. We treat it as a "
        "formal go or no go."]],
      widths=[1.55, 4.7], size=9)
caption("Table 6. Microsoft TDSP stage mapping.")

heading("3.3 Google ML Life Cycle and Pipeline Perspective", 1)
table(["Pipeline Stage", "Possible Automation", "Human Decision Required"],
      [["Data ingestion", "Course generation from seeds and frame export run unsupervised.",
        "Whether generated courses fairly represent the intended environment."],
       ["Data validation",
        "Range, missing value and camera parameter checks on every exported batch.",
        "What to do when validation fails. Discarding a batch changes the dataset and must "
        "be recorded."],
       ["Data transformation",
        "Resizing, normalisation and alignment are deterministic and scripted.",
        "The choice of alignment method, which materially changes every accuracy figure."],
       ["Model evaluation",
        "Benchmark metrics and flight outcomes computed on every change.",
        "The threshold below which the system is unfit to fly."],
       ["Model validation",
        "A gate running unit tests and a short headless flight before a change is "
        "accepted.",
        "Whether passing that gate is enough to proceed to a physical flight. It is not."],
       ["Serving", "Building the container image and recording measured latency.",
        "The serving configuration and acceptance of the resulting latency at flight "
        "speed."],
       ["Monitoring", "Continuous comparison of scene statistics against a reference.",
        "The response policy on drift, and the decision to ground the aircraft if it "
        "persists."]],
      widths=[1.05, 2.6, 2.6], size=9)
caption("Table 7. Google ML life cycle pipeline stages.")

heading("3.4 Final Framework Choice and Justification", 1)
para("We have chosen CRISP-DM as the primary framework, with the pipeline discipline of "
     "the Google life cycle applied to the parts of the work that repeat.")
para("CRISP-DM fits because our project is investigative. The question is how much "
     "performance is lost when measured depth is replaced by predicted depth, and we do "
     "not know the answer in advance. CRISP-DM is explicitly cyclical and expects "
     "evaluation to send work back to data preparation and modelling. That is exactly what "
     "happened to us, more than once, and a framework treating it as normal rather than as "
     "failure is the right shape for this work.")
para("TDSP was a serious candidate because our team maps well onto its role structure and "
     "its documentation deliverables are close to what the course requires. We did not "
     "choose it because its customer acceptance stage assumes an external client with an "
     "agreed specification, which we do not have. Forcing that stage would produce "
     "paperwork rather than insight. We have borrowed its habit of assigning a named owner "
     "to each deliverable, which appears on the cover page.")
para("The Google life cycle is the most useful of the three for anything that runs more "
     "than once, which for us is course generation, evaluation and the quality gate. It is "
     "a poor organising framework at this stage because it assumes a system already in "
     "production with a stable retraining loop. The arrangement is therefore CRISP-DM for "
     "the shape of the work, with pipeline thinking applied to the repeated parts.")

# ================================================================== CHAPTER 4
heading("CHAPTER IV. PROBLEM SCOPING AND FEASIBILITY ANALYSIS", 0)
heading("4.1 Technical Feasibility", 1)
table(["Technical Aspect", "Analysis for Our Project", "Risk or Limitation", "Mitigation"],
      [["Data sufficiency",
        "No training data needed, since the model is used as published. The simulator "
        "produces perfectly aligned colour and depth pairs at no cost, and public "
        "benchmarks provide real photographs with measured depth.",
        "Simulator imagery is cleaner than real photographs, so good simulation results "
        "may not carry across.",
        "Report benchmark accuracy on real photographs alongside simulation results and "
        "state which claims are simulation only."],
       ["Model capability",
        "MiDaS-small is about twenty one million parameters with a 256 by 256 input, built "
        "for devices without a graphics processor.",
        "Output has no units and is undetermined up to both a scale and an offset, so a "
        "rule in metres cannot be applied directly.",
        "Fit both terms by least squares. Keep steering on relative comparisons and give "
        "the stop rule its own conservative calibration."],
       ["Latency and hardware",
        "The simulation runs on an ordinary laptop and sustains over two hundred complete "
        "loops per second including physics and both renders, against a requirement of "
        "ten.",
        "The proposed architecture streams video over a wireless link and returns the "
        "command the same way, which can consume the whole latency budget.",
        "Measure the round trip before committing. Benchmark the model directly on the "
        "companion computer, since the assumption that it is too slow is untested."],
       ["Sensor coverage",
        "The camera covers a wedge ahead. The airframe is one metre across the wing, taken "
        "from the team's own design files.",
        "Anything leaving the frame becomes invisible while the wingtip keeps sweeping "
        "through it. This dominated contacts in our measurements.",
        "Use a wide angle lens and keep a short term decaying memory of recent obstacles. "
        "Both were tested and both help."],
       ["Airframe control",
        "The electronics design uses four motors with two tilt servos, making this a "
        "tilting rotor aircraft rather than a fixed rotor design.",
        "Tilting mechanisms are the hardest vertical take off and landing class to build "
        "and tune, and transition is a known failure point.",
        "Treat the build as a stretch goal, keep avoidance testing in hover where it "
        "behaves like a multirotor, and treat transition as a separate demonstration."]],
      widths=[1.0, 1.95, 1.7, 1.6], size=8)
caption("Table 8. Technical feasibility analysis.")
figure("figures/fig4_simulation.png", 4.8,
       "Figure 4. Simulation environment. Chase view left, aircraft camera top right, "
       "perfect depth beneath it.")
para("Measured results follow. Every figure uses perfect depth from the simulator, so it "
     "is the best the steering policy could achieve with a flawless depth network. The "
     "estimated depth arm cannot exceed it.")
table(["Obstacles in a 10 m room", "Route completed", "No contact", "Contacts per run",
       "Timeouts"],
      [["4", "47 of 50", "41 of 50", "0.16", "3"],
       ["6", "38 of 50", "33 of 50", "0.20", "12"],
       ["9", "28 of 50", "22 of 50", "0.34", "22"]],
      widths=[1.6, 1.2, 1.1, 1.2, 0.9], size=9)
caption("Table 9. Measured performance using perfect depth on fifty held out courses.")
figure("figures/fig5_results.png", 3.4,
       "Figure 5. Collision free completion against obstacle density, with the 90 per "
       "cent target shown.")
para("The depth model has since been substituted into the same loop. On ten courses at "
     "six obstacles the aircraft touched something 1.6 times per run on perfect depth, 3.4 "
     "times on estimated depth, and 37.1 times with no depth at all. That last figure "
     "confirms the task is not trivially easy, and the gap between the first two is the "
     "price of the prediction. Speed is not a constraint. The model runs in 8.7 "
     "milliseconds per frame on this laptop, about 115 frames per second, against a "
     "requirement of ten. Appendix G records the integration and the mistake inside it "
     "that took longest to find.")
para("Two findings changed how we work and belong in a feasibility chapter rather than "
     "being quietly corrected later. The first concerns tuning. We searched the policy "
     "parameters against twelve courses and reached eleven successes out of twelve, about "
     "92 per cent. The same parameters applied unchanged to fifty held back courses gave "
     "66 per cent. The gap is not noise. It is the difference between measuring on the "
     "sample you optimised against and one you did not. The confidence interval on the "
     "held out figure runs from 52 to 78 per cent, wide enough that the original claim was "
     "never supportable. This is why the splits in Chapter 7 exist and why honest "
     "reporting became an explicit success criterion.")
para("The second concerns where the system fails. Contacts are rare at roughly one in "
     "five runs, which shows the safety layer working. Almost every failure is a timeout "
     "instead. The aircraft flies into a concave pocket, finds every forward direction "
     "blocked, backs out and repeats. A purely reactive policy has no representation in "
     "which going around the far side exists, so it cannot form that intention. We "
     "confirmed by flood filling the free space that every target was geometrically "
     "reachable at every density, which rules out an impossible course. This is a "
     "limitation of the chosen method, not a defect in the implementation.")
para("The consequence is uncomfortable and worth stating plainly. Our original target of "
     "90 per cent collision free completion using estimated depth cannot be met while the "
     "perfect depth ceiling sits at 66 per cent at the same density. Either the courses "
     "become less cluttered and we report success against density as a curve, or the "
     "target moves and we say so, or the policy gains a way out of local traps, which "
     "means admitting some planning and amending the scope. We favour the first, because a "
     "curve says more about the method than a single number. Overall, the project is "
     "technically feasible in simulation and this is demonstrated rather than assumed. The "
     "physical build is feasible in principle but carries substantial risk in the tilting "
     "mechanism and the wireless link, and remains a stretch goal.")

heading("4.2 Economic Feasibility", 1)
table(["Cost or Benefit Item", "Description", "Level", "Justification"],
      [["Data acquisition", "Simulator frames generated locally. Benchmark splits are "
        "public research releases.", "Low",
        "No purchase and no collection effort. A few gigabytes of download and a record of "
        "licence terms."],
       ["Data cleaning and labelling",
        "The simulator supplies exact depth, so nothing needs labelling. Benchmarks arrive "
        "annotated.", "Low",
        "Labelling is normally the largest cost in a vision project. Here it is near zero, "
        "a real advantage of working in simulation."],
       ["Computing and infrastructure",
        "Development on laptops the team already owns. A free cloud graphics processor "
        "only for the accelerated profiling comparison.", "Low",
        "No training means no sustained compute cost, and the loop already exceeds the "
        "required rate on a laptop."],
       ["Development effort",
        "Four students across one semester covering simulation, perception, hardware and "
        "documentation.", "High",
        "The real cost, paid in time rather than money, and the resource most likely to "
        "run out."],
       ["Maintenance and retraining",
        "The model is used as published and never retrained. Maintenance is dependency "
        "updates and recalibration if the camera changes.", "Low",
        "Choosing zero shot use over training removes the retraining pipeline entirely."],
       ["Physical airframe and electronics",
        "Flight controller, companion computer, positioning, propulsion, servos, battery, "
        "radio link and crash spares.", "Medium",
        "Estimated 55,000 to 90,000 rupees for a first build including spares. Early "
        "transition flights are expected to cause damage."],
       ["Expected benefit and value",
        "A measurement of how much avoidance performance is lost when a distance sensor is "
        "replaced by a prediction.", "High",
        "Transferable to any small aircraft where sensor mass matters, and it is a "
        "measurement rather than an opinion."]],
      widths=[1.2, 1.95, 0.6, 2.5], size=8)
caption("Table 10. Economic feasibility analysis.")
para("Economic feasibility conclusion. The graded simulation costs nothing beyond hardware "
     "the team owns and time the semester allocates, so it is unambiguously feasible. The "
     "airframe is the only real expenditure. The team has adopted a two stage purchase. "
     "Flight controller, positioning, power regulation, receiver and servos are bought "
     "first because any configuration needs them. Motors, propellers and speed controllers "
     "are deferred until all up mass and thrust to weight are known, because selecting "
     "them earlier is guessing with money.")
table(["Subsystem", "Component", "Qty", "Notes"],
      [["Flight controller", "Pixhawk 6C", "1",
        "Runs PX4. Handles vertical take off and landing modes, stabilisation and actuator "
        "outputs."],
       ["Companion computer", "Raspberry Pi 5, 8 GB", "1",
        "Camera capture, wireless link and command relay."],
       ["Positioning", "M10 GPS and compass", "1", "Position and heading for autonomy."],
       ["Power monitoring", "Compatible power module", "1",
        "Battery voltage and current sensing, regulated flight controller power."],
       ["Propulsion", "Brushless motors", "4",
        "Roughly 22xx to 28xx class initially. Final speed constant depends on mass, "
        "propeller and battery."],
       ["Propulsion", "30 to 40 A speed controllers", "4",
        "One per motor. Rating checked against measured current."],
       ["VTOL actuation", "High torque metal gear tilt servos", "2",
        "Left and right tilt mechanisms. Low backlash matters."],
       ["Flight controls", "Control surface servos", "2 to 4",
        "Aileron, elevator and rudder arrangement depends on the airframe."],
       ["Servo power", "External 5 V regulator, 5 A or more", "1",
        "Powers servos separately so heavy loads cannot disturb the flight controller."],
       ["Vision", "1080p camera", "1", "Forward facing colour camera for depth estimation."],
       ["Radio safety", "Long range receiver and transmitter", "1 each",
        "Manual override, required at all times during testing."],
       ["Battery", "4S or 6S lithium polymer, 4000 to 6000 mAh", "1",
        "Capacity and voltage sized after the propulsion calculation."],
       ["Power distribution", "Connectors, wiring and distribution board", "1 set",
        "Main battery connection and high current distribution."],
       ["Safety", "Buzzer and arming switch", "1 each",
        "Recommended for any physical testing."]],
      widths=[1.15, 1.75, 0.45, 2.9], size=8)
caption("Table 11. Electronics bill of materials for the physical airframe.")

heading("4.3 Operational Feasibility", 1)
table(["Operational Question", "Analysis for Our Project"],
      [["Who will operate the system?",
        "During the semester, the four team members. Any physical flight requires a named "
        "pilot in command holding a manual override, responsible for the aircraft "
        "regardless of what the software decides."],
       ["Who will maintain the data?",
        "The simulator dataset is regenerated from committed seeds rather than stored, so "
        "maintenance is keeping the generator and manifest under version control. "
        "Benchmarks are fixed public releases recorded with their licence terms."],
       ["Who will monitor the model?",
        "Scene statistics are computed each run and compared against a reference. Within "
        "the project the team reviews this. Any real deployment needs a named owner, "
        "because an alert nobody reads is not monitoring."],
       ["Who will handle retraining?",
        "Nobody, by design. The model is used as published. If performance became "
        "unacceptable the first response is lower speed and a larger stop distance. Light "
        "adaptation is a second line response and must pass the quality gate."],
       ["What skills and infrastructure are required?",
        "Python, working knowledge of the simulation and autopilot software, and enough "
        "understanding of monocular depth to know when to distrust it. A laptop, version "
        "control and a free continuous integration allowance. Physical flight adds an "
        "enclosed space with soft flooring and propeller guards."],
       ["Can the organisation sustain it over time?",
        "As a student project, only within the semester. Seeded courses, pinned "
        "dependencies and a readme that reproduces the headline result in under an hour "
        "are what give it a life afterwards."]],
      widths=[1.55, 4.7], size=9)
caption("Table 12. Operational feasibility analysis.")
para("Operational feasibility conclusion. The simulation is comfortably operable as it "
     "stands. Physical operation is feasible only under stated conditions, namely a manual "
     "override held by a named pilot, propeller guards fitted, an enclosed space with soft "
     "flooring for hover testing, and no transition attempt until hover is stable and "
     "repeatable.")

heading("4.4 Ethical Feasibility", 1)
para("Ethical feasibility is treated as a question that can return the answer no. It is "
     "not a cost to be balanced against performance. If a harm cannot be reduced to an "
     "acceptable level the work does not proceed in that form, and the simulation only "
     "scope of the graded deliverable is that decision taken early.")
table(["Ethical Issue", "Who May Be Affected", "Potential Harm",
       "Requirement and Enforcement"],
      [["Privacy and data use",
        "Anyone within view of the camera, including people who never agreed to be "
        "recorded and are not involved in the flight.",
        "A camera above head height sees into gardens, windows and private ground. "
        "Retaining that footage creates a surveillance record of people with no "
        "relationship to the project.",
        "The model needs the image only for the instant it is processed. No frame is "
        "written to disk in flight, processing stays on the aircraft or the operator's own "
        "machine, and nothing goes to a third party. Enforced by keeping recording off by "
        "default and reviewing the code path before any outdoor flight."],
       ["Bias and fairness",
        "People and property in environments unlike the scenes the model was trained on.",
        "The model inherits its training data's blind spots and performs worse on "
        "textureless surfaces, thin structures, glass and mirrors. An aircraft reliable in "
        "a furnished room and unreliable in a bare corridor transfers risk onto whoever is "
        "in the corridor.",
        "Failure modes are enumerated and tested rather than discovered in flight. Reduced "
        "performance on textureless surfaces and thin obstacles is stated in the model "
        "documentation and reflected in a more conservative stop distance."],
       ["Transparency and explainability",
        "Operators, reviewers and anyone investigating an incident.",
        "After a collision an operator must be able to establish whether the depth, the "
        "steering or the safety layer failed. A system that cannot be interrogated cannot "
        "be improved or trusted.",
        "Only one stage learns anything and every safety relevant stage is readable "
        "arithmetic. Per frame depth statistics, chosen heading, issued commands and "
        "minimum clearance are logged for every run, which makes reconstruction possible."],
       ["Misuse or harmful decisions",
        "Bystanders, property owners and people who could be observed without their "
        "knowledge.",
        "Autonomy that lets an aircraft navigate without a skilled pilot also lowers the "
        "barrier to persistent unattended observation. The capability that makes "
        "inspection cheaper makes following someone cheaper.",
        "Intended use is stated as civil inspection and short range navigation, with a "
        "responsible use statement. The system carries no person detection, target "
        "tracking or recording capability, which are deliberate omissions."],
       ["Human oversight and accountability",
        "Bystanders and the operator, who carries legal responsibility.",
        "Treating an autonomous system as responsible for its own behaviour leaves nobody "
        "accountable when it causes harm, and automation can encourage an operator to stop "
        "paying attention.",
        "A named pilot in command holds a manual override at all times. The non learned "
        "stop layer sits beneath the policy and cannot be overridden by it. Autonomy is "
        "never presented as a substitute for supervision."]],
      widths=[1.0, 1.2, 2.0, 2.05], size=8)
caption("Table 13. Ethical feasibility analysis.")
para("Ethical feasibility conclusion. The project may proceed under specific conditions. "
     "The graded deliverable stays in simulation. Any physical flight begins indoors, "
     "enclosed, over soft flooring, with guards fitted and a named pilot holding an "
     "override. No transition is attempted until hover is stable, because transition is "
     "the highest risk phase and the aircraft cannot stop once flying on the wing. No "
     "frames are written to disk in flight. Published results always quote the estimated "
     "depth figure on held out courses, with the perfect depth result reported alongside "
     "as a stated ceiling and never as the headline.")
para("The last condition follows directly from Section 4.1. Having found that our own "
     "tuned number overstated performance by more than twenty percentage points, treating "
     "honest reporting as an ethical requirement rather than a stylistic preference seemed "
     "the only defensible position. Overstating the reliability of a system that can "
     "strike a person is a safety problem and not a presentational one.")
para("One further point belongs here. Regulation in India places uncrewed aircraft into "
     "weight categories with obligations that increase as the aircraft gets heavier, and "
     "an airframe with a wing, battery, companion computer and four motors sits well above "
     "the lightest category. A research exemption is also available to recognised "
     "educational institutions flying within their own premises. Confirming which applies "
     "is a prerequisite for outdoor flight and the team treats it as a gate rather than "
     "paperwork to complete afterwards.")

# ================================================================== CHAPTER 5
heading("CHAPTER V. REQUIREMENTS ENGINEERING FOR AI", 0)
para("Requirements are written so each can be shown to pass or fail. Statements such as "
     "the system should be responsive are avoided, because they cannot be tested and "
     "therefore cannot be argued about usefully.")
heading("5.1 Functional Requirements", 1)
table(["ID", "Functional Requirement", "Priority", "Acceptance or Test Criterion"],
      [["FR1", "The perception module shall accept a single colour image from the forward "
        "camera and produce a dense depth map covering the full frame.", "Essential",
        "Reference frames are processed and every output checked for correct dimensions, "
        "no missing values, and depth inside the expected range."],
       ["FR2", "The avoidance module shall convert each depth map into a steering command "
        "of forward speed, yaw rate and climb rate.", "Essential",
        "For each reference frame the command is compared with the expected direction. An "
        "obstacle on the left must produce a turn to the right and the reverse."],
       ["FR3", "A safety layer shall refuse forward motion whenever the nearest surface at "
        "flying height ahead is closer than a configurable distance, overriding the "
        "policy.", "Essential",
        "Twenty runs with the policy disabled so only the stop rule is active. Met only if "
        "there are zero contacts."],
       ["FR4", "The system shall fly from a start position through an ordered sequence of "
        "operator specified targets without further human input.", "Essential",
        "A route of four targets flown on held out courses. Each target counts as reached "
        "within 0.7 metres."],
       ["FR5", "The system shall record per frame depth statistics, issued commands, "
        "minimum clearance and contact events for every run.", "Essential",
        "After any run the log can reconstruct why a command was issued at a given "
        "moment."],
       ["FR6", "The course generator shall produce an identical layout for a given seed "
        "and a different layout for a different seed.", "Essential",
        "The same seed built twice gives identical obstacle positions. Two seeds give "
        "different ones. Both checked automatically."],
       ["FR7", "The operator shall specify targets on a plan view before flight, and "
        "targets inside an obstacle or too close to a wall shall be refused.", "Desirable",
        "A target placed inside an obstacle is rejected with a message and not added to "
        "the route."],
       ["FR8", "The system shall reduce speed and increase the stop distance when scene "
        "statistics diverge from the reference.", "Desirable",
        "A deliberately degraded scene is introduced. Met if commanded speed falls and "
        "stop distance rises without manual intervention."]],
      widths=[0.4, 2.2, 0.7, 2.95], size=8)
caption("Table 14. Functional requirements.")

heading("5.2 Non Functional Requirements", 1)
table(["ID", "Non Functional Requirement", "Target or Constraint", "How It Is Verified"],
      [["NFR1", "Task success on courses the aircraft has not seen before.",
        "Reported as a curve against obstacle density rather than one figure, on at least "
        "fifty held out courses.",
        "Batch evaluation over held out seeds, reported with a confidence interval and "
        "with the perfect depth result alongside as a stated ceiling."],
       ["NFR2", "Perception keeps up with the control loop.",
        "At least ten depth maps per second and a control loop of at least ten cycles per "
        "second end to end.",
        "Measured over a full run and reported as a distribution. Our simulation loop "
        "currently sustains more than two hundred cycles per second."],
       ["NFR3", "The delay between capturing an image and issuing a command is bounded.",
        "Not more than one hundred milliseconds at a cruise speed of two metres per "
        "second.",
        "Timestamped at each stage. The budget is derived below rather than asserted."],
       ["NFR4", "The stop layer prevents contact on its own.",
        "Zero contacts across twenty runs with the steering policy disabled.",
        "Dedicated runs driving the aircraft at obstacles with only the stop rule active."],
       ["NFR5", "The pretrained model is accurate enough on real photographs to justify "
        "use.",
        "At least 0.80 of pixels within a factor of 1.25 of true depth on the NYU split, "
        "with absolute relative error.",
        "Benchmark evaluation after aligning both scale and offset by least squares. "
        "Median scaling alone is not acceptable and would invalidate the result."],
       ["NFR6", "Results can be regenerated by someone else.",
        "Seeded courses, pinned dependency versions and a readme reproducing the headline "
        "number in under an hour.",
        "A team member who did not write the code follows the readme from a clean checkout "
        "and obtains the same figures."],
       ["NFR7", "The depth source can be replaced without touching the planner.",
        "The policy receives the depth map as an argument and holds no dependency on how "
        "it was produced.",
        "The same harness runs unchanged with simulator depth and model depth. This is "
        "what makes the ablation possible."],
       ["NFR8", "Reduced confidence produces more caution, never less.",
        "Detected drift results in lower speed and a larger stop distance.",
        "Verified by introducing a degraded scene and confirming commanded speed falls."]],
      widths=[0.42, 1.85, 1.85, 2.13], size=8)
caption("Table 15. Non functional requirements.")
para("The latency figure in NFR3 is derived rather than chosen. At two metres per second "
     "the aircraft travels 0.20 metres during a hundred millisecond delay. Slowing from "
     "that speed at three metres per second squared takes a further 0.67 metres. Stopping "
     "therefore needs about 0.87 metres before any margin, which is why the stop distance "
     "in FR3 is set above one metre. The two requirements are linked by a physical "
     "calculation, so changing either the cruise speed or the latency budget forces the "
     "other to be revisited.")

heading("5.3 Data Requirements", 1)
table(["Data Requirement", "Project Specific Specification"],
      [["Required data sources",
        "Three. Colour and true depth pairs from the simulator. The NYU Depth V2 labelled "
        "test split of 654 indoor images. A sample of the KITTI outdoor benchmark. The "
        "first is generated, the others downloaded."],
       ["Required features and variables",
        "Per frame, the colour image, true depth where available, camera intrinsic "
        "parameters, aircraft position and heading, the issued command and the minimum "
        "clearance for that step."],
       ["Data volume and availability",
        "At least five thousand simulator pairs across indoor and outdoor style scenes. "
        "Benchmarks are a few gigabytes. Simulator data is unlimited in principle, so the "
        "practical limit is disk space."],
       ["Data format and integration",
        "Images as lossless raster files, depth as single precision arrays in metres, run "
        "logs as tabular records. Camera intrinsics recorded for every source so "
        "comparisons between sources are valid."],
       ["Data quality",
        "Checked on five dimensions. Completeness means no missing depth in the region the "
        "policy uses. Accuracy means simulator depth is exact while benchmark depth "
        "carries sensor error. Consistency means one unit convention throughout. "
        "Timeliness matters only for the live loop. Uniqueness means duplicates are "
        "removed so evaluation is not inflated by repeats."],
       ["Labelling requirements",
        "None for training, since the model is used as published. The simulator supplies "
        "exact depth for evaluation and benchmarks arrive annotated, which removes the "
        "largest single cost in a typical vision project."],
       ["Data update frequency and retention",
        "Simulator data is regenerated from committed seeds rather than retained, so the "
        "seed list is the dataset. Benchmarks are fixed releases. Run logs are kept for "
        "the project to support failure analysis. No imagery of real people is collected "
        "or stored at any point."]],
      widths=[1.45, 4.8], size=9)
caption("Table 16. Data requirements.")

# ================================================================== CHAPTER 6
heading("CHAPTER VI. STAKEHOLDER MANAGEMENT IN AI", 0)
heading("6.1 Stakeholder Identification", 1)
para("For an aircraft that flies over ground it does not own, the people with the most at "
     "stake usually have the least say, and the table is ordered with that in mind.")
table(["Stakeholder Category", "Interest or Role", "Influence", "Potential Concern"],
      [["Bystanders and people on the ground",
        "Present beneath the aircraft. They agreed to nothing and gain nothing.",
        "Very low. They usually cannot see it coming and cannot object.",
        "Injury from a falling or colliding aircraft. Being recorded without consent. "
        "Noise and intrusion."],
       ["Property owners", "Own the buildings, land and vehicles flown near.",
        "Low during flight, high afterwards through complaints and legal action.",
        "Damage from a collision. Overflight of private ground without permission."],
       ["Operator and pilot in command",
        "Flies the aircraft and carries legal responsibility.",
        "High. Holds the override and can stop the flight.",
        "Being held responsible for behaviour produced by software they did not write."],
       ["Project team", "Design, build, evaluate and document the system.",
        "High. Every design decision here is ours.",
        "Delivering a working result within a semester while reporting honestly, including "
        "when results disappoint."],
       ["Faculty and assessors", "Evaluate the work and the reasoning.",
        "High over the academic outcome.",
        "Whether the analysis is genuine or reconstructed afterwards to fit the result."],
       ["Regulators",
        "Set and enforce rules for uncrewed aircraft including registration and airspace.",
        "Very high. Can prohibit outdoor flight entirely.",
        "Unregistered operation. Restricted airspace. Aircraft without a demonstrated "
        "failsafe."],
       ["Institution",
        "Provides the premises for indoor testing and carries institutional liability.",
        "High. Can withdraw permission to test.",
        "Injury on its premises, damage to property, reputational exposure."],
       ["Model and dataset providers",
        "Released the pretrained model and benchmark datasets under stated terms.",
        "Low but binding through licence conditions.",
        "Correct attribution and use within the terms granted, including the non "
        "commercial condition on one dataset."],
       ["Data subjects in benchmark datasets",
        "People captured in the indoor and driving imagery used for evaluation.",
        "None. They cannot influence how the data is used now.",
        "Their imagery being used beyond the research purpose it was released for."],
       ["Insurers", "Would carry the financial consequence of an incident.",
        "Medium. Can refuse cover, which prevents operation.",
        "Whether the system has demonstrated evidence of safe behaviour rather than claims "
        "about it."],
       ["Future maintainers", "Anyone continuing the work after this team disperses.",
        "Low now, high for the project's later usefulness.",
        "Whether results can be reproduced without asking the original authors."],
       ["Adversarial actors", "Would deliberately misuse or exploit the system.",
        "Medium. Cannot be negotiated with, only designed against.",
        "Covered separately in Section 6.5."]],
      widths=[1.2, 1.75, 1.4, 1.9], size=8)
caption("Table 17. Stakeholder identification.")

heading("6.2 Stakeholder Categories Considered", 1)
bullet("Model and system users. The operator and pilot in command, and within the project "
       "the team members running evaluations.")
bullet("Business owners and decision makers. The faculty and the institution, which hold "
       "the equivalent authority for a student project.")
bullet("Data owners. The releasing institutions behind the benchmarks, and the team "
       "itself for the generated simulator data.")
bullet("Data subjects. People appearing in the benchmark imagery, and in any real "
       "deployment anyone coming within view of the camera.")
bullet("Regulators and compliance authorities. The civil aviation authority, whose weight "
       "categories and airspace rules govern outdoor flight.")
bullet("Affected communities. Everyone beneath the flight path, affected without being "
       "consulted.")
bullet("Auditors and reviewers. Faculty assessors now, incident investigators and "
       "insurers in a real deployment.")
bullet("Adversarial stakeholders. Treated separately in Section 6.5.")

heading("6.3 Stakeholder Conflict Analysis", 1)
table(["Stakeholder 1", "Stakeholder 2", "Conflict", "How the Project Addresses It"],
      [["Project team", "Bystanders and property owners",
        "The team benefits from demonstrating a working aircraft outdoors. Bystanders "
        "carry all the physical risk and gain nothing.",
        "Testing is staged. Indoor hover over soft flooring with guards first, no "
        "transition until hover is stable. The graded deliverable stays the simulation, "
        "removing pressure to fly early."],
       ["Project team", "Faculty and assessors",
        "A high headline number is rewarded. The honest number is lower and we know it is "
        "lower because we measured both.",
        "The reporting rule is fixed in advance. Held out courses only, estimated depth "
        "only, perfect depth alongside as a ceiling. Both our tuned and held out figures "
        "appear in Section 4.1."],
       ["Operator and pilot", "Regulators",
        "The operator wants to fly and demonstrate. The regulator requires registration "
        "and airspace compliance first, which is slow.",
        "Regulatory confirmation is a gate before outdoor flight rather than something "
        "resolved afterwards. Indoor testing proceeds meanwhile."],
       ["Institution", "Project team",
        "The team wants space for flight testing. The institution carries liability if "
        "somebody is hurt.",
        "Testing confined to an enclosed area with soft flooring and guards, a named pilot "
        "present and an override held. Permission requested per session rather than "
        "assumed."],
       ["Bystanders", "Operator and pilot",
        "Bystanders prefer the camera never records them. The operator benefits from "
        "footage for debugging.",
        "No frames written to disk in flight. Debugging uses numerical logs of depth "
        "statistics, commands and clearances, enough to reconstruct a failure without "
        "retaining imagery."],
       ["Future maintainers", "Project team",
        "Finishing quickly at the end of a semester conflicts with leaving the work "
        "usable by somebody else.",
        "Seeded courses, pinned dependencies and a reproducibility requirement written as "
        "a requirement rather than an aspiration."]],
      widths=[1.05, 1.05, 2.0, 2.15], size=8)
caption("Table 18. Stakeholder conflict analysis.")

heading("6.4 Data Subjects and Affected Communities", 1)
para("These two groups are often treated as one and they are not the same. The data "
     "subjects are people appearing in the benchmark datasets used to evaluate depth "
     "accuracy. The indoor split contains photographs of furnished rooms in real "
     "buildings and the outdoor split contains street scenes from a moving vehicle. People "
     "are visible in some images. They provided data in the sense that matters and have no "
     "continuing control over its use. Our obligation is narrow but real. Use the data "
     "only for the research purpose it was released for, respect the licence terms "
     "including the non commercial condition on the outdoor dataset, and cite properly.")
para("The affected communities are different people entirely. They are whoever is beneath "
     "the aircraft when it flies. They contributed no data. They are affected by the "
     "system's decisions rather than its inputs, and the harm they face is physical rather "
     "than informational. Nobody in the benchmarks is at risk of being struck by our "
     "aircraft, and nobody beneath our aircraft appears in the benchmarks.")
para("Keeping them apart matters because the protections differ. Data subjects are "
     "protected by licence compliance and intended use. Affected communities are protected "
     "by the stop layer, propeller guards, staged testing and a pilot holding an override. "
     "Conflating them produces a privacy policy where a safety case was needed. In a real "
     "deployment a third group appears, since anyone within view of the camera becomes a "
     "data subject involuntarily while also being an affected community member.")

heading("6.5 Adversarial Stakeholders", 1)
table(["Possible Adversarial Actor", "Possible Action or Threat", "Potential Impact",
       "Basic Mitigation"],
      [["Someone deliberately deceiving the camera",
        "Presenting a large photograph, mirror or screen showing open space where there is "
        "a solid surface. Monocular depth is easy to mislead because it works from "
        "appearance alone.",
        "The aircraft flies into an obstacle it believes is not there, damaging property "
        "or injuring somebody.",
        "The stop layer is calibrated conservatively and does not depend on interpreting "
        "the scene correctly. Reflective and transparent surfaces are documented failure "
        "modes. A pilot override is always available."],
       ["An attacker on the wireless link",
        "Jamming the connection between aircraft and laptop, or injecting false commands.",
        "Loss of control, or the aircraft following commands issued by somebody else.",
        "A link loss failsafe that halts rather than continuing on the last command, and "
        "radio override on a separate link. This is the weakest part of the proposed "
        "architecture and is recorded as such."],
       ["Someone misusing the autonomy for observation",
        "Repurposing hands off navigation to follow or watch a person over time.",
        "Persistent surveillance of an individual without their knowledge.",
        "No person detection, target tracking or recording capability exists. These are "
        "deliberate omissions. A responsible use statement scopes intended application to "
        "civil inspection."],
       ["Someone tampering between flights",
        "Altering the stop distance, disabling the safety layer or replacing the model "
        "file.",
        "A system that appears to work normally while its guardrail has been removed.",
        "Safety parameters held in version control and checked before flight. Model file "
        "verified by checksum. The quality gate must pass before any change is accepted."],
       ["Someone exploiting known model weaknesses",
        "Using knowledge that textureless walls and thin structures are poorly estimated "
        "to create a situation the aircraft cannot see.",
        "A collision that appears to be an ordinary failure but was arranged.",
        "Known weaknesses are published rather than hidden so operators can avoid such "
        "environments, and the stop distance is set for the worst case."],
       ["A careless or overconfident operator",
        "Trusting the autonomy in untested conditions or leaving the override unattended. "
        "Not malicious, but the most likely of these to happen.",
        "An avoidable collision with responsibility unclear afterwards.",
        "Operating limits stated explicitly, a named pilot per session, and autonomy "
        "described throughout as supervised rather than independent."]],
      widths=[1.2, 1.75, 1.5, 1.8], size=8)
caption("Table 19. Adversarial stakeholders and mitigations.")
para("The wireless link is the honest weak point. The proposed architecture sends video "
     "off the aircraft and brings commands back over the same connection, so an ordinary "
     "radio problem and a deliberate attack look identical to the aircraft. Whether the "
     "model can run on the companion computer instead is recorded in Chapter 9 as the "
     "first thing to measure, because moving that computation onto the aircraft would "
     "remove this entire class of risk rather than mitigating it.")

# ================================================================== CHAPTER 7
heading("CHAPTER VII. DATASET OVERVIEW", 0)
heading("7.1 Data Required for the Project", 1)
table(["Dataset or Data Item", "Purpose in Project", "Format", "Size", "Availability"],
      [["Simulator frame pairs",
        "Measuring the gap between simulated and real imagery, and acting as the perfect "
        "depth reference for the ablation.",
        "Lossless images with matching depth arrays in metres", "5,000 pairs, a few GB",
        "Generated on demand from committed seeds. Available now."],
       ["Seeded course definitions",
        "Producing identical layouts so different depth sources compare fairly.",
        "Integer seeds with generator parameters", "Negligible",
        "In version control. Available now."],
       ["NYU Depth V2 test split",
        "Depth accuracy on real indoor photographs, the closest public analogue to our "
        "environment.",
        "654 colour images with measured depth", "About 3 GB",
        "Public research release. Terms recorded."],
       ["KITTI depth benchmark sample",
        "Depth accuracy on real outdoor scenes, a second and very different domain.",
        "Colour images with laser derived depth", "A few GB",
        "Public release under a non commercial share alike licence."],
       ["Run logs",
        "Failure analysis, drift monitoring and reconstructing why a command was issued.",
        "Tabular records, one row per control step", "Tens of MB per batch",
        "Produced by the evaluation harness. Available now."],
       ["Airframe geometry",
        "Setting the collision envelope and the wing clearance the policy plans around.",
        "Exchange format files converted to meshes", "Under 5 MB",
        "Produced by the team. Wingspan measured at 1.00 metres."]],
      widths=[1.15, 1.85, 1.2, 0.85, 1.2], size=8)
caption("Table 20. Data required for the project.")
para("The airframe geometry is data in exactly the sense this chapter means, even though "
     "it is not imagery. The wingspan measured from those files sets the clearance the "
     "policy plans around and the collision envelope in the simulator. When we measured it "
     "at one metre rather than assuming a smaller aircraft, the room had to be enlarged and "
     "the required gap between obstacles changed. A wrong number there would have "
     "invalidated every flight result.")

heading("7.2 Data Provenance", 1)
table(["Dataset", "Source", "Owner", "Collection Period", "Collection Method",
       "Permission Status"],
      [["Simulator frame pairs", "Generated locally by our course generator",
        "Project team", "September 2026 onward",
        "Rendered from a physics simulator with exact depth from the depth buffer",
        "Owned by the team. No restriction."],
       ["NYU Depth V2", "New York University public release", "New York University",
        "2011 to 2012", "Indoor scenes with a structured light depth camera",
        "Free for research use. Citation required."],
       ["KITTI depth benchmark", "Karlsruhe Institute of Technology and Toyota "
        "Technological Institute", "Releasing institutions", "2011 to 2012",
        "Street scenes from an instrumented vehicle with laser derived depth",
        "Non commercial share alike. Suitable for coursework. Citation required."],
       ["Pretrained model weights", "Intel Intelligent Systems Lab public release",
        "Intel Intelligent Systems Lab", "2019 onward",
        "Trained on a mixture of public depth datasets",
        "Permissive open source licence. Attribution required."],
       ["Airframe geometry", "Produced by the team", "Project team", "September 2026",
        "Computer aided design export to a neutral format",
        "Owned by the team. No restriction."]],
      widths=[1.05, 1.3, 0.95, 0.85, 1.25, 0.85], size=8)
caption("Table 21. Data provenance.")
para("Two points carry practical weight. The outdoor benchmark is non commercial, "
     "acceptable for coursework but needing reconsideration if the work went further. And "
     "the model was trained on a mixture we did not choose and cannot change, so its "
     "weaknesses are inherited rather than introduced by us.")

heading("7.3 Data Lineage Diagram", 1)
figure("figures/fig3_lineage.png", 2.9,
       "Figure 3. Data lineage from source through to the final evaluated dataset.")
para("At each step the record kept is the seed or source identifier, the software version "
     "used, and a checksum of the input. That combination is what makes a past result "
     "reproducible.")
para("The value of the record is best shown by something that happened to us. An early "
     "evaluation produced results so poor the aircraft barely moved. Because the "
     "transformation steps were recorded we worked backwards through the lineage rather "
     "than guessing. The fault was in feature creation. The per column distance handed to "
     "the policy took the nearest surface over a vertical band that included the floor, so "
     "every direction reported roughly the same distance and the policy could not "
     "distinguish open space from an obstacle. The fix was to discard pixels outside the "
     "aircraft's own flying height. Without a lineage record we would have been changing "
     "the steering logic, which was not at fault.")
para("The record also answers reproduction. Because courses come from integer seeds "
     "rather than stored files, a result from six weeks ago is regenerated exactly by "
     "rebuilding the seed with the recorded software version. The dataset in effect is the "
     "seed list, small enough to keep in version control and impossible to lose.")

heading("7.4 Data Transformation Log", 1)
table(["Step", "Input", "Operation", "Reason", "Output", "Tool or Method"],
      [["1", "Integer seed",
        "Generate obstacle layout with bounded random placement on a fixed grid",
        "Produces a repeatable course and keeps the narrowest gap wider than the wingspan",
        "Course definition", "Project course generator"],
       ["2", "Course definition and aircraft pose",
        "Render the forward camera view and the exact depth buffer",
        "Supplies the image the model consumes and the perfect depth used as reference",
        "Colour image and depth array", "Simulator renderer"],
       ["3", "Depth array", "Discard pixels outside the aircraft's flying height band",
        "Floor and ceiling are always present and would otherwise dominate every "
        "measurement", "Height filtered depth", "Geometric mask from camera parameters"],
       ["4", "Height filtered depth", "Reduce each column to the nearest remaining surface",
        "Turns a two dimensional map into the one dimensional profile the policy needs",
        "Per column distance profile", "Column wise minimum"],
       ["5", "Per column profile",
        "Widen each obstacle by the angle the wing needs at its own distance",
        "A gap only counts if the aircraft physically fits through it", "Free space profile",
        "Angular shadow casting"],
       ["6", "Free space profile and bearing", "Score every candidate heading and select "
        "the best", "Produces the steering command", "Forward speed, yaw rate, climb rate",
        "Weighted scoring with time smoothing"],
       ["7", "Colour image", "Resize to 256 wide and normalise. Implemented",
        "Matches the input the pretrained model expects. The hub transform scales by 255 "
        "itself, so the image must be handed over unscaled", "Model input tensor",
        "MiDaS small_transform"],
       ["8", "Model output",
        "Fit both scale and offset by least squares against a reference. Implemented",
        "Output has no units and is undetermined up to a scale and an offset. Correcting "
        "only the scale leaves a systematic error", "Depth in metres",
        "Closed form two by two solve in inverse depth"]],
      widths=[0.35, 1.0, 1.45, 1.55, 1.05, 0.85], size=8)
caption("Table 22. Data transformation log.")
para("Step 8 is the one most likely to be got wrong and the most damaging when it is. The "
     "published model does not produce metres. It produces a quantity correct up to an "
     "unknown multiplier and an unknown additive term, both varying between images. "
     "Correcting only the multiplier, the common shortcut, leaves the additive term "
     "uncorrected and produces benchmark figures that look like a failure of the model "
     "when they are a failure of the alignment.")

# ================================================================== CHAPTER 8
heading("CHAPTER VIII. FINAL PROJECT INITIATION SUMMARY", 0)
table(["Item", "Final Summary"],
      [["Problem being addressed",
        "A small aircraft with a single forward facing camera must reach a sequence of "
        "positions in a cluttered space without striking anything, using no distance "
        "sensor, no prior map and no external positioning. Depth must be predicted rather "
        "than measured, the prediction has no units, and the camera sees a wedge while a "
        "one metre wing sweeps a circle."],
       ["Proposed AI and ML approach",
        "A pretrained MiDaS-small model used as published with no training, supplying a "
        "depth map to a hand written reactive policy, with a non learned safety layer "
        "underneath that can override it. Exactly one stage learns anything and no safety "
        "relevant stage does. The measurement of record is an ablation comparing perfect, "
        "estimated and absent depth on identical courses."],
       ["Primary stakeholders",
        "Bystanders and property owners carry the physical risk with the least influence, "
        "which is why they are listed first. The pilot in command carries legal "
        "responsibility. Regulators can prohibit outdoor flight. The institution provides "
        "premises and carries liability. The team makes every design decision."],
       ["Major data requirement",
        "At least five thousand colour and true depth pairs from seeded simulator courses, "
        "plus the NYU and KITTI evaluation splits for depth accuracy on real photographs. "
        "No training data and no labelling are needed, which removes the largest cost in a "
        "typical vision project."],
       ["Most important feasibility risk",
        "The reactive policy has no way out of a concave trap. On fifty held out courses "
        "with perfect depth the aircraft completes 66 per cent without contact at moderate "
        "density, and almost every failure is a timeout rather than a collision. Since "
        "this is the ceiling, the original 90 per cent target cannot be met with estimated "
        "depth without changing the courses, the target or the method."],
       ["Most important ethical concern",
        "Overstating reliability. Our tuned figure of 92 per cent fell to 66 per cent on "
        "courses held back from tuning. For a system that can strike a person, reporting "
        "the flattering number would be a safety failure rather than a presentational one."],
       ["Final project recommendation",
        "Proceed with the simulation as the graded deliverable under the reporting "
        "discipline in Section 4.4. Report collision free completion as a curve against "
        "obstacle density rather than a single figure. Treat the physical airframe as a "
        "stretch goal, keep avoidance testing in hover, and confirm the regulatory "
        "position before any outdoor flight."]],
      widths=[1.35, 4.9], size=9)
caption("Table 23. Final project initiation summary.")

# ================================================================== CHAPTER 9
heading("CHAPTER IX. PRELIMINARY NEXT STEPS", 0)
para("The steps below are ordered so that those capable of invalidating later work come "
     "first. Each states what would count as done.")
table(["Step", "Action", "What Counts as Done"],
      [["1", "Substitute the depth model into the existing loop and run the ablation.",
        "The policy already takes the depth map as an argument, so the planner needs no "
        "change. Done when both arms are measured on the identical fifty courses and the "
        "difference is reported with a confidence interval."],
       ["2", "Verify the scale and offset alignment before trusting any depth figure.",
        "Fit both terms by least squares. Done when the indoor benchmark figure is "
        "reproduced within a small tolerance, which confirms the alignment rather than the "
        "model."],
       ["3", "Measure whether the depth model can run on the companion computer.",
        "The architecture assumes it cannot and streams video to a laptop, which has never "
        "been tested. If it reaches ten frames per second on the aircraft, the wireless "
        "link leaves the control loop along with the largest latency risk. Done when a "
        "measured frame rate on the actual hardware exists."],
       ["4", "Decide how the 90 per cent target is resolved.",
        "The ceiling measurement makes it unreachable at moderate density. The team "
        "prefers a curve against obstacle density. Done when the decision is recorded and "
        "the success criteria are amended in writing."],
       ["5", "Complete the mass and thrust budget before buying propulsion hardware.",
        "All up mass, hover thrust to weight, battery voltage, propeller constraints and "
        "controller current come first. Done when the numbers exist and the motors are "
        "chosen from them."],
       ["6", "Confirm the regulatory position with the institution.",
        "Establish the weight category and whether the research exemption for recognised "
        "educational institutions applies on institutional premises. Done when a written "
        "answer exists. This is a gate on outdoor flight."],
       ["7", "Build the drift monitoring and degraded perception response.",
        "Done when a deliberately degraded scene lowers speed and raises the stop distance "
        "without manual intervention."],
       ["8", "Run the safety layer verification.",
        "Twenty runs with the steering policy disabled and only the stop rule active. Done "
        "when zero contacts are recorded, the acceptance criterion for FR3 and NFR4."]],
      widths=[0.4, 2.15, 3.7], size=9)
page_break()

# ================================================================== CHAPTER 10
heading("CHAPTER X. REFERENCES", 0)
refs = [
 "R. Ranftl, K. Lasinger, D. Hafner, K. Schindler and V. Koltun, \"Towards robust "
 "monocular depth estimation: mixing datasets for zero-shot cross-dataset transfer,\" "
 "IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 44, no. 3, "
 "pp. 1623 to 1637, 2022.",
 "R. Ranftl, A. Bochkovskiy and V. Koltun, \"Vision transformers for dense prediction,\" "
 "in Proc. IEEE International Conference on Computer Vision, 2021, pp. 12179 to 12188.",
 "Intel Intelligent Systems Lab, \"MiDaS: monocular depth estimation,\" software "
 "repository. [Online]. Available: https://github.com/isl-org/MiDaS",
 "N. Silberman, D. Hoiem, P. Kohli and R. Fergus, \"Indoor segmentation and support "
 "inference from RGBD images,\" in Proc. European Conference on Computer Vision, 2012, "
 "pp. 746 to 760.",
 "A. Geiger, P. Lenz and R. Urtasun, \"Are we ready for autonomous driving? The KITTI "
 "vision benchmark suite,\" in Proc. IEEE Conference on Computer Vision and Pattern "
 "Recognition, 2012, pp. 3354 to 3361.",
 "J. Uhrig, N. Schneider, L. Schneider, U. Franke, T. Brox and A. Geiger, \"Sparsity "
 "invariant convolutional neural networks,\" in Proc. International Conference on 3D "
 "Vision, 2017, pp. 11 to 20.",
 "E. Todorov, T. Erez and Y. Tassa, \"MuJoCo: a physics engine for model-based control,\" "
 "in Proc. IEEE/RSJ International Conference on Intelligent Robots and Systems, 2012, "
 "pp. 5026 to 5033.",
 "L. Meier, D. Honegger and M. Pollefeys, \"PX4: a node-based multithreaded open source "
 "robotics framework for deeply embedded platforms,\" in Proc. IEEE International "
 "Conference on Robotics and Automation, 2015, pp. 6235 to 6240.",
 "V. Sezer and M. Gokasan, \"A novel obstacle avoidance algorithm: follow the gap "
 "method,\" Robotics and Autonomous Systems, vol. 60, no. 9, pp. 1123 to 1134, 2012.",
 "P. Chapman, J. Clinton, R. Kerber, T. Khabaza, T. Reinartz, C. Shearer and R. Wirth, "
 "CRISP-DM 1.0: Step-by-step data mining guide. SPSS Inc., 2000.",
 "Microsoft Corporation, \"Team Data Science Process documentation.\" [Online]. "
 "Available: https://learn.microsoft.com/azure/architecture/data-science-process/",
 "D. Sculley, G. Holt, D. Golovin, E. Davydov, T. Phillips, D. Ebner, V. Chaudhary, "
 "M. Young, J. Crespo and D. Dennison, \"Hidden technical debt in machine learning "
 "systems,\" in Advances in Neural Information Processing Systems, vol. 28, 2015, "
 "pp. 2503 to 2511.",
 "E. Breck, S. Cai, E. Nielsen, M. Salib and D. Sculley, \"The ML test score: a rubric "
 "for ML production readiness and technical debt reduction,\" in Proc. IEEE International "
 "Conference on Big Data, 2017, pp. 1123 to 1132.",
 "M. Mitchell, S. Wu, A. Zaldivar, P. Barnes, L. Vasserman, B. Hutchinson, E. Spitzer, "
 "I. D. Raji and T. Gebru, \"Model cards for model reporting,\" in Proc. Conference on "
 "Fairness, Accountability and Transparency, 2019, pp. 220 to 229.",
 "T. Gebru, J. Morgenstern, B. Vecchione, J. W. Vaughan, H. Wallach, H. Daume III and "
 "K. Crawford, \"Datasheets for datasets,\" Communications of the ACM, vol. 64, no. 12, "
 "pp. 86 to 92, 2021.",
 "Ministry of Civil Aviation, Government of India, The Drone Rules, 2021. New Delhi, "
 "India, 2021.",
 "Directorate General of Civil Aviation, Government of India, \"Digital Sky platform.\" "
 "[Online]. Available: https://digitalsky.dgca.gov.in/",
 "European Parliament and Council of the European Union, Regulation (EU) 2024/1689 "
 "laying down harmonised rules on artificial intelligence, Official Journal of the "
 "European Union, 2024.",
 "T. Akiba, S. Sano, T. Yanase, T. Ohta and M. Koyama, \"Optuna: a next-generation "
 "hyperparameter optimization framework,\" in Proc. ACM SIGKDD International Conference "
 "on Knowledge Discovery and Data Mining, 2019, pp. 2623 to 2631.",
 "Ministry of Civil Aviation, Government of India, Drone (Amendment) Rules and "
 "associated airspace map notifications. New Delhi, India, 2022.",
]
for i, r in enumerate(refs, 1):
    p = _new("just", space_after=4, line=1.05)
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    _run(p.add_run(f"[{i}]  "), 10)
    _run(p.add_run(r), 10)
page_break()

# ================================================================== APPENDIX
heading("CHAPTER XI. APPENDIX", 0)
heading("Appendix A. Derivation of the Latency Budget", 1)
para("At a cruise speed of two metres per second, a delay of one hundred milliseconds "
     "between capturing an image and issuing a command allows the aircraft to travel 0.20 "
     "metres before it can react. Decelerating from two metres per second at three metres "
     "per second squared consumes a further 0.67 metres. Stopping therefore needs about "
     "0.87 metres before any margin for depth error or control lag, which is why the stop "
     "distance in FR3 is set above one metre. Raising the cruise speed or relaxing the "
     "latency budget forces the stop distance up, so the three numbers cannot be chosen "
     "independently.")

heading("Appendix B. Measured Simulation Performance", 1)
table(["Measurement", "Value"],
      [["Complete loop including physics, colour render and depth render",
        "More than 200 cycles per second"],
       ["Steering policy computation alone", "About 0.24 milliseconds per call"],
       ["Camera resolution supplied to the policy", "320 by 240 pixels"],
       ["Requirement to be met", "10 cycles per second"]],
      widths=[4.3, 1.95], size=9)

heading("Appendix C. Airframe Dimensions Measured From the Design Files", 1)
table(["Component", "Length (m)", "Width (m)", "Height (m)"],
      [["Combined aerodynamic shell", "0.81", "1.00", "0.23"],
       ["Wing", "0.22", "1.00", "0.02"],
       ["Fuselage", "0.80", "0.06", "0.05"],
       ["Tail assembly", "0.07", "0.26", "0.06"],
       ["Landing gear", "0.25", "0.46", "0.09"],
       ["Lift rotor mounts", "0.25", "0.47", "0.07"],
       ["Electronics layout", "0.76", "0.46", "0.08"]],
      widths=[2.5, 1.25, 1.25, 1.25], size=9)
para("The wingspan of one metre constrains the course design. Obstacle gaps are held at "
     "1.40 metres so the aircraft has 0.20 metres of clearance each side. A standard "
     "doorway is narrower than this aircraft, which is why indoor testing needs an open "
     "hall rather than an ordinary room.")

heading("Appendix D. Responsible Use Statement", 1)
para("This system is intended for civil inspection and short range autonomous navigation "
     "in environments where the operator has permission to fly. It contains no person "
     "detection, no target tracking and no recording capability, and these are deliberate "
     "omissions rather than features awaiting implementation. It is not intended for "
     "surveillance of individuals, for operation over people who have not consented, or "
     "for any application in which a person is the subject of the flight. No claim is made "
     "that the system is certified for flight, and all results in this report are obtained "
     "in simulation.")

heading("Appendix E. Running the Simulator", 1)
para("All commands are run from the repository root. The virtual environment holds "
     "MuJoCo, NumPy, OpenCV, PyTorch and the depth model dependencies.")
para("Ground truth depth, taken straight from the simulator depth buffer. No neural "
     "network is loaded. This is the ceiling arm of the ablation.", space_after=2)
code(["cd /Users/sid/drone-sim",
      ".venv/bin/python fly.py --seed 0"])
para("Estimated depth. The same aircraft and the same policy, with the depth map now "
     "produced by the network. The first launch fits the scale and offset once and caches "
     "them, so later launches start immediately.", space_after=2)
code(["cd /Users/sid/drone-sim",
      ".venv/bin/python fly.py --seed 0 --midas"])
para("With the model in the loop the display shows three panels instead of two. The "
     "camera image, the estimated depth the aircraft is flying on, and the true depth "
     "beneath it as a reference the aircraft never sees. Live absolute relative error is "
     "reported on screen.")
table(["Option", "Effect"],
      [["--midas", "Fly on estimated depth instead of simulator truth"],
       ["--align frozen", "Scale and offset fitted once on a calibration set. The honest arm"],
       ["--align oracle", "Refit per frame against true depth. An upper bound, not flyable"],
       ["--seed N", "Choose the course. The same integer always gives the same layout"],
       ["--obstacles N", "Obstacle count, default 9"],
       ["--room M", "Room side in metres, default 10"],
       ["--flat", "Untextured world, for comparing visual realism"],
       ["--show-hull", "Tint the collision envelope so the colliding shape is visible"],
       ["--snapshot PATH", "Fly headlessly and save one composite frame, then exit"]],
      widths=[1.45, 5.0], size=9.5)
caption("Table 24. Simulator command line options.")
para("Headless scoring, which is how every number in this report was produced.", space_after=2)
code(["# score many seeds on ground truth depth",
      ".venv/bin/python run_route.py --seeds 100-149 --stations 4",
      "",
      "# the three arm ablation: perfect depth, estimated depth, no depth",
      ".venv/bin/python ablation.py --seeds 100-149",
      "",
      "# depth quality and speed of the model on simulator frames",
      ".venv/bin/python bench_midas.py"])

heading("Appendix F. Formulae Used in the Simulator", 1)
para("Symbols. W and H are the image width and height in pixels, i and j are column and "
     "row index, D is depth in metres measured along the camera axis, theta is the yaw "
     "offset a column corresponds to with positive meaning left, psi is heading, beta is "
     "the bearing to the next station, b is half the wingspan plus margin at 0.55 m, and "
     "R is the range beyond which a direction counts as fully open at 8 m.")
para("Two conventions were verified rather than assumed. The simulator returns planar "
     "depth, confirmed by pointing the camera at a flat wall and checking every column "
     "reported the same value. And the camera is mounted with image right along the body "
     "negative y axis, which is where the minus sign in the yaw offset comes from.")
heading("F.1 Camera geometry", 2)
code(["hfov       = 2 * atan( tan(vfov / 2) * W / H )",
      "ndc_x[i]   = (i + 0.5) / W * 2 - 1",
      "theta[i]   = -atan( ndc_x[i] * tan(hfov / 2) )",
      "ndc_y[j]   = 1 - 2 * (j + 0.5) / H",
      "row_gain[j]= ndc_y[j] * tan(vfov / 2)"])
heading("F.2 Depth map to free space", 2)
para("Only surfaces near the aircraft's own flying height can be struck. Without this "
     "mask the floor dominates every column and the policy cannot tell open space from an "
     "obstacle, which is the fault described in Section 7.3.", space_after=2)
code(["height[j,i] = D[j,i] * row_gain[j]",
      "keep if |height[j,i]| < z_band                   z_band = 0.35 m",
      "raw[i]      = clip( min over kept rows of D[.,i], 0, R )"])
para("A gap only counts if the aircraft fits through it. Each obstacle blocks a wedge "
     "whose half width comes from that obstacle's own range.", space_after=2)
code(["k[j]          = atan( b / max(raw[j], 0.35) )",
      "shadowed[i,j] = |theta[i] - theta[j]| < k[j]",
      "free[i]       = min over shadowed j of raw[j], otherwise R",
      "min_front     = min of free[i] over |theta[i]| < 12 degrees"])
heading("F.3 Heading selection and speed", 2)
code(["align[i] = cos( clip( theta[i] - beta, -pi, pi ) )",
      "stay[i]  = |theta[i] - psi_cmd| / hfov",
      "score[i] = free[i] / R + w_goal * align[i] - w_commit * stay[i]",
      "best     = theta[ argmax score ]",
      "",
      "a        = exp( -dt / tau )                      tau = 0.25 s",
      "psi_cmd  = a * psi_cmd + (1 - a) * best",
      "",
      "throttle = clip( (min_front - d_stop) / (d_clear - d_stop), 0, 1 )",
      "throttle = max( throttle, throttle_min )",
      "v        = v_max * throttle * clip(cos psi_cmd, 0.25, 1)",
      "                            * clip(cos beta,    0.20, 1)",
      "omega    = clip( 2.2 * psi_cmd, -omega_max, omega_max )",
      "climb    = clip( 1.5 * altitude_error, -c_max, c_max )"])
heading("F.4 Safety layer and wing guard", 2)
code(["blocked = min_front < d_stop                     d_stop = 1.2 m",
      "if blocked:",
      "    v     = 0, or -v_escape after escape_after seconds",
      "    omega = turn_dir * omega_max * 0.85          # latched once, then held",
      "",
      "reach     = b + 0.25",
      "wing_risk = left_clear if omega > 0 else right_clear",
      "if wing_risk < reach:  omega = omega * 0.15      # damp only, never reverse"])
heading("F.5 All round obstacle memory", 2)
code(["x  = d * cos(phi) - v * dt",
      "y  = d * sin(phi)",
      "xr = cos(-omega*dt) * x - sin(-omega*dt) * y",
      "yr = sin(-omega*dt) * x + cos(-omega*dt) * y",
      "d' = hypot(xr, yr)        phi' = atan2(yr, xr)",
      "d' = min( R, d' + forget * dt )                  forget = 0.15 m/s"])
heading("F.6 Navigation, motion and course generation", 2)
code(["wrap(a)  = (a + pi) mod 2*pi - pi",
      "beta     = wrap( atan2(y_s - y, x_s - x) - psi )",
      "arrived  when |station - position| < 0.7 m",
      "step     = [ cos(psi)*v - sin(psi)*s, sin(psi)*v + cos(psi)*s, climb ] * dt",
      "quat     = [ cos(psi/2), 0, 0, sin(psi/2) ]",
      "",
      "min_gap  = grid_pitch - 2*max_radius - 2*max_jitter",
      "         = 2.50 - 0.60 - 0.50 = 1.40 m   against a 1.00 m wingspan",
      "d_stop   = v * t_latency + v^2 / (2a) = 0.20 + 0.67 = 0.87 m"])

heading("Appendix G. Depth Model Integration", 1)
para("The model is MiDaS-small version 2.1, an encoder and decoder network of 21.3 "
     "million parameters, loaded from the published weights and never trained. It returns "
     "inverse depth, meaning one divided by distance, correct only up to an unknown "
     "multiplier and an unknown offset that differ from image to image.")
heading("G.1 A preprocessing mistake worth recording", 2)
para("The published transform divides the image by 255 itself. Passing an image already "
     "scaled to the range zero to one therefore scales it twice, and the network sees a "
     "nearly black frame. It raises no error. It returns a plausible looking vertical "
     "gradient for every input, which is easily mistaken for a domain gap between "
     "simulated and real imagery.")
para("We nearly reported that false conclusion. The simulator was textured with "
     "procedurally generated plaster, wood and paint to close the supposed gap, and the "
     "measured depth quality did not move at all, to three decimal places. That was "
     "implausible enough to test the model on a real photograph instead, where it returned "
     "the same featureless ramp. No working monocular depth model does that on a real "
     "photograph, which placed the fault upstream of the network.")
table(["Measurement on simulator frames", "Image scaled twice", "Correct"],
      [["Correlation with true inverse depth", "0.29", "0.92"],
       ["Absolute relative error", "0.40", "0.21"],
       ["Pixels within a factor of 1.25", "0.42", "0.62"]],
      widths=[3.3, 1.6, 1.5], size=9.5)
caption("Table 25. Effect of the preprocessing fault on depth quality.")
para("The lesson generalises beyond this one bug. A silent failure that produces "
     "confident, plausible output is the characteristic failure of a learned component, "
     "and the only defence is checking it against a case where the right answer is "
     "obvious.")
heading("G.2 Recovering scale and offset", 2)
code(["minimise over s and t:   sum_i ( s * pred_i + t - target_i )^2",
      "",
      "a00 = sum(p*p)   a01 = sum(p)   a11 = N",
      "b0  = sum(p*q)   b1  = sum(q)",
      "det = a00*a11 - a01*a01",
      "s   = ( a11*b0 - a01*b1) / det",
      "t   = (-a01*b0 + a00*b1) / det",
      "",
      "depth = 1 / max( s * pred + t, 1e-3 )"])
table(["Arm", "How scale and offset are obtained", "What it measures"],
      [["frozen", "Fitted once across a calibration set, then held fixed",
        "The honest arm. What an aircraft could do, using a known height above the floor"],
       ["oracle", "Refitted on every frame against the true depth",
        "An upper bound. Separates error in depth structure from error in alignment"]],
      widths=[0.75, 2.5, 3.15], size=9.5)
caption("Table 26. The two alignment arms.")
heading("G.3 Where it attaches", 2)
para("The policy receives the depth map as an argument and holds no dependency on how it "
     "was produced. That single seam is what makes the ablation fair, because everything "
     "downstream is identical across all three arms.", space_after=2)
code(["from midas_depth import MidasDepth",
      "md = MidasDepth()              # selects Metal, CUDA or CPU automatically",
      "md.calibrate(cal_rgb_frames, cal_true_depths)",
      "",
      "def estimated(rgb, true_depth):",
      "    return md.metric_depth(rgb, true_depth, mode='frozen')",
      "",
      "run(seed, stations, obstacles, room, depth_fn=estimated)"])
heading("G.4 Measured", 2)
table(["Measurement", "Value"],
      [["Inference on the Metal backend", "8.7 ms per frame, about 115 frames per second"],
       ["Requirement", "10 frames per second"],
       ["Correlation with true inverse depth", "0.92"],
       ["Absolute relative error, frozen alignment", "0.21"],
       ["Pixels within a factor of 1.25, frozen", "0.62"],
       ["Pixels within a factor of 1.25, oracle", "0.77"],
       ["Effect of texturing the world on depth quality", "below one part in five hundred"]],
      widths=[3.6, 2.85], size=9.5)
caption("Table 27. Measured depth model performance.")
para("Texturing the simulator changed depth quality by almost nothing. Visual realism is "
     "therefore not what limits the estimate here, and the textures are kept because the "
     "simulator looks better rather than because they help the model. That is worth "
     "stating plainly, since the opposite is widely assumed.")

heading("Appendix H. Policy Parameter Reference", 1)
para("Every value below is a constructor argument of the policy, which is what makes the "
     "automated parameter search the course asks for straightforward to run.")
table(["Parameter", "Default", "Meaning"],
      [["max_range", "8.0 m", "Beyond this a direction counts as fully open"],
       ["stop_threshold", "1.2 m", "Safety layer trip point, linked to the stopping distance"],
       ["release_margin", "0.0 m", "Hysteresis on the stop layer. Tested and rejected"],
       ["clear_distance", "3.5 m", "Full speed once this much room is ahead"],
       ["goal_weight", "1.8", "Pull toward the station in the heading score"],
       ["commit", "0.25", "Penalty for abandoning the heading already chosen"],
       ["half_span", "0.55 m", "Half the wingspan plus margin. Sets the shadow width"],
       ["z_band", "0.35 m", "Height band around flight level that counts as an obstacle"],
       ["min_throttle", "0.30", "Speed floor, so it commits or declares itself blocked"],
       ["smoothing", "0.25 s", "Time constant of the heading average"],
       ["memory_bins", "72", "Bearing bins in the memory, one every five degrees"],
       ["forget", "0.15 m/s", "Memory decay. The most influential single parameter"],
       ["escape_after", "1.0 s", "Time blocked before backing out"],
       ["escape_speed", "0.35 m/s", "Reverse speed while escaping. Blind, so it is slow"],
       ["desperate_after", "3.0 s", "Time blocked before the station is ignored entirely"],
       ["flip_cooldown", "0.0 s", "Wing guard side switching. Tested and rejected"],
       ["max_speed", "2.0 m/s", "Cruise speed the latency budget was derived from"],
       ["max_yaw", "1.8 rad/s", "Yaw rate limit"],
       ["max_climb", "1.0 m/s", "Climb rate limit"]],
      widths=[1.45, 1.05, 3.95], size=9.5)
caption("Table 28. Policy parameter reference.")
para("Two entries are marked tested and rejected. Both were implemented, measured across "
     "fifty held out seeds, found to be worse than leaving them off, and kept in the code "
     "with that result recorded. Deleting them would invite the next person to try the "
     "same ideas.")

OUT = "Project_Report_Unit1_2_Monocular_Depth_VTOL.docx"
doc.save(OUT)
print("saved", OUT)
