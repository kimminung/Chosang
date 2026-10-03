"""Glasses_<id>(3) · Beard_<id>(2) · Shoulders_<id>(2) 라이브러리. 결정적.
· Glasses: 림·브리지·코받침·다리(튜브), 렌즈(투명). Head 100%.
· Beard: Bust 수염 영역 면을 법선 방향으로 띄운 셸 + 알파(버즈 타일). Head 100%, 정점 속성 chosang_bust_index(원본 Bust 정점) — 턱 셰이프를 따라가게 하려면 앱이 이 대응으로 변형을 복사.
· Shoulders: Bust 몸통(목둘레 아래) 셸 + 목둘레 두께 + (셔츠) 스탠드 칼라. 스킨 = Bust 의 Root/Neck 가중치 복사(목둘레만 Neck 소량).
"""
import bpy, bmesh, numpy as np, math, json, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
TEX = os.path.expanduser("~/Desktop/Chosang_Blender/textures/")

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def nz(v):
    l = np.linalg.norm(v); return v / l if l > 1e-12 else v

class Bust:
    def __init__(self):
        b = bpy.data.objects["Bust"]; me = b.data; n = len(me.vertices); self.ob = b; self.n = n
        V = np.empty(n * 3); me.shape_keys.key_blocks["Basis"].data.foreach_get("co", V); self.V = V.reshape(-1, 3)
        N = np.empty(n * 3); me.vertices.foreach_get("normal", N); self.N = N.reshape(-1, 3)
        self.faces = [tuple(p.vertices) for p in me.polygons]
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.V], self.faces)
        self.meta = json.loads(b["chosang_patch"])
        self.w = {}
        for g in ("Root", "Neck", "Head"):
            gi = b.vertex_groups[g].index; w = np.zeros(n)
            for v in me.vertices:
                for gg in v.groups:
                    if gg.group == gi: w[v.index] = gg.weight
            self.w[g] = w
    def ray(self, o, d):
        loc, nrm, idx, dist = self.bvh.ray_cast(Vector(o), Vector(d), 1.0)
        return (np.array(loc), np.array(nrm)) if loc is not None else (None, None)

def get_mat(name, color, rough=0.5, img=None, alpha_from_img=False, alpha=None, extra_img=None, extra_label=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'): nt.nodes.remove(nd)
    b = nt.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    if img:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(TEX + img, check_existing=True); t.location = (-400, 200)
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if alpha_from_img: nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    if extra_img:
        t2 = nt.nodes.new("ShaderNodeTexImage"); t2.image = bpy.data.images.load(TEX + extra_img, check_existing=True); t2.location = (-400, -150)
        t2.label = extra_label or "Mask"; t2.image.colorspace_settings.name = 'Non-Color'
    if alpha is not None: b.inputs["Alpha"].default_value = alpha
    if alpha is not None or alpha_from_img:
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
    m.use_backface_culling = False; m.diffuse_color = (*color, 1 if alpha is None else max(alpha, 0.3))
    return m

def new_obj(name, verts, faces, coll, mats, mat_idx=None, uvs=None, smooth=True):
    old = bpy.data.objects.get(name)
    if old:
        d = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if d.users == 0: bpy.data.meshes.remove(d)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(f) for f in faces]); me.update()
    for m in mats: me.materials.append(m)
    if mat_idx is not None: me.polygons.foreach_set("material_index", list(mat_idx))
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
    if uvs is not None:
        uv = me.uv_layers.new(name="UVMap"); uv.data.foreach_set("uv", [c for fu in uvs for p in fu for c in p])
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob

def skin(ob, arm, weights):
    for g, w in weights.items():
        vg = ob.vertex_groups.new(name=g)
        for i, ww in enumerate(w):
            if ww > 1e-4: vg.add([i], float(ww), 'REPLACE')
    ob.parent = arm; ob.matrix_parent_inverse.identity()
    mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm

# ---------------- 안경 ----------------
def tube(path, radius, nprof=8, closed=False):
    P = np.asarray(path); n = len(P); V, F = [], []
    for i in range(n):
        t = nz(P[(i + 1) % n] - P[i - 1]) if closed else nz(P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        a = nz(np.cross(t, [0, 0, 1.0]) if abs(t[2]) < 0.9 else np.cross(t, [1.0, 0, 0])); b = np.cross(t, a)
        for k in range(nprof):
            th = 2 * math.pi * k / nprof
            V.append(P[i] + radius * (math.cos(th) * a + math.sin(th) * b))
    segs = n if closed else n - 1
    for i in range(segs):
        j = (i + 1) % n
        for k in range(nprof):
            F.append((i * nprof + k, i * nprof + (k + 1) % nprof, j * nprof + (k + 1) % nprof, j * nprof + k))
    return V, F

def outline(kind, cx, cz, m=48):
    th = np.linspace(0, 2 * math.pi, m, endpoint=False)
    if kind == "round": a, b, e = 0.0215, 0.0215, 2.0
    elif kind == "square": a, b, e = 0.026, 0.0185, 5.0
    else: a, b, e = 0.0245, 0.0165, 2.0
    c, s = np.cos(th), np.sin(th)
    x = a * np.sign(c) * np.abs(c) ** (2 / e); z = b * np.sign(s) * np.abs(s) ** (2 / e)
    return np.stack([cx + x, cz + z], 1)

def build_glasses(B, kind, coll, arm, mats):
    V = B.V; patch = V[:1220]
    sel = (np.abs(np.abs(patch[:, 0]) - 0.032) < 0.026) & (np.abs(patch[:, 2] - 0.442) < 0.021) & (np.abs(patch[:, 0]) > 0.012)
    y_lens = patch[sel, 1].min() - 0.0065
    nose = patch[(np.abs(patch[:, 0]) < 0.006) & (np.abs(patch[:, 2] - 0.437) < 0.005)]
    y_bridge = min(y_lens - 0.002, nose[:, 1].min() - 0.0035)
    tilt = math.tan(math.radians(8)); cz = 0.443 if kind == "square" else 0.441
    rad = {"round": 0.0012, "square": 0.0017, "thin": 0.00065}[kind]
    Vs, Fs, Ms = [], [], []
    def add(v, f, mi):
        base = len(Vs); Vs.extend(v); Fs.extend([tuple(base + i for i in ff) for ff in f]); Ms.extend([mi] * len(f))
    for side in (1, -1):
        cx = side * (0.033 if kind == "square" else 0.032)
        O = outline(kind, cx, cz)
        rim = np.stack([O[:, 0], y_lens + (cz - O[:, 1]) * tilt + 0.0025 * ((np.abs(O[:, 0]) - abs(cx)) / 0.025) ** 2, O[:, 1]], 1)
        v, f = tube(rim, rad, 8, True); add(v, f, 0)
        c = np.array([cx, y_lens - 0.0008, cz]); lv = [c] + [r for r in rim]
        lf = [(0, 1 + i, 1 + (i + 1) % len(rim)) for i in range(len(rim))]
        if side < 0: lf = [tuple(reversed(t)) for t in lf]
        add(lv, lf, 1)
        outer = rim[np.argmax(side * rim[:, 0] + 0.3 * rim[:, 2])]
        path = [outer + np.array([side * 0.002, 0.0, 0.0])]
        for yy in np.linspace(outer[1] + 0.012, 0.004, 7):
            zz = 0.449 - 0.002 * (yy - outer[1]) / 0.1
            hit, _ = B.ray(np.array([0.0, yy, zz]), np.array([side * 1.0, 0, 0]))
            xs = (hit[0] + side * 0.0028) if hit is not None else side * 0.075
            path.append(np.array([xs, yy, zz]))
        for yy, zz in ((0.012, 0.440), (0.017, 0.428)):
            hit, _ = B.ray(np.array([0.0, yy, zz]), np.array([side * 1.0, 0, 0]))
            path.append(np.array([(hit[0] + side * 0.0022) if hit is not None else side * 0.072, yy, zz]))
        v, f = tube(np.array(path), rad * 0.85 + 0.0003, 6, False); add(v, f, 0)
        hit, _ = B.ray(np.array([side * 0.0085, -0.2, 0.433]), np.array([0, 1.0, 0]))
        if hit is not None:
            pc = hit + np.array([0, -0.0012, 0]); pv, pf = tube(np.array([pc + [0, 0, 0.003], pc - [0, 0, 0.003]]), 0.0016, 8, False); add(pv, pf, 0)
    br = [np.array([s * 0.0108, y_lens + 0.0005, cz + 0.006 - 0.0005 * (1 - abs(s))]) for s in np.linspace(1, -1, 9)]
    br = [p + np.array([0, (y_bridge - y_lens) * (1 - p[0] ** 2 / 0.0108 ** 2), 0.002 * (1 - p[0] ** 2 / 0.0108 ** 2)]) for p in br]
    v, f = tube(np.array(br), rad * 0.9 + 0.0002, 8, False); add(v, f, 0)
    ob = new_obj("Glasses_" + kind, Vs, Fs, coll, mats, Ms)
    skin(ob, arm, {"Head": np.ones(len(Vs))})
    ob["chosang_kind"] = "glasses"; ob["chosang_bone"] = "Head"; ob["chosang_nose_bridge"] = [0.0, float(y_bridge), float(cz + 0.008)]
    return ob, len(Vs)

# ---------------- 수염 ----------------
def beard_mask(B, kind):
    V = B.V; x, y, z = V[:, 0], V[:, 1], V[:, 2]; n = B.n
    mc = V[B.meta["mouth_loop"]].mean(0)
    zline = 0.398 + 0.032 * smoothstep(0.035, 0.066, np.abs(x))
    zlow = 0.305 if kind == "short" else 0.312
    m = (z < zline) & (z > zlow) & (y < -0.004)
    m &= ~(((x / 0.0255) ** 2 + ((z - mc[2]) / 0.0095) ** 2) < 1.0)
    m &= ~((np.abs(x) < 0.019) & (z > 0.394))
    excl = np.zeros(n, bool); excl[B.meta["lid_inner"] + B.meta["lip_inner"]] = True; excl[B.meta["ear_left_range"][0]:] = True
    return m & ~excl

def build_beard(B, kind, coll, arm, mat):
    mask = beard_mask(B, kind)
    fsel = [f for f in B.faces if all(mask[v] for v in f)]
    layers = [(0.0003, 0.040)] if kind == "stubble" else [(0.0012, 0.05), (0.0026, 0.06)]
    Vs, Fs, UVs, src = [], [], [], []
    for off, tile in layers:
        vm = {}
        for f in fsel:
            ff = []; uvf = []
            for v in f:
                if v not in vm:
                    vm[v] = len(Vs); Vs.append(B.V[v] + B.N[v] * off); src.append(v)
                ff.append(vm[v])
                p = B.V[v]; ph = math.atan2(p[0], -(p[1] - 0.003))
                uvf.append((ph * 0.07 / tile, p[2] / tile))
            Fs.append(ff); UVs.append(uvf)
    ob = new_obj("Beard_" + kind, Vs, Fs, coll, [mat], None, UVs)
    skin(ob, arm, {"Head": np.ones(len(Vs))})
    a = ob.data.attributes.new("chosang_bust_index", 'INT', 'POINT'); a.data.foreach_set("value", src)
    ob["chosang_kind"] = "beard"; ob["chosang_bone"] = "Head"; ob["chosang_tint"] = True
    return ob, len(Vs)

# ---------------- 어깨 옷 ----------------
def cloth_textures():
    import numpy as np
    def save(name, arr, noncolor):
        h, w = arr.shape[:2]
        old = bpy.data.images.get(name)
        if old: bpy.data.images.remove(old)
        im = bpy.data.images.new(name, w, h, alpha=True); im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
        im.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
        im.filepath_raw = TEX + name + ".png"; im.file_format = 'PNG'; im.save(); im.source = 'FILE'; im.filepath = TEX + name + ".png"; im.reload()
    S = 1024; yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    rng = np.random.default_rng(5)
    noise = rng.normal(0, 1, (S // 8, S // 8)); noise = np.kron(noise, np.ones((8, 8)))
    tee = 0.80 + 0.035 * np.sin(2 * np.pi * xx / 5.0) + 0.012 * noise
    save("T_Cloth_Tee_base", np.dstack([tee, tee, tee, np.ones_like(tee)]), False)
    save("T_Cloth_Tee_mask", np.dstack([np.ones_like(tee)] * 3 + [np.ones_like(tee)]), True)
    weave = 0.84 + 0.02 * np.sin(2 * np.pi * xx / 4.0) * np.sin(2 * np.pi * yy / 4.0) + 0.01 * noise
    u = xx / S; v = 1 - yy / S
    plk = np.exp(-((u - 0.5) / 0.012) ** 2)
    weave = weave - 0.05 * (np.exp(-((np.abs(u - 0.5) - 0.012) / 0.0015) ** 2))
    mask = np.ones_like(weave)
    for zb in (0.045, 0.105, 0.165, 0.225):
        d = np.hypot((u - 0.5) * S, (v - zb / 0.30) * S)
        btn = d < 7.0; weave = np.where(btn, 0.92 - 0.1 * (d / 7.0), weave); mask = np.where(btn, 0.0, mask)
    save("T_Cloth_Shirt_base", np.dstack([weave, weave, weave, np.ones_like(weave)]), False)
    save("T_Cloth_Shirt_mask", np.dstack([mask, mask, mask, np.ones_like(mask)]), True)

def build_shoulders(B, kind, coll, arm, mat):
    V = B.V; x, y, z = V[:, 0], V[:, 1], V[:, 2]
    ph = np.arctan2(x, -(y - 0.02))
    zn = 0.270 - 0.015 * np.cos(ph)
    if kind == "shirt": zn = zn - 0.030 * np.clip(np.cos(ph), 0, 1) ** 8
    s0, s1 = B.meta["shell_vertex_range"]
    m = np.zeros(B.n, bool); m[s0:s1] = True; m &= (z < zn)
    bottom = s1 - 1
    fsel = [f for f in B.faces if all(m[v] for v in f) and bottom not in f]
    off = 0.003 if kind == "tee" else 0.004
    vm = {}; Vs, Fs, UVs, src = [], [], [], []
    for f in fsel:
        ff, uf = [], []
        for v in f:
            if v not in vm:
                vm[v] = len(Vs); Vs.append(V[v] + B.N[v] * off); src.append(v)
            ff.append(vm[v]); uf.append(((ph[v] + math.pi) / (2 * math.pi), z[v] / 0.30))
        Fs.append(ff); UVs.append(uf)
    # 목둘레 경계 → 안쪽 접힘(두께) + 셔츠 칼라
    cnt = {}
    for f in Fs:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)]); cnt[e] = cnt.get(e, 0) + 1
    nxt = {a: b for (a, b) in cnt if (b, a) not in cnt}
    top = [a for a in nxt if Vs[a][2] > 0.15]
    loop = []; 
    if top:
        s = top[0]; loop = [s]; c = nxt[s]
        while c != s and c in nxt and len(loop) < 5000: loop.append(c); c = nxt[c]
    fold, collar = [], []
    if loop:
        for i in loop:   # 목둘레 계단 제거: 경계 정점 높이를 매끈한 목선 zn(φ) 로
            sv = src[i]; Vs[i] = np.array(Vs[i]); Vs[i][2] = zn[sv] + 0.0
        for _ in range(3):   # 경계를 따라 1D 평활
            P = np.array([Vs[i] for i in loop]); P2 = (np.roll(P, 1, 0) + 2 * P + np.roll(P, -1, 0)) / 4
            for i, q in zip(loop, P2): Vs[i] = q
        Lp = np.array([Vs[i] for i in loop])
        Nn = np.array([B.N[src[i]] for i in loop])
        inner = Lp - Nn * (off + 0.0015) - np.array([0, 0, 0.004])
        base = len(Vs); Vs.extend(inner.tolist()); src.extend([src[i] for i in loop])
        k = len(loop)
        for i in range(k):
            a, b = loop[i], loop[(i + 1) % k]
            Fs.append([b, a, base + i, base + (i + 1) % k]); UVs.append([(0.01, 0.99), (0.0, 0.99), (0.0, 0.98), (0.01, 0.98)])
        if kind == "shirt":
            php = np.arctan2(Lp[:, 0], -(Lp[:, 1] - 0.02))
            openf = np.abs(php) < math.radians(28)
            rings = [Lp]
            for h, o in ((0.012, 0.002), (0.026, 0.004)):
                rings.append(Lp + np.array([0, 0, h]) + Nn * o)
            idxs = [loop]
            for r in rings[1:]:
                b0 = len(Vs); Vs.extend(r.tolist()); src.extend([src[i] for i in loop]); idxs.append(list(range(b0, b0 + k)))
            for a_, b_ in zip(idxs[:-1], idxs[1:]):
                for i in range(k):
                    j = (i + 1) % k
                    if openf[i] and openf[j]: continue
                    Fs.append([a_[j], a_[i], b_[i], b_[j]]); UVs.append([(0.02, 0.97), (0.03, 0.97), (0.03, 0.96), (0.02, 0.96)])
    ob = new_obj("Shoulders_" + kind, Vs, Fs, coll, [mat], None, UVs)
    src = np.array(src)
    wr = B.w["Root"][src]; wn = B.w["Neck"][src]; s = np.maximum(wr + wn, 1e-6)
    skin(ob, arm, {"Root": wr / s, "Neck": wn / s})
    ob["chosang_kind"] = "shoulders"; ob["chosang_bone"] = "Root"; ob["chosang_tint"] = True
    return ob, len(Vs)

def run():
    B = Bust(); arm = bpy.data.objects["Armature"]
    frame = get_mat("Glasses_Frame", (0.05, 0.05, 0.055), 0.35)
    lens = get_mat("Glasses_Lens", (0.85, 0.88, 0.9), 0.05, alpha=0.15)
    out = {}
    for k in ("round", "square", "thin"):
        out["Glasses_" + k] = build_glasses(B, k, bpy.data.collections["Library_Glasses"], arm, [frame, lens])[1]
    bmat = get_mat("Beard", (0.5, 0.5, 0.5), 0.6, "T_Hair_Buzz_base.png", True, extra_img="T_Hair_Buzz_mask.png", extra_label="HighlightMask")
    for k in ("stubble", "short"):
        out["Beard_" + k] = build_beard(B, k, bpy.data.collections["Library_Beard"], arm, bmat)[1]
    cloth_textures()
    tee = get_mat("Cloth_Tee", (0.8, 0.8, 0.8), 0.85, "T_Cloth_Tee_base.png", extra_img="T_Cloth_Tee_mask.png", extra_label="RecolorMask")
    shirt = get_mat("Cloth_Shirt", (0.85, 0.85, 0.85), 0.8, "T_Cloth_Shirt_base.png", extra_img="T_Cloth_Shirt_mask.png", extra_label="RecolorMask")
    out["Shoulders_tee"] = build_shoulders(B, "tee", bpy.data.collections["Library_Shoulders"], arm, tee)[1]
    out["Shoulders_shirt"] = build_shoulders(B, "shirt", bpy.data.collections["Library_Shoulders"], arm, shirt)[1]
    return out
