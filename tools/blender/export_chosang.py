# -*- coding: utf-8 -*-
"""
export_chosang.py — 초상(Chosang) 흉상 템플릿 내보내기 (Chosang_Template.blend, Blender 5.2 / 4.4+ 슬롯 액션, 4.1 호환 폴백)

실행 (블렌더 쪽에서):
  헤드리스:  /Applications/Blender.app/Contents/MacOS/Blender -b ~/Desktop/Chosang_Blender/Chosang_Template.blend \\
               --python tools/blender/export_chosang.py -- --out ~/Desktop/Chosang_Blender/Template [--no-usdz] [--previz] [--version 1.0]
  GUI:       Scripting 탭에서 이 파일을 열고 ▶ (출력 폴더는 CONFIG["out"] 또는 환경변수 CHOSANG_OUT)
  검증:      cd ChosangKit && swift run chosang-validate ~/Desktop/Chosang_Blender/Template

이 스크립트는 .blend 를 **저장하지 않는다**(읽기만). 필요한 변경은 Blender-요청.md 의 "블렌더 쪽 할 일" 로 돌린다.

읽는 것: Bust 커스텀 속성 4개 — chosang_patch(루프·범위·눈알 중심·해시·obj→blender 변환), chosang_uv_regions, chosang_rig(턱 피벗·입 중심),
        chosang_landmarks — 와 Chosang_Template·Library 컬렉션의 오브젝트, clip_* 액션(슬롯: OBJECT → Armature, KEY → Bust 셰이프키).
좌표 변환: USD(x, y, z) = 블렌더(x, z, −y). 확인값 코끝(정점 8) = (0, 0.4142, 0.1209), 왼눈알 중심 = (0.032, 0.44, 0.0722).
산출물 (<out>/):
  Template.usdz(Armature+Bust+Eye_L/R+Mouth_Inner) · EyesMouth.usdz(Bust 제외, 앱 오버레이) · library/<name>.usdz(Armature+오브젝트) · bust.mesh(CBM1 v2) · template.json(스키마 2) · library.json · clips/<name>.json · textures/*.png ·
  source/ARFaceGeometry.obj + ARFaceGeometry_LICENSE.txt(Apple 고지) · previz/<name>.mp4(--previz 또는 기존 렌더 복사)
Apply Modifiers 는 OFF — Bust 에 모디파이어가 있으면(Armature 외) 경고하고 USD 는 평가되지 않은 메시(셰이프키 보존)로 내보낸다.
"""

import bpy, json, math, os, sys, struct, hashlib, shutil
import numpy as np
from mathutils import Quaternion, Vector, Matrix

# ----------------------------------------------------------------------------- CONFIG
CONFIG = {
    "out": os.environ.get("CHOSANG_OUT", os.path.join(os.path.expanduser("~"), "Desktop", "Chosang_Blender", "Template")),
    "template_id": "chosang-bust",
    "template_version": "1.0",
    "fps": 30,
    "usdz": True,
    "previz": False,
    "template_collection": "Chosang_Template",
    "library_collection": "Library",
}
BUST, ARM, EYE_L, EYE_R, MOUTH_INNER = "Bust", "Armature", "Eye_L", "Eye_R", "Mouth_Inner"
BONES = ["Root", "Spine", "Neck", "Head", "Eye_L", "Eye_R"]
CLIP_BONES = ["Neck", "Head", "Eye_L", "Eye_R"]
GROUPS = ["ARKitFace", "Scalp", "EarL", "EarR", "Neck", "Shoulders", "LipInner", "LidInner"]
SKIN_GROUPS = ["Root", "Neck", "Head"]
ARKIT_52 = """eyeBlinkLeft eyeLookDownLeft eyeLookInLeft eyeLookOutLeft eyeLookUpLeft eyeSquintLeft eyeWideLeft
eyeBlinkRight eyeLookDownRight eyeLookInRight eyeLookOutRight eyeLookUpRight eyeSquintRight eyeWideRight
jawForward jawLeft jawRight jawOpen
mouthClose mouthFunnel mouthPucker mouthLeft mouthRight mouthSmileLeft mouthSmileRight mouthFrownLeft mouthFrownRight
mouthDimpleLeft mouthDimpleRight mouthStretchLeft mouthStretchRight mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper
mouthPressLeft mouthPressRight mouthLowerDownLeft mouthLowerDownRight mouthUpperUpLeft mouthUpperUpRight
browDownLeft browDownRight browInnerUp browOuterUpLeft browOuterUpRight
cheekPuff cheekSquintLeft cheekSquintRight noseSneerLeft noseSneerRight tongueOut""".split()
CLIPS = [("idle_breathe", 4, True), ("listen", 3, True), ("nod", 1, False), ("talk_a", 2, True), ("talk_b", 2, True), ("talk_c", 2, True),
         ("laugh", 1.5, False), ("surprise", 1, False), ("bow", 1.5, False), ("think", 3, True), ("blink_set", 2, True)]
# 랜드마크 이름 매핑: 블렌더 chosang_landmarks → 계약(template.json). 같으면 그대로.
LANDMARK_REQUIRED = ["eye_left_inner", "eye_left_outer", "eye_right_inner", "eye_right_outer", "nose_tip", "mouth_left", "mouth_right", "chin",
                     "ear_top_left", "ear_top_right", "shoulder_left", "shoulder_right"]
PREVIZ_CONTRACT = dict(aim=[0.0, 0.41, 0.09], position=[0.0, 0.41, 1.29], horizontalFOVDegrees=39.60, width=1920, height=1080, fps=30.0, bareBust=True)

# 좌표 변환 (블렌더 Z-up·얼굴 −Y → USD Y-up·얼굴 +Z)
C = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)      # usd = C @ b
def to_usd(p):
    p = np.asarray(p, float)
    return p @ C.T
def quat_to_usd(q):   # mathutils Quaternion (w,x,y,z) in blender space → [x, y, z, w] usd
    return [float(q.x), float(q.z), float(-q.y), float(q.w)]
def mat_to_usd(M):    # 4x4 (블렌더) → 4x4 (USD 좌표, 열 우선 16개)
    M = np.array(M, float)
    R = C @ M[:3, :3] @ C.T; t = C @ M[:3, 3]
    out = np.eye(4); out[:3, :3] = R; out[:3, 3] = t
    return [float(x) for x in out.T.ravel()]   # 열 우선


def log(msg): print("[export_chosang] " + str(msg), flush=True)
def fail(msg): raise RuntimeError("[export_chosang] " + msg)

def parse_args():
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]; it = iter(args)
        for a in it:
            if a == "--out": CONFIG["out"] = os.path.expanduser(next(it))
            elif a == "--no-usdz": CONFIG["usdz"] = False
            elif a == "--previz": CONFIG["previz"] = True
            elif a == "--version": CONFIG["template_version"] = next(it)
            elif a == "--id": CONFIG["template_id"] = next(it)

def jprop(ob, key):
    v = ob.get(key)
    if v is None: fail("%s 에 커스텀 속성 %s 가 없습니다 (build/ 스크립트가 넣음)" % (ob.name, key))
    return json.loads(v) if isinstance(v, str) else dict(v)

def fnv1a_u32(values):
    h = 0xcbf29ce484222325
    for v in values:
        for b in struct.pack("<I", int(v)):
            h ^= b; h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return "%016x" % h

def collection_objects(name):
    c = bpy.data.collections.get(name)
    if c is None: return []
    out = list(c.objects)
    for ch in c.children: out += collection_objects(ch.name)
    return out

# ----------------------------------------------------------------------------- Bust 읽기
def read_bust(ob, arm):
    me = ob.data
    n = len(me.vertices)
    if me.shape_keys is None: fail("Bust 에 셰이프키가 없습니다")
    blocks = me.shape_keys.key_blocks
    basis = blocks[0]
    Vb = np.empty(n * 3); basis.data.foreach_get("co", Vb); Vb = Vb.reshape(-1, 3)
    Nb = np.empty(n * 3); me.vertices.foreach_get("normal", Nb); Nb = Nb.reshape(-1, 3)
    # 삼각형: 다각형 팬 (사각형 → (a,b,c)+(a,c,d)) + 코너(루프) UV
    luv = None
    if me.uv_layers.active:
        layer = me.uv_layers.active.data
        luv = np.empty(len(me.loops) * 2, np.float32); layer.foreach_get("uv", luv); luv = luv.reshape(-1, 2)
    tris, tri_loops, quads_patch = [], [], []
    for p in me.polygons:
        vs = list(p.vertices); ls = list(p.loop_indices)
        if p.index < 1152: quads_patch.append(vs)
        for i in range(1, len(vs) - 1):
            tris.append((vs[0], vs[i], vs[i + 1])); tri_loops.append((ls[0], ls[i], ls[i + 1]))
    tris = np.array(tris, np.int64); tri_loops = np.array(tri_loops, np.int64)
    corner_uv = luv[tri_loops.ravel()] if luv is not None else np.zeros((len(tris) * 3, 2), np.float32)
    # UV: 정점당 첫 루프(호환용), 솔기 정점 수 세기 — 렌더·텍스처는 corner_uv 를 쓴다(bust.mesh v2)
    uv = np.zeros((n, 2), np.float32); seen = {}
    seam = set()
    if luv is not None:
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
        for li in range(len(lv)):
            v = int(lv[li]); q = (round(float(luv[li, 0]), 5), round(float(luv[li, 1]), 5))
            if v not in seen: seen[v] = q; uv[v] = luv[li]
            elif seen[v] != q: seam.add(v)
    # 셰이프 델타 (기준 대비)
    deltas = {}
    mags = {}
    for name in ARKIT_52:
        kb = blocks.get(name)
        if kb is None: continue
        K = np.empty(n * 3); kb.data.foreach_get("co", K); K = K.reshape(-1, 3)
        D = K - Vb
        deltas[name] = to_usd(D)
        mags[name] = float(np.linalg.norm(D, axis=1).max() * 1000)
    # 그룹
    def group_weights(gname):
        gi = ob.vertex_groups.find(gname)
        w = np.zeros(n)
        if gi < 0: return None
        for v in me.vertices:
            for g in v.groups:
                if g.group == gi: w[v.index] = g.weight
        return w
    groups, group_weights_out = {}, {}
    for g in GROUPS:
        w = group_weights(g)
        if w is None: groups[g] = []; continue
        if g == "Neck":
            ids = np.nonzero(w > 1e-6)[0]; groups[g] = ids.tolist(); group_weights_out[g] = [float(x) for x in w[ids]]
        else:
            groups[g] = np.nonzero(w > 0.5)[0].tolist()
    for g in ("Root", "Head"):
        w = group_weights(g)
        if w is not None:
            ids = np.nonzero(w > 1e-6)[0]; group_weights_out[g] = [float(x) for x in w[ids]]; groups.setdefault("_" + g, ids.tolist())
    # 스킨 (Root/Neck/Head → 뼈 인덱스)
    bone_index = {b: i for i, b in enumerate(BONES)}
    skinw = {g: group_weights(g) for g in SKIN_GROUPS}
    skin = np.zeros((n, 4), np.float32); skinj = np.zeros((n, 4), np.uint16)
    for i in range(n):
        infl = sorted([(float(skinw[g][i]) if skinw[g] is not None else 0.0, bone_index[g]) for g in SKIN_GROUPS], reverse=True)
        tot = sum(w for w, _ in infl) or 1.0
        for k, (w, j) in enumerate(infl[:4]): skin[i, k] = w / tot; skinj[i, k] = j
    return dict(V=to_usd(Vb), Vb=Vb, N=to_usd(Nb), tris=tris, quads_patch=quads_patch, uv=uv, corner_uv=corner_uv, seam_count=len(seam), deltas=deltas, mags=mags,
                groups=groups, group_weights=group_weights_out, skin=skin, skinj=skinj, shape_names=[kb.name for kb in blocks if kb.name != "Basis"])

def read_skeleton(arm):
    names, parents, rest = [], [], []
    for b in arm.data.bones:
        names.append(b.name); parents.append(b.parent.name if b.parent else None)
        rest.append(arm.matrix_world @ b.matrix_local)
    missing = [b for b in BONES if b not in names]
    if missing: fail("Armature 에 뼈가 없습니다: %s" % missing)
    order = [names.index(b) for b in BONES]
    return [names[i] for i in order], [parents[i] for i in order], [rest[i] for i in order]

def symmetry_map(V):
    cell = 0.004
    grid = {}
    for i, c in enumerate(V): grid.setdefault((int(c[0] // cell), int(c[1] // cell), int(c[2] // cell)), []).append(i)
    out = np.full(len(V), -1, np.int64)
    for i, c in enumerate(V):
        m = (-c[0], c[1], c[2]); key = (int(m[0] // cell), int(m[1] // cell), int(m[2] // cell))
        best, bd = -1, 4e-6
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), []):
                        d = (V[j][0] - m[0]) ** 2 + (V[j][1] - m[1]) ** 2 + (V[j][2] - m[2]) ** 2
                        if d < bd: bd, best = d, j
        out[i] = best
    return out

# ----------------------------------------------------------------------------- bust.mesh (CBM1)
def write_bust_mesh(path, B, names, parents, rest):
    V, N, uv, tris = B["V"], B["N"], B["uv"], B["tris"]
    with open(path, "wb") as f:
        f.write(b"CBM1")
        f.write(struct.pack("<IIIIII", 2, len(V), len(tris), len(B["deltas"]), len(names), 1 | 2))   # v2: flags bit1 = 코너 UV
        f.write(np.ascontiguousarray(V, "<f4").tobytes())
        f.write(np.ascontiguousarray(N, "<f4").tobytes())
        f.write(np.ascontiguousarray(uv, "<f4").tobytes())
        f.write(np.ascontiguousarray(B["corner_uv"], "<f4").tobytes())      # 3 × T × float2 (삼각형 코너 순서)
        f.write(np.ascontiguousarray(tris, "<u4").tobytes())
        for name in ARKIT_52:
            if name not in B["deltas"]: continue
            nb = name.encode("utf-8"); f.write(struct.pack("<I", len(nb))); f.write(nb)
            f.write(np.ascontiguousarray(B["deltas"][name], "<f4").tobytes())
        for i in range(len(V)):
            f.write(struct.pack("<4H", *[int(x) for x in B["skinj"][i]])); f.write(struct.pack("<4f", *[float(x) for x in B["skin"][i]]))
        for nm, par, M in zip(names, parents, rest):
            nb = nm.encode("utf-8"); f.write(struct.pack("<I", len(nb))); f.write(nb)
            f.write(struct.pack("<i", names.index(par) if par in names else -1)); f.write(struct.pack("<16f", *mat_to_usd(M)))

# ----------------------------------------------------------------------------- 클립
def slots_of(action):
    return list(action.slots) if hasattr(action, "slots") else []

def assign(idblock, action, slot_type):
    ad = idblock.animation_data or idblock.animation_data_create()
    ad.action = action
    for s in slots_of(action):
        if s.target_id_type == slot_type:
            try: ad.action_slot = s
            except Exception as e: log("슬롯 할당 실패 %s: %s" % (s.identifier, e))
            break
    return ad

def export_clips(out_dir, bust, arm):
    os.makedirs(os.path.join(out_dir, "clips"), exist_ok=True)
    scene = bpy.context.scene
    scene.render.fps = CONFIG["fps"]; scene.render.fps_base = 1.0
    key = bust.data.shape_keys
    rest_q = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
    saved = (arm.animation_data.action if arm.animation_data else None, key.animation_data.action if key.animation_data else None, scene.frame_current)
    names = []
    for name, seconds, loop in CLIPS:
        act = bpy.data.actions.get("clip_" + name)
        if act is None: log("클립 없음: clip_%s" % name); continue
        L = int(round(act.frame_range[1])); start = int(round(act.frame_range[0]))
        expected = int(round(seconds * CONFIG["fps"]))
        if start != 0 or L != expected: log("경고: clip_%s 프레임 범위 %d…%d (계약 0…%d)" % (name, start, L, expected))
        assign(arm, act, 'OBJECT'); assign(key, act, 'KEY')
        for kb in key.key_blocks: kb.value = 0.0          # 이전 클립이 남긴 값 제거 (애니메이션된 키만 frame_set 이 덮어씀)
        for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        frames = L - start + 1
        bones = {b: [] for b in CLIP_BONES}; shapes = {n: [] for n in ARKIT_52 if key.key_blocks.get(n)}
        for f in range(start, L + 1):
            scene.frame_set(f)
            for b in CLIP_BONES:
                pb = arm.pose.bones.get(b)
                if pb is None: bones[b].append([0, 0, 0, 1, 0, 0, 0]); continue
                qr = rest_q[b]
                ql = pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.to_quaternion()
                qw = qr @ ql @ qr.inverted()            # 블렌더 아마추어 공간의 회전 (뼈 피벗 기준)
                tw = qr @ pb.location                   # 블렌더 아마추어 공간의 이동
                bones[b].append(quat_to_usd(qw) + [float(x) for x in to_usd(np.array(tw))])
            for n in shapes: shapes[n].append(float(key.key_blocks[n].value))
        shapes = {k: v for k, v in shapes.items() if any(abs(x) > 1e-4 for x in v)}
        bones = {k: v for k, v in bones.items() if any(abs(x[0]) + abs(x[1]) + abs(x[2]) + abs(x[4]) + abs(x[5]) + abs(x[6]) > 1e-5 or abs(x[3] - 1) > 1e-5 for x in v)}
        clip = {"name": name, "fps": CONFIG["fps"], "frames": frames, "loop": bool(loop), "bones": bones, "shapes": shapes}
        with open(os.path.join(out_dir, "clips", name + ".json"), "w", encoding="utf-8") as fh: json.dump(clip, fh, ensure_ascii=False)
        names.append(name)
        log("clip %s: %d 프레임(0…%d), 뼈 %d, 셰이프 %d" % (name, frames, L, len(bones), len(shapes)))
    # 복구
    if arm.animation_data: arm.animation_data.action = saved[0]
    if key.animation_data: key.animation_data.action = saved[1]
    for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    for kb in key.key_blocks: kb.value = 0.0
    scene.frame_set(saved[2])
    return names

# ----------------------------------------------------------------------------- 라이브러리
def material_textures(ob):
    tex = {}
    for m in ob.data.materials:
        if not m or not m.use_nodes: continue
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE' and nd.image:
                role = "mask" if "mask" in (nd.label or "").lower() or "mask" in nd.image.name.lower() else ("cap" if "buzz" in nd.image.name.lower() and tex.get("base") else "base")
                fn = os.path.basename(bpy.path.abspath(nd.image.filepath)) if nd.image.filepath else nd.image.name + ".png"
                tex.setdefault(role, fn)
    return tex

def read_library():
    out = []
    for ob in collection_objects(CONFIG["library_collection"]):
        if ob.type != 'MESH': continue
        kind = str(ob.get("chosang_kind") or ob.name.split("_")[0].lower())
        if kind not in ("hair", "glasses", "beard", "shoulders"): continue
        e = dict(name=ob.name, kind=kind, bone=str(ob.get("chosang_bone") or "Head"), tintable=bool(ob.get("chosang_tint", kind != "glasses")),
                 vertexCount=len(ob.data.vertices), faceCount=len(ob.data.polygons), materials=[m.name for m in ob.data.materials if m],
                 textures=material_textures(ob), skinGroups=[vg.name for vg in ob.vertex_groups])
        attr = ob.data.attributes.get("chosang_bust_index")
        if attr is not None:
            arr = np.empty(len(ob.data.vertices), np.int64); attr.data.foreach_get("value", arr); e["bustIndex"] = [int(x) for x in arr]
        nb = ob.get("chosang_nose_bridge")
        if nb is not None: e["noseBridge"] = [float(x) for x in to_usd(np.array(list(nb)))]
        out.append(e)
    return out

# ----------------------------------------------------------------------------- USD
def export_usdz(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        try:
            o.hide_set(False); o.hide_viewport = False; o.select_set(True)
        except Exception as e: log("선택 불가 %s: %s" % (o.name, e))
    bpy.context.view_layer.objects.active = objects[0]
    props = {p.identifier for p in bpy.ops.wm.usd_export.get_rna_type().properties}
    want = dict(filepath=path, selected_objects_only=True, visible_objects_only=False, export_animation=False, export_hair=False,
                export_uvmaps=True, export_normals=True, export_materials=True, export_textures=True, overwrite_textures=True,
                export_armatures=True, export_shapekeys=True, only_deform_bones=False, use_instancing=False,
                # Blender 의 forward 는 "블렌더 −Y 가 가는 USD 축". 'Z' 로 내보내면 RealityKit 에서 얼굴이 −Z 를 향했다(1차 교차 검증, 180° 요) → NEGATIVE_Z.
                convert_orientation=True, export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y',
                root_prim_path='/Chosang', relative_paths=True, export_mesh_colors=False)
    if "export_textures_mode" in props and "export_textures" not in props: want["export_textures_mode"] = 'NEW'
    kwargs = {k: v for k, v in want.items() if k in props}
    dropped = sorted(set(want) - set(kwargs))
    if dropped: log("USD 내보내기에서 지원하지 않는 옵션 제외: %s" % dropped)
    if "convert_orientation" not in props:
        log("경고: 이 블렌더는 convert_orientation 이 없습니다 — USD 는 Z-up(upAxis=Z) 으로 저장되며 RealityKit 이 Y-up 으로 바꿔 읽습니다(검증기 usdz.position 으로 확인)")
    bpy.ops.wm.usd_export(**kwargs)
    bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- 프리비즈
def render_previz(out_dir, bust, arm, names):
    scene = bpy.context.scene; vl = bpy.context.view_layer
    cam = bpy.data.objects.get("Previz_Camera")
    if cam is None: log("Previz_Camera 가 없어 프리비즈 렌더를 건너뜁니다"); return
    def find(lc, name):
        if lc.collection.name == name: return lc
        for ch in lc.children:
            r = find(ch, name)
            if r: return r
    for n in (CONFIG["library_collection"], "_QA_Shapes", "_QA_Hair", "_Ref_Soban"):
        lc = find(vl.layer_collection, n)
        if lc: lc.exclude = True
    scene.camera = cam; scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1920, 1080, 100
    scene.render.fps = 30
    im = scene.render.image_settings
    try: im.media_type = 'VIDEO'
    except Exception: pass
    im.file_format = 'FFMPEG'; ff = scene.render.ffmpeg; ff.format = 'MPEG4'; ff.codec = 'H264'; ff.constant_rate_factor = 'HIGH'; ff.audio_codec = 'NONE'
    key = bust.data.shape_keys
    os.makedirs(os.path.join(out_dir, "previz"), exist_ok=True)
    import glob
    for name in names:
        act = bpy.data.actions.get("clip_" + name)
        if act is None: continue
        assign(arm, act, 'OBJECT'); assign(key, act, 'KEY')
        scene.frame_start = int(act.frame_range[0]); scene.frame_end = int(act.frame_range[1])
        base = os.path.join(out_dir, "previz", name + "_")
        scene.render.filepath = base
        bpy.ops.render.render(animation=True)
        made = sorted(glob.glob(base + "*.mp4"), key=os.path.getmtime)
        if made: os.replace(made[-1], os.path.join(out_dir, "previz", name + ".mp4"))
        log("previz %s" % name)

# ----------------------------------------------------------------------------- main
def main():
    parse_args()
    out = CONFIG["out"]; os.makedirs(out, exist_ok=True)
    blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    bust = bpy.data.objects.get(BUST); arm = bpy.data.objects.get(ARM)
    if bust is None or bust.type != 'MESH': fail("오브젝트 'Bust'(메시)가 없습니다")
    if arm is None or arm.type != 'ARMATURE': fail("오브젝트 'Armature' 가 없습니다")
    for o in (bust, arm):
        if any(abs(a - b) > 1e-6 for a, b in zip(sum([list(r) for r in o.matrix_world], []), sum([list(r) for r in Matrix.Identity(4)], []))):
            log("경고: %s 의 월드 변환이 항등이 아닙니다 — 좌표가 어긋날 수 있습니다(위치 0·회전 0·스케일 1 로 두세요)" % o.name)
    mods = [m.type for m in bust.modifiers if m.type != 'ARMATURE']
    if mods: log("경고: Bust 에 Armature 외 모디파이어 %s — 적용하거나 지우세요(USD 는 셰이프키 보존을 위해 미적용 메시로 나감)" % mods)

    patch = jprop(bust, "chosang_patch"); uvr = jprop(bust, "chosang_uv_regions"); rig = jprop(bust, "chosang_rig"); lm = jprop(bust, "chosang_landmarks")
    B = read_bust(bust, arm)
    V = B["V"]; n = len(V)
    # --- 검증값
    nose = V[lm.get("nose_tip", 8)]
    log("코끝(정점 %d) = %s (기대 0, 0.4142, 0.1209)" % (lm.get("nose_tip", 8), np.round(nose, 4).tolist()))
    eyeL = to_usd(np.array(patch["eyeball_center_left"])); eyeR = to_usd(np.array(patch["eyeball_center_right"]))
    log("왼눈알 중심 = %s (기대 0.032, 0.44, 0.0722)" % np.round(eyeL, 4).tolist())
    # --- 해시
    quads = np.array(B["quads_patch"], np.int32)
    if quads.shape != (1152, 4): log("경고: 패치 앞 1152개 면이 모두 사각형이 아닙니다: %s" % (quads.shape,))
    quads_sha = hashlib.sha256(quads.astype("<i4").tobytes()).hexdigest() if quads.ndim == 2 and quads.shape[1] == 4 else ""
    tris_patch = B["tris"][np.all(B["tris"] < 1220, axis=1)]
    tris_sha = hashlib.sha256(np.ascontiguousarray(tris_patch, "<i4").tobytes()).hexdigest()
    tris_fnv = fnv1a_u32(tris_patch.ravel())
    if quads_sha and quads_sha != patch.get("patch_quads_sha256"): log("경고: 패치 사각형 해시가 chosang_patch 기록과 다릅니다 (%s vs %s)" % (quads_sha[:12], str(patch.get("patch_quads_sha256"))[:12]))
    # --- 스켈레톤
    names, parents, rest = read_skeleton(arm)
    bone_rest = {nm: [float(x) for x in to_usd(np.array(M.translation))] for nm, M in zip(names, rest)}
    bone_parents = {nm: p for nm, p in zip(names, parents) if p}
    # --- 랜드마크 (+ 입 루프에서 lip mid 유도)
    landmarks = {k: int(v) for k, v in lm.items()}
    mouth = patch.get("mouth_loop", [])
    if mouth:
        P = B["Vb"][mouth]; mz = P[:, 2].mean()
        up = [v for v, p in zip(mouth, P) if p[2] > mz]; lo = [v for v, p in zip(mouth, P) if p[2] <= mz]
        if up: landmarks.setdefault("lip_upper_mid", int(min(up, key=lambda v: abs(B["Vb"][v][0]))))
        if lo: landmarks.setdefault("lip_lower_mid", int(min(lo, key=lambda v: abs(B["Vb"][v][0]))))
    missing_lm = [k for k in LANDMARK_REQUIRED if k not in landmarks]
    if missing_lm: log("경고: 랜드마크 없음 %s" % missing_lm)
    # --- 측정
    s = float(patch["scale_m_per_obj_mm"]); T = np.array(patch["translate"], float)
    obj_to_template = {"scale": [s], "translate": [float(x) for x in to_usd(T)]}
    chin_y = float(V[landmarks["chin"]][1]) if "chin" in landmarks else None
    mouth_center = [float(x) for x in to_usd(np.array(rig["mouth_center"]))]
    sym = symmetry_map(V)
    # --- Mouth_Inner
    mi = bpy.data.objects.get(MOUTH_INNER)
    mi_shapes = [kb.name for kb in mi.data.shape_keys.key_blocks if kb.name != "Basis"] if (mi and mi.data.shape_keys) else []
    # --- 라이브러리
    library = read_library()
    # --- 클립
    clip_names = export_clips(out, bust, arm)
    # --- bust.mesh
    write_bust_mesh(os.path.join(out, "bust.mesh"), B, names, parents, rest)
    # --- 텍스처·소스 복사
    tex_dir = os.path.join(out, "textures"); os.makedirs(tex_dir, exist_ok=True)
    tex_names = set()
    for img in bpy.data.images:
        if img.filepath and img.name.startswith("T_"):
            src = bpy.path.abspath(img.filepath)
            if os.path.isfile(src):
                dst = os.path.join(tex_dir, os.path.basename(src))
                if not os.path.exists(dst): shutil.copy2(src, dst)
                tex_names.add(os.path.basename(src))
    src_dir = os.path.join(out, "source"); os.makedirs(src_dir, exist_ok=True)
    for fn in ("ARFaceGeometry.obj", "ARFaceGeometry_LICENSE.txt"):
        for cand in (os.path.join(blend_dir, "source", fn), os.path.join(os.path.expanduser("~/Desktop/Chosang_Blender/source"), fn)):
            if os.path.isfile(cand):
                if os.path.abspath(cand) != os.path.abspath(os.path.join(src_dir, fn)): shutil.copy2(cand, os.path.join(src_dir, fn))
                break
    obj_path = os.path.join(src_dir, "ARFaceGeometry.obj")
    obj_sha = hashlib.sha256(open(obj_path, "rb").read()).hexdigest() if os.path.isfile(obj_path) else patch.get("obj_sha256")
    # 기존 previz 복사 (blend 옆 Template/previz)
    pv_src = os.path.join(blend_dir, "Template", "previz"); pv_dst = os.path.join(out, "previz")
    if os.path.isdir(pv_src) and os.path.abspath(pv_src) != os.path.abspath(pv_dst):
        os.makedirs(pv_dst, exist_ok=True)
        for fn in os.listdir(pv_src):
            if fn.endswith(".mp4"): shutil.copy2(os.path.join(pv_src, fn), os.path.join(pv_dst, fn))
    # --- 프리비즈 카메라 (씬 값 기록)
    cam = bpy.data.objects.get("Previz_Camera")
    previz = dict(PREVIZ_CONTRACT)
    if cam:
        previz["position"] = [float(x) for x in to_usd(np.array(cam.matrix_world.translation))]
        aim = cam.get("chosang_aim")
        if aim is not None: previz["aim"] = [float(x) for x in to_usd(np.array(list(aim)))]
        if cam.data.sensor_fit == 'HORIZONTAL' or cam.data.sensor_fit == 'AUTO':
            previz["horizontalFOVDegrees"] = float(math.degrees(2 * math.atan(cam.data.sensor_width / 2 / cam.data.lens)))
        previz["width"] = bpy.context.scene.render.resolution_x; previz["height"] = bpy.context.scene.render.resolution_y; previz["fps"] = float(bpy.context.scene.render.fps)
    # --- template.json
    groups = {g: B["groups"][g] for g in GROUPS}
    manifest = dict(
        schema=2, id=CONFIG["template_id"], version=CONFIG["template_version"],
        generator="export_chosang.py 2 / Blender %s" % bpy.app.version_string,
        vertexCount=n, triangleCount=int(len(B["tris"])), patchVertexCount=1220, patchFaceCount=int(len(quads)),
        objSHA256=obj_sha, patchQuadsSHA256=quads_sha, patchTrianglesSHA256=tris_sha, patchTriangleHash=tris_fnv,
        objToTemplate=obj_to_template,
        landmarks=landmarks, visionIndices={}, groups=groups, groupWeights=B["group_weights"],
        patchLoops={"eye_left": patch.get("eye_loop_left", []), "eye_right": patch.get("eye_loop_right", []), "mouth": mouth, "outer": patch.get("outer_loop", [])},
        uvRegions={k: [float(x) for x in v] for k, v in uvr.items()},
        symmetryMap=[int(x) for x in sym],
        eyeL=[float(x) for x in eyeL], eyeR=[float(x) for x in eyeR], eyeRadius=float(patch.get("eyeball_radius", 0.012)),
        eyeSpacing=float(np.linalg.norm(eyeL - eyeR)), mouthCenter=mouth_center, chinY=chin_y, crownY=float(V[:, 1].max()),
        jawPivot=[float(x) for x in to_usd(np.array(rig["jaw_pivot"]))], jawOpenDegrees=float(rig["jaw_open_deg"]),
        jawOpenTranslate=[float(x) for x in to_usd(np.array(rig["jaw_open_translate"]))],
        boneRest=bone_rest, boneParents=bone_parents,
        shapeKeys=B["shape_names"], shapeMaxDisplacementMM=B["mags"], mouthInnerShapes=mi_shapes,
        libraryObjects=[e["name"] for e in library], clips=clip_names, previz=previz, textures=sorted(tex_names),
        uvSeamVertexCount=int(B["seam_count"]),
    )
    with open(os.path.join(out, "template.json"), "w", encoding="utf-8") as f: json.dump(manifest, f, ensure_ascii=False)
    with open(os.path.join(out, "library.json"), "w", encoding="utf-8") as f: json.dump(library, f, ensure_ascii=False)
    log("template.json: 정점 %d · 삼각형 %d · 셰이프 %d · 그룹 %s · 라이브러리 %d · 클립 %d · 솔기 정점 %d" %
        (n, len(B["tris"]), len(B["shape_names"]), {k: len(v) for k, v in groups.items()}, len(library), len(clip_names), B["seam_count"]))
    # --- USDZ
    if CONFIG["usdz"]:
        base = [o for o in collection_objects(CONFIG["template_collection"]) if o.type in ('MESH', 'ARMATURE')]
        export_usdz(os.path.join(out, "Template.usdz"), base)
        log("Template.usdz: %d 오브젝트 (%s) — 라이브러리는 library/<name>.usdz 로 따로" % (len(base), ", ".join(o.name for o in base)))
        # 앱 오버레이용: Bust 없이 눈알·입안만 (앱은 Bust 를 bust.mesh 로 직접 그리므로 USDZ 의 Bust 파트를 숨길 필요가 없게)
        acc = [o for o in base if o.name != BUST]
        export_usdz(os.path.join(out, "EyesMouth.usdz"), acc)
        log("EyesMouth.usdz: %s" % ", ".join(o.name for o in acc))
        # RealityKit 은 한 아마추어 아래 스킨 메시를 **모델 하나(파트 여러 개)** 로 합치므로, 머리카락·안경 등은 개별 USDZ 로 내보내야 엔티티로 켜고 끌 수 있다.
        lib_dir = os.path.join(out, "library"); os.makedirs(lib_dir, exist_ok=True)
        for o in [o for o in collection_objects(CONFIG["library_collection"]) if o.type == 'MESH']:
            export_usdz(os.path.join(lib_dir, o.name + ".usdz"), [arm, o])
        log("library/*.usdz: %d 개" % len([o for o in collection_objects(CONFIG["library_collection"]) if o.type == 'MESH']))
    if CONFIG["previz"]:
        render_previz(out, bust, arm, clip_names)
    log("완료 → %s   (검증: cd ChosangKit && swift run chosang-validate '%s')" % (out, out))


if __name__ == "__main__":
    main()
