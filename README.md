# VTOL indoor course sim

A keyboard-flyable drone in a procedurally generated room, built to prototype the
monocular obstacle-avoidance pipeline before any of it touches ROS 2, Gazebo, or hardware.

Runs natively on Apple Silicon. No Unity, no Docker, no virtual machine.

## Setup

Python 3.11 or newer.

    git clone https://github.com/JustSid26/drone-midas.git
    cd drone-midas
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt

On Windows the interpreter is `.venv\Scripts\python` instead of `.venv/bin/python`
in every command below.

## Run

    .venv/bin/python fly.py --seed 0

    click map   add a station
    right-click remove the nearest station
    N           toggle auto navigation
    C           clear all stations
    arrows      forward / back / yaw left / yaw right (manual only)
    a  d        strafe
    r  f        climb / descend
    space       reset to start
    q or esc    quit

## Auto navigation

Click stations on the map panel and press N. The aircraft flies them in order,
steering by depth alone and advancing when it comes within 0.7 m of each one.
Nothing about the route is planned in advance: the policy only ever reacts to
the frame in front of it plus a short-term memory of what has just left view.

The policy lives in `policy.py` and takes the depth map as an argument. That is
the seam for the ablation. Pass MuJoCo ground truth today, pass a MiDaS estimate
later, and the difference between the two runs on the same seeds is the result
the project is actually after.

Three layers, in priority order:

1. Safety stop. If anything at flight level is closer than 1.2 m in the forward
   wedge, forward motion is refused and the aircraft rotates on the spot. No
   learned component sits in this path.
2. Wing guard. The camera sees a wedge but the wingtip sweeps a full circle, so
   a coarse all-round memory of recent obstacles prevents rotating into
   something that has already left the frame. It is ego-motion compensated and
   decays; nothing is localised and no map is built.
3. Steering. Among headings wide enough for the wing at their own range, pick
   the one trading free depth against bearing to the station.

## Where it currently stands

Measured with perfect simulator depth, which is the ceiling. Seeds 100-149 were
never used while tuning, 4 stations per run, 10 m room, 100 degree lens.

    obstacles   route completed   collision-free   contacts/run   timeouts
            4          47/50           41/50           0.16           3
            6          38/50           33/50           0.20          12
            9          28/50           22/50           0.34          22

At 6 obstacles the 95% Wilson interval on collision-free completion is 52% to 78%.

Two things to read off this table.

Tuning the policy on 12 seeds gave 11/12, or 92%. The same parameters score 66%
on 50 seeds that were held out. That gap is overfitting to a small sample, and it
is the reason the project specification asks for separate tuning, validation and
frozen test splits. Quote the held-out number, never the tuned one.

Failures are overwhelmingly timeouts, not crashes. The safety layer is doing its
job at 0.2 contacts per run; what fails is the planner getting stuck in a concave
pocket with no representation in which "go around the far side" exists. That is a
property of a purely reactive method, not a bug, and belongs in the failure
analysis.

## Running with MiDaS

MiDaS-small estimates depth from the camera image alone, standing in for the
perfect simulator depth. The first run downloads the model, about 100 MB, into
`.torch/`, so it needs internet once. It runs on the Apple GPU (MPS), CUDA, or CPU,
whichever is available.

Fly on estimated depth instead of simulator truth:

    .venv/bin/python fly.py --seed 0 --midas

Controls are the same as above. The depth panel now shows the MiDaS estimate the
aircraft is actually flying on. MiDaS gives depth only up to an unknown scale and
offset, so both are fitted once against true depth and frozen. That fit is cached
in `.midas_calib.json`. Add `--align oracle` to refit against true depth every
frame instead: an upper bound, not something a real aircraft could do.

Measure depth accuracy and speed on still frames, no flying:

    .venv/bin/python bench_midas.py

Prints AbsRel, RMSE and the delta < 1.25 accuracy for both alignments, plus
milliseconds per frame on your device.

Run the ablation, the result the project is after:

    .venv/bin/python ablation.py --seeds 100-129 --obstacles 6

Flies the same courses three times, on perfect depth, on MiDaS depth, and on no
depth at all, and prints route completion, collision-free runs with a 95%
interval, contacts and timeouts for each. MiDaS runs on every frame, so this is
slow. Try `--seeds 100-104` first to check it works.

## Headless evaluation

    .venv/bin/python run_route.py --seeds 0-49 --stations 4

Scores every seed for stations reached, contact events, and time. This is the
harness the graded numbers come from.

Three panels: chase view on the left, the aircraft's camera top right, and perfect
ground-truth depth below it. The depth panel is what the MiDaS estimate will be
scored against later.

Other seeds give different courses. `--obstacles` and `--room` change the difficulty.

    .venv/bin/python fly.py --seed 12 --obstacles 14 --room 12

## The aircraft

The flying model is the team's own airframe, tessellated from
`09_vtol_shell_combined_aero.step` into `meshes/vtol_shell.stl` and recentred so
the body origin sits at the planform centre with the nose toward +x. The camera
is mounted just ahead of the nose.

The shell is visual only. Collision uses a box matching the measured envelope,
0.815 by 1.000 by 0.231 m, which keeps contacts cheap and makes the wingspan
exactly what the course was designed around. Run with `--show-hull` to see it.

Regenerate the mesh after any CAD change:

    .venv/bin/python convert_cad.py <folder-with-step-files>

## Why the room is 10 m

The airframe measures 1.00 m across the wing, taken from the team's STEP files.
Obstacles sit on a 2.5 m grid with bounded jitter, so the narrowest gap is 1.40 m,
leaving 0.40 m of clearance. Shrink the room and the course stops being flyable
rather than becoming harder.

## Flight model

Motion is kinematic with collision rejection. A move that would intersect geometry
is refused and counted. That keeps the aircraft controllable by hand and makes the
collision count exact, which is the metric the graded project reports. Real
dynamics, rotor thrust, and hover-to-cruise transition come later from PX4 SITL.

## Files

    room.py                seeded course generator, emits MJCF
    fly.py                 interactive sim, map panel, manual and auto flight
    policy.py              reactive avoidance policy and safety layers
    run_route.py           headless batch scoring over many seeds
    midas_depth.py         MiDaS-small wrapper, scale and offset alignment, metrics
    bench_midas.py         MiDaS depth accuracy and speed on sim frames
    ablation.py            perfect vs MiDaS vs no depth on identical courses
    convert_cad.py         STEP to STL for the team's airframe parts
    cad/                   the team's STEP parts, copied out of WhatsApp temp
    meshes/vtol_shell.stl  the flying model

## Next

1. Tune the policy parameters with Optuna against `run_route`, which is what the
   coursework asks for. The parameters are already constructor arguments.
2. Log every run to MLflow: seed, contacts, time, minimum clearance.
3. Move to PX4 SITL for real flight dynamics and the hover-to-cruise transition.
