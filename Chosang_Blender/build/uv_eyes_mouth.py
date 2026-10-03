"""UV 배치 · Skin · 눈알 · 입안(Mouth_Inner) · 아마추어 바인딩. 결정적."""
import bpy, bmesh, numpy as np, json, math
from mathutils import Vector, Matrix

UV_REGIONS = {
    "face":      (0.0, 0.0, 1.0, 0.5),      # Apple OBJ UV → (u, 0.5·v)
    "head_neck": (0.005, 0.505, 0.775, 0.795),
    "ear_L":     (0.785, 0.655, 0.995, 0.795),
    "ear_R":     (0.785, 0.505, 0.995, 0.645),
    "torso":     (0.005, 0.805, 0.995, 0.995),
    "lid_L":     (0.005, 0.003, 0.300, 0.045),
    "lid_R":     (0.310, 0.003, 0.605, 0.045),
    "lip":       (0.615, 0.003, 0.995, 0.045),
}
Z_SPLIT = 0.265
AXIS = [(0.0, 0.022), (0.2, 0.020), (0.30, 0.014), (0.36, 0.008), (0.42, 0.004), (0.6, 0.003)]
def ay(z): a = np.array(AXIS); return float(np.interp(z, a[:, 0], a[:, 1]))

def classify(ob, meta):
    me = ob.data
    eL = range(*meta["ear_left_range"]); eR = range(*meta["ear_right_range"])
    lid = set(meta["lid_inner"]); lip = set(meta["lip_inner"])
    cls = {}
    co = [v.co for v in me.vertices]
    for p in me.polygons:
        if p.index < 1152: continue
        vs = list(p.vertices)
        if vs[0] in eL: cls[p.index] = "ear_L"
        elif vs[0] in eR: cls[p.index] = "ear_R"
        elif any(v in lid for v in vs):
            cls[p.index] = "lid_L" if np.mean([co[v].x for v in vs]) > 0 else "lid_R"
        elif any(v in lip for v in vs): cls[p.index] = "lip"
        elif all(co[v].z <= Z_SPLIT + 1e-6 for v in vs): cls[p.index] = "torso"
        else: cls[p.index] = "head_neck"
    return cls

def layout_uv(ob):
    me = ob.data; meta = json.loads(ob["chosang_patch"])
    cls = classify(ob, meta)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(me); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    shell0, shell1 = meta["shell_vertex_range"]
    for e in bm.edges:
        a, b = e.verts; e.seam = False
        ia, ib = a.index, b.index
        if shell0 <= ia < shell1 and shell0 <= ib < shell1:
            if abs(a.co.x) < 1e-7 and abs(b.co.x) < 1e-7 and a.co.y > ay(a.co.z) + 1e-4 and b.co.y > ay(b.co.z) + 1e-4:
                e.seam = True
            if abs(a.co.z - Z_SPLIT) < 1e-6 and abs(b.co.z - Z_SPLIT) < 1e-6:
                e.seam = True
    def mark(u, v):
        e = bm.edges.get((bm.verts[u], bm.verts[v]))
        if e: e.seam = True
    lidI = meta["lid_inner"]
    for k, loop in enumerate((meta["eye_loop_left"], meta["eye_loop_right"])):
        i1 = lidI[48 * k: 48 * k + 24]; i2 = lidI[48 * k + 24: 48 * k + 48]
        mark(loop[0], i1[0]); mark(i1[0], i2[0])
    lipI = meta["lip_inner"]; mark(meta["mouth_loop"][0], lipI[0]); mark(lipI[0], lipI[36])
    for f in bm.faces: f.select = f.index in cls
    bmesh.update_edit_mesh(me)
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.002)
    bm = bmesh.from_edit_mesh(me); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    groups = {}
    for fi, c in cls.items(): groups.setdefault(c, []).append(fi)
    report = {}
    for c, fis in groups.items():
        loops = [l for fi in fis for l in bm.faces[fi].loops]
        uv = np.array([l[uvl].uv[:] for l in loops])
        mn, mx = uv.min(0), uv.max(0); sz = np.maximum(mx - mn, 1e-9)
        u0, v0, u1, v1 = UV_REGIONS[c]
        s = min((u1 - u0) / sz[0], (v1 - v0) / sz[1])
        off = np.array([u0 + ((u1 - u0) - sz[0] * s) / 2, v0 + ((v1 - v0) - sz[1] * s) / 2])
        new = off + (uv - mn) * s
        for l, q in zip(loops, new): l[uvl].uv = (float(q[0]), float(q[1]))
        report[c] = dict(faces=len(fis), scale=round(float(s), 4))
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode='OBJECT')
    ob["chosang_uv_regions"] = json.dumps(UV_REGIONS)
    return report

def principled(name, color, rough=0.5, alpha=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0); b.inputs["Roughness"].default_value = rough
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        try: m.surface_render_method = 'BLENDED'
        except Exception: pass
    return m

def skin_material(ob):
    m = principled("Skin", (0.78, 0.58, 0.48), 0.55)
    nt = m.node_tree
    t = nt.nodes.get("BaseColorTex") or nt.nodes.new("ShaderNodeTexImage")
    t.name = "BaseColorTex"; t.label = "BaseColor (앱이 채움 — 비워 둠)"; t.image = None; t.location = (-400, 300)
    ob.data.materials.clear(); ob.data.materials.append(m)
    return m

def bind(ob, arm, groups_weight=None):
    ob.parent = arm; ob.matrix_parent_inverse.identity()
    mod = ob.modifiers.get("Armature") or ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm; mod.use_vertex_groups = True; mod.use_bone_envelopes = False
    if groups_weight:
        for gname in groups_weight:
            vg = ob.vertex_groups.get(gname) or ob.vertex_groups.new(name=gname)
            vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')

def make_eye(name, center, coll, mats):
    old = bpy.data.objects.get(name)
    if old:
        m_old = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if m_old.users == 0: bpy.data.meshes.remove(m_old)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=36, radius=0.012, calc_uvs=True)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    c = Vector(center)
    for f in bm.faces:
        d = f.calc_center_median() - c
        ang = math.degrees(math.acos(max(-1.0, min(1.0, -d.y / d.length))))
        f.material_index = 2 if ang < 9.5 else (1 if ang < 29.0 else 0); f.smooth = True
    bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob

def arch_tube(bm, A, B, y_front, z0, z1, thick, n=26, a_deg=82):
    al = np.radians(np.linspace(-a_deg, a_deg, n))
    yc = y_front + B
    xs = A * np.sin(al); ys = yc - B * np.cos(al)
    nx = np.sin(al) / A; ny = -np.cos(al) / B; nl = np.hypot(nx, ny); nx, ny = nx / nl, ny / nl
    zm = 0.5 * (z0 + z1); r = 0.25 * (z1 - z0)
    prof = [(0.0, z0 + r * 0.3), (0.0, zm), (0.0, z1 - r * 0.3), (-thick * 0.5, z1), (-thick, zm), (-thick * 0.5, z0)]
    rings = []
    for i in range(n):
        ring = [bm.verts.new((xs[i] + d * nx[i], ys[i] + d * ny[i], z)) for d, z in prof]
        rings.append(ring)
    fs = []
    for i in range(n - 1):
        for k in range(6):
            fs.append(bm.faces.new((rings[i][k], rings[i][(k + 1) % 6], rings[i + 1][(k + 1) % 6], rings[i + 1][k])))
    fs.append(bm.faces.new(rings[0][::-1])); fs.append(bm.faces.new(rings[-1]))
    return [v for r in rings for v in r], fs

def make_mouth_inner(bust, coll, mats):
    meta = json.loads(bust["chosang_patch"])
    Vb = np.array([v.co[:] for v in bust.data.vertices])
    m = Vb[meta["mouth_loop"]].mean(0); my, mz = m[1], m[2]
    old = bpy.data.objects.get("Mouth_Inner")
    if old:
        m_old = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if m_old.users == 0: bpy.data.meshes.remove(m_old)
    me = bpy.data.meshes.new("Mouth_Inner"); bm = bmesh.new()
    parts = {}
    def add(name, verts, faces, mat):
        for f in faces: f.material_index = mat; f.smooth = True
        parts[name] = verts
    v, f = arch_tube(bm, 0.0235, 0.030, my + 0.0088, mz - 0.0010, mz + 0.0095, 0.0065); add("MI_UpperTeeth", v, f, 0)
    v, f = arch_tube(bm, 0.0215, 0.027, my + 0.0102, mz - 0.0105, mz - 0.0015, 0.0060); add("MI_LowerTeeth", v, f, 0)
    v, f = arch_tube(bm, 0.0245, 0.031, my + 0.0080, mz + 0.0090, mz + 0.0150, 0.0080); add("MI_UpperGum", v, f, 1)
    v, f = arch_tube(bm, 0.0225, 0.028, my + 0.0094, mz - 0.0160, mz - 0.0100, 0.0080); add("MI_LowerGum", v, f, 1)
    # 혀
    tv0 = len(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=1.0)
    tv = res["verts"]
    for vv in tv:
        x, y, z = vv.co
        z = z * (0.6 if z > 0 else 1.0)
        vv.co = Vector((x * 0.019, my + 0.030 + y * 0.026, mz - 0.0075 + z * 0.0068))
    tf = list({f for vv in tv for f in vv.link_faces}); add("MI_Tongue", tv, tf, 2)
    # 입안 주머니: 입술 안쪽 띠 2번째 링에서 뒤로
    lip = meta["lip_inner"]; L2 = Vb[lip[36:72]]
    c2 = L2.mean(0)
    ang = np.arctan2((L2[:, 2] - mz) / 0.006, (L2[:, 0] - m[0]) / 0.02)
    rings = []
    r0 = c2 + (L2 - c2) * 0.94 + np.array([0, 0.0004, 0]); rings.append(r0)
    for dy, A, Bz, zc in ((0.014, 0.022, 0.0115, -0.001), (0.030, 0.028, 0.021, -0.003), (0.046, 0.024, 0.018, -0.002), (0.058, 0.014, 0.010, 0.0)):
        rings.append(np.stack([A * np.cos(ang), np.full(len(ang), my + dy), mz + zc + Bz * np.sin(ang)], 1))
    RV = [[bm.verts.new(tuple(p)) for p in ring] for ring in rings]
    endv = bm.verts.new((0.0, my + 0.064, mz))
    cf = []
    n = len(ang)
    for k in range(len(RV) - 1):
        for j in range(n):
            cf.append(bm.faces.new((RV[k][j], RV[k][(j + 1) % n], RV[k + 1][(j + 1) % n], RV[k + 1][j])))
    for j in range(n):
        cf.append(bm.faces.new((RV[-1][j], RV[-1][(j + 1) % n], endv)))
    add("MI_Cavity", [v for r in RV for v in r] + [endv], cf, 3)
    # 법선: 치아·잇몸·혀는 바깥, 주머니는 안쪽(입 벌릴 때 안이 보이게)
    for name in ("MI_UpperTeeth", "MI_LowerTeeth", "MI_UpperGum", "MI_LowerGum", "MI_Tongue"):
        fs = list({f for vv in parts[name] for f in vv.link_faces})
        bmesh.ops.recalc_face_normals(bm, faces=fs)
    cfs = list({f for vv in parts["MI_Cavity"] for f in vv.link_faces})
    bmesh.ops.recalc_face_normals(bm, faces=cfs); bmesh.ops.reverse_faces(bm, faces=cfs)
    bm.verts.index_update()
    idx = {k: [vv.index for vv in vs] for k, vs in parts.items()}
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (0.5 + l.vert.co.x * 8, 0.5 + (l.vert.co.z - mz) * 8)
    bm.to_mesh(me); bm.free()
    for mt in mats: me.materials.append(mt)
    ob = bpy.data.objects.new("Mouth_Inner", me); coll.objects.link(ob)
    for k, ids in idx.items():
        vg = ob.vertex_groups.new(name=k); vg.add(ids, 1.0, 'REPLACE')
    ob["chosang_mouth_center"] = [float(m[0]), float(my), float(mz)]
    return ob

def run():
    tpl = bpy.data.collections["Chosang_Template"]
    bust = bpy.data.objects["Bust"]; arm = bpy.data.objects["Armature"]
    rep = layout_uv(bust)
    skin_material(bust)
    sc = principled("Eye_Sclera", (0.93, 0.91, 0.87), 0.15)
    ir = principled("Eye_Iris", (0.33, 0.22, 0.13), 0.30)
    pu = principled("Eye_Pupil", (0.004, 0.004, 0.004), 0.10)
    meta = json.loads(bust["chosang_patch"])
    eL = make_eye("Eye_L", meta["eyeball_center_left"], tpl, [sc, ir, pu])
    eR = make_eye("Eye_R", meta["eyeball_center_right"], tpl, [sc, ir, pu])
    mi = make_mouth_inner(bust, tpl, [principled("Teeth", (0.88, 0.85, 0.78), 0.25), principled("Gums", (0.62, 0.28, 0.28), 0.45),
                                      principled("Tongue", (0.60, 0.25, 0.25), 0.40), principled("Mouth_Interior", (0.10, 0.025, 0.03), 0.60)])
    bind(bust, arm)
    bind(eL, arm, ["Eye_L"]); bind(eR, arm, ["Eye_R"]); bind(mi, arm, ["Head"])
    # 프리비즈 조준점: 눈(0.44)·입(0.38) 사이 얼굴 중심
    aim = bpy.data.objects["Previz_Aim"]; aim.location = (0.0, -0.09, 0.41)
    cam = bpy.data.objects["Previz_Camera"]; cam.location = (0.0, -1.29, 0.41)
    cam["chosang_aim"] = [0.0, -0.09, 0.41]
    return rep, len(eL.data.vertices), len(mi.data.vertices)
