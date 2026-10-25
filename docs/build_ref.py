"""Builds the technical reference: commands, formulae, MiDaS integration."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT, MONO = "Times New Roman", "Courier New"
BLACK = RGBColor(0, 0, 0)
BODY, LEAD = 11.5, 1.15

doc = Document()
for s in doc.sections:
    s.top_margin = Inches(0.85); s.bottom_margin = Inches(0.85)
    s.left_margin = Inches(1.0); s.right_margin = Inches(0.9)
n = doc.styles["Normal"]
n.font.name = FONT; n.font.size = Pt(BODY); n.font.color.rgb = BLACK
n._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
n.paragraph_format.space_after = Pt(5); n.paragraph_format.line_spacing = LEAD
_pending = [False]


def _run(r, size=BODY, bold=False, italic=False, font=FONT):
    r.font.name = font; r.font.size = Pt(size)
    r.font.bold = bold; r.font.italic = italic; r.font.color.rgb = BLACK
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    return r


def _new(align="just", after=5, line=LEAD, before=0, left=0):
    p = doc.add_paragraph()
    p.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = line
    if left:
        p.paragraph_format.left_indent = Inches(left)
    if _pending[0]:
        p.paragraph_format.page_break_before = True; _pending[0] = False
    return p


def para(t="", size=BODY, bold=False, italic=False, align="just", after=5, before=0):
    p = _new(align, after, LEAD, before)
    if t:
        _run(p.add_run(t), size, bold, italic)
    return p


def heading(t, level=1):
    sizes = {0: 14, 1: 12.5, 2: 11.5}
    p = _new("left", after=5, line=1.05, before={0: 16, 1: 10, 2: 7}[level])
    _run(p.add_run(t), sizes[level], bold=True)
    return p


def code(lines, size=9.5, left=0.25):
    for i, ln in enumerate(lines):
        p = _new("left", after=(6 if i == len(lines) - 1 else 0), line=1.0,
                 before=(6 if i == 0 else 0), left=left)
        _run(p.add_run(ln if ln else " "), size, font=MONO)


def _shade(cell, v="D9D9D9"):
    el = OxmlElement("w:shd"); el.set(qn("w:val"), "clear"); el.set(qn("w:fill"), v)
    cell._tc.get_or_add_tcPr().append(el)


def table(headers, rows, widths=None, size=9.5, mono_cols=()):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]; c.text = ""
        p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        _run(p.add_run(h), size, bold=True); _shade(c)
    for row in rows:
        cells = t.add_row().cells
        for j, v in enumerate(row):
            c = cells[j]; c.text = ""
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
            _run(p.add_run(str(v)), size, font=(MONO if j in mono_cols else FONT))
    if widths:
        for r in t.rows:
            for j, w in enumerate(widths):
                r.cells[j].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def page_break():
    _pending[0] = True

# ---------------------------------------------------------------- title
para("Autonomous Drone Obstacle Avoidance Using Monocular Depth Estimation",
     15, bold=True, align="center", after=4)
para("Technical Reference. Commands, Formulae and MiDaS Integration",
     12, italic=True, align="center", after=14)
table(["Project", "Autonomous Drone Obstacle Avoidance Using Monocular Depth Estimation"],
      [["Team", "Siddharth Lama, Manit Aravind, Sahil Asopa, Riyaan Sheth"],
       ["Simulator", "MuJoCo 3.13, Python 3.13, macOS on Apple Silicon"],
       ["Depth model", "MiDaS-small v2.1, 21.3 million parameters, used as published"],
       ["Repository", "/Users/sid/drone-sim"],
       ["Date", "11 September 2026"]],
      widths=[1.5, 5.0], size=10.5)

heading("1. Contents", 1)
table(["Sr. No.", "Section", "Page"],
      [["1", "Contents", "1"],
       ["2", "How to run", "1"],
       ["3", "Conventions and notation", "4"],
       ["4", "Camera geometry", "5"],
       ["5", "Depth map to free space", "5"],
       ["6", "Heading selection and speed", "7"],
       ["7", "Safety layer and wing guard", "7"],
       ["8", "All round obstacle memory", "8"],
       ["9", "Navigation and motion", "8"],
       ["10", "Course generation", "8"],
       ["11", "MiDaS integration", "9"],
       ["12", "Measured values", "11"],
       ["13", "Parameter reference", "12"]],
      widths=[0.8, 4.7, 0.8], size=10)

# ---------------------------------------------------------------- commands
heading("2. How to run", 1)
para("All commands are run from the repository root. The virtual environment holds "
     "MuJoCo, NumPy, OpenCV, PyTorch and the MiDaS dependencies.")

heading("2.1 The simulator on ground truth depth", 2)
para("Depth comes straight from the MuJoCo depth buffer. Nothing is estimated and no "
     "neural network is loaded. This is the ceiling arm of the ablation.")
code(["cd /Users/sid/drone-sim",
      ".venv/bin/python fly.py --seed 0"])
para("Controls. Click the map panel to add a station and right click to remove the "
     "nearest one. Press N to engage autonomous flight and C to clear the route. The "
     "arrow keys fly manually, a and d strafe, r and f change altitude, space resets, "
     "and q quits.")

heading("2.2 The simulator on MiDaS estimated depth", 2)
para("The same aircraft and the same policy, but the depth map now comes from the "
     "network rather than the simulator. The first launch fits the scale and offset once "
     "and caches them, so later launches start immediately.")
code(["cd /Users/sid/drone-sim",
      ".venv/bin/python fly.py --seed 0 --midas"])
para("The middle column changes to three panels. The camera image, the MiDaS depth the "
     "aircraft is flying on, and the true depth underneath as a reference the aircraft "
     "never sees. The heads up block reports the live absolute relative error and the "
     "fraction of pixels within a factor of 1.25.")
table(["Option", "Effect"],
      [["--midas", "Fly on estimated depth instead of simulator truth"],
       ["--align frozen", "Scale and offset fitted once on a calibration set. The honest arm"],
       ["--align oracle", "Refit per frame against true depth. An upper bound, not achievable in flight"],
       ["--seed N", "Choose the course. The same integer always gives the same layout"],
       ["--obstacles N", "Obstacle count. Default 9"],
       ["--room M", "Room side in metres. Default 10"],
       ["--flat", "Untextured world, for comparing visual realism"],
       ["--show-hull", "Tint the collision envelope so you can see what actually collides"],
       ["--snapshot PATH", "Fly a route headlessly and save one composite frame, then exit"]],
      widths=[1.5, 5.0], size=10, mono_cols=(0,))

heading("2.3 Headless evaluation and the ablation", 2)
para("Scoring runs without opening a window, which is how every number in the report is "
     "produced.")
code(["# score many seeds on ground truth depth",
      ".venv/bin/python run_route.py --seeds 100-149 --stations 4",
      "",
      "# the three arm ablation: perfect depth, MiDaS depth, no depth",
      ".venv/bin/python ablation.py --seeds 100-149",
      "",
      "# depth quality and speed of the model on simulator frames",
      ".venv/bin/python bench_midas.py",
      "",
      "# regenerate the wall, floor and obstacle textures",
      ".venv/bin/python textures.py",
      "",
      "# rebuild the airframe mesh from the team's CAD",
      ".venv/bin/python convert_cad.py cad/"])
page_break()

# ---------------------------------------------------------------- conventions
heading("3. Conventions and notation", 1)
table(["Symbol", "Meaning", "Units"],
      [["W, H", "Camera image width and height in pixels. 320 by 240", "pixels"],
       ["i, j", "Image column index and row index", "index"],
       ["D[j,i]", "Depth at a pixel, measured along the camera axis, not radial", "metres"],
       ["theta_i", "Yaw offset the column i corresponds to. Positive is left", "radians"],
       ["psi", "Aircraft heading in the world frame", "radians"],
       ["beta", "Bearing to the next station in the body frame. Positive is left", "radians"],
       ["v, omega", "Commanded forward speed and yaw rate", "m/s, rad/s"],
       ["b", "Half the wingspan plus margin. 0.55 m", "metres"],
       ["R", "Range beyond which a direction counts as fully open. 8 m", "metres"]],
      widths=[0.9, 4.3, 1.1], size=10, mono_cols=(0,))
para("Two conventions matter and both were verified rather than assumed. MuJoCo returns "
     "planar depth, meaning distance along the camera axis, which was confirmed by "
     "pointing the camera at a flat wall and checking that every column reported the same "
     "value. And the camera is mounted with image right along the body negative y axis, "
     "so a column to the right of centre corresponds to a right turn, which is where the "
     "minus sign in the yaw offset comes from.")

# ---------------------------------------------------------------- camera
heading("4. Camera geometry", 1)
para("The vertical field of view is set on the camera. The horizontal one follows from "
     "the aspect ratio.")
code(["hfov = 2 * atan( tan(vfov / 2) * W / H )"])
para("Each image column maps to a yaw offset, and each row to a height gain used later "
     "to discard floor and ceiling.")
code(["ndc_x[i]   = (i + 0.5) / W * 2 - 1          # -1 at the left edge, +1 at the right",
      "theta[i]   = -atan( ndc_x[i] * tan(hfov / 2) )",
      "",
      "ndc_y[j]   = 1 - 2 * (j + 0.5) / H          # +1 at the top, -1 at the bottom",
      "row_gain[j]= ndc_y[j] * tan(vfov / 2)"])

# ---------------------------------------------------------------- free space
heading("5. Depth map to free space", 1)
heading("5.1 Discarding floor and ceiling", 2)
para("A pixel at depth D on row j sits at this height relative to the camera. Only "
     "surfaces near the aircraft's own flying height can be struck, so everything outside "
     "a band is thrown away. Without this step the floor dominates every column and the "
     "policy cannot tell open space from an obstacle.")
code(["height[j,i] = D[j,i] * row_gain[j]",
      "keep if  |height[j,i]| < z_band                 z_band = 0.35 m",
      "raw[i]  = clip( min over kept rows of D[.,i],  0,  R )"])

heading("5.2 Angular shadow casting", 2)
para("A gap only counts as a gap if the aircraft fits through it. Every obstacle blocks "
     "a wedge of headings whose half width depends on that obstacle's own range. Sizing "
     "the wedge from the candidate heading's range instead is a sign error that makes "
     "close obstacles poison headings they do not really block.")
code(["k[j]          = atan( b / max(raw[j], 0.35) )",
      "shadowed[i,j] = |theta[i] - theta[j]| < k[j]",
      "free[i]       = min over shadowed j of raw[j],   otherwise R"])
para("The clearance directly ahead, which the safety layer uses, is the worst value "
     "inside a narrow forward wedge.")
code(["min_front = min of free[i] over |theta[i]| < 12 degrees"])
page_break()

# ---------------------------------------------------------------- steering
heading("6. Heading selection and speed", 1)
para("Every candidate heading is scored on three terms. Open space, alignment with the "
     "station, and a penalty for abandoning the heading already chosen. The third term "
     "exists because two gaps of near equal value otherwise make the aircraft alternate "
     "between them at loop rate and average its heading to zero.")
code(["align[i] = cos( clip( theta[i] - beta, -pi, pi ) )",
      "stay[i]  = |theta[i] - psi_cmd| / hfov",
      "score[i] = free[i] / R  +  w_goal * align[i]  -  w_commit * stay[i]",
      "best     = theta[ argmax score ]"])
para("The chosen heading is smoothed over time with an exponential moving average. This "
     "is what lets the loop tolerate a depth map that flickers frame to frame, which "
     "matters much more once MiDaS supplies the depth.")
code(["a       = exp( -dt / tau )                      tau = 0.25 s",
      "psi_cmd = a * psi_cmd + (1 - a) * best"])
para("Speed falls as the space ahead shrinks, but never below a floor. Allowing it to "
     "decay smoothly to zero lets the aircraft park itself just outside the stop "
     "threshold forever without ever declaring itself blocked.")
code(["throttle = clip( (min_front - d_stop) / (d_clear - d_stop), 0, 1 )",
      "throttle = max( throttle, throttle_min )",
      "v        = v_max * throttle",
      "           * clip( cos psi_cmd, 0.25, 1 )        # slow down while turning hard",
      "           * clip( cos beta,    0.20, 1 )        # slow down if the station is behind",
      "omega    = clip( 2.2 * psi_cmd, -omega_max, omega_max )",
      "climb    = clip( 1.5 * altitude_error, -c_max, c_max )"])

# ---------------------------------------------------------------- safety
heading("7. Safety layer and wing guard", 1)
para("The safety layer is the guardrail and contains no learned component. It is the "
     "reason the system can be argued to be safe at all.")
code(["blocked = min_front < d_stop                    d_stop = 1.2 m",
      "",
      "if blocked:",
      "    v     = 0,  or -v_escape after escape_after seconds",
      "    omega = turn_dir * omega_max * 0.85         # direction latched once, then held"])
para("The turn direction is chosen once when the block begins, using mean free space on "
     "each side with any side the wing cannot sweep through removed from consideration. "
     "Re-deciding every frame is what produced the visible left and right jitter.")
code(["left_free  = mean of free[i] for theta[i] > 0",
      "right_free = mean of free[i] for theta[i] < 0",
      "penalise a side whose wing clearance is below  b + 0.25",
      "turn_dir   = +1 if left_free >= right_free else -1"])
para("The wing guard damps a rotation that would sweep the wingtip into something the "
     "memory still holds. It only damps. Reversing the latch here recreates the jitter it "
     "exists to prevent.")
code(["reach     = b + 0.25",
      "wing_risk = left_clear  if omega > 0  else right_clear",
      "if wing_risk < reach:   omega = omega * 0.15"])
para("Hysteresis on the stop threshold was implemented and measured at release margins "
     "of 0.25, 0.45 and 0.70 metres. Every setting scored worse than no hysteresis, so "
     "the parameter exists but defaults to zero.")
page_break()

# ---------------------------------------------------------------- memory
heading("8. All round obstacle memory", 1)
para("The camera sees a wedge of about 116 degrees. The wingtip sweeps a full circle. A "
     "coarse memory of 72 bearing bins keeps obstacles that have left the frame from "
     "being forgotten at the moment they matter most. It is ego motion compensated and it "
     "decays, so nothing is localised and no map is built.")
code(["# carry each remembered obstacle through last step's motion",
      "x  = d * cos(phi) - v * dt",
      "y  = d * sin(phi)",
      "xr = cos(-omega*dt) * x - sin(-omega*dt) * y",
      "yr = sin(-omega*dt) * x + cos(-omega*dt) * y",
      "d' = hypot(xr, yr)          phi' = atan2(yr, xr)",
      "",
      "# forget slowly, then overwrite whatever the camera can currently see",
      "d' = min( R,  d' + forget * dt )               forget = 0.15 m/s"])
para("The decay rate is the single most influential parameter in the whole policy. "
     "Sweeping it between 0.15 and 3.0 metres per second moved collision free completion "
     "from 9 out of 12 down to 4 out of 12 on the tuning seeds.")

# ---------------------------------------------------------------- navigation
heading("9. Navigation and motion", 1)
code(["wrap(a)  = (a + pi) mod 2*pi - pi",
      "beta     = wrap( atan2(y_station - y, x_station - x) - psi )",
      "arrived  when |station - position| < 0.7 m",
      "",
      "# body frame command to a world frame step",
      "step = [ cos(psi)*v - sin(psi)*s,   sin(psi)*v + cos(psi)*s,   climb ] * dt",
      "",
      "# free joint orientation from heading",
      "quat = [ cos(psi/2), 0, 0, sin(psi/2) ]"])
para("Motion is kinematic with collision rejection. The proposed move is written to the "
     "model and the contact count is read back. If the full move collides, rotation alone "
     "is tried, then translation alone. Refusing everything leaves a wedged aircraft "
     "unable to turn away, and because its view never changes it reissues the identical "
     "command forever.")
code(["if clear(pos + step, psi + omega*dt):  accept both",
      "elif clear(pos, psi + omega*dt):       accept the rotation only",
      "elif clear(pos + step, psi):           accept the translation only",
      "else:                                  hold position and count a contact"])

# ---------------------------------------------------------------- course
heading("10. Course generation", 1)
para("Courses come from an integer seed rather than a stored file, so the dataset is the "
     "seed list. Obstacles sit on a jittered grid chosen so the narrowest possible gap "
     "still exceeds the wingspan.")
code(["min_gap = grid_pitch - 2 * max_radius - 2 * max_jitter",
      "        = 2.50 - 2(0.30) - 2(0.25)  =  1.40 m      against a 1.00 m wingspan",
      "",
      "cell centre    cx = -half + grid_pitch * (i + 0.5)",
      "map projection px = (x + half) * MAP / room",
      "                py = MAP - (y + half) * MAP / room"])
para("Reachability was verified independently by flood filling the free space for a disc "
     "of the aircraft's radius. Every station was reachable at every obstacle density "
     "tested, which rules out an impossible course as an explanation for any failure.")
page_break()

# ---------------------------------------------------------------- midas
heading("11. MiDaS integration", 1)
heading("11.1 What the model is and what it returns", 2)
para("MiDaS-small version 2.1 is an encoder and decoder network of 21.3 million "
     "parameters. The encoder is a lightweight convolutional backbone built for devices "
     "without a graphics processor. The decoder climbs back up, fusing coarse features "
     "that know the layout with fine features that know where edges are.")
para("It is loaded from the published weights and never trained. What it returns is "
     "inverse depth, meaning one divided by distance, and only up to an unknown "
     "multiplier and an unknown offset that differ from image to image. It is not metres "
     "and it cannot be handed to the policy directly.")

heading("11.2 The preprocessing trap", 2)
para("The hub transform divides the image by 255 itself. Passing an image already scaled "
     "to the range zero to one therefore scales it twice, and the network sees a nearly "
     "black frame. It does not error. It returns a plausible looking vertical gradient "
     "for every input, which is easy to mistake for a domain gap.")
table(["Measurement on simulator frames", "Image scaled twice", "Correct"],
      [["Correlation with true inverse depth", "0.29", "0.92"],
       ["Absolute relative error", "0.40", "0.21"],
       ["Pixels within a factor of 1.25", "0.42", "0.62"]],
      widths=[3.4, 1.6, 1.3], size=10)
code(["# correct",
      "img = rgb.astype(np.float32)          # 0 to 255, the transform scales it",
      "x   = transform(img)",
      "",
      "# wrong, and it fails silently",
      "img = rgb.astype(np.float32) / 255.0"])
para("The check that caught it was running the model on a real photograph. A featureless "
     "vertical ramp on a real indoor photo is not something any working monocular depth "
     "model produces, which located the fault upstream of the network rather than in it.")

heading("11.3 Recovering scale and offset", 2)
para("Both unknowns are found by least squares against a reference, in inverse depth "
     "space. Median scaling corrects the multiplier alone and leaves a systematic error "
     "behind, which is why the original project specification needed correcting on this "
     "point.")
code(["minimise over s and t:    sum_i ( s * pred_i + t - target_i )^2",
      "",
      "# two unknowns, so a closed form 2x2 solve",
      "a00 = sum(p*p)   a01 = sum(p)   a11 = N",
      "b0  = sum(p*q)   b1  = sum(q)",
      "det = a00*a11 - a01*a01",
      "s   = ( a11*b0 - a01*b1) / det",
      "t   = (-a01*b0 + a00*b1) / det",
      "",
      "# then back to metres",
      "depth = 1 / max( s * pred + t,  1e-3 )"])
para("Two alignment arms exist and they answer different questions.")
table(["Arm", "How scale and offset are obtained", "What it measures"],
      [["frozen", "Fitted once across a calibration set of simulator frames, then held fixed",
        "The honest arm. It is what an aircraft could actually do, using a known height "
        "above the floor as its reference"],
       ["oracle", "Refitted on every frame against the true depth",
        "An upper bound. It separates error in the depth structure from error in the "
        "alignment, and is not achievable in flight"]],
      widths=[0.8, 2.6, 3.1], size=10, mono_cols=(0,))

heading("11.4 Where it plugs in", 2)
para("The policy takes the depth map as an argument and holds no dependency on how it "
     "was produced. That single seam is what makes the ablation a fair comparison, "
     "because everything downstream is byte for byte identical across the three arms.")
code(["from midas_depth import MidasDepth",
      "md = MidasDepth()                       # picks Metal, CUDA or CPU automatically",
      "md.calibrate(cal_rgb_frames, cal_true_depths)",
      "",
      "def estimated(rgb, true_depth):",
      "    return md.metric_depth(rgb, true_depth, mode='frozen')",
      "",
      "run(seed, stations, obstacles, room, depth_fn=estimated)"])

heading("11.5 Quality metrics", 2)
code(["ratio  = max( pred/true,  true/pred )",
      "AbsRel = mean( |pred - true| / true )",
      "RMSE   = sqrt( mean( (pred - true)^2 ) )",
      "d1     = fraction of pixels with ratio < 1.25",
      "d2     = fraction of pixels with ratio < 1.25^2"])
page_break()

# ---------------------------------------------------------------- measured
heading("12. Measured values", 1)
para("Everything below was measured on this machine, an Apple M5 with 16 GB of memory. "
     "Nothing is quoted from the literature.")
heading("12.1 Speed", 2)
table(["Measurement", "Value"],
      [["MiDaS-small inference, Metal backend", "8.7 ms per frame, about 115 frames per second"],
       ["Complete loop, physics with colour and depth render", "over 200 cycles per second"],
       ["Reactive policy computation alone", "about 0.24 ms per call"],
       ["Requirement to be met", "10 frames per second"]],
      widths=[3.6, 2.9], size=10)
heading("12.2 Depth quality on simulator frames", 2)
table(["World", "Alignment", "Correlation", "AbsRel", "d1", "d2"],
      [["flat grey", "frozen", "0.917", "0.222", "0.598", "0.902"],
       ["flat grey", "oracle", "0.917", "0.146", "0.774", "0.935"],
       ["textured", "frozen", "0.915", "0.207", "0.622", "0.918"],
       ["textured", "oracle", "0.915", "0.752", "0.759", "0.952"]],
      widths=[1.1, 1.1, 1.3, 1.0, 1.0, 1.0], size=10)
para("Texturing the world changed depth quality by less than one part in five hundred. "
     "Visual realism is therefore not what limits the estimate here, and the textures are "
     "kept because the simulator looks better rather than because they help the model.")
heading("12.3 Flight outcomes", 2)
para("Ground truth depth, fifty held out seeds never used during tuning, four stations "
     "per run.")
table(["Obstacles in a 10 m room", "Routes completed", "Collision free", "Contacts per run"],
      [["4", "47 of 50", "41 of 50", "0.16"],
       ["6", "38 of 50", "33 of 50", "0.20"],
       ["9", "28 of 50", "22 of 50", "0.34"]],
      widths=[1.9, 1.6, 1.6, 1.4], size=10)
para("The three arm ablation on ten seeds at six obstacles, which is too small a sample "
     "to conclude from but shows the harness working end to end.")
table(["Depth source", "Routes completed", "Collision free", "Contacts per run"],
      [["Perfect, from the simulator", "10 of 10", "5 of 10", "1.60"],
       ["MiDaS, from one camera image", "9 of 10", "2 of 10", "3.40"],
       ["None", "9 of 10", "3 of 10", "37.10"]],
      widths=[2.2, 1.5, 1.5, 1.3], size=10)
para("The contact column carries the signal. A blind aircraft touches something 37 times "
     "a run, one flying on an estimate 3.4 times, and one with a true sensor 1.6 times. "
     "One caution applies to every figure on this page. Tuning the policy on 12 seeds "
     "gave 92 per cent collision free, and the same settings gave 66 per cent on 50 seeds "
     "held back. Only the held out number should ever be quoted.")

# ---------------------------------------------------------------- parameters
heading("13. Parameter reference", 1)
para("Every value below is a constructor argument of the policy, which is what makes the "
     "automated parameter search the coursework asks for straightforward to run.")
table(["Parameter", "Default", "Meaning"],
      [["max_range", "8.0 m", "Beyond this a direction counts as fully open"],
       ["stop_threshold", "1.2 m", "Safety layer trip point. Linked to the stopping distance"],
       ["release_margin", "0.0 m", "Hysteresis on the stop layer. Tested and rejected"],
       ["clear_distance", "3.5 m", "Full speed once this much room is ahead"],
       ["goal_weight", "1.8", "Pull toward the station in the heading score"],
       ["commit", "0.25", "Penalty for abandoning the heading already chosen"],
       ["half_span", "0.55 m", "Half the wingspan plus margin. Sets the shadow width"],
       ["z_band", "0.35 m", "Height band around flight level that counts as an obstacle"],
       ["min_throttle", "0.30", "Speed floor, so it commits or declares itself blocked"],
       ["smoothing", "0.25 s", "Time constant of the heading average"],
       ["memory_bins", "72", "Bearing bins in the all round memory, one every 5 degrees"],
       ["forget", "0.15 m/s", "Memory decay. The most influential single parameter"],
       ["escape_after", "1.0 s", "Time blocked before backing out"],
       ["escape_speed", "0.35 m/s", "Reverse speed while escaping. Blind, so it is slow"],
       ["desperate_after", "3.0 s", "Time blocked before the station is ignored entirely"],
       ["flip_cooldown", "0.0 s", "Wing guard side switching. Tested and rejected"],
       ["max_speed", "2.0 m/s", "Cruise speed the latency budget was derived from"],
       ["max_yaw", "1.8 rad/s", "Yaw rate limit"],
       ["max_climb", "1.0 m/s", "Climb rate limit"]],
      widths=[1.5, 1.1, 3.9], size=10, mono_cols=(0,))
para("Airframe and world constants, taken from the team's own design files rather than "
     "assumed.")
table(["Constant", "Value", "Source"],
      [["Wingspan", "1.000 m", "Measured from 09_vtol_shell_combined_aero.step"],
       ["Length", "0.815 m", "Same file"],
       ["Height", "0.231 m", "Same file"],
       ["Camera vertical field of view", "100 degrees", "Chosen by measurement, not by default"],
       ["Camera resolution", "320 by 240", "What the depth model consumes"],
       ["Room", "10 m square, 3 m high", "Set by the wingspan"],
       ["Narrowest obstacle gap", "1.40 m", "Leaves 0.20 m clearance each side"],
       ["Cruise altitude", "1.20 m", "Mid height between floor and ceiling"],
       ["Control step", "0.05 s", "20 cycles per second"]],
      widths=[2.2, 1.3, 3.0], size=10)

OUT = "Technical_Reference_Formulae_and_MiDaS.docx"
doc.save(OUT)
print("saved", OUT)
