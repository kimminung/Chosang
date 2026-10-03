"""귀 v2 — Bust 에 왼쪽/오른쪽 귀를 별도 연결 성분으로 추가(새 정점은 기존 정점 뒤). 결정적, 난수 없음.
v1 은 귓불(아래)이 좁은 타원 끝이라 뾰족했고 위아래 모두 같은 만큼(약 13 mm) 튀어나왔다.
v2: 실제 귀 윤곽 제어점(스플라인) — 위(이륜)는 넓고 둥글게, 아래(귓불)는 둥근 덮개로.
    돌출각을 높이에 따라 다르게(귓불 13° → 가운데 19° → 위 22°) 해서 귓불은 머리 가까이, 위·뒤 이륜이 가장 바깥.
    림 말림 방향은 윤곽의 실제 바깥 법선(이전: 귓구멍 중심에서의 방사 방향 → 위쪽에서 비틀림).
위상은 v1 과 같다(중심 1 + 링 15 × 28) → 정점 수·순서·면 동일."""
import bpy, bmesh, numpy as np, math, json

NT = 28
FRONT_R = [0.12, 0.26, 0.40, 0.53, 0.64, 0.74, 0.83, 0.91, 0.97, 1.0]
CTRL = [(1.5, 12), (4.5, 21.5), (9, 28.5), (15, 31), (21.5, 28.5), (26, 21), (27.5, 11), (27, 1), (24.5, -9.5), (20, -18), (13, -23.5), (6.5, -22), (3, -15), (1, -7), (0, 2)]
SCALE = 0.00105                       # 제어점 mm → m
CC = np.array([9.0, -2.0]) * SCALE   # 귓구멍(concha) 중심

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def catmull_closed(P, n_per=60):
    P = np.asarray(P, float); m = len(P); out = []
    for i in range(m):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for k in range(n_per):
            t = k / n_per
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

def outline(th):
    C = catmull_closed(CTRL) * SCALE
    ang = np.arctan2(C[:, 1] - CC[1], C[:, 0] - CC[0]); rad = np.hypot(C[:, 0] - CC[0], C[:, 1] - CC[1])
    o = np.argsort(ang); a = ang[o]; r = rad[o]
    ae = np.r_[a - 2 * np.pi, a, a + 2 * np.pi]; re_ = np.r_[r, r, r]
    def at(t):
        tw = (t + np.pi) % (2 * np.pi) - np.pi
        R = np.interp(tw, ae, re_)
        return CC + R[:, None] * np.stack([np.cos(t), np.sin(t)], 1)
    P = at(th); T = at(th + 1e-3) - P
    N = np.stack([T[:, 1], -T[:, 0]], 1); N /= np.linalg.norm(N, axis=1, keepdims=True)   # 반시계 곡선의 바깥 법선
    return P, N

def outline_samples(n=NT):
    """윤곽을 호 길이로 고르게 n 점 샘플(반시계: 뒤 → 위 → 앞 → 아래). 귓구멍 중심 기준 균등 각도로 뽑으면
    중심이 앞쪽에 치우쳐 있어 위·뒤 테두리에 점이 3~4개뿐이라 각지고 뾰족해 보였다(v2 초판의 문제)."""
    C = catmull_closed(CTRL, 80)[::-1] * SCALE
    Cc = np.vstack([C, C[:1]])
    cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Cc, axis=0), axis=1))]; L = cum[-1]
    i0 = int(np.argmin(np.abs(np.arctan2(C[:, 1] - CC[1], C[:, 0] - CC[0]))))
    tg = (cum[i0] + L * np.arange(n) / n) % L
    at = lambda q: np.stack([np.interp(q, cum, Cc[:, 0]), np.interp(q, cum, Cc[:, 1])], 1)
    P = at(tg); T = at((tg + L * 1e-3) % L) - P
    N = np.stack([T[:, 1], -T[:, 0]], 1); N /= np.linalg.norm(N, axis=1, keepdims=True)
    th = np.arctan2(P[:, 1] - CC[1], P[:, 0] - CC[0]) % (2 * np.pi)
    return P, N, th

def ear_rings(side):
    a = math.radians(15)
    BASE = 0.004          # 귀뿌리 두께: 오목한 귓바퀴 바닥이 머리 표면 밖에 남도록 전체를 4 mm 띄움
    up = np.array([0, math.sin(a), math.cos(a)]); back = np.array([0, math.cos(a), -math.sin(a)])
    xo = np.array([float(side), 0, 0])
    O = np.array([side * 0.0688, -0.006, 0.4175])
    OP, ON, th = outline_samples()                               # th: 각 점의 귓구멍 중심 기준 각(0 뒤, π/2 위)
    st, ct = np.sin(th), np.cos(th)
    lobe = smoothstep(0.55, 0.9, -st); top = smoothstep(0.1, 0.6, st)
    front = smoothstep(0.2, 0.8, -ct) * (1 - smoothstep(0.010, 0.016, OP[:, 1]))   # 머리에 붙는 앞쪽은 이륜 뿌리(t≈13 mm) 아래만
    dfr = (th - (math.pi + 0.18) + np.pi) % (2 * np.pi) - np.pi                 # 이주(tragus) 방향과의 각도차
    def k_of(t): return np.tan(np.radians(np.interp(t, [-0.025, 0.0, 0.032], [13.0, 19.0, 22.0])))
    def pt(rho, extra_n=0.0, extra_out=0.0):
        s2 = CC[0] + rho * (OP[:, 0] - CC[0]) + extra_out * ON[:, 0]
        t2 = CC[1] + rho * (OP[:, 1] - CC[1]) + extra_out * ON[:, 1]
        sect = (1 - lobe) * (1 - 0.5 * top); cw = 1 - smoothstep(0.35, 0.6, rho) * (1 - sect)
        concha = -0.0065 * (1 - smoothstep(0.05, 0.55, rho)) * cw       # 귓구멍 가까이(ρ<0.35)는 모든 방향 같은 깊이 → 중심 별 모양 주름 제거
        anti = 0.0020 * np.exp(-((rho - 0.63) / 0.11) ** 2) * (1 - lobe) * (1 - front)
        scapha = -0.0015 * np.exp(-((rho - 0.83) / 0.06) ** 2) * (1 - lobe) * (1 - front)
        helix = 0.0030 * smoothstep(0.86, 1.0, rho) * (1 - lobe) * (1 - 0.7 * front)
        tragus = 0.0030 * np.exp(-(dfr / 0.30) ** 2) * np.exp(-((rho - 0.80) / 0.12) ** 2)
        lobe_h = 0.0008 * lobe * (1 - smoothstep(0.85, 1.0, rho))
        bury = -0.0060 * front * smoothstep(0.55, 1.0, rho)     # 머리에 붙는 앞쪽(이주 둘레) 바깥 링은 머리 속으로
        h = concha + anti + scapha + helix + tragus + lobe_h + bury + extra_n
        return O[None, :] + s2[:, None] * back + t2[:, None] * up + (BASE + s2 * k_of(t2) + h)[:, None] * xo
    center = O + CC[0] * back + CC[1] * up + (BASE + CC[0] * float(k_of(np.array([CC[1]]))[0]) - 0.0068) * xo
    rings = [pt(r) for r in FRONT_R]
    roll = 1 - 0.8 * front          # 앞쪽(머리에 붙는 쪽)은 말림 없음
    rings.append(pt(1.0, extra_n=-0.0025 - 0.0003 * lobe, extra_out=(0.0027 - 0.0003 * lobe) * roll))
    rings.append(pt(1.0, extra_n=-0.0055, extra_out=(0.0010 - 0.0002 * lobe) * roll))
    for rb, dn in ((0.88, -0.0062), (0.72, -0.0095), (0.55, -0.0135)):
        rings.append(pt(rb, extra_n=dn))
    return center, rings

def ear_positions(side):
    c, rings = ear_rings(side)
    return np.vstack([c[None, :]] + rings)

def add_ears(ob):
    """처음 만들 때(build_all). 정점 순서: 귀마다 [중심, 링0(28), …, 링14(28)]."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.verts.layers.deform.verify()
    gi = {g.name: g.index for g in ob.vertex_groups}
    for nm in ("EarL", "EarR"):
        if nm not in gi: gi[nm] = ob.vertex_groups.new(name=nm).index
    meta = json.loads(ob["chosang_patch"])
    for side, gname in ((1, "EarL"), (-1, "EarR")):
        start = len(bm.verts)
        P = ear_positions(side)
        vs = [bm.verts.new(p.tolist()) for p in P]
        cv = vs[0]; R = [vs[1 + k * NT: 1 + (k + 1) * NT] for k in range((len(P) - 1) // NT)]
        def face(q):
            if side < 0: q = q[::-1]
            bm.faces.new(q)
        for j in range(NT): face([cv, R[0][j], R[0][(j + 1) % NT]])
        for k in range(len(R) - 1):
            for j in range(NT): face([R[k][j], R[k + 1][j], R[k + 1][(j + 1) % NT], R[k][(j + 1) % NT]])
        for v in vs:
            v[dl][gi[gname]] = 1.0; v[dl][gi["Head"]] = 1.0
        meta["ear_left_range" if side > 0 else "ear_right_range"] = [start, len(bm.verts)]
    bm.to_mesh(me); bm.free(); me.update()
    for p in me.polygons: p.use_smooth = True
    ob["chosang_patch"] = json.dumps(meta)
    return meta

def update_ears(ob):
    """이미 귀가 있는 Bust: 위상은 그대로 두고 귀 정점 위치만 교체(기본 메시 + 모든 셰이프키 — 셰이프는 귀를 움직이지 않음)."""
    me = ob.data; meta = json.loads(ob["chosang_patch"]); n = len(me.vertices)
    new = {}
    for side, key in ((1, "ear_left_range"), (-1, "ear_right_range")):
        a, b = meta[key]; P = ear_positions(side); assert len(P) == b - a, (len(P), b - a); new[(a, b)] = P
    def patch(arr):
        arr = arr.reshape(-1, 3)
        for (a, b), P in new.items(): arr[a:b] = P
        return arr.ravel()
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); me.vertices.foreach_set("co", patch(co))
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            c2 = np.empty(n * 3); kb.data.foreach_get("co", c2); kb.data.foreach_set("co", patch(c2))
    me.update()
