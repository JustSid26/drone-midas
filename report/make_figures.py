"""Figures for the Unit 1 and 2 report. Black and white only."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"],
                     "font.size": 9, "text.color": "black",
                     "axes.edgecolor": "black", "axes.labelcolor": "black",
                     "xtick.color": "black", "ytick.color": "black"})

def box(ax, x, y, w, h, text, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                linewidth=1.0, edgecolor="black", facecolor="white",
                                linestyle="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.2, wrap=True)

def arrow(ax, p, q, style="-|>", dashed=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=11,
                                 linewidth=0.9, color="black",
                                 linestyle="--" if dashed else "-",
                                 connectionstyle=f"arc3,rad={rad}"))

# Figure 1 - project life cycle with feedback loops
fig, ax = plt.subplots(figsize=(6.0, 5.2))
stages = ["Problem scoping and\nstakeholder analysis", "Requirements and\nfeasibility study",
          "Simulation environment\nand course generation", "Data acquisition\nand exploration",
          "Depth model integration\n(MiDaS)", "Avoidance policy and\nsafety layer",
          "Evaluation and\nablation study", "Deployment profiling\nand monitoring"]
L, W, H = 0.30, 0.40, 0.085
ys = [0.88 - i * 0.118 for i in range(8)]
for s_, y in zip(stages, ys):
    box(ax, L, y, W, H, s_)
for y1, y2 in zip(ys[:-1], ys[1:]):
    arrow(ax, (L + W / 2, y1), (L + W / 2, y2 + H))

def loop(ax, x_out, y_from, y_to, side, label):
    """Route a feedback path out to the side, along, and back in."""
    x_edge = L + W if side == "right" else L
    ax.plot([x_edge, x_out], [y_from, y_from], color="black", lw=0.9, ls="--")
    ax.plot([x_out, x_out], [y_from, y_to], color="black", lw=0.9, ls="--")
    arrow(ax, (x_out, y_to), (x_edge, y_to), dashed=True)
    ax.text(x_out + (0.015 if side == "right" else -0.015), (y_from + y_to) / 2,
            label, fontsize=7.4, ha="left" if side == "right" else "right",
            va="center", linespacing=1.4)

loop(ax, 0.78, ys[6] + H / 2, ys[3] + H / 2, "right",
     "evaluation below target\nreturns work to the data\nand the model")
loop(ax, 0.20, ys[7] + H / 2, ys[1] + H / 2, "left",
     "scene drift or a new\nrequirement reopens\nscoping")
ax.set_xlim(0.02, 0.99); ax.set_ylim(0.01, 0.99); ax.axis("off")
fig.tight_layout(); fig.savefig("figures/fig1_lifecycle.png", dpi=220); plt.close(fig)

# Figure 2 - system architecture from sensing to actuation
fig, ax = plt.subplots(figsize=(6.0, 5.4))
chain = ["Monocular RGB camera\non the airframe",
         "Raspberry Pi 5\ncaptures and streams the frame",
         "Laptop\nMiDaS estimates a depth map",
         "Laptop\navoidance policy selects a heading",
         "Raspberry Pi 5\nrelays the command over serial",
         "Pixhawk 6C running PX4\nholds attitude and flight mode",
         "ESCs, motors, tilt servos\nand control surfaces"]
L, W, H = 0.26, 0.44, 0.084
ys = [0.88 - i * 0.132 for i in range(len(chain))]
for t, y in zip(chain, ys):
    box(ax, L, y, W, H, t)
links = ["", "Wi-Fi", "", "Wi-Fi", "UART serial", ""]
for i, (y1, y2) in enumerate(zip(ys[:-1], ys[1:])):
    arrow(ax, (L + W / 2, y1), (L + W / 2, y2 + H))
    if links[i]:
        ax.text(L - 0.012, (y1 + y2 + H) / 2, links[i], fontsize=7.0,
                ha="right", va="center")
# the learned stage
ax.plot([L, 0.175], [ys[2] + H / 2, ys[2] + H / 2], color="black", lw=0.9, ls="--")
ax.text(0.165, ys[2] + H / 2, "the only learned\ncomponent in the\nwhole system",
        fontsize=7.4, ha="right", va="center", linespacing=1.4)
# the safety layer overrides the policy
box(ax, 0.745, ys[4] - 0.012, 0.245, H + 0.024, "Safety stop layer\noverrides the policy\nwith no learning", dashed=True)
ax.plot([0.745, 0.715], [ys[4] + H / 2, ys[4] + H / 2], color="black", lw=0.9, ls="--")
arrow(ax, (0.715, ys[4] + H / 2), (L + W, ys[4] + H / 2), dashed=True)
ax.set_xlim(0.0, 1.0); ax.set_ylim(0.03, 0.99); ax.axis("off")
fig.tight_layout(); fig.savefig("figures/fig2_architecture.png", dpi=220); plt.close(fig)

# Figure 3 - data lineage
fig, ax = plt.subplots(figsize=(6.3, 3.4))
chain = ["Data source\nsimulator seed,\nNYU, KITTI", "Raw data\nRGB frames and\nground truth depth",
         "Cleaning and\nvalidation\nrange and NaN checks", "Transformation\nresize, normalise,\nscale and shift align",
         "Feature creation\nper column free\ndepth profile", "Final dataset\nversioned with\nmanifest and seed"]
for i, t in enumerate(chain):
    y = 0.80 - i * 0.145
    box(ax, 0.20, y, 0.46, 0.105, t)
    if i:
        arrow(ax, (0.43, y + 0.145), (0.43, y + 0.105))
ax.text(0.755, 0.50, "every step records\nthe seed, the tool\nversion and the\ninput checksum",
        fontsize=7.6, ha="center", va="center")
arrow(ax, (0.66, 0.55), (0.70, 0.52), dashed=True)
ax.set_xlim(0, 1); ax.set_ylim(-0.03, 1); ax.axis("off")
fig.tight_layout(); fig.savefig("figures/fig3_lineage.png", dpi=220); plt.close(fig)

# Figure 5 - measured results
fig, ax = plt.subplots(figsize=(5.6, 3.5))
obs = [4, 6, 9]
completed = [47 / 50 * 100, 38 / 50 * 100, 28 / 50 * 100]
clean = [41 / 50 * 100, 33 / 50 * 100, 22 / 50 * 100]
w = 0.34
xs = range(len(obs))
ax.bar([x - w / 2 for x in xs], completed, w, color="0.75", edgecolor="black",
       linewidth=0.8, label="Route completed")
ax.bar([x + w / 2 for x in xs], clean, w, color="0.35", edgecolor="black",
       linewidth=0.8, label="Completed with no contact")
ax.axhline(90, color="black", linestyle="--", linewidth=0.9)
ax.text(2.28, 91.5, "target", fontsize=7.6, ha="right")
ax.set_xticks(list(xs)); ax.set_xticklabels([str(o) for o in obs])
ax.set_xlabel("Obstacles in a 10 metre room")
ax.set_ylabel("Percentage of 50 held-out courses")
ax.set_ylim(0, 105)
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig("figures/fig5_results.png", dpi=220); plt.close(fig)
print("figures written")
