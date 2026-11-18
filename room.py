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


STYLES = ("photo", "procedural", "flat")

BOX_LOOKS = ["wood_cabinet_worn_long", "kitchen_wood", "plywood", "brown_leather",
             "leather_white", "fabric_pattern_07"]
COLUMN_LOOKS = ["painted_concrete", "metal_plate", "white_plaster_02"]


# MuJoCo maps a 2D texture properly only onto upward-facing surfaces; on a wall it
# smears into streaks. So in the photo style every textured solid is drawn as a
# mesh that carries its own texture coordinates, in units of one texture tile.
# The mesh is for the camera only. Collisions use the same invisible box or
# cylinder primitive as the other styles: mesh contacts let the thin hull slip
# partway in before reporting, and the aircraft then wedged against obstacles.

def _box_uv(half, tile):
    a = np.asarray(half, float)
    V, UV, F = [], [], []
    for axis in range(3):
        for sign in (-1, 1):
            n = np.zeros(3); n[axis] = sign
            u_ax, v_ax = [i for i in range(3) if i != axis]
            base = len(V)
            for su, sv in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                p = n * a
                p[u_ax], p[v_ax] = su * a[u_ax], sv * a[v_ax]
                V.append(p)
                UV.append(((su + 1) * a[u_ax] / tile, (sv + 1) * a[v_ax] / tile))
            tri = [(0, 1, 2), (0, 2, 3)]
            if np.dot(np.cross(V[base + 1] - V[base], V[base + 2] - V[base]), n) < 0:
                tri = [(0, 2, 1), (0, 3, 2)]           # keep every face wound outward
            F += [(base + i, base + j, base + k) for i, j, k in tri]
    return V, UV, F


def _cylinder_uv(r, h, tile, n=48):
    V, UV, F = [], [], []
    for i in range(n + 1):                             # seam column repeated for the wrap
        th = 2 * np.pi * i / n
        for z in (-h, h):
            V.append((r * np.cos(th), r * np.sin(th), z))
            UV.append((r * th / tile, (z + h) / tile))
    for i in range(n):
        a, b, c, d = 2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1
        F += [(a, b, c), (a, c, d)]
    for z, up in ((-h, False), (h, True)):
        centre = len(V)
        V.append((0, 0, z)); UV.append((0.5, 0.5))
        ring = []
        for i in range(n):
            th = 2 * np.pi * i / n
            ring.append(len(V))
            V.append((r * np.cos(th), r * np.sin(th), z))
            UV.append((r * np.cos(th) / tile, r * np.sin(th) / tile))
        for i in range(n):
            j, k = ring[i], ring[(i + 1) % n]
            F.append((centre, j, k) if up else (centre, k, j))
    return V, UV, F


def _box(name, pos, size, mat, rgba=None, euler=None):
    extra = f' rgba="{rgba}"' if rgba else ""
    extra += f' euler="{euler}"' if euler else ""
    return (f'<geom name="{name}" type="box" pos="{pos[0]:.3f} {pos[1]:.3f} {pos[2]:.3f}" '
            f'size="{size[0]:.3f} {size[1]:.3f} {size[2]:.3f}" material="{mat}"{extra}/>')


def _photo_room(seed, half, height, obstacles, wall_t):
    """Photographic surfaces, ceiling lights and furniture for style 'photo'.

    Uses its own random stream, so the obstacle layout is identical in every
    style and results stay paired. Nothing added changes which gaps the wing
    fits through: tall furniture stands only in the corners, beyond the obstacle
    grid, and everything else in the room is either flush with a wall or lower
    than 0.8 m, under the band the policy treats as flight level. It is there
    for the camera, which is the point: real rooms are full of such things.
    """
    import json
    from textures import THEMES
    srng = np.random.default_rng(seed * 7919 + 17)
    theme_name = list(THEMES)[int(srng.integers(len(THEMES)))]
    theme = THEMES[theme_name]
    tiles = json.load(open(os.path.join(TEXDIR, "photo", "manifest.json")))

    # Materials. Real rooms are lit by light bouncing off every surface, which
    # MuJoCo does not model; a little emission on walls and ceiling stands in.
    tile_of, assets = {}, []
    for pid in sorted(set(theme.values()) | set(BOX_LOOKS) | set(COLUMN_LOOKS)):
        assets.append(f'<texture name="t_{pid}" type="2d" file="photo/{pid}.png"/>')
        tile_of[pid] = tiles[pid]["tile_m"][0]
    for pid in sorted(set(BOX_LOOKS) | set(COLUMN_LOOKS)):
        sp = 0.6 if pid == "metal_plate" else 0.15
        assets.append(f'<material name="m_{pid}" texture="t_{pid}" specular="{sp}"/>')
        tile_of[f"m_{pid}"] = tile_of[pid]
    ft = tile_of[theme["floor"]]
    assets.append(f'<material name="floor" texture="t_{theme["floor"]}" texuniform="true" '
                  f'texrepeat="{1 / ft:.3f} {1 / ft:.3f}" specular="0.2" reflectance="0.06"/>')
    assets.append(f'<material name="wall" texture="t_{theme["wall"]}" specular="0.05" emission="0.06"/>')
    assets.append(f'<material name="ceiling" texture="t_{theme["ceiling"]}" specular="0.0" emission="0.3"/>')
    assets.append('<material name="window" rgba="0.86 0.92 1 1" emission="0.8"/>')
    tile_of["wall"], tile_of["ceiling"] = tile_of[theme["wall"]], tile_of[theme["ceiling"]]

    meshes = {}

    def mesh(kind, dims, tile):
        key = (kind, tuple(round(d, 3) for d in dims), round(tile, 3))
        if key not in meshes:
            V, UV, F = _box_uv(dims, tile) if kind == "box" else _cylinder_uv(*dims, tile)
            fmt = lambda a, d: " ".join(f"{x:.{d}f}" for x in np.ravel(a))
            name = f"mesh{len(meshes)}"
            assets.append(f'<mesh name="{name}" vertex="{fmt(V, 4)}" texcoord="{fmt(UV, 4)}" '
                          f'face="{" ".join(str(int(x)) for x in np.ravel(F))}"/>')
            meshes[key] = name
        return meshes[key]

    def solid(name, pos, dims, mat, kind="box", euler=None, rgba=None):
        at = f'pos="{pos[0]:.3f} {pos[1]:.3f} {pos[2]:.3f}"' + (f' euler="{euler}"' if euler else "")
        size = " ".join(f"{d:.3f}" for d in dims)
        look = f' rgba="{rgba}"' if rgba else ""
        return (f'<geom name="{name}" type="{kind}" size="{size}" {at} group="3" rgba="0 0 0 0"/>'
                f'<geom name="{name}_look" type="mesh" mesh="{mesh(kind, dims, tile_of[mat])}" {at} '
                f'material="{mat}" contype="0" conaffinity="0"{look}/>')

    # The room shell and the obstacles: same shapes as the other styles.
    t = wall_t
    shell = [solid("wall_n", (0, half, height / 2), (half, t, height / 2), "wall"),
             solid("wall_s", (0, -half, height / 2), (half, t, height / 2), "wall"),
             solid("wall_e", (half, 0, height / 2), (t, half, height / 2), "wall"),
             solid("wall_w", (-half, 0, height / 2), (t, half, height / 2), "wall"),
             solid("ceiling", (0, 0, height), (half, half, t), "ceiling")]
    obs = []
    for o in obstacles:
        if o["kind"] == "cylinder":
            mat = "wall" if srng.random() < 0.35 else f"m_{srng.choice(COLUMN_LOOKS)}"
            obs.append(solid(f"obs{o['i']}", (o["x"], o["y"], o["h"] / 2), (o["r"], o["h"] / 2), mat, "cylinder"))
        else:
            obs.append(solid(f"obs{o['i']}", (o["x"], o["y"], o["h"] / 2), (o["r"], o["r"], o["h"] / 2),
                             f"m_{srng.choice(BOX_LOOKS)}"))

    face = half - t                                  # inner face of each wall
    geoms, k = [], 0

    def on_wall(w, u, depth, width, z, h):
        """Centre and half sizes for something standing against wall w."""
        if w in "ns":
            y = (face - depth / 2) * (1 if w == "n" else -1)
            return (u, y, z), (width / 2, depth / 2, h / 2)
        x = (face - depth / 2) * (1 if w == "e" else -1)
        return (x, u, z), (depth / 2, width / 2, h / 2)

    # Tall shelving in the corners only.
    for cx in (-1, 1):
        for cy in (-1, 1):
            if srng.random() < 0.6:
                s = srng.uniform(0.35, 0.45)
                h = srng.uniform(1.6, 2.2)
                geoms.append(solid(f"shelf{k}", (cx * (face - s), cy * (face - s), h / 2),
                                   (s, s, h / 2), f"m_{srng.choice(BOX_LOOKS[:3])}"))
                k += 1

    # Low sideboards against the walls, a door, windows and pictures.
    taken = {w: [] for w in "nsew"}

    def free_slot(w, width):
        for _ in range(30):
            u = srng.uniform(-face + 1.0 + width / 2, face - 1.0 - width / 2)
            if all(abs(u - v) > (width + vw) / 2 + 0.2 for v, vw in taken[w]):
                taken[w].append((u, width))
                return u
        return None

    walls = list("nsew")
    for _ in range(int(srng.integers(2, 5))):
        w, width = srng.choice(walls), srng.uniform(0.8, 1.8)
        u = free_slot(w, width)
        if u is not None:
            h = srng.uniform(0.5, 0.8)
            pos, size = on_wall(w, u, 0.45, width, h / 2, h)
            geoms.append(solid(f"sideboard{k}", pos, size, f"m_{srng.choice(BOX_LOOKS)}")); k += 1
    w = srng.choice(walls)
    u = free_slot(w, 0.9)
    if u is not None:
        pos, size = on_wall(w, u, 0.03, 0.9, 1.03, 2.06)
        geoms.append(solid(f"door{k}", pos, size, f"m_{srng.choice(BOX_LOOKS[:2])}")); k += 1
    for _ in range(int(srng.integers(0, 3))):
        w = srng.choice(walls)
        u = free_slot(w, 1.3)
        if u is not None:
            pos, size = on_wall(w, u, 0.02, 1.3, 1.6, 1.1)
            geoms.append(_box(f"window{k}", pos, size, "window")); k += 1
    for _ in range(int(srng.integers(2, 6))):
        w, width = srng.choice(walls), srng.uniform(0.4, 0.9)
        u = free_slot(w, width)
        if u is not None:
            h = srng.uniform(0.3, 0.7)
            pos, size = on_wall(w, u, 0.03, width, srng.uniform(1.3, 1.8), h)
            tint = f"{srng.uniform(.4, 1):.2f} {srng.uniform(.4, 1):.2f} {srng.uniform(.4, 1):.2f} 1"
            geoms.append(solid(f"picture{k}", pos, size,
                               f"m_{srng.choice(['fabric_pattern_07', 'brown_leather', 'plywood'])}", rgba=tint)); k += 1

    # Tables and boxes on the open floor, clear of the obstacles.
    def clear_of_obstacles(x, y, r):
        return all(np.hypot(x - o["x"], y - o["y"]) > o["r"] + r + 0.15 for o in obstacles)

    for _ in range(int(srng.integers(2, 5))):
        for _ in range(30):
            x, y = srng.uniform(-face + 0.8, face - 0.8, 2)
            tw, td = srng.uniform(0.6, 1.4), srng.uniform(0.5, 0.8)
            if clear_of_obstacles(x, y, np.hypot(tw, td) / 2):
                break
        else:
            continue
        yaw = srng.uniform(0, 180)
        mat = f"m_{srng.choice(BOX_LOOKS[:3])}"
        top = 0.74
        body = [solid(f"table{k}_top", (0, 0, top - 0.02), (tw / 2, td / 2, 0.02), mat)]
        for lx in (-1, 1):
            for ly in (-1, 1):
                body.append(solid(f"table{k}_leg{lx}{ly}", (lx * (tw / 2 - 0.05), ly * (td / 2 - 0.05), (top - 0.04) / 2),
                                  (0.025, 0.025, (top - 0.04) / 2), mat))
        geoms.append(f'<body name="table{k}" pos="{x:.3f} {y:.3f} 0" euler="0 0 {yaw:.1f}">'
                     + "".join(body) + "</body>")
        k += 1
    for _ in range(int(srng.integers(2, 7))):
        for _ in range(30):
            x, y = srng.uniform(-face + 0.5, face - 0.5, 2)
            s = srng.uniform(0.2, 0.4)
            if clear_of_obstacles(x, y, s * 1.5):
                break
        else:
            continue
        h = srng.uniform(0.25, 0.6)
        geoms.append(solid(f"box{k}", (x, y, h / 2), (s, s * srng.uniform(0.6, 1.0), h / 2),
                           "m_plywood", euler=f"0 0 {srng.uniform(0, 90):.1f}"))
        k += 1

    lights = []
    for lx in (-1, 1):
        for ly in (-1, 1):
            lights.append(f'<light pos="{lx * half / 2:.2f} {ly * half / 2:.2f} {height - 0.15:.2f}" dir="0 0 -1" '
                          f'cutoff="80" exponent="1" diffuse="0.40 0.39 0.36" specular="0.1 0.1 0.1" castshadow="true"/>')
    return dict(theme=theme_name, assets="\n    ".join(assets), shell=shell, obstacles=obs,
                geoms=geoms, lights="\n    ".join(lights),
                headlight='<headlight ambient="0.28 0.28 0.28" diffuse="0.14 0.14 0.14" specular="0 0 0"/>')


def build(seed=0, room=10.0, height=3.0, n_obstacles=9, grid_pitch=2.5,
          cam_w=640, cam_h=480, fovy=70, show_hull=False, textured=True, style=None):
    """Return (mjcf_xml, meta). Obstacles sit on a jittered grid so the
    narrowest gap is always wider than the wingspan.

    style is 'photo' (photographic surfaces, furniture and ceiling lights),
    'procedural' (the original generated textures) or 'flat'. The layout of the
    obstacles is the same in all three for a given seed."""
    if style is None:
        style = "procedural" if textured else "flat"
    assert style in STYLES, style
    textured = style != "flat"
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

    dressing = None
    if style == "photo":
        dressing = _photo_room(seed, half, height, obstacles, t)
        walls, geoms = dressing["shell"], dressing["obstacles"] + dressing["geoms"]

    # Airframe: tessellated shell for looks, box envelope for collision.
    # Splitting them keeps contacts cheap and exactly matches the measured span.
    if dressing:
        assets = dressing["assets"]
    elif textured and os.path.isdir(TEXDIR):
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

    lights = (f'<light pos="0 0 {height-0.3}" dir="0 0 -1" diffuse="0.7 0.7 0.7" castshadow="true"/>\n'
              f'    <light pos="{-half/2} {-half/2} {height-0.3}" dir="0 0 -1" diffuse="0.35 0.35 0.35"/>\n'
              f'    <light pos="{half/2} {half/2} {height-0.3}" dir="0 0 -1" diffuse="0.35 0.35 0.35"/>')

    xml = f"""<mujoco model="room_seed{seed}">
  <compiler meshdir="{MESHDIR}" texturedir="{TEXDIR}" inertiafromgeom="auto"/>
  <option gravity="0 0 0" timestep="0.004" integrator="RK4"/>
  <visual>
    <global offwidth="{cam_w}" offheight="{cam_h}"/>
    {dressing["headlight"] if dressing else '<headlight ambient="0.45 0.45 0.45" diffuse="0.5 0.5 0.5"/>'}
    <quality shadowsize="2048"/>
  </visual>
  <asset>
    {mesh_asset}
    {assets}
    <material name="body" rgba="0.42 0.48 0.58 1" specular="0.7" shininess="0.6"/>
  </asset>
  <worldbody>
    {dressing["lights"] if dressing else lights}
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
                mesh=have_mesh, style=style, theme=dressing["theme"] if dressing else None)
    return xml, meta
