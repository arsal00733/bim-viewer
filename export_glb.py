"""
Kakkathode Bridge — Direct GLB Export (Option B)
Bypasses Revit + Enscape entirely.
Uses trimesh to build geometry and export colored GLB.

Usage:  py export_glb.py
Output: bim-viewer/bridge_model.glb
"""

import numpy as np
import trimesh
import os

MATERIALS = {
    "concrete_a":  (205, 198, 182, 255),  # Warm off-white / light beige concrete
    "concrete_b":  (190, 183, 168, 255),  # Slightly darker warm beige concrete
    "pcc":         (130, 127, 120, 255),  # Plain cement concrete (grey)
    "footing":     (175, 170, 158, 255),  # Structural footing concrete
    "bedblock":    (200, 195, 180, 255),  # Light concrete for bed blocks
    "deck":        (155, 153, 148, 255),  # Muted grey weathered deck surface
    "earth":       (139,  90,  43, 255),  # Brown earth fill
    "steel":       ( 85,  88,  92, 255),  # Muted grey steel
    "asphalt":     ( 45,  45,  48, 255),  # Dark asphalt road
    "handrail":    (210, 210, 207, 255),  # White / light grey railing
    "misc":        (150, 148, 142, 200),  # Neutral grey misc
}

# ═══════════════════════════════════════════════════════════════
#  Geometry helper — axis-aligned box as trimesh
# ═══════════════════════════════════════════════════════════════
def make_box(x0, x1, y0, y1, z0, z1):
    """Create a trimesh box from min/max coords."""
    dx, dy, dz = abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)
    if dx < 1e-6 or dy < 1e-6 or dz < 1e-6:
        return None
    cx, cy, cz = (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0
    b = trimesh.creation.box(extents=[dx, dy, dz])
    b.apply_translation([cx, cy, cz])
    return b

def make_cylinder(p1, p2, radius, sections=8):
    """Create a trimesh cylinder between two points."""
    p1, p2 = np.array(p1), np.array(p2)
    diff = p2 - p1
    height = np.linalg.norm(diff)
    if height < 1e-6 or radius < 1e-6:
        return None
    c = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    # Align cylinder axis (default Z) to the direction vector
    direction = diff / height
    z_axis = np.array([0, 0, 1.0])
    cross = np.cross(z_axis, direction)
    dot = np.dot(z_axis, direction)
    if np.linalg.norm(cross) < 1e-8:
        if dot < 0:
            rot = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
            c.apply_transform(rot)
    else:
        angle = np.arccos(np.clip(dot, -1, 1))
        rot = trimesh.transformations.rotation_matrix(angle, cross)
        c.apply_transform(rot)
    center = (p1 + p2) / 2.0
    c.apply_translation(center)
    return c

def make_colored_box(x0, x1, y0, y1, z0, z1, rgba):
    box_mesh = make_box(x0, x1, y0, y1, z0, z1)
    if box_mesh is not None and len(box_mesh.faces) > 0:
        vc = np.tile(np.array(rgba, dtype=np.uint8), (len(box_mesh.vertices), 1))
        box_mesh.visual = trimesh.visual.ColorVisuals(mesh=box_mesh, vertex_colors=vc)
    return box_mesh

def make_colored_cylinder(p1, p2, radius, rgba, sections=8):
    cyl_mesh = make_cylinder(p1, p2, radius, sections)
    if cyl_mesh is not None and len(cyl_mesh.faces) > 0:
        vc = np.tile(np.array(rgba, dtype=np.uint8), (len(cyl_mesh.vertices), 1))
        cyl_mesh.visual = trimesh.visual.ColorVisuals(mesh=cyl_mesh, vertex_colors=vc)
    return cyl_mesh


# ═══════════════════════════════════════════════════════════════
#  Bridge parameters (from DPR)
# ═══════════════════════════════════════════════════════════════
SPAN = 10.0;  WIDTH = 7.0
PCC_X = 7.6;  PCC_Y = 6.3;  PCC_Z = 0.15
AF_X = 7.3;   AF_Y = 2.8;   AF_Z = 1.0
WF_Y = 5.0;   WF_X = 2.8;   WF_Z = 1.0
ABUT_H = 5.7; ABUT_TB = 2.5; ABUT_TT = 1.0
WING_H = 6.74; WING_LB = 5.0; WING_LT = 5.0
WING_TB = 0.6; WING_TT = 0.4
BB_X = 7.0;   BB_Y = 1.0;   BB_Z = 0.3
DECK_SPAN = 11.4; DECK_WT = 7.0; DECK_WB = 6.0; DECK_Z = 0.74
WC_Z = 0.075
HP_S = 0.2;   HP_H = 1.0;   N_POSTS = 15
HR_T = 0.1;   HR_H = 0.075
NB_L = 4.0;   NB_H = 1.08;  NB_T = 0.2
BR_S = 0.3;   BR_Z = 0.05
EXP_GAP = 0.040
DR_R = 0.0375
GS_S = 0.2;   GS_H = 1.0;   N_GS = 56
PIPE_R = 0.45; PIPE_WALL = 0.075; PIPE_L = 10.0

z_ftg = 0.0
z_abut = z_ftg + ABUT_H   # 5.7
z_bb = z_abut + BB_Z       # 6.0
z_deck = z_bb + BR_Z + DECK_Z  # 6.79
ovhg = (DECK_SPAN - SPAN) / 2.0  # 0.7


def abut_y(side):
    if side == 'L':
        return 0.0, -ABUT_TB, -ABUT_TT
    else:
        return SPAN, SPAN + ABUT_TB, SPAN + ABUT_TT


# ═══════════════════════════════════════════════════════════════
#  Build geometry groups (component-specific)
# ═══════════════════════════════════════════════════════════════

pcc_l_meshes = []
pcc_r_meshes = []
footing_l_meshes = []
footing_r_meshes = []
abutment_l_meshes = []
abutment_r_meshes = []
wingwall_l_meshes = []
wingwall_r_meshes = []
bedblock_l_meshes = []
bedblock_r_meshes = []
bearings_s_meshes = []
bearings_n_meshes = []
deck_meshes = []
backwall_l_meshes = []
backwall_r_meshes = []
asphalt_meshes = []
approach_slab_s_meshes = []
approach_slab_n_meshes = []
handrail_l_meshes = []
handrail_r_meshes = []
nameboard_meshes = []
drainage_s_meshes = []
drainage_n_meshes = []
earth_s_meshes = []
earth_n_meshes = []
protection_wall_s_meshes = []
protection_wall_n_meshes = []
guard_stone_s_meshes = []
guard_stone_n_meshes = []
rcc_pipe_meshes = []
retaining_wall_l_south_meshes = []
retaining_wall_l_north_meshes = []
retaining_wall_r_south_meshes = []
retaining_wall_r_north_meshes = []
expansion_joint_s_meshes = []
expansion_joint_n_meshes = []


def add(lst, m):
    if m is not None:
        lst.append(m)


# 1. PCC
print("Building PCC...")
dx_pcc = (PCC_X - WIDTH) / 2.0
z0_pcc = -AF_Z - PCC_Z
z1_pcc = -AF_Z
for side in ['L', 'R']:
    inn, bkb, _ = abut_y(side)
    cy = (inn + bkb) / 2.0
    target_lst = pcc_l_meshes if side == 'L' else pcc_r_meshes
    add(target_lst, make_colored_box(-dx_pcc, WIDTH + dx_pcc,
        cy - PCC_Y / 2, cy + PCC_Y / 2, z0_pcc, z1_pcc, MATERIALS["pcc"]))

# 2. Footings
print("Building footings...")
dx_a = (AF_X - WIDTH) / 2.0
for side in ['L', 'R']:
    inn, bkb, _ = abut_y(side)
    cy = (inn + bkb) / 2.0
    target_lst = footing_l_meshes if side == 'L' else footing_r_meshes
    add(target_lst, make_colored_box(-dx_a, WIDTH + dx_a,
        cy - AF_Y / 2, cy + AF_Y / 2, -AF_Z, 0.0, MATERIALS["footing"]))
    if side == 'L':
        wy0, wy1 = inn - WF_Y - 0.15, inn + 0.15
    else:
        wy0, wy1 = inn - 0.15, inn + WF_Y + 0.15
    add(target_lst, make_colored_box(-WING_TB - 0.15, 0.15, wy0, wy1, -AF_Z, 0.0, MATERIALS["footing"]))
    add(target_lst, make_colored_box(WIDTH - 0.15, WIDTH + WING_TB + 0.15, wy0, wy1, -AF_Z, 0.0, MATERIALS["footing"]))

# 3. Abutments
print("Building abutments...")
N = 12
for side in ['L', 'R']:
    inn, bkb, bkt = abut_y(side)
    target_lst = abutment_l_meshes if side == 'L' else abutment_r_meshes
    for i in range(N):
        t0 = i / float(N)
        t1 = (i + 1) / float(N)
        zi0 = z_ftg + t0 * ABUT_H
        zi1 = z_ftg + t1 * ABUT_H
        yb0 = bkb + t0 * (bkt - bkb)
        yb1 = bkb + t1 * (bkt - bkb)
        y_lo = min(inn, min(yb0, yb1))
        y_hi = max(inn, max(yb0, yb1))
        dx = (7.3 - WIDTH) / 2.0
        # Alternate layer colors to create clear horizontal banding
        col = MATERIALS["concrete_a"] if i % 2 == 0 else MATERIALS["concrete_b"]
        add(target_lst, make_colored_box(-dx, WIDTH + dx, y_lo, y_hi, zi0, zi1, col))

# 4. Wing walls
print("Building wing walls...")
for side in ['L', 'R']:
    inn, _, _ = abut_y(side)
    if side == 'L':
        wy0, wy1 = inn - WING_LB, inn
    else:
        wy0, wy1 = inn, inn + WING_LB
    target_lst = wingwall_l_meshes if side == 'L' else wingwall_r_meshes
    for i in range(N):
        t0 = i / float(N)
        t1 = (i + 1) / float(N)
        zi0 = z_ftg + t0 * WING_H
        zi1 = z_ftg + t1 * WING_H
        t_max = WING_TB + max(t0, t1) * (WING_TT - WING_TB)
        col = MATERIALS["concrete_a"] if i % 2 == 0 else MATERIALS["concrete_b"]
        add(target_lst, make_colored_box(-t_max, 0, wy0, wy1, zi0, zi1, col))
        add(target_lst, make_colored_box(WIDTH, WIDTH + t_max, wy0, wy1, zi0, zi1, col))

# 5. Bed blocks
print("Building bed blocks...")
add(bedblock_l_meshes, make_colored_box(0, BB_X, -BB_Y, 0, z_abut, z_bb, MATERIALS["bedblock"]))
add(bedblock_r_meshes, make_colored_box(0, BB_X, SPAN, SPAN + BB_Y, z_abut, z_bb, MATERIALS["bedblock"]))

# 6. Bearings
print("Building bearings...")
positions_x = [1.5, 3.5, 5.5]
for yc in [-ovhg / 2.0, SPAN + ovhg / 2.0]:
    target_lst = bearings_s_meshes if yc < 0 else bearings_n_meshes
    for xc in positions_x:
        add(target_lst, make_colored_box(xc - BR_S / 2, xc + BR_S / 2,
            yc - BR_S / 2, yc + BR_S / 2, z_bb, z_bb + BR_Z, MATERIALS["steel"]))

# 7. Deck slab
print("Building deck...")
add(deck_meshes, make_colored_box(0, WIDTH, -ovhg, SPAN + ovhg, z_bb + BR_Z, z_deck, MATERIALS["deck"]))

# 8. Backwalls
print("Building backwalls...")
add(backwall_l_meshes, make_colored_box(0, WIDTH, -ABUT_TT, -ovhg - EXP_GAP, z_bb, z_deck, MATERIALS["concrete_a"]))
add(backwall_r_meshes, make_colored_box(0, WIDTH, SPAN + ovhg + EXP_GAP, SPAN + ABUT_TT, z_bb, z_deck, MATERIALS["concrete_a"]))

# 9. Wearing coat (asphalt)
print("Building wearing coat...")
dx_wc = (WIDTH - 6.0) / 2.0
add(asphalt_meshes, make_colored_box(dx_wc, WIDTH - dx_wc, -ovhg, SPAN + ovhg, z_deck, z_deck + WC_Z, MATERIALS["asphalt"]))

# 9b. Approach slabs
print("Building approach slabs...")
add(approach_slab_s_meshes, make_colored_box(0, WIDTH, -ovhg - EXP_GAP - 3.5, -ovhg - EXP_GAP, z_deck - 0.2, z_deck, MATERIALS["concrete_a"]))
add(approach_slab_n_meshes, make_colored_box(0, WIDTH, SPAN + ovhg + EXP_GAP, SPAN + ovhg + EXP_GAP + 3.5, z_deck - 0.2, z_deck, MATERIALS["concrete_a"]))

# 10. Handrails
print("Building handrails...")
y_start = -ovhg + 0.3
y_end = SPAN + ovhg - 0.3
spacing = (y_end - y_start) / (N_POSTS - 1)
for i in range(N_POSTS):
    y = y_start + i * spacing
    add(handrail_l_meshes, make_colored_box(0, HP_S, y - HP_S / 2, y + HP_S / 2, z_deck, z_deck + HP_H, MATERIALS["handrail"]))
    add(handrail_r_meshes, make_colored_box(WIDTH - HP_S, WIDTH, y - HP_S / 2, y + HP_S / 2, z_deck, z_deck + HP_H, MATERIALS["handrail"]))
for rz in [0.4, 0.8]:
    for i in range(N_POSTS - 1):
        y0r = y_start + i * spacing + HP_S / 2
        y1r = y_start + (i + 1) * spacing - HP_S / 2
        if y1r - y0r <= 0:
            continue
        add(handrail_l_meshes, make_colored_box(0, HR_T, y0r, y1r, z_deck + rz, z_deck + rz + HR_H, MATERIALS["handrail"]))
        add(handrail_r_meshes, make_colored_box(WIDTH - HR_T, WIDTH, y0r, y1r, z_deck + rz, z_deck + rz + HR_H, MATERIALS["handrail"]))

# 11. Name board
print("Building name board...")
yc_nb = SPAN / 2.0
add(nameboard_meshes, make_colored_box(-NB_T, 0, yc_nb - NB_L / 2, yc_nb + NB_L / 2, z_deck, z_deck + NB_H, MATERIALS["bedblock"]))

# 12. Drainage (small cylinders as misc)
print("Building drainage...")
n_x_dr = 5; n_z_dr = 3
xs_dr = [WIDTH * (i + 1) / (n_x_dr + 1) for i in range(n_x_dr)]
zs_dr = [z_ftg + ABUT_H * (i + 1) / (n_z_dr + 1) for i in range(n_z_dr)]
for x in xs_dr:
    for z in zs_dr:
        add(drainage_s_meshes, make_colored_cylinder([x, -ABUT_TB - 0.05, z], [x, 0.05, z], DR_R, MATERIALS["misc"]))
        add(drainage_n_meshes, make_colored_cylinder([x, SPAN - 0.05, z], [x, SPAN + ABUT_TB + 0.05, z], DR_R, MATERIALS["misc"]))

# 13. Earth fill
print("Building earth fill...")
z_earth_top = 6.74
segments = [
    (-19.0, -12.0), (-12.0, -5.0), (-5.0, -ABUT_TB),
    (SPAN + ABUT_TB, 15.0), (15.0, 21.0), (21.0, 29.0),
    (29.0, 39.0), (39.0, 53.0)
]
for (y0, y1) in segments:
    target_lst = earth_s_meshes if y1 <= 0 else earth_n_meshes
    add(target_lst, make_colored_box(0, WIDTH, y0, y1, z_ftg, z_earth_top, MATERIALS["earth"]))

# 14. Protection walls
print("Building protection walls...")
z_f_bottom = -AF_Z - PCC_Z
z_pw_base = z_f_bottom + 0.15
z_pw_top = z_pw_base + 2.5
wt_b_pw, wt_t_pw = 1.0, 0.4
f_w = 1.2
N_pw = 8

def build_pw(x0, x1, y_inner, y_dir):
    for i in range(N_pw):
        t0 = i / float(N_pw); t1 = (i + 1) / float(N_pw)
        zi0 = z_pw_base + t0 * (z_pw_top - z_pw_base)
        zi1 = z_pw_base + t1 * (z_pw_top - z_pw_base)
        tb0 = wt_b_pw + t0 * (wt_t_pw - wt_b_pw)
        tb1 = wt_b_pw + t1 * (wt_t_pw - wt_b_pw)
        t_max = max(tb0, tb1)
        col = MATERIALS["concrete_a"] if i % 2 == 0 else MATERIALS["concrete_b"]
        target_lst = protection_wall_s_meshes if y_dir == -1 else protection_wall_n_meshes
        if y_dir == -1:
            add(target_lst, make_colored_box(x0, x1, y_inner - t_max, y_inner, zi0, zi1, col))
        else:
            add(target_lst, make_colored_box(x0, x1, y_inner, y_inner + t_max, zi0, zi1, col))
    if y_dir == -1:
        add(footing_l_meshes, make_colored_box(x0, x1, y_inner - f_w, y_inner, z_f_bottom, z_pw_base, MATERIALS["footing"]))
    else:
        add(footing_r_meshes, make_colored_box(x0, x1, y_inner, y_inner + f_w, z_f_bottom, z_pw_base, MATERIALS["footing"]))

xl_dn = -WING_TB - 10.0; xl_up = -WING_TB
xr_up = WIDTH + WING_TB; xr_dn = WIDTH + WING_TB + 10.0
build_pw(xl_dn, xl_up, 0, -1); build_pw(xr_up, xr_dn, 0, -1)
build_pw(xl_dn, xl_up, SPAN, 1); build_pw(xr_up, xr_dn, SPAN, 1)

# 15. Guard stones
print("Building guard stones...")
gs_per_side = N_GS // 4
total_app = 20.0
gs_sp = total_app / gs_per_side
rw_top_z = 2.74 + 4.0
for i in range(gs_per_side):
    y = -ovhg - 1.0 - i * gs_sp
    if y >= -19.0:
        add(guard_stone_s_meshes, make_colored_box(-0.5, -0.5 + GS_S, y, y + GS_S, rw_top_z, rw_top_z + GS_H, MATERIALS["bedblock"]))
        add(guard_stone_s_meshes, make_colored_box(WIDTH + 0.5 - GS_S, WIDTH + 0.5, y, y + GS_S, rw_top_z, rw_top_z + GS_H, MATERIALS["bedblock"]))
    y2 = SPAN + ovhg + 1.0 + i * gs_sp
    if y2 <= 53.0:
        add(guard_stone_n_meshes, make_colored_box(-0.5, -0.5 + GS_S, y2, y2 + GS_S, rw_top_z, rw_top_z + GS_H, MATERIALS["bedblock"]))
        add(guard_stone_n_meshes, make_colored_box(WIDTH + 0.5 - GS_S, WIDTH + 0.5, y2, y2 + GS_S, rw_top_z, rw_top_z + GS_H, MATERIALS["bedblock"]))

# 16. RCC Pipe
print("Building RCC pipe...")
yc_pipe = SPAN / 2.0; zc_pipe = -AF_Z - 1.5
add(rcc_pipe_meshes, make_colored_cylinder([-PIPE_L / 2, yc_pipe, zc_pipe],
    [PIPE_L / 2, yc_pipe, zc_pipe], PIPE_R, MATERIALS["footing"], sections=16))

# 17. Retaining walls
print("Building retaining walls...")
def add_rw_seg(side, y0, y1, wall_h, wt_b, wt_t, footings):
    z_base = 2.74; z_top = z_base + wall_h; N_rw = 8
    if y0 < 0:
        target_lst = retaining_wall_l_south_meshes if side == 'L' else retaining_wall_r_south_meshes
    else:
        target_lst = retaining_wall_l_north_meshes if side == 'L' else retaining_wall_r_north_meshes
    for i in range(N_rw):
        t0 = i / float(N_rw); t1 = (i + 1) / float(N_rw)
        zi0 = z_base + t0 * (z_top - z_base)
        zi1 = z_base + t1 * (z_top - z_base)
        tb = wt_b + max(t0, t1) * (wt_t - wt_b)
        col = MATERIALS["concrete_a"] if i % 2 == 0 else MATERIALS["concrete_b"]
        if side == 'L':
            add(target_lst, make_colored_box(-tb, 0, y0, y1, zi0, zi1, col))
        else:
            add(target_lst, make_colored_box(WIDTH, WIDTH + tb, y0, y1, zi0, zi1, col))
    current_z = z_base
    for idx, (w, d) in enumerate(footings):
        z_f = current_z - d
        if side == 'L': cx = -wt_b / 2.0
        else: cx = WIDTH + wt_b / 2.0
        col = MATERIALS["footing"] if idx % 2 == 0 else MATERIALS["pcc"]
        footing_lst = footing_l_meshes if side == 'L' else footing_r_meshes
        pcc_lst = pcc_l_meshes if side == 'L' else pcc_r_meshes
        add(footing_lst if idx % 2 == 0 else pcc_lst, make_colored_box(cx - w / 2, cx + w / 2, y0, y1, z_f, current_z, col))
        current_z = z_f

for s in ['L', 'R']:
    add_rw_seg(s, -12.0, -5.0, 4.0, 1.6, 0.4,
               [(1.9, 0.9), (2.2, 0.9), (2.5, 0.9), (2.7, 0.3), (2.7, 0.15)])
    add_rw_seg(s, -19.0, -12.0, 4.0, 1.0, 0.4, [(1.2, 0.3), (1.2, 0.15)])
for s in ['L', 'R']:
    add_rw_seg(s, 15.0, 21.0, 4.0, 1.6, 0.4,
               [(1.9, 0.9), (2.2, 0.9), (2.5, 0.9), (2.7, 0.3), (2.7, 0.15)])
add_rw_seg('L', 21.0, 29.0, 4.0, 1.2, 0.4, [(1.7, 0.3), (1.4, 1.15), (1.4, 0.15)])
add_rw_seg('R', 21.0, 29.0, 4.0, 1.1, 0.4, [(1.3, 0.3), (1.3, 0.15)])
add_rw_seg('L', 29.0, 39.0, 4.0, 1.1, 0.4, [(1.3, 0.3), (1.3, 0.15)])
add_rw_seg('R', 29.0, 39.0, 4.0, 1.025, 0.4, [(1.125, 0.3), (1.125, 0.15)])
add_rw_seg('L', 39.0, 53.0, 4.0, 1.05, 0.4, [(1.25, 0.3), (1.25, 0.15)])
add_rw_seg('R', 39.0, 53.0, 4.0, 1.0, 0.4, [(0.95, 0.3), (0.95, 0.15)])

# 18. Expansion joints
print("Building expansion joints...")
g = EXP_GAP; groove = 0.02
add(expansion_joint_s_meshes, make_colored_box(0, WIDTH, -g / 2, g / 2, z_deck - groove, z_deck + WC_Z, MATERIALS["misc"]))
add(expansion_joint_n_meshes, make_colored_box(0, WIDTH, SPAN - g / 2, SPAN + g / 2, z_deck - groove, z_deck + WC_Z, MATERIALS["misc"]))


# ═══════════════════════════════════════════════════════════════
#  Merge each group and export as GLB
# ═══════════════════════════════════════════════════════════════
print("\nMerging geometry groups...")

groups = [
    (pcc_l_meshes,            "PCC_Left"),
    (pcc_r_meshes,            "PCC_Right"),
    (footing_l_meshes,        "Footings_Left"),
    (footing_r_meshes,        "Footings_Right"),
    (abutment_l_meshes,       "Abutment_Left"),
    (abutment_r_meshes,       "Abutment_Right"),
    (wingwall_l_meshes,       "WingWalls_Left"),
    (wingwall_r_meshes,       "WingWalls_Right"),
    (bedblock_l_meshes,       "BedBlocks_Left"),
    (bedblock_r_meshes,       "BedBlocks_Right"),
    (bearings_s_meshes,       "Bearings_South"),
    (bearings_n_meshes,       "Bearings_North"),
    (deck_meshes,             "DeckSlab"),
    (backwall_l_meshes,       "Backwalls_Left"),
    (backwall_r_meshes,       "Backwalls_Right"),
    (asphalt_meshes,          "AsphaltWC"),
    (approach_slab_s_meshes,  "ApproachSlabs_South"),
    (approach_slab_n_meshes,  "ApproachSlabs_North"),
    (handrail_l_meshes,       "Handrails_Left"),
    (handrail_r_meshes,       "Handrails_Right"),
    (nameboard_meshes,        "NameBoard"),
    (drainage_s_meshes,       "Drainage_South"),
    (drainage_n_meshes,       "Drainage_North"),
    (earth_s_meshes,          "EarthFill_South"),
    (earth_n_meshes,          "EarthFill_North"),
    (protection_wall_s_meshes,"ProtectionWalls_South"),
    (protection_wall_n_meshes,"ProtectionWalls_North"),
    (guard_stone_s_meshes,    "GuardStones_South"),
    (guard_stone_n_meshes,    "GuardStones_North"),
    (rcc_pipe_meshes,         "RCC_Pipe"),
    (retaining_wall_l_south_meshes, "RetainingWalls_Left_South"),
    (retaining_wall_l_north_meshes, "RetainingWalls_Left_North"),
    (retaining_wall_r_south_meshes, "RetainingWalls_Right_South"),
    (retaining_wall_r_north_meshes, "RetainingWalls_Right_North"),
    (expansion_joint_s_meshes,"ExpansionJoints_South"),
    (expansion_joint_n_meshes,"ExpansionJoints_North"),
]

# Z-up → Y-up rotation (-90° around X axis)
z_to_y_up = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])

scene = trimesh.Scene()
stats = []
for meshes, name in groups:
    valid = [m for m in meshes if m is not None and len(m.faces) > 0]
    if valid:
        merged = trimesh.util.concatenate(valid)
        merged.apply_transform(z_to_y_up)
        # PBR parameters per component type
        if any(kw in name for kw in ['Steel', 'Bearings', 'Handrail']):
            rough, metal = 0.35, 0.85
        elif any(kw in name for kw in ['Asphalt', 'WC']):
            rough, metal = 0.95, 0.0
        elif any(kw in name for kw in ['Earth']):
            rough, metal = 1.0, 0.0
        elif any(kw in name for kw in ['Deck', 'Slab']):
            rough, metal = 0.85, 0.0
        elif any(kw in name for kw in ['Pipe', 'Drainage']):
            rough, metal = 0.5, 0.6
        else:
            rough, metal = 0.9, 0.0   # default concrete
        merged.visual.material = trimesh.visual.material.PBRMaterial(
            name=name,
            baseColorFactor=[255, 255, 255, 255],
            roughnessFactor=rough,
            metallicFactor=metal
        )
        scene.add_geometry(merged, node_name=name)
        stats.append(f"  {name}: {len(merged.vertices):,} verts, {len(merged.faces):,} faces")

print("Scene contents:")
for s in stats:
    print(s)

# Export
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bim-viewer")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "bridge_model_v2.glb")

scene.export(out_path, file_type="glb")
file_size = os.path.getsize(out_path) / (1024 * 1024)
print(f"\n[OK] GLB exported: {out_path}")
print(f"   File size: {file_size:.2f} MB")
print(f"\nDone! Run py export_glb.py again to generate model.")
