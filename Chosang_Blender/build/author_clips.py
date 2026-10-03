
"""초상 프리비즈 클립 작성기 — 다시 실행해도 같은 결과(기존 clip_* 액션을 지우고 새로 만든다).
규칙: 액션 이름 clip_<name>, 30 fps, 프레임 0…L(끝 프레임 포함). 루프 클립은 0 프레임 = L 프레임, use_cyclic.
뼈 트랙: Neck·Head·Eye_L·Eye_R 의 rotation_quaternion + location (모든 클립에 존재, 안 쓰면 항등).
셰이프키 트랙: Bust 의 shape_keys 에 같은 액션을 두 번째 슬롯으로 할당(Blender 4.4+ 슬롯 액션).
각도 규약(블렌더 월드, 얼굴 = -Y): pitch + = 고개/시선 아래, yaw + = 피사체 왼쪽(+X), roll + = 정수리가 +X 쪽으로 기울어짐.
"""
import bpy, math
from mathutils import Quaternion, Vector, Matrix

FPS = 30
BONES = ("Neck", "Head", "Eye_L", "Eye_R")

def sine_keys(amp, cycles, phase, L, step=15):
    return [(f, amp * math.sin(2 * math.pi * cycles * f / L + phase)) for f in range(0, L + 1, step)]

def blink(c, peak=1.0, close=3, hold=1, open_=5):
    return [(c - close, 0.0), (c, peak), (c + hold, peak), (c + hold + open_, 0.0)]

def zip3(p, y, r):
    """세 채널 키 목록(각 [(f,v)])을 프레임 합집합으로 합쳐 [(f,(p,y,r))] 로. 없는 프레임은 선형 보간."""
    def at(keys, f):
        if not keys: return 0.0
        keys = sorted(keys)
        if f <= keys[0][0]: return keys[0][1]
        for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
            if f0 <= f <= f1: return v0 + (v1 - v0) * (f - f0) / max(1e-9, (f1 - f0))
        return keys[-1][1]
    frames = sorted({f for ks in (p, y, r) for f, _ in ks})
    return [(f, (at(p, f), at(y, f), at(r, f))) for f in frames]

def eyes(pitch, yaw):
    k = zip3(pitch, yaw, [])
    return {"Eye_L": {"rot": k}, "Eye_R": {"rot": k}}

def shapes(*pairs):
    out = {}
    for names, keys in pairs:
        for n in (names if isinstance(names, (list, tuple)) else [names]):
            out.setdefault(n, []).extend(keys)
    return out

LR = lambda base: (base + "Left", base + "Right")

def clip_defs():
    C = {}
    # 1) idle_breathe 4 s 루프 — 호흡 고개 미세 움직임, 2초마다 깜빡임
    L = 120
    C["idle_breathe"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3(sine_keys(0.7, 1, 0, L), [], []), "loc": [(f, (0.0, 0.0, 0.0006 * math.sin(2 * math.pi * f / L))) for f in range(0, L + 1, 15)]},
        "Head": {"rot": zip3(sine_keys(-0.45, 1, 0.6, L), sine_keys(1.2, 1, 1.3, L), sine_keys(0.8, 1, 2.4, L))},
        **eyes([(0, 0), (38, 0), (40, 0.8), (78, 0.8), (80, -0.5), (112, -0.5), (114, 0), (120, 0)],
               [(0, 0), (38, 0), (40, 2.5), (78, 2.5), (80, -1.5), (112, -1.5), (114, 0), (120, 0)])},
        shapes=shapes((LR("eyeBlink"), [(0, 0)] + blink(22) + blink(82) + [(120, 0)])))
    # 2) listen 3 s 루프 — 앞으로 약간 기울임 + 고개 갸웃, 눈썹 살짝, 작은 끄덕임 1회
    L = 90
    C["listen"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3([(0, 4.0), (45, 4.4), (90, 4.0)], [], []), "loc": [(0, (0, 0.006, 0)), (90, (0, 0.006, 0))]},
        "Head": {"rot": zip3([(0, -2.0), (36, -2.0), (44, 1.5), (52, -3.0), (60, -2.0), (90, -2.0)], [(0, -3.0), (90, -3.0)], [(0, 4.0), (30, 4.8), (90, 4.0)])},
        **eyes([(0, 0), (90, 0)], [(0, 2.2), (20, 2.2), (22, 3.6), (58, 3.6), (60, 2.2), (90, 2.2)])},
        shapes=shapes(("browInnerUp", [(0, 0.22), (40, 0.22), (46, 0.38), (58, 0.22), (90, 0.22)]),
                      (LR("browOuterUp"), [(0, 0.1), (90, 0.1)]), (LR("mouthSmile"), [(0, 0.1), (90, 0.1)]),
                      (LR("eyeBlink"), [(0, 0)] + blink(70) + [(90, 0)])))
    # 3) nod 1 s — 끄덕임 2회
    L = 30
    hp = [(0, 0), (6, 9), (11, 2), (17, 8), (23, 1), (30, 0)]
    C["nod"] = dict(L=L, loop=False, bones={
        "Neck": {"rot": zip3([(0, 0), (6, 3), (11, 0.8), (17, 2.6), (23, 0.4), (30, 0)], [], [])},
        "Head": {"rot": zip3(hp, [], [])},
        **eyes([(0, 0), (6, -7.2), (11, -1.7), (17, -6.4), (23, -0.8), (30, 0)], [])},
        shapes=shapes(("browInnerUp", [(0, 0), (5, 0.15), (25, 0.1), (30, 0)]), (LR("eyeBlink"), [(0, 0)] + blink(6, 0.8) + [(30, 0)])))
    # 4) talk_a/b/c 2 s 루프 — 입은 비움(앱이 비셈), 고개·눈썹 제스처만
    L = 60
    C["talk_a"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3([(0, 1.0), (30, 1.6), (60, 1.0)], [], [])},
        "Head": {"rot": zip3([(0, 0), (8, 3.5), (16, -0.5), (34, 2.5), (42, -0.5), (60, 0)], [(0, 1.5), (20, -1.5), (40, 2.5), (60, 1.5)], [(0, 0), (30, 1.5), (60, 0)])},
        **eyes([(0, 0), (8, -1.7), (16, 0.2), (34, -1.2), (42, 0.2), (60, 0)], [(0, -1.05), (20, 1.05), (40, -1.75), (60, -1.05)])},
        shapes=shapes(("browInnerUp", [(0, 0.05), (6, 0.35), (16, 0.08), (32, 0.25), (42, 0.05), (60, 0.05)]),
                      (LR("browOuterUp"), [(0, 0.03), (6, 0.28), (16, 0.05), (32, 0.18), (42, 0.03), (60, 0.03)]),
                      (LR("eyeBlink"), [(0, 0)] + blink(50) + [(60, 0)])))
    C["talk_b"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3([(0, 2.0), (30, 2.3), (60, 2.0)], [], [])},
        "Head": {"rot": zip3([(0, 0.5), (22, 2.0), (40, -0.5), (60, 0.5)], [(0, -2.0), (15, 2.5), (45, -3.0), (60, -2.0)], [(0, -2.0), (15, 4.5), (30, 0.5), (45, -4.0), (60, -2.0)])},
        **eyes([(0, 0), (60, 0)], [(0, 1.4), (15, -1.75), (45, 2.1), (60, 1.4)])},
        shapes=shapes(("browInnerUp", [(0, 0.05), (36, 0.08), (41, 0.45), (50, 0.12), (60, 0.05)]),
                      (LR("eyeBlink"), [(0, 0)] + blink(27) + [(60, 0)])))
    C["talk_c"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3([(0, 1.5), (60, 1.5)], [(0, -1.5), (30, 1.5), (60, -1.5)], [])},
        "Head": {"rot": zip3([(0, 0), (12, 1.8), (30, 0.3), (44, 1.5), (60, 0)], [(0, -5.5), (30, 5.5), (60, -5.5)], [(0, -1.0), (30, 1.0), (60, -1.0)])},
        **eyes([(0, 0), (60, 0)], [(0, 0), (2, 4), (14, 2), (28, 0), (30, 0), (32, -4), (44, -2), (58, 0), (60, 0)])},
        shapes=shapes(("browOuterUpLeft", [(0, 0.05), (16, 0.5), (28, 0.1), (60, 0.05)]), ("browDownRight", [(0, 0), (16, 0.22), (28, 0), (60, 0)]),
                      ("browInnerUp", [(0, 0.05), (46, 0.3), (54, 0.05), (60, 0.05)]), (LR("eyeBlink"), [(0, 0)] + blink(30) + [(60, 0)])))
    # 5) laugh 1.5 s — 고개 뒤로, 눈 감김, 미소·턱
    L = 45
    C["laugh"] = dict(L=L, loop=False, bones={
        "Neck": {"rot": zip3([(0, 0), (6, -3), (30, -3), (45, 0)], [], [])},
        "Head": {"rot": zip3([(0, 0), (6, -10), (10, -13), (14, -9.5), (18, -13), (22, -9.5), (26, -12.5), (30, -9), (36, -5), (45, 0)], [(0, 0), (20, 1.5), (45, 0)], [(0, 0), (10, 2.5), (30, 2.0), (45, 0)])},
        **eyes([(0, 0), (6, 5), (30, 4), (45, 0)], [])},
        shapes=shapes((LR("mouthSmile"), [(0, 0), (5, 0.85), (32, 0.85), (45, 0)]),
                      ("jawOpen", [(0, 0), (6, 0.3), (10, 0.45), (14, 0.28), (18, 0.45), (22, 0.28), (26, 0.42), (30, 0.25), (36, 0.12), (45, 0)]),
                      (LR("eyeBlink"), [(0, 0), (6, 0.75), (30, 0.75), (40, 0.1), (45, 0)]), (LR("eyeSquint"), [(0, 0), (6, 0.65), (30, 0.65), (45, 0)]),
                      (LR("cheekSquint"), [(0, 0), (6, 0.6), (32, 0.6), (45, 0)]), ("browInnerUp", [(0, 0), (8, 0.25), (30, 0.2), (45, 0)]),
                      (LR("mouthUpperUp"), [(0, 0), (6, 0.25), (30, 0.25), (45, 0)])))
    # 6) surprise 1 s — eyeWide·browInnerUp·jawOpen 작게
    L = 30
    C["surprise"] = dict(L=L, loop=False, bones={
        "Neck": {"rot": zip3([(0, 0), (4, -2), (30, -0.5)], [], []), "loc": [(0, (0, 0, 0)), (4, (0, -0.006, 0)), (18, (0, -0.005, 0)), (30, (0, -0.002, 0))]},
        "Head": {"rot": zip3([(0, 0), (4, -5), (18, -4.5), (30, -1.5)], [], [])}},
        shapes=shapes((LR("eyeWide"), [(0, 0), (3, 0.95), (16, 0.9), (30, 0.2)]), ("browInnerUp", [(0, 0), (3, 0.9), (16, 0.85), (30, 0.2)]),
                      (LR("browOuterUp"), [(0, 0), (3, 0.75), (16, 0.7), (30, 0.15)]), ("jawOpen", [(0, 0), (4, 0.22), (16, 0.2), (30, 0.05)]),
                      ("mouthFunnel", [(0, 0), (4, 0.12), (16, 0.1), (30, 0)])))
    # 7) bow 1.5 s — 목례: Neck+Head 앞으로 25°, 시선 아래, 복귀
    L = 45
    C["bow"] = dict(L=L, loop=False, bones={
        "Neck": {"rot": zip3([(0, 0), (14, 12), (26, 12), (42, 0.5), (45, 0)], [], []), "loc": [(0, (0, 0, 0)), (14, (0, 0.01, 0)), (26, (0, 0.01, 0)), (45, (0, 0, 0))]},
        "Head": {"rot": zip3([(0, 0), (14, 13), (26, 13), (42, 0.5), (45, 0)], [], [])},
        **eyes([(0, 0), (10, 15), (28, 15), (40, 3), (45, 0)], [])},
        shapes=shapes((LR("eyeLookDown"), [(0, 0), (10, 0.5), (28, 0.5), (40, 0.1), (45, 0)]), (LR("eyeBlink"), [(0, 0)] + blink(32, 0.9) + [(45, 0)])))
    # 8) think 3 s 루프 — 시선 위·옆, 한쪽 browDown, mouthPress
    L = 90
    ey = [(0, 14), (40, 14), (43, 9), (78, 9), (81, 14), (90, 14)]
    ep = [(0, -12), (40, -12), (43, -8), (78, -8), (81, -12), (90, -12)]
    C["think"] = dict(L=L, loop=True, bones={
        "Neck": {"rot": zip3([(0, 0.5), (90, 0.5)], [], [])},
        "Head": {"rot": zip3([(0, -3), (45, -4), (90, -3)], [(0, 5), (45, 6.5), (90, 5)], [(0, 5), (45, 6), (90, 5)])},
        **eyes(ep, ey)},
        shapes=shapes((LR("eyeLookUp"), [(0, 0.45), (40, 0.45), (43, 0.32), (78, 0.32), (81, 0.45), (90, 0.45)]),
                      (("eyeLookOutLeft", "eyeLookInRight"), [(0, 0.4), (40, 0.4), (43, 0.28), (78, 0.28), (81, 0.4), (90, 0.4)]),
                      ("browDownRight", [(0, 0.4), (45, 0.45), (90, 0.4)]), ("browInnerUp", [(0, 0.15), (90, 0.15)]),
                      (LR("mouthPress"), [(0, 0.35), (45, 0.42), (90, 0.35)]), ("mouthRollLower", [(0, 0.12), (90, 0.12)]),
                      (LR("eyeBlink"), [(0, 0)] + blink(60) + [(90, 0)])))
    # 9) blink_set 2 s 루프 — 깜빡임만
    L = 60
    C["blink_set"] = dict(L=L, loop=True, bones={}, shapes=shapes((LR("eyeBlink"), [(0, 0)] + blink(14) + blink(46) + [(60, 0)])))
    return C

def q_world(p, y, r):
    return (Quaternion((0, 0, 1), math.radians(y)) @ Quaternion((1, 0, 0), math.radians(p)) @ Quaternion((0, 1, 0), math.radians(r)))

def fcurves_of(act):
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield cb, cb.fcurves

def author(arm_name="Armature", bust_name="Bust", only=None):
    arm = bpy.data.objects[arm_name]
    bust = bpy.data.objects.get(bust_name)
    key = bust.data.shape_keys if (bust and bust.type == 'MESH') else None
    rest = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
    report = {}
    for name, d in clip_defs().items():
        if only and name not in only: continue
        an = "clip_" + name
        old = bpy.data.actions.get(an)
        if old: bpy.data.actions.remove(old)
        act = bpy.data.actions.new(an); act.use_fake_user = True
        L = d["L"]
        act.use_frame_range = True; act.frame_start = 0; act.frame_end = L; act.use_cyclic = bool(d["loop"])
        act["chosang_fps"] = FPS; act["chosang_loop"] = bool(d["loop"]); act["chosang_frames"] = L + 1; act["chosang_seconds"] = L / FPS
        ad = arm.animation_data_create(); ad.action = act
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        for bn in BONES:
            pb = arm.pose.bones[bn]; qr = rest[bn]
            spec = d["bones"].get(bn, {})
            rk = spec.get("rot") or [(0, (0, 0, 0)), (L, (0, 0, 0))]
            prev = None
            for f, (p, y, r) in sorted(rk):
                q = qr.inverted() @ (q_world(p, y, r) if bn.startswith("Neck") or bn.startswith("Head") else q_world(p, y, 0)) @ qr
                if prev is not None and prev.dot(q) < 0: q.negate()
                prev = q.copy()
                pb.rotation_quaternion = q; pb.keyframe_insert("rotation_quaternion", frame=f, group=bn)
            lk = spec.get("loc") or [(0, (0, 0, 0)), (L, (0, 0, 0))]
            for f, (dx, fwd, up) in sorted(lk):
                t = qr.inverted() @ Vector((dx, -fwd, up))
                pb.location = t; pb.keyframe_insert("location", frame=f, group=bn)
        nsh = 0; missing = []
        if key:
            kad = key.animation_data_create(); kad.action = act
            for sn, ks in d["shapes"].items():
                kb = key.key_blocks.get(sn)
                if kb is None: missing.append(sn); continue
                for f, v in sorted(ks):
                    kb.value = v; kb.keyframe_insert("value", frame=f)
                kb.value = 0.0; nsh += 1
            kad.action = None
        for cb, fcs in fcurves_of(act):
            for fc in fcs:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'; kp.handle_left_type = 'AUTO_CLAMPED'; kp.handle_right_type = 'AUTO_CLAMPED'
                if d["loop"] and not any(m.type == 'CYCLES' for m in fc.modifiers):
                    fc.modifiers.new('CYCLES')
                fc.update()
        ad.action = None
        report[an] = dict(frames=L + 1, loop=d["loop"], shapes=nsh, missing_shapes=missing, slots=[s.identifier for s in act.slots])
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    if key:
        for kb in key.key_blocks: kb.value = 0.0
    return report
