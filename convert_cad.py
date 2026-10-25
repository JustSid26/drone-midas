"""Convert the team's STEP parts into meshes MuJoCo can load.

    python convert_cad.py <dir-containing-step-files> [--out meshes]

Writes one STL per part and prints the measured envelope of each, which is
how the 1.00 m wingspan figure driving the course dimensions was obtained.
"""
import argparse, glob, os, sys, tempfile, warnings
warnings.filterwarnings("ignore")
import cascadio, trimesh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="directory tree containing .step files")
    ap.add_argument("--out", default="meshes")
    ap.add_argument("--tol", type=float, default=0.5, help="tessellation tolerance")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(args.src, "**", "*.step"), recursive=True))
    if not files:
        sys.exit(f"no .step files under {args.src}")

    seen, rows = set(), []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        if name in seen:
            continue
        seen.add(name)
        glb = tempfile.mktemp(suffix=".glb")
        try:
            cascadio.step_to_glb(f, glb, tol_linear=args.tol, tol_angular=args.tol)
            scene = trimesh.load(glb)
            mesh = scene.to_geometry() if hasattr(scene, "to_geometry") else scene
            # Recentre on the planform so the sim body origin sits at the
            # aircraft centre and the nose lands at +x.
            mesh.apply_translation(-mesh.bounds.mean(axis=0))
            mesh.export(os.path.join(args.out, name + ".stl"))
            if "combined_aero" in name:
                mesh.export(os.path.join(args.out, "vtol_shell.stl"))
            rows.append((name, *mesh.extents, len(mesh.faces)))
        except Exception as e:
            rows.append((name, None, None, None, f"FAILED {type(e).__name__}"))

    print(f"{'part':<34}{'L(m)':>7}{'W(m)':>7}{'H(m)':>7}{'tris':>8}")
    for r in rows:
        if r[1] is None:
            print(f"{r[0]:<34}  {r[4]}")
        else:
            print(f"{r[0]:<34}{r[1]:>7.2f}{r[2]:>7.2f}{r[3]:>7.2f}{r[4]:>8}")
    print(f"\nwrote {len([r for r in rows if r[1] is not None])} STL files to {args.out}/")


if __name__ == "__main__":
    main()
