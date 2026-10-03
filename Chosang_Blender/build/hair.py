"""Hair_<id> 라이브러리 — 캡(Scalp 그룹 전체를 덮는 셸) + 알파 머리카락 카드. Head 100% 스킨, 셰이프키 없음. 결정적(seed 고정).
카드 UV: 아틀라스 8칸 중 한 칸(u), 뿌리 v=1 → 끝 v=0. 카드 앞면 법선 = 두피 바깥(앱은 양면 렌더 권장)."""
import bpy, bmesh, numpy as np, math, json, zlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

COL = dict(straight_dense=0, straight_medium=1, wavy=2, coarse_wave=3, flyaway=4, bangs_blunt=5, tied_bunch=6, short_clump=7)
NCOL = 8
STYLES = ["short_crop", "short_side", "medium_wave", "long_straight", "long_wave", "tied_low", "tied_high",
          "bangs_short", "bangs_medium", "bangs_long", "buzz", "bald_cap"]
CROWN = np.array([0.0, 0.010, 0.567])
DOWN = np.array([0.0, 0.0, -1.0])

def nz(v):
    l = np.linalg.norm(v); return v / l if l > 1e-12 else v
def tangent(v, n): return nz(v - np.dot(v, n) * n)

class Head:
    def __init__(self):
        b = bpy.data.objects["Bust"]; me = b.data; n = len(me.vertices)
        V = np.empty(n * 3); me.shape_keys.key_blocks["Basis"].data.foreach_get("co", V); self.V = V.reshape(-1, 3)
        N = np.empty(n * 3); me.vertices.foreach_get("normal", N); self.N = N.reshape(-1, 3)
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.V], [tuple(p.vertices) for p in me.polygons])
        gi = b.vertex_groups["Scalp"].index
        self.scalp = np.array(sorted(v.index for v in me.vertices if any(g.group == gi for g in v.groups)))
        ss = set(self.scalp.tolist())
        uv = me.uv_layers["UVMap"].data
        self.cap_faces = []
        for p in me.polygons:
            if all(v in ss for v in p.vertices):
                self.cap_faces.append((tuple(p.vertices), [uv[li].uv[:] for li in p.loop_indices]))
    def near(self, p):
        loc, nrm, idx, dist = self.bvh.find_nearest(Vector(p))
        return np.array(loc), np.array(nrm)
    def push_out(self, p, off):
        loc, nrm = self.near(p); d = np.dot(p - loc, nrm)
        if d < off: p = p + nrm * (off - d)
        return p, nrm

def grow(H, root, steer, L, nseg, off, stop=None, inertia=0.55):
    pts = [root.copy()]; p = root.copy(); d = None; step = L / nseg
    for k in range(nseg):
        _, nrm = H.near(p)
        dd = steer(p, nrm, k / nseg)
        d = dd if d is None else nz(inertia * d + (1 - inertia) * dd)
        p = p + d * step
        p, _ = H.push_out(p, off)
        pts.append(p.copy())
        if stop is not None and stop(p): break
    return np.array(pts)

def card(H, pts, width, col):
    n = len(pts); V, U = [], []
    u0 = col / NCOL + 0.003; u1 = (col + 1) / NCOL - 0.003
    for i, p in enumerate(pts):
        t = i / (n - 1)
        tg = nz(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        _, nrm = H.near(p)
        b = nz(np.cross(tg, nrm)); w = width * (1 - 0.45 * t)
        V += [p - b * w / 2, p + b * w / 2]; U += [(u0, 1 - t), (u1, 1 - t)]
    F = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(n - 1)]
    return V, F, U

def azim(p): return math.degrees(math.atan2(p[0], -(p[1] - 0.003)))

def roots(H, count, seed, off, where=None):
    rng = np.random.default_rng(seed)
    P = H.V[H.scalp] + H.N[H.scalp] * off; Nn = H.N[H.scalp]
    idx = np.arange(len(P))
    if where is not None: idx = idx[np.array([where(P[i]) for i in idx], bool)]
    sel = rng.choice(idx, size=min(count, len(idx)), replace=False)
    return [(P[i], Nn[i]) for i in sel]

def style_strands(H, style):
    S = []          # (pts, width, col)
    rng = np.random.default_rng(zlib.crc32(style.encode()))
    def pick(*cols): return COL[cols[rng.integers(len(cols))]]
    def falling(part_x=0.0, part_soft=0.012, back_bias=0.15):
        def f(p, n, t):
            s = np.tanh((p[0] - part_x) / part_soft)
            flow = tangent(p - CROWN, n)
            side = tangent(np.array([s, back_bias, -0.5]), n)
            front = smooth_front(p)
            v = nz((1 - front) * flow + front * side + DOWN * (0.4 + 1.6 * t))
            return v
        return f
    def smooth_front(p):
        a = abs(azim(p)); return float(np.clip((70 - a) / 40, 0, 1)) * float(np.clip((p[2] - 0.48) / 0.03, 0, 1))
    def add(pts, w, col):
        if len(pts) >= 3: S.append((pts, w, col))
    if style in ("short_crop", "short_side"):
        part = 0.022 if style == "short_side" else None
        for layer, (cnt, off, Lr) in enumerate(((330, 0.0035, (0.030, 0.045)), (220, 0.0065, (0.035, 0.055)))):
            for r, n in roots(H, cnt, 11 + layer, off):
                L = rng.uniform(*Lr) * (1.0 if r[2] > 0.50 else 0.65)
                if part is None:
                    def st(p, nn, t, r=r): return nz(tangent(np.array([0, -0.6, 0.25]) if p[2] > 0.52 else (p - CROWN), nn) + DOWN * 0.3 * t)
                else:
                    def st(p, nn, t): return nz(falling(part, 0.006, 0.05)(p, nn, t) + DOWN * 0.2)
                add(grow(H, r, st, L, 5, off), rng.uniform(0.010, 0.015), pick("short_clump", "straight_medium"))
    elif style in ("medium_wave", "long_straight", "long_wave"):
        Lr = {"medium_wave": (0.11, 0.16), "long_straight": (0.25, 0.32), "long_wave": (0.25, 0.31)}[style]
        cols = {"medium_wave": ("wavy", "coarse_wave"), "long_straight": ("straight_dense", "straight_medium"), "long_wave": ("wavy", "coarse_wave")}[style]
        for layer, (cnt, off) in enumerate(((300, 0.0035), (230, 0.0075), (90, 0.011))):
            for r, n in roots(H, cnt, 21 + layer, off):
                L = rng.uniform(*Lr) * (0.85 if r[2] < 0.45 else 1.0)
                c = pick(*cols) if layer < 2 else COL["flyaway"]
                add(grow(H, r, falling(0.0), L, 12, off), rng.uniform(0.014, 0.022), c)
    elif style in ("tied_low", "tied_high"):
        T = np.array([0.0, 0.094, 0.425]) if style == "tied_low" else np.array([0.0, 0.080, 0.532])
        for layer, (cnt, off) in enumerate(((320, 0.003), (180, 0.006))):
            for r, n in roots(H, cnt, 31 + layer, off):
                L = np.linalg.norm(T - r) * 1.15
                def st(p, nn, t, T=T): return tangent(T - p, nn)
                add(grow(H, r, st, L, 9, off, stop=lambda p, T=T: np.linalg.norm(p - T) < 0.018, inertia=0.25), rng.uniform(0.012, 0.018), pick("straight_dense", "straight_medium"))
        for i in range(48):
            a = 2 * math.pi * i / 48; rr = rng.uniform(0.004, 0.011)
            r0 = T + np.array([rr * math.cos(a), 0.008, rr * math.sin(a)])
            r0, _ = H.push_out(r0, 0.008)
            L = rng.uniform(0.15, 0.20) if style == "tied_low" else rng.uniform(0.18, 0.24)
            def st(p, nn, t): return nz(np.array([0, 0.35, -1.0]))
            add(grow(H, r0, st, L, 8, 0.006), rng.uniform(0.012, 0.018), COL["tied_bunch"] if i % 3 else COL["straight_dense"])
    elif style.startswith("bangs_"):
        zend = {"bangs_short": 0.492, "bangs_medium": 0.466, "bangs_long": 0.452}[style]
        Lrest = {"bangs_short": (0.07, 0.10), "bangs_medium": (0.14, 0.19), "bangs_long": (0.24, 0.30)}[style]
        isb = lambda p: abs(azim(p)) < 55 and p[2] > 0.488
        for layer, (cnt, off) in enumerate(((150, 0.0035), (90, 0.0065))):
            for r, n in roots(H, cnt, 41 + layer, off, where=isb):
                ze = zend - 0.025 * float(np.clip((abs(r[0]) - 0.03) / 0.03, 0, 1)) if style == "bangs_long" else zend
                def st(p, nn, t): return tangent(np.array([p[0] * 1.5, -1.0, -1.2]), nn)
                add(grow(H, r, st, 0.12, 10, off, stop=lambda p, ze=ze: p[2] < ze), rng.uniform(0.012, 0.018), COL["bangs_blunt"])
        for layer, (cnt, off) in enumerate(((280, 0.0035), (200, 0.007))):
            for r, n in roots(H, cnt, 51 + layer, off, where=lambda p: not isb(p)):
                add(grow(H, r, falling(0.0), rng.uniform(*Lrest), 10, off), rng.uniform(0.014, 0.020), pick("straight_dense", "straight_medium"))
    return S

def materials():
    import os
    tex = os.path.expanduser("~/Desktop/Chosang_Blender/textures/")
    def img(name):
        im = bpy.data.images.get(name)
        if im is None: im = bpy.data.images.load(tex + name + ".png", check_existing=True)
        return im
    def mat(name, base_img=None, alpha=False, color=(0.8, 0.8, 0.8), mask_img=None, rough=0.45):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True; nt = m.node_tree
        for nd in list(nt.nodes):
            if nd.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'): nt.nodes.remove(nd)
        b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
        b.inputs["Base Color"].default_value = (*color, 1)
        if base_img:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(base_img); t.location = (-400, 200); t.label = "BaseColor"
            nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
            if alpha: nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        if mask_img:
            t2 = nt.nodes.new("ShaderNodeTexImage"); t2.image = img(mask_img); t2.location = (-400, -150); t2.label = "HighlightMask"
            t2.image.colorspace_settings.name = 'Non-Color'
        try: m.surface_render_method = 'DITHERED' if alpha else 'DITHERED'
        except Exception: pass
        m.use_backface_culling = False
        m.diffuse_color = (*color, 1)
        return m
    return dict(cards=mat("Hair_Cards", "T_Hair_Atlas_base", True, (0.55, 0.55, 0.55), "T_Hair_Atlas_mask"),
                cap=mat("Hair_Cap", "T_Hair_Buzz_base", False, (0.5, 0.5, 0.5), "T_Hair_Buzz_mask"),
                buzz=mat("Hair_Buzz", "T_Hair_Buzz_base", True, (0.5, 0.5, 0.5), "T_Hair_Buzz_mask", 0.5),
                bald=mat("Hair_BaldCap", None, False, (0.85, 0.85, 0.85), None, 0.55))

def build_style(H, style, M, coll, arm):
    name = "Hair_" + style
    old = bpy.data.objects.get(name)
    if old:
        d = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if d.users == 0: bpy.data.meshes.remove(d)
    verts, faces, uvs, mats = [], [], [], []
    off_cap = 0.0012 if style != "bald_cap" else 0.0006
    vmap = {}
    for vs, fuv in H.cap_faces:
        f = []
        for v in vs:
            if v not in vmap:
                vmap[v] = len(verts); verts.append(H.V[v] + H.N[v] * off_cap)
            f.append(vmap[v])
        faces.append(f); uvs.append([(u * 24.0, w * 24.0) for (u, w) in fuv]); mats.append(0)
    cap_mat = M["bald"] if style == "bald_cap" else (M["buzz"] if style == "buzz" else M["cap"])
    for pts, w, col in style_strands(H, style):
        V2, F2, U2 = card(H, pts, w, col); base = len(verts)
        verts += V2
        for f in F2:
            faces.append([base + i for i in f]); uvs.append([U2[i] for i in f]); mats.append(1)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    uv = me.uv_layers.new(name="UVMap")
    flat = [c for fu in uvs for uvp in fu for c in uvp]
    uv.data.foreach_set("uv", flat)
    me.materials.append(cap_mat); me.materials.append(M["cards"])
    me.polygons.foreach_set("material_index", mats)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    vg = ob.vertex_groups.new(name="Head"); vg.add(list(range(len(verts))), 1.0, 'REPLACE')
    ob.parent = arm; ob.matrix_parent_inverse.identity()
    mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    ob["chosang_kind"] = "hair"; ob["chosang_bone"] = "Head"; ob["chosang_tint"] = True
    ob["chosang_textures"] = json.dumps(dict(base="T_Hair_Atlas_base.png", mask="T_Hair_Atlas_mask.png", cap="T_Hair_Buzz_base.png"))
    return ob, len(verts), sum(1 for m in mats if m == 1)

def run(styles=STYLES):
    H = Head(); M = materials()
    coll = bpy.data.collections["Library_Hair"]; arm = bpy.data.objects["Armature"]
    out = {}
    for s in styles:
        ob, nv, nc = build_style(H, s, M, coll, arm); out[s] = (nv, nc // 9 if nc else 0)
    return out
