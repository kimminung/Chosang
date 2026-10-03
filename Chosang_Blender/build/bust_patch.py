
"""1단계: ARFaceGeometry.obj → Bust 얼굴 패치 (정점 0…1219 순서 그대로).
OBJ 는 mm 단위, Y-up, 얼굴 +Z, +X = 피사체 왼쪽 (ARKit 얼굴 좌표 ×1000), 면은 사각형 1152개, v 인덱스 = vt 인덱스.
배치: 눈꺼풀 구멍(24정점 루프) 중심 xy 에 반지름 12 mm 눈알을 두고(위·아래 눈꺼풀 정점이 구면 +0.3 mm 에 오도록 깊이 피팅),
      두 눈알 중심 간격 = 0.064 m 가 되도록 균일 스케일, 왼눈 중심 → 블렌더 (0.032, -0.0742, 0.44).
블렌더 좌표 = (x, -z, y)·s + T  (블렌더 Z-up·얼굴 -Y; USD Y-up 내보내기 시 계약 좌표가 됨)
"""
import bpy, bmesh, numpy as np, os, hashlib, collections, json

SRC = os.path.expanduser("~/Desktop/Chosang_Blender/source/ARFaceGeometry.obj")
EYE_TARGET_L = np.array([0.032, -0.0742, 0.44])
EYE_R_M = 0.012

def parse_obj(path):
    V, VT, F, FT = [], [], [], []
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if not p: continue
        if p[0] == 'v': V.append([float(x) for x in p[1:4]])
        elif p[0] == 'vt': VT.append([float(x) for x in p[1:3]])
        elif p[0] == 'f':
            F.append([int(c.split('/')[0]) - 1 for c in p[1:]])
            FT.append([int(c.split('/')[1]) - 1 for c in p[1:]])
    return np.array(V), np.array(VT), F, FT

def boundary_loops(F):
    ec = collections.Counter()
    for q in F:
        for i in range(len(q)):
            a, b = q[i], q[(i + 1) % len(q)]; ec[(min(a, b), max(a, b))] += 1
    # 방향 있는 경계 반변: 면 방향 그대로(a→b) — 루프 방향을 면 감김과 일치시킴
    nxt = {}
    for q in F:
        for i in range(len(q)):
            a, b = q[i], q[(i + 1) % len(q)]
            if ec[(min(a, b), max(a, b))] == 1: nxt[a] = b
    seen, loops = set(), []
    for s in sorted(nxt):
        if s in seen: continue
        L = [s]; seen.add(s); c = nxt[s]
        while c != s:
            L.append(c); seen.add(c); c = nxt[c]
        loops.append(L)
    return loops

def build():
    V, VT, F, FT = parse_obj(SRC)
    assert V.shape == (1220, 3) and len(F) == 1152, (V.shape, len(F))
    assert all(f == t for f, t in zip(F, FT)), "v/vt 인덱스 불일치"
    loops = boundary_loops(F)
    eyes = [l for l in loops if len(l) == 24]
    eyeL = [l for l in eyes if V[l][:, 0].mean() > 0][0]; eyeR = [l for l in eyes if V[l][:, 0].mean() < 0][0]
    mouth = [l for l in loops if len(l) == 36][0]; outer = [l for l in loops if len(l) == 56][0]
    # 눈알 깊이 피팅 (xy = 구멍 중심, z 만)
    cxy = V[eyeL][:, :2].mean(0)
    k = 64.0 / (2 * cxy[0])                     # OBJ mm → 최종 mm
    R = (EYE_R_M * 1000 + 0.3) / k
    P = V[eyeL]; d2 = ((P[:, :2] - cxy) ** 2).sum(1); ok = d2 < R * R
    cz = float(np.mean(P[ok, 2] - np.sqrt(R * R - d2[ok])))
    cL = np.array([cxy[0], cxy[1], cz]); cR = np.array([-cxy[0], cxy[1], cz])
    s = k / 1000.0
    to_b = lambda X: np.stack([X[..., 0], -X[..., 2], X[..., 1]], -1)
    T = EYE_TARGET_L - to_b(cL) * s
    B = to_b(V) * s + T
    me = bpy.data.meshes.get("Bust")
    ob = bpy.data.objects.get("Bust")
    if ob: bpy.data.objects.remove(ob, do_unlink=True)
    if me: bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("Bust")
    me.from_pydata(B.tolist(), [], F)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    # 루프 순서 = 면 순서·면 안 꼭짓점 순서 → vt 인덱스 = v 인덱스
    uv.data.foreach_set("uv", VT[lv].astype(np.float32).ravel())
    ob = bpy.data.objects.new("Bust", me)
    bpy.data.collections["Chosang_Template"].objects.link(ob)
    vg = ob.vertex_groups.new(name="ARKitFace"); vg.add(list(range(1220)), 1.0, 'REPLACE')
    # 메타데이터
    quads = np.array(F, np.int32)
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]], 0).reshape(-1, 3)
    tris_il = np.stack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]], 1).reshape(-1, 3)
    meta = dict(
        obj_sha256=hashlib.sha256(open(SRC, "rb").read()).hexdigest(),
        patch_vertex_count=1220, patch_face_count=1152,
        patch_quads_sha256=hashlib.sha256(quads.astype('<i4').tobytes()).hexdigest(),
        patch_tris_abc_acd_sha256=hashlib.sha256(tris_il.astype('<i4').tobytes()).hexdigest(),
        obj_to_blender="b = (x, -z, y) * scale + translate  (OBJ mm)",
        scale_m_per_obj_mm=s, translate=T.tolist(),
        eye_loop_left=eyeL, eye_loop_right=eyeR, mouth_loop=mouth, outer_loop=outer,
        eyeball_center_left=(to_b(cL) * s + T).tolist(), eyeball_center_right=(to_b(cR) * s + T).tolist(),
        eyeball_radius=EYE_R_M,
        eye_center_definition="eyeball center: xy = mean of the 24 lid-hole loop vertices, depth fitted so upper/lower lid vertices sit 0.3 mm outside a 12 mm sphere",
    )
    ob["chosang_patch"] = json.dumps(meta)
    return ob, meta, B

def check_official_importer(B):
    """블렌더 OBJ 가져오기가 정점 순서를 보존하는지 확인(결과만 보고, 메시는 지움)."""
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.obj_import(filepath=SRC, forward_axis='NEGATIVE_Z', up_axis='Y')
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    res = {}
    for o in new:
        co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        V, _, _, _ = parse_obj(SRC)
        ref = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)
        res[o.name] = dict(n=len(co), max_err_mm=float(np.abs(co - ref).max()) if len(co) == len(ref) else None,
                           order_preserved=bool(len(co) == len(ref) and np.abs(co - ref).max() < 1e-3))
        m = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(m)
    return res
