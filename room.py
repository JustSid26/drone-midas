"""Procedural indoor course generator for the VTOL avoidance sim.

Rooms are built from a seed so the same integer always yields the same layout.
That is what lets you compare depth sources on identical courses later.

The aircraft is the team's own airframe: meshes/vtol_shell.stl, tessellated
from 09_vtol_shell_combined_aero.step. Run convert_cad.py to regenerate it.
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MESHDIR = os.path.join(HERE, "meshes")
SHELL = os.path.join(MESHDIR, "vtol_shell.stl")
TEXDIR = os.path.join(HERE, "textures")

# Airframe envelope measured from the STEP file (metres).
DRONE_LEN = 0.815
DRONE_SPAN = 1.000
DRONE_HEIGHT = 0.231
NOSE_X = DRONE_LEN / 2.0        # mesh is centred on its planform


def build(seed=0, room=10.0, height=3.0, n_obstacles=9, grid_pitch=2.5,
          cam_w=640, cam_h=480, fovy=70, show_hull=False, textured=True):
    """Return (mjcf_xml, meta). Obstacles sit on a jittered grid so the
    narrowest gap is always wider than the wingspan."""
    rng = np.random.default_rng(seed)
    half = room / 2.0
    start = np.array([-half + 1.5, 0.0, 1.2])
    goal = np.array([half - 1.5, 0.0, 1.2])

    max_radius = 0.30
    max_jitter = 0.25
    min_gap = grid_pitch - 2 * max_radius - 2 * max_jitter

    cells = []
    n = int(room // grid_pitch)
    for i in range(n):
        for j in range(n):
            cx = -half + grid_pitch * (i + 0.5)
            cy = -half + grid_pitch * (j + 0.5)
            if np.hypot(cx - start[0], cy - start[1]) < 2.0:
                continue
            if np.hypot(cx - goal[0], cy - goal[1]) < 2.0:
                continue
            cells.append((cx, cy))
    rng.shuffle(cells)
    cells = cells[:n_obstacles]

    obstacles = []
    for k, (cx, cy) in enumerate(cells):
        x = cx + rng.uniform(-max_jitter, max_jitter)
        y = cy + rng.uniform(-max_jitter, max_jitter)
        r = rng.uniform(0.18, max_radius)
        kind = rng.choice(["cylinder", "box"])
        h = rng.uniform(1.6, height)
        hue = rng.uniform(0.25, 0.75)
        obstacles.append(dict(i=k, x=x, y=y, r=r, h=h, kind=kind, c=hue))

    geoms = []
    for o in obstacles:
        if textured:
            mat = ["obs_a", "obs_b", "obs_c"][o["i"] % 3]
            paint = f'material="{mat}"'
        else:
            rgba = f"{o['c']:.2f} {0.9 - o['c'] * 0.5:.2f} {0.35 + o['c'] * 0.4:.2f} 1"
            paint = f'material="obs" rgba="{rgba}"'
        if o["kind"] == "cylinder":
            geoms.append(
                f'<geom name="obs{o["i"]}" type="cylinder" pos="{o["x"]:.3f} {o["y"]:.3f} {o["h"]/2:.3f}" '
                f'size="{o["r"]:.3f} {o["h"]/2:.3f}" {paint}/>')
        else:
            geoms.append(
                f'<geom name="obs{o["i"]}" type="box" pos="{o["x"]:.3f} {o["y"]:.3f} {o["h"]/2:.3f}" '
                f'size="{o["r"]:.3f} {o["r"]:.3f} {o["h"]/2:.3f}" {paint}/>')

    t = 0.1
    walls = [
        f'<geom name="wall_n" type="box" pos="0 {half:.2f} {height/2}" size="{half:.2f} {t} {height/2}" material="wall"/>',
        f'<geom name="wall_s" type="box" pos="0 {-half:.2f} {height/2}" size="{half:.2f} {t} {height/2}" material="wall"/>',
        f'<geom name="wall_e" type="box" pos="{half:.2f} 0 {height/2}" size="{t} {half:.2f} {height/2}" material="wall"/>',
        f'<geom name="wall_w" type="box" pos="{-half:.2f} 0 {height/2}" size="{t} {half:.2f} {height/2}" material="wall"/>',
        f'<geom name="ceiling" type="box" pos="0 0 {height:.2f}" size="{half:.2f} {half:.2f} {t}" material="ceiling"/>',
    ]

    # Airframe: tessellated shell for looks, box envelope for collision.
    # Splitting them keeps contacts cheap and exactly matches the measured span.
    if textured and os.path.isdir(TEXDIR):
        assets = (
            '<texture name="floortex" type="2d" file="floor.png"/>\n'
            f'    <material name="floor" texture="floortex" texrepeat="{max(int(room)//2,3)} '
            f'{max(int(room)//2,3)}" reflectance="0.04" specular="0.15"/>\n'
            '    <texture name="walltex" type="2d" file="wall.png"/>\n'
            '    <material name="wall" texture="walltex" texrepeat="5 3" specular="0.05"/>\n'
            '    <texture name="ceiltex" type="2d" file="ceiling.png"/>\n'
            '    <material name="ceiling" texture="ceiltex" texrepeat="4 4" specular="0.05"/>\n'
            '    <texture name="obsatex" type="2d" file="obs_a.png"/>\n'
            '    <material name="obs_a" texture="obsatex" texrepeat="2 3" specular="0.25"/>\n'
            '    <texture name="obsbtex" type="2d" file="obs_b.png"/>\n'
            '    <material name="obs_b" texture="obsbtex" texrepeat="2 3" specular="0.25"/>\n'
            '    <texture name="obsctex" type="2d" file="obs_c.png"/>\n'
            '    <material name="obs_c" texture="obsctex" texrepeat="2 3" specular="0.25"/>')
    else:
        assets = (
            '<texture name="grid" type="2d" builtin="checker" rgb1="0.28 0.30 0.34" '
            'rgb2="0.38 0.40 0.45" width="512" height="512" mark="cross" markrgb="0.6 0.6 0.6"/>\n'
            f'    <material name="floor" texture="grid" texrepeat="{int(room)} {int(room)}" reflectance="0.05"/>\n'
            '    <texture name="walltex" type="2d" builtin="flat" rgb1="0.62 0.60 0.56" '
            'rgb2="0.50 0.48 0.45" width="256" height="256" mark="random" markrgb="0.42 0.40 0.38" random="0.02"/>\n'
            '    <material name="wall" texture="walltex" texrepeat="6 3"/>\n'
            '    <material name="ceiling" texture="walltex" texrepeat="6 6"/>\n'
            '    <material name="obs" specular="0.2" shininess="0.3"/>')

    have_mesh = os.path.exists(SHELL)
    hull_rgba = "0.9 0.2 0.2 0.18" if show_hull else "0 0 0 0"
    if have_mesh:
        mesh_asset = f'<mesh name="vtol" file="{os.path.basename(SHELL)}"/>'
        airframe = (
            f'<geom name="shell" type="mesh" mesh="vtol" material="body" '
            f'contype="0" conaffinity="0" group="1" density="0"/>\n'
            f'      <geom name="hull" type="box" '
            f'size="{DRONE_LEN/2:.4f} {DRONE_SPAN/2:.4f} {DRONE_HEIGHT/2:.4f}" '
            f'group="3" rgba="{hull_rgba}" mass="2.2"/>')
    else:
        mesh_asset = ""
        airframe = (f'<geom name="hull" type="box" '
                    f'size="{DRONE_LEN/2:.4f} {DRONE_SPAN/2:.4f} {DRONE_HEIGHT/2:.4f}" '
                    f'material="body" mass="2.2"/>')

    xml = f"""<mujoco model="room_seed{seed}">
  <compiler meshdir="{MESHDIR}" texturedir="{TEXDIR}" inertiafromgeom="auto"/>
  <option gravity="0 0 0" timestep="0.004" integrator="RK4"/>
  <visual>
    <global offwidth="{cam_w}" offheight="{cam_h}"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.5 0.5 0.5"/>
    <quality shadowsize="2048"/>
  </visual>
  <asset>
    {mesh_asset}
    {assets}
    <material name="body" rgba="0.42 0.48 0.58 1" specular="0.7" shininess="0.6"/>
  </asset>
  <worldbody>
    <light pos="0 0 {height-0.3}" dir="0 0 -1" diffuse="0.7 0.7 0.7" castshadow="true"/>
    <light pos="{-half/2} {-half/2} {height-0.3}" dir="0 0 -1" diffuse="0.35 0.35 0.35"/>
    <light pos="{half/2} {half/2} {height-0.3}" dir="0 0 -1" diffuse="0.35 0.35 0.35"/>
    <geom name="floor" type="plane" size="{half:.2f} {half:.2f} 0.1" material="floor"/>
    {chr(10).join('    ' + w for w in walls)}
    {chr(10).join('    ' + g for g in geoms)}
    <body name="drone" pos="{start[0]:.2f} {start[1]:.2f} {start[2]:.2f}">
      <freejoint name="root"/>
      {airframe}
      <camera name="fpv" pos="{NOSE_X + 0.03:.3f} 0 0.03" xyaxes="0 -1 0  0 0 1" fovy="{fovy}"/>
      <camera name="chase" pos="-2.1 0 1.05" xyaxes="0 -1 0  0.447 0 0.894" fovy="60"/>
    </body>
  </worldbody>
</mujoco>
"""
    meta = dict(seed=seed, room=room, height=height, start=start, goal=goal,
                obstacles=obstacles, min_gap=min_gap, grid_pitch=grid_pitch,
                mesh=have_mesh)
    return xml, meta
