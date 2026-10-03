"""ARKit 52 셰이프키 — 절차적 변형장. 다시 실행하면 Bust·Mouth_Inner 셰이프키를 새로 만든다.
· 눈꺼풀: 눈알 중심을 지나는 X축 회전(구면을 따라 감김) × 조화(harmonic) 가중치(위/아래 눈꺼풀이 구멍으로 분리됨).
· 턱: TMJ 축(JAW_PIVOT) 회전 22° + 앞 13 mm × 조화 가중치(아랫입술·턱=1, 윗입술·광대 위·목=0).
· 입·눈썹·볼·코: 조화 가중치/가우스의 조합. 눈꺼풀·입술 안쪽 띠는 각 셰이프마다 테두리에서 다시 계산.
· Left = 피사체 왼쪽(+X)."""
import bpy, numpy as np, json, math

ARKIT52 = ("eyeBlinkLeft eyeLookDownLeft eyeLookInLeft eyeLookOutLeft eyeLookUpLeft eyeSquintLeft eyeWideLeft "
           "eyeBlinkRight eyeLookDownRight eyeLookInRight eyeLookOutRight eyeLookUpRight eyeSquintRight eyeWideRight "
           "jawForward jawLeft jawRight jawOpen "
           "mouthClose mouthFunnel mouthPucker mouthLeft mouthRight mouthSmileLeft mouthSmileRight mouthFrownLeft mouthFrownRight "
           "mouthDimpleLeft mouthDimpleRight mouthStretchLeft mouthStretchRight mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper "
           "mouthPressLeft mouthPressRight mouthLowerDownLeft mouthLowerDownRight mouthUpperUpLeft mouthUpperUpRight "
           "browDownLeft browDownRight browInnerUp browOuterUpLeft browOuterUpRight "
           "cheekPuff cheekSquintLeft cheekSquintRight noseSneerLeft noseSneerRight tongueOut").split()
assert len(ARKIT52) == 52 and len(set(ARKIT52)) == 52
JAW_PIVOT = np.array([0.0, -0.006, 0.414]); JAW_DEG = 22.0; JAW_T = np.array([0.0, -0.013, 0.0])
LID_R = 0.0123

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0); return t * t * (3 - 2 * t)

class Mesh:
    def __init__(self, ob):
        me = ob.data; n = len(me.vertices); self.n = n
        B = np.empty(n * 3)
        if me.shape_keys: me.shape_keys.key_blocks[0].data.foreach_get("co", B)
        else: me.vertices.foreach_get("co", B)
        self.V = B.reshape(-1, 3)
        E = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
        self.src = np.r_[E[:, 0], E[:, 1]]; self.dst = np.r_[E[:, 1], E[:, 0]]
        self.deg = np.maximum(np.bincount(self.src, minlength=n), 1)
        N = np.empty(n * 3); me.vertices.foreach_get("normal", N); self.N = N.reshape(-1, 3)
    def avg(self, F):
        if F.ndim == 1: return np.bincount(self.src, weights=F[self.dst], minlength=self.n) / self.deg
        return np.stack([self.avg(F[:, k]) for k in range(F.shape[1])], 1)
    def harmonic(self, fixed_idx, fixed_val, iters=1400):
        w = np.zeros(self.n); free = np.ones(self.n, bool)
        fi = np.asarray(fixed_idx, np.int64); fv = np.asarray(fixed_val, float)
        w[fi] = fv; free[fi] = False
        for _ in range(iters):
            a = self.avg(w); w[free] = a[free]
        return np.clip(w, 0.0, 1.0)
    def smooth_field(self, D, lock, iters=3, lam=0.5):
        D = D.copy(); m = ~lock
        for _ in range(iters):
            A = self.avg(D); D[m] += lam * (A[m] - D[m])
        return D

def chains(V, loop):
    loop = list(loop); P = V[loop]; n = len(loop)
    i0 = int(np.argmin(P[:, 0])); i1 = int(np.argmax(P[:, 0]))
    A = [loop[(i0 + k) % n] for k in range(((i1 - i0) % n) + 1)]
    B = [loop[(i1 + k) % n] for k in range(((i0 - i1) % n) + 1)]
    up, lo = (A, B) if V[A][:, 2].mean() > V[B][:, 2].mean() else (B, A)
    return up, lo, loop[i0], loop[i1]

def elev(P, c): return np.arctan2(P[:, 2] - c[2], -(P[:, 1] - c[1]))
def rot_x(P, c, delta):
    f = -(P[:, 1] - c[1]); h = P[:, 2] - c[2]; r = np.hypot(f, h); e = np.arctan2(h, f) - delta
    Q = P.copy(); Q[:, 1] = c[1] - r * np.cos(e); Q[:, 2] = c[2] + r * np.sin(e); return Q
def rot_z(P, c, th):
    x = P[:, 0] - c[0]; y = P[:, 1] - c[1]
    Q = P.copy(); Q[:, 0] = c[0] + x * np.cos(th) - y * np.sin(th); Q[:, 1] = c[1] + x * np.sin(th) + y * np.cos(th); return Q
def jaw_rot(P, deg):
    a = math.radians(deg); q = P - JAW_PIVOT; Q = P.copy()
    Q[:, 1] = JAW_PIVOT[1] + q[:, 1] * math.cos(a) - q[:, 2] * math.sin(a)
    Q[:, 2] = JAW_PIVOT[2] + q[:, 1] * math.sin(a) + q[:, 2] * math.cos(a); return Q

def bust_shapes():
    ob = bpy.data.objects["Bust"]; M = Mesh(ob); V = M.V; n = M.n
    meta = json.loads(ob["chosang_patch"])
    lidI = meta["lid_inner"]; lipI = meta["lip_inner"]; mouth = meta["mouth_loop"]
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    is_patch = np.arange(n) < 1220
    s0, s1 = meta["shell_vertex_range"]; is_shell = (np.arange(n) >= s0) & (np.arange(n) < s1)
    is_ear = np.arange(n) >= meta["ear_left_range"][0]
    lid = np.zeros(n, bool); lid[lidI] = True; lipb = np.zeros(n, bool); lipb[lipI] = True
    up_m, lo_m, mRc, mLc = chains(V, mouth)
    corners_m = {mRc, mLc}
    up_set = [v for v in up_m if v not in corners_m]; lo_set = [v for v in lo_m if v not in corners_m]
    l1, l2 = lipI[:36], lipI[36:]
    pos = {v: i for i, v in enumerate(mouth)}
    band_up = [l1[pos[v]] for v in up_set] + [l2[pos[v]] for v in up_set]
    band_lo = [l1[pos[v]] for v in lo_set] + [l2[pos[v]] for v in lo_set]
    mc = V[mouth].mean(0)
    frontm = smoothstep(-0.035, -0.06, y)
    W = lambda idx: np.nonzero(idx)[0]
    def H(ones, zeros, iters=1400):
        ones = np.unique(np.asarray(ones, np.int64)); zeros = np.setdiff1d(np.unique(np.asarray(zeros, np.int64)), ones)
        return M.harmonic(np.r_[ones, zeros], np.r_[np.ones(len(ones)), np.zeros(len(zeros))], iters)
    # ---- 공통 가중치장
    m_up = H(np.r_[up_set, band_up, lidI, W(z > 0.42), W(is_patch & (z > 0.398) & (np.abs(x) < 0.03))],
             np.r_[lo_set, band_lo, W(z < 0.33), W(is_patch & (z < 0.355) & (np.abs(x) < 0.035))])
    w_jaw = H(np.r_[lo_set, band_lo, W(is_patch & (z < 0.352) & (np.abs(x) < 0.03)), W(is_shell & (z > 0.32) & (z < 0.345) & (y < -0.06))],
              np.r_[up_set, band_up, W(z > 0.403), W(z < 0.292), W(y > 0.025), W(is_ear), lidI])
    def ellip(ax, az): return (x / ax) ** 2 + ((z - mc[2]) / az) ** 2
    zeros_common = np.r_[W((z > 0.402) & (np.abs(x) < 0.022)), W(is_ear), lidI, W(y > -0.04)]
    w_mouth = H(np.r_[mouth, lipI], np.r_[W(ellip(0.040, 0.026) > 1), zeros_common])
    w_mn = H(np.r_[mouth, lipI], np.r_[W(ellip(0.032, 0.015) > 1), zeros_common])
    w_mw = H(np.r_[mouth, lipI], np.r_[W(ellip(0.052, 0.036) > 1), zeros_common])
    w_ul = w_mn * m_up; w_ll = w_mn * (1 - m_up)
    # ---- 눈
    def eye_fields(side):
        loop = meta["eye_loop_left" if side > 0 else "eye_loop_right"]
        c = np.array(meta["eyeball_center_left" if side > 0 else "eyeball_center_right"])
        up, lo, ca, cb = chains(V, loop); cor = [ca, cb]
        upc = [v for v in up if v not in cor]; loc = [v for v in lo if v not in cor]
        d = V - c
        rel = np.hypot(d[:, 0] / 0.026, np.where(d[:, 2] > 0, d[:, 2] / 0.024, d[:, 2] / 0.016))
        far = W(((rel > 1.0) | (d[:, 1] > 0.004)) & ~lid)
        w_up = H(upc, np.r_[far, loc, cor], 1200) ** 1.4
        w_lo = H(loc, np.r_[far, upc, cor], 1200) ** 1.4
        Pu, Pl = V[up], V[lo]; ou, ol = np.argsort(Pu[:, 0]), np.argsort(Pl[:, 0])
        zu = lambda q: np.interp(q, Pu[ou, 0], Pu[ou, 2]); zl = lambda q: np.interp(q, Pl[ol, 0], Pl[ol, 2])
        fu = lambda q: np.interp(q, Pu[ou, 0], -(Pu[ou, 1] - c[1])); fl = lambda q: np.interp(q, Pl[ol, 0], -(Pl[ol, 1] - c[1]))
        def tgt(q):
            zc = zl(q) + 0.25 * (zu(q) - zl(q)); fc = 0.75 * fl(q) + 0.25 * fu(q)
            return np.arctan2(zc - c[2], fc)
        du = elev(V[upc], c) - tgt(V[upc][:, 0]); dl = elev(V[loc], c) - tgt(V[loc][:, 0])
        xu = np.r_[V[upc][:, 0], V[cor][:, 0]]; vu = np.r_[du, 0, 0]; o1 = np.argsort(xu)
        xl = np.r_[V[loc][:, 0], V[cor][:, 0]]; vl = np.r_[dl, 0, 0]; o2 = np.argsort(xl)
        return dict(c=c, w_up=w_up, w_lo=w_lo, bu=lambda q: np.interp(q, xu[o1], vu[o1]), bl=lambda q: np.interp(q, xl[o2], vl[o2]))
    EYE = {1: eye_fields(1), -1: eye_fields(-1)}
    def lid_disp(E, d_up, d_lo, theta=0.0):
        du = d_up(x) if callable(d_up) else d_up; dl = d_lo(x) if callable(d_lo) else d_lo
        wsum = E["w_up"] + E["w_lo"]; m = wsum > 1e-5
        delta = E["w_up"] * du + E["w_lo"] * dl
        P = V.copy(); P[m] = rot_x(V[m], E["c"], delta[m])
        if theta: P[m] = rot_z(P[m], E["c"], theta * np.clip(wsum[m], 0, 1))
        q = P[m] - E["c"]; dq = np.linalg.norm(q, axis=1); rmin = meta["eyeball_radius"] + 0.00025
        push = (dq < rmin) & (q[:, 1] < 0)
        if push.any():
            Pm = P[m]; Pm[push] = E["c"] + q[push] / dq[push, None] * rmin; P[m] = Pm
        return P - V
    def fix_bands(D):
        P = V + D
        for k, side in enumerate((1, -1)):
            loop = meta["eye_loop_left" if side > 0 else "eye_loop_right"]; c = EYE[side]["c"]; r = meta["eyeball_radius"]
            i1 = lidI[48 * k: 48 * k + 24]; i2 = lidI[48 * k + 24: 48 * k + 48]; Q = P[loop]
            d1 = Q - c; d1 /= np.linalg.norm(d1, axis=1, keepdims=True)
            d2 = (Q - c) + np.array([0.0, 0.006, 0.0]); d2 /= np.linalg.norm(d2, axis=1, keepdims=True)
            D[i1] = c + d1 * (r - 0.0002) - V[i1]; D[i2] = c + d2 * (r - 0.0015) - V[i2]
        for i, v in enumerate(mouth):
            D[l1[i]] = D[v]; D[l2[i]] = D[v]
        return D
    lock = lid | lipb | is_ear
    lock[meta["eye_loop_left"]] = True; lock[meta["eye_loop_right"]] = True; lock[mouth] = True
    def g2(cx, cz, sx, szu, szd=None):
        szd = szu if szd is None else szd
        sz = np.where(z > cz, szu, szd)
        return np.exp(-((x - cx) / sx) ** 2 - ((z - cz) / sz) ** 2) * frontm
    D = {}
    def put(name, disp, smooth=True):
        disp = np.asarray(disp, float)
        if smooth: disp = M.smooth_field(disp, lock, 3)
        D[name] = fix_bands(disp.copy())
    jaw_open = w_jaw[:, None] * (jaw_rot(V, JAW_DEG) - V + JAW_T)
    for side, S in ((1, "Left"), (-1, "Right")):
        E = EYE[side]
        put("eyeBlink" + S, lid_disp(E, E["bu"], E["bl"]), False)
        put("eyeWide" + S, lid_disp(E, -0.0026 / LID_R, 0.0008 / LID_R), False)
        sq = lid_disp(E, 0.0008 / LID_R, -0.0028 / LID_R) + g2(side * 0.034, 0.418, 0.013, 0.008)[:, None] * np.array([0, -0.0005, 0.0018])
        put("eyeSquint" + S, sq, False)
        put("eyeLookUp" + S, lid_disp(E, -0.0020 / LID_R, -0.0012 / LID_R), False)
        put("eyeLookDown" + S, lid_disp(E, 0.0035 / LID_R, 0.0015 / LID_R), False)
        put("eyeLookIn" + S, lid_disp(E, 0.0, 0.0, -side * math.radians(6)), False)
        put("eyeLookOut" + S, lid_disp(E, 0.0, 0.0, side * math.radians(6)), False)
        # 눈썹
        g = g2(side * 0.026, 0.458, 0.016, 0.010, 0.0075); put("browDown" + S, g[:, None] * np.array([-side * 0.0024, -0.0010, -0.0060]))
        g = g2(side * 0.046, 0.457, 0.013, 0.018, 0.006); put("browOuterUp" + S, g[:, None] * np.array([side * 0.0006, 0.0, 0.0068]))
        # 볼·코
        g = g2(side * 0.034, 0.415, 0.013, 0.010)
        put("cheekSquint" + S, g[:, None] * np.array([0, -0.0008, 0.0028]) + lid_disp(E, 0.0, -0.0010 / LID_R))
        g1 = g2(side * 0.013, 0.405, 0.009, 0.010) * smoothstep(-0.07, -0.09, y)
        gl = g2(side * 0.012, 0.392, 0.009, 0.006) * m_up
        put("noseSneer" + S, g1[:, None] * np.array([side * 0.0004, 0.0008, 0.0030]) + gl[:, None] * np.array([0, 0, 0.0015]))
        # 입꼬리 계열
        cpos = V[mLc if side > 0 else mRc]
        gc = np.exp(-np.sum(((V - cpos) / 0.011) ** 2, 1)) * w_mw
        gcw = np.exp(-np.sum(((V - cpos) / 0.016) ** 2, 1)) * w_mw
        ch = g2(side * 0.032, 0.395, 0.012, 0.012)
        put("mouthSmile" + S, gc[:, None] * np.array([side * 0.0045, 0.0030, 0.0060]) + ch[:, None] * np.array([side * 0.0005, -0.0018, 0.0022])
            + lid_disp(E, 0.0, -0.0007 / LID_R))
        put("mouthFrown" + S, gc[:, None] * np.array([side * 0.0012, 0.0005, -0.0055]))
        put("mouthDimple" + S, gc[:, None] * np.array([side * 0.0020, 0.0032, 0.0002]))
        lm = smoothstep(-0.008, 0.008, side * x)
        put("mouthStretch" + S, gcw[:, None] * np.array([side * 0.0055, 0.0012, -0.0022]) + (w_ll * lm)[:, None] * np.array([0, 0, -0.0012]))
        put("mouthPress" + S, lm[:, None] * (w_ul[:, None] * np.array([0, 0.0012, -0.0010]) + w_ll[:, None] * np.array([0, 0.0012, 0.0010]))
            + gc[:, None] * np.array([side * 0.0010, 0, 0]))
        lms = np.exp(-((side * x - 0.012) / 0.012) ** 2)
        put("mouthLowerDown" + S, (w_ll * lms)[:, None] * np.array([0, 0.0006, -0.0042]))
        put("mouthUpperUp" + S, (w_ul * lms)[:, None] * np.array([0, -0.0006, 0.0040]))
    put("mouthLeft", w_mw[:, None] * np.array([0.0075, 0, 0]) + (np.exp(-np.sum(((V - V[mLc]) / 0.011) ** 2, 1)) * w_mw)[:, None] * np.array([0, 0.0015, 0]))
    put("mouthRight", w_mw[:, None] * np.array([-0.0075, 0, 0]) + (np.exp(-np.sum(((V - V[mRc]) / 0.011) ** 2, 1)) * w_mw)[:, None] * np.array([0, 0.0015, 0]))
    gin = sum(g2(s * 0.014, 0.459, 0.012, 0.020, 0.0065) for s in (1, -1)); gin = np.clip(gin, 0, 1)
    put("browInnerUp", np.c_[-np.sign(x) * 0.0010 * gin, -0.0006 * gin, 0.0078 * gin])
    gp = sum(g2(s * 0.040, 0.386, 0.017, 0.016) for s in (1, -1)) * smoothstep(-0.03, -0.05, y)
    put("cheekPuff", gp[:, None] * 0.0045 * M.N + w_mouth[:, None] * np.array([0, -0.0008, 0]))
    put("jawOpen", jaw_open)
    put("jawLeft", w_jaw[:, None] * np.array([0.008, 0, 0])); put("jawRight", w_jaw[:, None] * np.array([-0.008, 0, 0]))
    put("jawForward", w_jaw[:, None] * np.array([0, -0.007, 0.0005]))
    put("mouthClose", -0.85 * w_ll[:, None] * jaw_open + w_ul[:, None] * np.array([0, 0, -0.0012]))
    put("mouthFunnel", np.c_[-0.22 * (x - mc[0]) * w_mouth, -0.0055 * w_mouth - 0.0015 * w_mn, w_mouth * (m_up * 0.0025 - (1 - m_up) * 0.0030)])
    put("mouthPucker", np.c_[-0.40 * (x - mc[0]) * w_mouth, -0.0075 * w_mouth, -0.25 * (z - mc[2]) * w_mn])
    put("mouthRollLower", (w_ll ** 1.5)[:, None] * np.array([0, 0.0042, 0.0016]))
    put("mouthRollUpper", (w_ul ** 1.5)[:, None] * np.array([0, 0.0042, -0.0016]))
    gch = np.exp(-(x / 0.016) ** 2 - ((z - 0.348) / 0.012) ** 2) * frontm
    put("mouthShrugLower", w_ll[:, None] * np.array([0, -0.0015, 0.0028]) + gch[:, None] * np.array([0, -0.0015, 0.0018]))
    put("mouthShrugUpper", w_ul[:, None] * np.array([0, -0.0010, 0.0020]))
    put("tongueOut", 0.12 * jaw_open + w_ll[:, None] * np.array([0, -0.0005, -0.0015]))
    assert set(D) == set(ARKIT52), set(ARKIT52) - set(D)
    # ---- 셰이프키 쓰기
    if ob.data.shape_keys:
        ob.shape_key_clear()
    ob.shape_key_add(name="Basis", from_mix=False)
    for nm in ARKIT52:
        kb = ob.shape_key_add(name=nm, from_mix=False)
        kb.data.foreach_set("co", (V + D[nm]).astype(np.float32).ravel()); kb.slider_min = 0.0; kb.slider_max = 1.0; kb.value = 0.0
    ob["chosang_rig"] = json.dumps(dict(jaw_pivot=JAW_PIVOT.tolist(), jaw_open_deg=JAW_DEG, jaw_open_translate=JAW_T.tolist(),
                                        mouth_center=mc.tolist(), lid_rotation_radius=LID_R))
    mags = {nm: float(np.linalg.norm(D[nm], axis=1).max() * 1000) for nm in ARKIT52}
    return V, D, mags, dict(lo_set=lo_set, up_set=up_set, mouth=mouth)

def mouth_inner_shapes(info):
    mi = bpy.data.objects["Mouth_Inner"]; me = mi.data; n = len(me.vertices)
    MV = np.empty(n * 3)
    if me.shape_keys: me.shape_keys.key_blocks[0].data.foreach_get("co", MV)
    else: me.vertices.foreach_get("co", MV)
    MV = MV.reshape(-1, 3)
    grp = {g.name: sorted(v.index for v in me.vertices if any(gg.group == g.index for gg in v.groups)) for g in mi.vertex_groups}
    mz = mi["chosang_mouth_center"][2]; my = mi["chosang_mouth_center"][1]
    w = np.zeros(n)
    for k in ("MI_LowerTeeth", "MI_LowerGum", "MI_Tongue"): w[grp[k]] = 1.0
    cav = grp["MI_Cavity"]; w[cav] = smoothstep(mz + 0.002, mz - 0.008, MV[cav, 2])
    lo = set(info["lo_set"]); up = set(info["up_set"])
    for i, v in enumerate(info["mouth"]):
        w[cav[i]] = 1.0 if v in lo else (0.0 if v in up else 0.5)
    jo = w[:, None] * (jaw_rot(MV, JAW_DEG) - MV + JAW_T)
    tf = np.zeros(n); tg = grp["MI_Tongue"]; tf[tg] = smoothstep(my + 0.048, my + 0.012, MV[tg, 1])
    Dm = {"jawOpen": jo, "jawLeft": w[:, None] * np.array([0.008, 0, 0]), "jawRight": w[:, None] * np.array([-0.008, 0, 0]),
          "jawForward": w[:, None] * np.array([0, -0.007, 0.0005]), "tongueOut": 0.12 * jo + tf[:, None] * np.array([0, -0.024, -0.003])}
    if me.shape_keys: mi.shape_key_clear()
    mi.shape_key_add(name="Basis", from_mix=False)
    bust_key = bpy.data.objects["Bust"].data.shape_keys
    for nm, d in Dm.items():
        kb = mi.shape_key_add(name=nm, from_mix=False)
        kb.data.foreach_set("co", (MV + d).astype(np.float32).ravel())
        fc = kb.driver_add("value"); drv = fc.driver; drv.type = 'AVERAGE'
        for v in list(drv.variables): drv.variables.remove(v)
        var = drv.variables.new(); var.name = "w"; var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'KEY'; var.targets[0].id = bust_key; var.targets[0].data_path = 'key_blocks["%s"].value' % nm
    return list(Dm)
