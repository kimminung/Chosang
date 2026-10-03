"""눈알 중심 보정: 눈꺼풀 구멍 24정점이 모두 구면(r)+0.2 mm 바깥에 오도록 중심을 뒤(+Y)로 Δ 이동.
Bust 메타·눈꺼풀 안쪽 띠(기본 자세)를 갱신한다. (눈알 오브젝트·눈 뼈는 이후 단계가 메타에서 만든다)"""
import bpy, numpy as np, json
def fix(bust):
    me = bust.data; meta = json.loads(bust["chosang_patch"]); R = meta["eyeball_radius"] + 0.0002
    if me.shape_keys: bust.shape_key_clear()
    n = len(me.vertices); V = np.empty(n * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    need = []
    for key in ("left", "right"):
        c = np.array(meta["eyeball_center_" + key]); P = V[meta["eye_loop_" + key]]
        f = -(P[:, 1] - c[1]); h = P[:, 2] - c[2]; dx = P[:, 0] - c[0]; rem = R * R - h * h - dx * dx
        need.append(np.max(np.where(rem > 0, np.sqrt(np.maximum(rem, 0)) - f, 0)))
    delta = float(max(0.0, max(need)))
    for key in ("left", "right"): meta["eyeball_center_" + key][1] += delta
    meta["eye_center_shift_back_mm"] = delta * 1000
    lidI = meta["lid_inner"]
    for k, key in enumerate(("left", "right")):
        loop = meta["eye_loop_" + key]; c = np.array(meta["eyeball_center_" + key]); r = meta["eyeball_radius"]
        Q = V[loop]; d1 = Q - c; d1 /= np.linalg.norm(d1, axis=1, keepdims=True)
        d2 = (Q - c) + np.array([0, 0.006, 0]); d2 /= np.linalg.norm(d2, axis=1, keepdims=True)
        V[lidI[48 * k:48 * k + 24]] = c + d1 * (r - 0.0002); V[lidI[48 * k + 24:48 * k + 48]] = c + d2 * (r - 0.0015)
    me.vertices.foreach_set("co", V.ravel()); me.update()
    bust["chosang_patch"] = json.dumps(meta)
    return delta
