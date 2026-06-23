"""
Kakkathode Bridge — DPR-Accurate Parametric Model
Navakerala Sadas | Thrikkadeeri GP, Palakkad
OEO/KEL/EST/7994/2025 | DSR 2021
"""

import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *
import math

clr.AddReference('DSCoreNodes')
from DSCore import Color
clr.AddReference('GeometryColor')
from Modifiers import GeometryColor

try:
    clr.AddReference('RevitNodes')
    import Revit
    clr.ImportExtensions(Revit.Elements)
    clr.ImportExtensions(Revit.GeometryConversion)
    _has_revit = True
except:
    _has_revit = False

# ═══════════════════════════════════════════════════════════════
#  Geometry helpers
# ═══════════════════════════════════════════════════════════════

def box(x0, x1, y0, y1, z0, z1):
    cx, cy, cz = (x0+x1)/2.0, (y0+y1)/2.0, (z0+z1)/2.0
    cs = CoordinateSystem.ByOrigin(Point.ByCoordinates(cx, cy, cz))
    return Cuboid.ByLengths(cs, abs(x1-x0), abs(y1-y0), abs(z1-z0))

def pt(x, y, z):
    return Point.ByCoordinates(x, y, z)

def cyl(p1, p2, r):
    return Cylinder.ByPointsRadius(p1, p2, r)

def sliced_trapezoid(x0, x1, y_inner, yb_base, yb_top, z0, z1, n=12):
    """Approximate a tapered solid with N stacked box slices."""
    solids = []
    for i in range(n):
        t0 = i / float(n)
        t1 = (i + 1) / float(n)
        zi0 = z0 + t0 * (z1 - z0)
        zi1 = z0 + t1 * (z1 - z0)
        yb0 = yb_base + t0 * (yb_top - yb_base)
        yb1 = yb_base + t1 * (yb_top - yb_base)
        y_lo = min(y_inner, min(yb0, yb1))
        y_hi = max(y_inner, max(yb0, yb1))
        solids.append(box(x0, x1, y_lo, y_hi, zi0, zi1))
    return solids

# ═══════════════════════════════════════════════════════════════
#  Bridge class
# ═══════════════════════════════════════════════════════════════

class KakkathodeBridge:
    SPAN        = 10.0
    WIDTH       = 7.0
    PCC_X       = 7.6
    PCC_Y       = 6.3
    PCC_Z       = 0.15
    AF_X        = 7.3
    AF_Y        = 2.8
    AF_Z        = 1.0
    WF_Y        = 5.0
    WF_X        = 2.8
    WF_Z        = 1.0
    ABUT_H      = 5.7
    ABUT_TB     = 2.5
    ABUT_TT     = 1.0
    WING_H      = 6.74
    WING_LB     = 5.0
    WING_LT     = 5.0
    WING_TB     = 0.6
    WING_TT     = 0.4
    BB_X        = 7.0
    BB_Y        = 1.0
    BB_Z        = 0.3
    DECK_SPAN   = 11.4
    DECK_WT     = 7.0
    DECK_WB     = 6.0
    DECK_Z      = 0.74
    WC_Z        = 0.075
    HP_S        = 0.2
    HP_H        = 1.0
    N_POSTS     = 15
    HR_L        = 1.2
    HR_H        = 0.075
    HR_T        = 0.1
    NB_L        = 4.0
    NB_H        = 1.08
    NB_T        = 0.2
    BR_S        = 0.3
    BR_Z        = 0.05
    EXP_GAP     = 0.040
    DR_R        = 0.0375
    EARTH_VOL   = 691.762
    PW_L        = 10.0
    PW_H        = 2.5
    PW_T        = 0.7
    GS_S        = 0.2
    GS_H        = 1.0
    N_GS        = 56
    PIPE_R      = 0.45
    PIPE_WALL   = 0.075
    PIPE_L      = 10.0
    DW_R        = 0.010
    DW_L        = 1.5
    N_DW        = 70
    RW_L        = 15.0
    RW_H        = 3.0
    RW_T        = 0.45

    def __init__(self):
        self.concrete = []
        self.earth    = []
        self.steel    = []
        self.misc     = []
        self.z_ftg    = 0.0
        self.z_abut   = 0.0
        self.z_bb     = 0.0
        self.z_deck   = 0.0

    def _c(self, s): self.concrete.append(s)
    def _e(self, s): self.earth.append(s)
    def _s(self, s): self.steel.append(s)
    def _m(self, s): self.misc.append(s)

    def _abut_y(self, side):
        if side == 'L':
            inner = 0.0
            return inner, inner - self.ABUT_TB, inner - self.ABUT_TT
        else:
            inner = self.SPAN
            return inner, inner + self.ABUT_TB, inner + self.ABUT_TT

    # ─────────────────── 1. PCC ───────────────────
    def CreatePCC(self):
        dx = (self.PCC_X - self.WIDTH) / 2.0
        z0 = -self.AF_Z - self.PCC_Z
        z1 = -self.AF_Z
        for side in ['L', 'R']:
            inn, bkb, _ = self._abut_y(side)
            cy = (inn + bkb) / 2.0
            y0 = cy - self.PCC_Y / 2.0
            y1 = cy + self.PCC_Y / 2.0
            self._c(box(-dx, self.WIDTH+dx, y0, y1, z0, z1))
        return self

    # ─────────────────── 2. Footings ───────────────────
    def CreateFootings(self):
        z0 = -self.AF_Z
        z1 = 0.0
        self.z_ftg = z1
        dx_a = (self.AF_X - self.WIDTH) / 2.0
        for side in ['L', 'R']:
            inn, bkb, _ = self._abut_y(side)
            cy = (inn + bkb) / 2.0
            self._c(box(-dx_a, self.WIDTH+dx_a,
                        cy - self.AF_Y/2.0, cy + self.AF_Y/2.0, z0, z1))
            if side == 'L':
                wy0 = inn - self.WF_Y - 0.15
                wy1 = inn + 0.15
            else:
                wy0 = inn - 0.15
                wy1 = inn + self.WF_Y + 0.15
            self._c(box(-self.WING_TB - 0.15, 0.15, wy0, wy1, z0, z1))
            self._c(box(self.WIDTH - 0.15, self.WIDTH + self.WING_TB + 0.15, wy0, wy1, z0, z1))
        return self

    # ─────────────────── 3. Abutments (sliced boxes) ───────────────────
    def CreateAbutments(self):
        z0 = self.z_ftg
        z1 = z0 + self.ABUT_H
        self.z_abut = z1
        dx = (7.3 - self.WIDTH) / 2.0
        N = 12
        for side in ['L', 'R']:
            inn, bkb, bkt = self._abut_y(side)
            for i in range(N):
                t0 = i / float(N)
                t1 = (i + 1) / float(N)
                zi0 = z0 + t0 * (z1 - z0)
                zi1 = z0 + t1 * (z1 - z0)
                yb0 = bkb + t0 * (bkt - bkb)
                yb1 = bkb + t1 * (bkt - bkb)
                y_lo = min(inn, min(yb0, yb1))
                y_hi = max(inn, max(yb0, yb1))
                self._c(box(-dx, self.WIDTH + dx, y_lo, y_hi, zi0, zi1))
        return self

    # ─────────────────── 4. Wing walls (sliced boxes) ───────────────────
    def CreateWingWalls(self):
        z0 = self.z_ftg
        z1 = z0 + self.WING_H
        N = 12
        for side in ['L', 'R']:
            inn, _, _ = self._abut_y(side)
            if side == 'L':
                wy0, wy1 = inn - self.WING_LB, inn
            else:
                wy0, wy1 = inn, inn + self.WING_LB
            for i in range(N):
                t0 = i / float(N)
                t1 = (i + 1) / float(N)
                zi0 = z0 + t0 * (z1 - z0)
                zi1 = z0 + t1 * (z1 - z0)
                t_max = self.WING_TB + max(t0, t1) * (self.WING_TT - self.WING_TB)
                self._c(box(-t_max, 0, wy0, wy1, zi0, zi1))
                self._c(box(self.WIDTH, self.WIDTH + t_max, wy0, wy1, zi0, zi1))
        return self

    # ─────────────────── 5. Bed blocks ───────────────────
    def CreateBedBlocks(self):
        z0 = self.z_abut
        z1 = z0 + self.BB_Z
        self.z_bb = z1
        self._c(box(0, self.BB_X, -self.BB_Y, 0, z0, z1))
        self._c(box(0, self.BB_X, self.SPAN, self.SPAN + self.BB_Y, z0, z1))
        return self

    # ─────────────────── 6. Bearings ───────────────────
    def CreateBearings(self):
        z0 = self.z_bb
        z1 = z0 + self.BR_Z
        positions_x = [1.5, 3.5, 5.5]
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        for yc in [-ovhg/2.0, self.SPAN + ovhg/2.0]:
            for xc in positions_x:
                self._c(box(xc-self.BR_S/2, xc+self.BR_S/2,
                            yc-self.BR_S/2, yc+self.BR_S/2, z0, z1))
        return self

    # ─────────────────── 7. Deck slab ───────────────────
    def CreateDeck(self):
        z0 = self.z_bb + self.BR_Z
        z1 = z0 + self.DECK_Z
        self.z_deck = z1
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        y0 = -ovhg
        y1 = self.SPAN + ovhg
        self._c(box(0, self.WIDTH, y0, y1, z0, z1))
        return self

    # ─────────────────── 8. Backwalls ───────────────────
    def CreateBackwalls(self):
        z0 = self.z_bb
        z1 = self.z_deck
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        self._c(box(0, self.WIDTH, -self.ABUT_TT, -ovhg - self.EXP_GAP, z0, z1))
        self._c(box(0, self.WIDTH,
                    self.SPAN + ovhg + self.EXP_GAP, self.SPAN + self.ABUT_TT, z0, z1))
        return self

    # ─────────────────── 9. Wearing coat ───────────────────
    def CreateWearingCoat(self):
        z0 = self.z_deck
        z1 = z0 + self.WC_Z
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        dx = (self.WIDTH - 6.0) / 2.0
        self._c(box(dx, self.WIDTH - dx, -ovhg, self.SPAN+ovhg, z0, z1))
        return self

    # ─────────────────── 9b. Approach slabs ───────────────────
    def CreateApproachSlab(self):
        z1 = self.z_deck
        z0 = z1 - 0.2
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        self._c(box(0, self.WIDTH, -ovhg - self.EXP_GAP - 3.5, -ovhg - self.EXP_GAP, z0, z1))
        self._c(box(0, self.WIDTH, self.SPAN + ovhg + self.EXP_GAP,
                    self.SPAN + ovhg + self.EXP_GAP + 3.5, z0, z1))
        return self

    # ─────────────────── 10. Handrails ───────────────────
    def CreateHandrails(self):
        z0 = self.z_deck
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        y_start = -ovhg + 0.3
        y_end   = self.SPAN + ovhg - 0.3
        spacing = (y_end - y_start) / (self.N_POSTS - 1)
        hs = self.HP_S
        for i in range(self.N_POSTS):
            y = y_start + i * spacing
            self._c(box(0, hs, y-hs/2, y+hs/2, z0, z0+self.HP_H))
            self._c(box(self.WIDTH-hs, self.WIDTH, y-hs/2, y+hs/2, z0, z0+self.HP_H))
        for rz in [0.4, 0.8]:
            for i in range(self.N_POSTS - 1):
                y0r = y_start + i * spacing + hs/2
                y1r = y_start + (i+1) * spacing - hs/2
                if y1r - y0r <= 0:
                    continue
                self._c(box(0, self.HR_T, y0r, y1r, z0+rz, z0+rz+self.HR_H))
                self._c(box(self.WIDTH-self.HR_T, self.WIDTH, y0r, y1r, z0+rz, z0+rz+self.HR_H))
        return self

    # ─────────────────── 11. Name board ───────────────────
    def CreateNameBoard(self):
        z0 = self.z_deck
        yc = self.SPAN / 2.0
        self._c(box(-self.NB_T, 0,
                    yc - self.NB_L/2, yc + self.NB_L/2,
                    z0, z0 + self.NB_H))
        return self

    # ─────────────────── 12. Drainage ───────────────────
    def CreateDrainage(self):
        r = self.DR_R
        n_x = 5
        n_z = 3
        xs = [self.WIDTH * (i+1) / (n_x+1) for i in range(n_x)]
        zs = [self.z_ftg + self.ABUT_H * (i+1) / (n_z+1) for i in range(n_z)]
        for x in xs:
            for z in zs:
                self._m(cyl(pt(x, -self.ABUT_TB-0.05, z), pt(x, 0.05, z), r))
                self._m(cyl(pt(x, self.SPAN-0.05, z),
                            pt(x, self.SPAN+self.ABUT_TB+0.05, z), r))
        return self

    # ─────────────────── 13. Earth fill (box segments) ───────────────────
    def CreateEarthFill(self):
        z_bot = self.z_ftg
        z_top = 6.74
        segments = [
            (-19.0, -12.0), (-12.0, -5.0), (-5.0, -self.ABUT_TB),
            (self.SPAN + self.ABUT_TB, 15.0),
            (15.0, 21.0), (21.0, 29.0), (29.0, 39.0), (39.0, 53.0)
        ]
        for (y0, y1) in segments:
            self._e(box(0, self.WIDTH, y0, y1, z_bot, z_top))
        return self

    # ─────────────────── 14. Protection walls (sliced boxes) ───────────────────
    def CreateProtectionWalls(self):
        z_f_bottom = -self.AF_Z - self.PCC_Z
        z_base = z_f_bottom + 0.15
        z_top  = z_base + 2.5
        wt_b, wt_t = 1.0, 0.4
        f_w = 1.2
        N = 8

        def _pw(x0, x1, y_inner, y_dir):
            for i in range(N):
                t0 = i / float(N)
                t1 = (i + 1) / float(N)
                zi0 = z_base + t0 * (z_top - z_base)
                zi1 = z_base + t1 * (z_top - z_base)
                tb0 = wt_b + t0 * (wt_t - wt_b)
                tb1 = wt_b + t1 * (wt_t - wt_b)
                t_max = max(tb0, tb1)
                if y_dir == -1:
                    self._c(box(x0, x1, y_inner - t_max, y_inner, zi0, zi1))
                else:
                    self._c(box(x0, x1, y_inner, y_inner + t_max, zi0, zi1))
            if y_dir == -1:
                self._c(box(x0, x1, y_inner - f_w, y_inner, z_f_bottom, z_base))
            else:
                self._c(box(x0, x1, y_inner, y_inner + f_w, z_f_bottom, z_base))

        xl_dn = -self.WING_TB - self.PW_L
        xl_up = -self.WING_TB
        xr_up = self.WIDTH + self.WING_TB
        xr_dn = self.WIDTH + self.WING_TB + self.PW_L

        _pw(xl_dn, xl_up, 0, -1)
        _pw(xr_up, xr_dn, 0, -1)
        _pw(xl_dn, xl_up, self.SPAN, 1)
        _pw(xr_up, xr_dn, self.SPAN, 1)
        return self

    # ─────────────────── 15. Guard stones ───────────────────
    def _get_rw_top_z(self, y, side):
        return 2.74 + 4.0

    def CreateGuardStones(self):
        gs_per_side = self.N_GS // 4
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        total_app = 20.0
        sp = total_app / gs_per_side
        for i in range(gs_per_side):
            y = -ovhg - 1.0 - i * sp
            if y >= -19.0:
                z0_l = self._get_rw_top_z(y, 'L')
                z0_r = self._get_rw_top_z(y, 'R')
                self._c(box(-0.5, -0.5+self.GS_S, y, y+self.GS_S, z0_l, z0_l+self.GS_H))
                self._c(box(self.WIDTH+0.5-self.GS_S, self.WIDTH+0.5, y, y+self.GS_S, z0_r, z0_r+self.GS_H))
            y2 = self.SPAN + ovhg + 1.0 + i * sp
            if y2 <= 53.0:
                z0_l = self._get_rw_top_z(y2, 'L')
                z0_r = self._get_rw_top_z(y2, 'R')
                self._c(box(-0.5, -0.5+self.GS_S, y2, y2+self.GS_S, z0_l, z0_l+self.GS_H))
                self._c(box(self.WIDTH+0.5-self.GS_S, self.WIDTH+0.5, y2, y2+self.GS_S, z0_r, z0_r+self.GS_H))
        return self

    # ─────────────────── 16. RCC pipe culvert ───────────────────
    def CreateRCCPipe(self):
        yc = self.SPAN / 2.0
        zc = -self.AF_Z - 1.5
        p1 = pt(-self.PIPE_L/2, yc, zc)
        p2 = pt(self.PIPE_L/2,  yc, zc)
        outer = cyl(p1, p2, self.PIPE_R)
        inner = cyl(p1, p2, self.PIPE_R - self.PIPE_WALL)
        try:
            self._c(outer.Difference(inner))
        except:
            self._c(outer)
        return self

    # ─────────────────── 17. Dowel bars ───────────────────
    def CreateDowelBars(self):
        z_rock = -self.AF_Z - self.PCC_Z
        n_per_ftg = self.N_DW // 4
        if n_per_ftg < 1:
            n_per_ftg = 1
        for side in ['L', 'R']:
            inn, bkb, _ = self._abut_y(side)
            cy = (inn + bkb) / 2.0
            for wing_x in [self.WF_X/4, self.WIDTH - self.WF_X/4]:
                sp = self.AF_Y / (n_per_ftg + 1)
                for i in range(n_per_ftg):
                    yy = cy - self.AF_Y/2 + (i+1)*sp
                    self._s(cyl(pt(wing_x, yy, z_rock),
                                pt(wing_x, yy, z_rock - self.DW_L), self.DW_R))
        return self

    # ─────────────────── 18. Retaining walls (sliced boxes) ───────────────────
    def _add_rw_seg(self, side, y0, y1, wall_h, wt_b, wt_t, footings):
        z_base = 2.74
        z_top  = z_base + wall_h
        N = 8
        for i in range(N):
            t0 = i / float(N)
            t1 = (i + 1) / float(N)
            zi0 = z_base + t0 * (z_top - z_base)
            zi1 = z_base + t1 * (z_top - z_base)
            tb = wt_b + max(t0, t1) * (wt_t - wt_b)
            if side == 'L':
                self._c(box(-tb, 0, y0, y1, zi0, zi1))
            else:
                self._c(box(self.WIDTH, self.WIDTH + tb, y0, y1, zi0, zi1))
        current_z = z_base
        for (w, d) in footings:
            z_f = current_z - d
            if side == 'L':
                cx = -wt_b / 2.0
            else:
                cx = self.WIDTH + wt_b / 2.0
            self._c(box(cx - w/2.0, cx + w/2.0, y0, y1, z_f, current_z))
            current_z = z_f

    def CreateRetainingWalls(self):
        for s in ['L', 'R']:
            self._add_rw_seg(s, -12.0, -5.0,  4.0, 1.6, 0.4,
                             [(1.9, 0.9), (2.2, 0.9), (2.5, 0.9), (2.7, 0.3), (2.7, 0.15)])
            self._add_rw_seg(s, -19.0, -12.0, 4.0, 1.0, 0.4,
                             [(1.2, 0.3), (1.2, 0.15)])
        for s in ['L', 'R']:
            self._add_rw_seg(s, 15.0, 21.0, 4.0, 1.6, 0.4,
                             [(1.9, 0.9), (2.2, 0.9), (2.5, 0.9), (2.7, 0.3), (2.7, 0.15)])
        self._add_rw_seg('L', 21.0, 29.0, 4.0, 1.2, 0.4, [(1.7, 0.3), (1.4, 1.15), (1.4, 0.15)])
        self._add_rw_seg('R', 21.0, 29.0, 4.0, 1.1, 0.4, [(1.3, 0.3), (1.3, 0.15)])
        self._add_rw_seg('L', 29.0, 39.0, 4.0, 1.1, 0.4, [(1.3, 0.3), (1.3, 0.15)])
        self._add_rw_seg('R', 29.0, 39.0, 4.0, 1.025, 0.4, [(1.125, 0.3), (1.125, 0.15)])
        self._add_rw_seg('L', 39.0, 53.0, 4.0, 1.05, 0.4, [(1.25, 0.3), (1.25, 0.15)])
        self._add_rw_seg('R', 39.0, 53.0, 4.0, 1.0,  0.4, [(0.95, 0.3), (0.95, 0.15)])
        return self

    # ─────────────────── 19. Reinforcement ───────────────────
    def CreateReinforcement(self):
        r = 0.008
        for side in ['L', 'R']:
            inn, bkb, _ = self._abut_y(side)
            cy = (inn + bkb) / 2.0
            z  = -self.AF_Z + 0.05
            n_x = int(self.WIDTH / 0.20)
            for i in range(n_x):
                x = self.WIDTH * (i+1) / float(n_x + 1)
                self._s(cyl(pt(x, cy-self.AF_Y/2+0.05, z),
                            pt(x, cy+self.AF_Y/2-0.05, z), r))
            n_y = int(self.AF_Y / 0.20)
            for j in range(n_y):
                y = cy - self.AF_Y/2 + self.AF_Y*(j+1) / float(n_y + 1)
                self._s(cyl(pt(0.05, y, z), pt(self.WIDTH-0.05, y, z), r))
        z    = self.z_bb + self.BR_Z + 0.05
        ovhg = (self.DECK_SPAN - self.SPAN) / 2.0
        n_xd = int(self.WIDTH / 0.15)
        for i in range(n_xd):
            x = self.WIDTH * (i+1) / float(n_xd + 1)
            self._s(cyl(pt(x, -ovhg+0.05, z), pt(x, self.SPAN+ovhg-0.05, z), r))
        n_yd = int(self.DECK_SPAN / 0.15)
        for j in range(n_yd):
            y = -ovhg + self.DECK_SPAN*(j+1) / float(n_yd + 1)
            self._s(cyl(pt(0.05, y, z), pt(self.WIDTH-0.05, y, z), r))
        return self

    # ─────────────────── 20. Expansion joints ───────────────────
    def CreateExpansionJoints(self):
        z0 = self.z_deck
        z1 = z0 + self.WC_Z
        g  = self.EXP_GAP
        groove = 0.02
        self._m(box(0, self.WIDTH, -g/2, g/2, z0-groove, z1))
        self._m(box(0, self.WIDTH, self.SPAN-g/2, self.SPAN+g/2, z0-groove, z1))
        return self

    # ═══════════════════════════════════════════════════════════
    #  Build
    # ═══════════════════════════════════════════════════════════
    def Build(self):
        (self
            .CreatePCC()
            .CreateFootings()
            .CreateAbutments()
            .CreateWingWalls()
            .CreateBedBlocks()
            .CreateBearings()
            .CreateDeck()
            .CreateBackwalls()
            .CreateApproachSlab()
            .CreateWearingCoat()
            .CreateHandrails()
            .CreateNameBoard()
            .CreateDrainage()
            .CreateEarthFill()
            .CreateProtectionWalls()
            .CreateGuardStones()
            .CreateRCCPipe()
            .CreateDowelBars()
            .CreateRetainingWalls()
            .CreateReinforcement()
            .CreateExpansionJoints()
        )
        return self

# ═══════════════════════════════════════════════════════════════
bridge = KakkathodeBridge()
bridge.Build()

# ═══════════════════════════════════════════════════════════════
#  OBJ + MTL Export with embedded colors
#  Import into Revit via: Insert → Import CAD → .obj
#  Enscape will read colors automatically
# ═══════════════════════════════════════════════════════════════
import os

_sat_dir = r"C:\Users\mohda\kakathod bim"

try:
    clr.AddReference("RevitAPI")
    import Autodesk.Revit.DB as DB
    clr.AddReference("RevitNodes")
    import Revit
    clr.ImportExtensions(Revit.GeometryConversion)
except:
    pass

def tessellate_group(geom_list, name=""):
    """Tessellate using Revit API Face.Triangulate()"""
    all_verts = []
    all_tris  = []
    offset    = 0
    errs      = []
    for solid in geom_list:
        if solid is None:
            continue
        try:
            # Convert Dynamo Solid to Revit Geometry
            revit_geoms = solid.ToRevitType()
            
            for r_geom in revit_geoms:
                # We only want to triangulate solids/faces
                if str(r_geom.GetType()) == "Autodesk.Revit.DB.Solid":
                    for face in r_geom.Faces:
                        mesh = face.Triangulate()
                        if mesh is None:
                            continue
                        
                        pts = mesh.Vertices
                        for i in range(pts.Count):
                            p = pts[i]
                            # Revit internal is feet. Convert back to Meters for OBJ!
                            all_verts.append((p.X * 0.3048, p.Y * 0.3048, p.Z * 0.3048))
                            
                        for i in range(mesh.NumTriangles):
                            tri = mesh.get_Triangle(i)
                            all_tris.append((
                                tri.get_Index(0) + offset + 1,
                                tri.get_Index(1) + offset + 1,
                                tri.get_Index(2) + offset + 1
                            ))
                        offset += pts.Count
        except Exception as e:
            errs.append(str(e))
    return all_verts, all_tris, errs

def write_obj_mtl(groups, obj_path, mtl_path):
    all_errs = []
    # Write MTL file
    with open(mtl_path, 'w') as mf:
        for (name, r, g, b, _) in groups:
            mf.write("newmtl " + name + "\n")
            mf.write("Kd {:.6f} {:.6f} {:.6f}\n".format(r/255.0, g/255.0, b/255.0))
            mf.write("Ka 0.2 0.2 0.2\n")
            mf.write("Ks 0.1 0.1 0.1\n")
            mf.write("Ns 10.0\n")
            mf.write("d 1.0\n\n")

    # Write OBJ file
    mtl_name = os.path.basename(mtl_path)
    with open(obj_path, 'w') as of:
        of.write("# Kakkathode Bridge\n")
        of.write("mtllib " + mtl_name + "\n\n")

        global_vert_offset = 0

        for (name, r, g, b, geom_list) in groups:
            verts, tris, errs = tessellate_group(geom_list, name)
            if errs:
                all_errs.extend(errs)
                
            if not verts:
                continue

            of.write("o " + name + "\n")
            of.write("usemtl " + name + "\n")

            for (x, y, z) in verts:
                # Format to 6 decimals, and map Z to Y for OBJ Y-up orientation
                of.write("v {:.6f} {:.6f} {:.6f}\n".format(x, z, -y))

            for (a, b_idx, c) in tris:
                va = a + global_vert_offset
                vb = b_idx + global_vert_offset
                vc = c + global_vert_offset
                of.write("f {} {} {}\n".format(va, vb, vc))

            global_vert_offset += len(verts)
            of.write("\n")
    return all_errs

# ── Define groups with colors ─────────────────────────────────
_groups = [
    # name,         R    G    B    geometry list
    ("Concrete",   180, 180, 180, bridge.concrete),
    ("Earth",      139,  90,  43, bridge.earth),
    ("Steel",       70, 100, 140, bridge.steel[:80]),
    ("Misc",       100, 160, 220, bridge.misc),
]

_obj_path = os.path.join(_sat_dir, "bridge.obj")
_mtl_path = os.path.join(_sat_dir, "bridge.mtl")

try:
    write_obj_mtl(_groups, _obj_path, _mtl_path)
    _export_msg = "OBJ exported: " + _obj_path
except Exception as e:
    _export_msg = "OBJ export failed: " + str(e)

# ── Also keep SAT export for backup ──────────────────────────
for (geom_list, fname) in [
    (bridge.concrete, "bridge_concrete.sat"),
    (bridge.earth,    "bridge_earth.sat"),
]:
    _geom = [g for g in geom_list if g is not None]
    if _geom:
        _path = os.path.join(_sat_dir, fname)
        try:
            Geometry.ExportToSAT(_geom, _path)
            _export_msg += " | SAT: " + fname
        except Exception as e:
            _export_msg += " | SAT fail: " + str(e)

# ── Dynamo viewport colors ────────────────────────────────────
_clr_concrete = Color.ByARGB(255, 180, 180, 180)
_clr_earth    = Color.ByARGB(255, 139,  90,  43)
_clr_steel    = Color.ByARGB(255,  70, 100, 140)
_clr_misc     = Color.ByARGB(150, 100, 160, 220)

_display = []
for g in bridge.concrete:
    if g is not None:
        try: _display.append(GeometryColor.ByGeometryColor(g, _clr_concrete))
        except: pass
for g in bridge.earth:
    if g is not None:
        try: _display.append(GeometryColor.ByGeometryColor(g, _clr_earth))
        except: pass
for g in bridge.steel:
    if g is not None:
        try: _display.append(GeometryColor.ByGeometryColor(g, _clr_steel))
        except: pass
for g in bridge.misc:
    if g is not None:
        try: _display.append(GeometryColor.ByGeometryColor(g, _clr_misc))
        except: pass

OUT = [_display, _export_msg]
