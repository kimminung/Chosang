"""초상 Bust 빌더 — ARKit 패치(정점 0…1219 고정) + 절차적 셸(두피·목·어깨) + 눈꺼풀/입술 안쪽 띠.
다시 실행하면 Bust 를 처음부터 다시 만든다(셰이프키·UV 배치·스킨은 이후 단계 스크립트가 다시 붙임). 난수 없음.
좌표: 블렌더 Z-up, 얼굴 -Y, 피사체 왼쪽 +X (USD Y-up 내보내기 시 계약 좌표).
"""
import numpy as np, json, os, hashlib, collections

def interp(z, pts):
    pts = np.asarray(pts, float)
    return np.interp(z, pts[:, 0], pts[:, 1])

# ---------------- 셸 원시 형상(높이 z 의 단면) ----------------
CRANIUM = dict(cy=0.003, cz=0.4824, rx=0.078, ry=0.099, rz_top=0.0851, rz_low=0.120, m_low=2.0)
JAW = dict(z=[0.312, 0.33, 0.345, 0.365, 0.39, 0.42, 0.445],
           cy=[-0.048, -0.046, -0.038, -0.030, -0.022, -0.020, -0.018],
           a=[0.000, 0.036, 0.050, 0.058, 0.064, 0.066, 0.060],
           b=[0.000, 0.040, 0.054, 0.062, 0.068, 0.070, 0.064])
NECK = dict(z=[0.22, 0.26, 0.30, 0.35, 0.40, 0.43],
            cy=[0.024, 0.018, 0.014, 0.012, 0.016, 0.02],
            a=[0.070, 0.060, 0.057, 0.058, 0.058, 0.0],
            b=[0.066, 0.060, 0.056, 0.054, 0.052, 0.0], n=2.2)
SHOULDER_TOP = [(0.0, 0.300), (0.055, 0.290), (0.07, 0.283), (0.10, 0.270), (0.13, 0.258), (0.16, 0.248),
                (0.18, 0.238), (0.195, 0.225), (0.205, 0.205), (0.212, 0.170), (0.215, 0.120), (0.216, 0.0)]
TORSO = dict(z=[0.0, 0.08, 0.14, 0.18, 0.22, 0.26, 0.30],
             cy=[0.022, 0.022, 0.022, 0.024, 0.026, 0.026, 0.026],
             a=[0.198, 0.208, 0.214, 0.216, 0.216, 0.216, 0.216],
             b=[0.104, 0.106, 0.104, 0.098, 0.086, 0.070, 0.060], n=2.8)
AXIS = [(0.0, 0.022), (0.2, 0.020), (0.30, 0.014), (0.36, 0.008), (0.42, 0.004), (0.6, 0.003)]

def ray_superellipse(ax, ay, ux, uy, cx, cy, a, b, n, tmax=0.4):
    a = np.maximum(a, 1e-9); b = np.maximum(b, 1e-9)
    def f(t):
        x = (ax + t * ux - cx) / a; y = (ay + t * uy - cy) / b
        return np.abs(x) ** n + np.abs(y) ** n - 1.0
    ts = np.linspace(0, tmax, 160)[:, None]
    vals = np.abs((ax + ts * ux - cx) / a) ** n + np.abs((ay + ts * uy - cy) / b) ** n - 1.0
    inside_any = (vals < 0)
    last_in = np.where(inside_any.any(0), (inside_any * np.arange(len(ts))[:, None]).max(0), -1)
    ok = last_in >= 0
    lo = np.where(ok, ts[np.clip(last_in, 0, len(ts) - 1), 0], 0.0)
    hi = np.where(ok, ts[np.clip(last_in + 1, 0, len(ts) - 1), 0], 0.0)
    for _ in range(40):
        mid = 0.5 * (lo + hi); fm = f(mid)
        lo = np.where(fm < 0, mid, lo); hi = np.where(fm < 0, hi, mid)
    t = 0.5 * (lo + hi)
    return np.where(ok & (a > 1e-6) & (b > 1e-6), t, 0.0)

def cranium_section(z):
    c = CRANIUM; dz = z - c['cz']
    if dz >= 0:
        g = np.sqrt(max(1 - (dz / c['rz_top']) ** 2, 0.0))
    else:
        q = min(abs(dz) / c['rz_low'], 1.0)
        g = max(1 - q ** c['m_low'], 0.0) ** (1 / c['m_low'])
    return c['cy'], c['rx'] * g, c['ry'] * g

def shoulder_x_top(z):
    pts = np.array(SHOULDER_TOP)
    if z >= pts[0, 1]: return 0.0
    return float(np.interp(z, pts[::-1, 1], pts[::-1, 0]))

def section_radii(z, phis, p=8.0):
    ay = interp(z, AXIS)
    ux, uy = np.sin(phis), -np.cos(phis)
    ts = []
    cy, a, b = cranium_section(z)
    if a > 1e-5: ts.append(ray_superellipse(0.0, ay, ux, uy, 0.0, cy, a, b, 2.0))
    if JAW['z'][0] < z < JAW['z'][-1]:
        ts.append(ray_superellipse(0.0, ay, ux, uy, 0.0, interp(z, np.c_[JAW['z'], JAW['cy']]),
                                   interp(z, np.c_[JAW['z'], JAW['a']]), interp(z, np.c_[JAW['z'], JAW['b']]), 2.0))
    if NECK['z'][0] <= z < NECK['z'][-1]:
        ts.append(ray_superellipse(0.0, ay, ux, uy, 0.0, interp(z, np.c_[NECK['z'], NECK['cy']]),
                                   interp(z, np.c_[NECK['z'], NECK['a']]), interp(z, np.c_[NECK['z'], NECK['b']]), NECK['n']))
    xt = shoulder_x_top(z)
    if xt > 0.0 and z <= TORSO['z'][-1]:
        a_t = min(interp(z, np.c_[TORSO['z'], TORSO['a']]), xt)
        b_t = interp(z, np.c_[TORSO['z'], TORSO['b']]) * (min(1.0, xt / 0.10) ** 0.5)   # 목으로 좁아질 때 깊이도 함께 줄여 턱(층) 방지
        ts.append(ray_superellipse(0.0, ay, ux, uy, 0.0, interp(z, np.c_[TORSO['z'], TORSO['cy']]),
                                   a_t, b_t, TORSO['n']))
    T = np.array(ts) if ts else np.zeros((1, len(phis)))
    r = (np.sum(np.maximum(T, 0) ** p, 0)) ** (1.0 / p)
    return ay, r

# ---------------- 링 격자 · 크라운 캡 ----------------
NSIDE = 28
NCOL = 4 * NSIDE

def cap_square_boundary():
    n = NSIDE; seq = []; h = n // 2
    for i in range(h, n): seq.append((i, n))
    for j in range(n, 0, -1): seq.append((n, j))
    for i in range(n, 0, -1): seq.append((i, 0))
    for j in range(0, n): seq.append((0, j))
    for i in range(0, h): seq.append((i, n))
    assert len(seq) == 4 * n
    return seq

def sq2disk(u, v):
    return u * np.sqrt(1 - v * v / 2), v * np.sqrt(1 - u * u / 2)

def column_phis():
    n = NSIDE; seq = cap_square_boundary()
    uv = np.array([(-1 + 2 * i / n, -1 + 2 * j / n) for i, j in seq])
    X, Y = sq2disk(uv[:, 0], uv[:, 1])
    phis = np.unwrap(np.arctan2(X, Y)); phis = phis - phis[0]
    return phis, seq

def ring_heights():
    z = list(np.arange(0.0, 0.18, 0.03))
    z += list(np.linspace(0.18, 0.30, 25)[:-1])
    z += list(np.linspace(0.30, 0.335, 8)[:-1])
    z += list(np.linspace(0.335, 0.52, 45)[:-1])
    c = CRANIUM; lat0 = np.arcsin((0.52 - c['cz']) / c['rz_top']); lat1 = np.arcsin((0.555 - c['cz']) / c['rz_top'])
    z += list(c['cz'] + c['rz_top'] * np.sin(np.linspace(lat0, lat1, 8)))
    return np.array(z)

def build_prim_grid():
    phis, seq = column_phis(); Z = ring_heights()
    R = np.zeros((len(Z), NCOL)); AY = np.zeros(len(Z))
    for k, z in enumerate(Z):
        AY[k], R[k] = section_radii(z, phis)
    return Z, phis, AY, R, seq

def grid_points(Z, phis, AY, R):
    ux, uy = np.sin(phis)[None, :], -np.cos(phis)[None, :]
    X = R * ux; Y = AY[:, None] + R * uy
    return np.stack([X, Y, np.broadcast_to(Z[:, None], X.shape)], -1)

def diffuse_fill(D, known, iters=600):
    D = np.where(known, D, 0.0).copy()
    for _ in range(iters):
        up = np.vstack([D[1:], D[-1:]]); dn = np.vstack([D[:1], D[:-1]])
        avg = (up + dn + np.roll(D, 1, 1) + np.roll(D, -1, 1)) / 4.0
        D = np.where(known, D, avg)
    return D

def grid_distance(mask, maxd=40):
    INF = 10 ** 6
    d = np.where(mask, 0, INF).astype(np.int64)
    for _ in range(maxd):
        up = np.vstack([d[1:], np.full((1, d.shape[1]), INF)]); dn = np.vstack([np.full((1, d.shape[1]), INF), d[:-1]])
        nd = np.minimum(d, np.minimum(np.minimum(up, dn), np.minimum(np.roll(d, 1, 1), np.roll(d, -1, 1))) + 1)
        if (nd == d).all(): break
        d = nd
    return d

def fill_enclosed(hit):
    K, J = hit.shape
    reach = np.zeros_like(hit); reach[0] = ~hit[0]; reach[-1] = ~hit[-1]
    while True:
        up = np.vstack([reach[1:], np.zeros((1, J), bool)]); dn = np.vstack([np.zeros((1, J), bool), reach[:-1]])
        new = reach | ((up | dn | np.roll(reach, 1, 1) | np.roll(reach, -1, 1)) & ~hit)
        if (new == reach).all(): break
        reach = new
    return ~reach

def blend_with_patch(R, hit, Rhit, sigma=5.0):
    inside = fill_enclosed(hit)
    Dx = diffuse_fill(np.where(hit, Rhit - R, 0.0), hit)
    w = np.exp(-(grid_distance(inside) / sigma) ** 2)
    Rb = np.where(inside, np.where(hit, Rhit, R + Dx), R + w * Dx)
    return Rb, inside

def cap_points(Z, phis, AY, Rtop, seq):
    c = CRANIUM; n = NSIDE
    order = np.argsort(phis % (2 * np.pi))
    ph_s = (phis % (2 * np.pi))[order]; r_s = Rtop[order]
    ph_e = np.concatenate([ph_s - 2 * np.pi, ph_s, ph_s + 2 * np.pi]); r_e = np.concatenate([r_s, r_s, r_s])
    ay = AY[-1]; pts = {}
    for i in range(1, n):
        for j in range(1, n):
            X, Y = sq2disk(-1 + 2 * i / n, -1 + 2 * j / n)
            rho = np.hypot(X, Y); ph = np.arctan2(X, Y) % (2 * np.pi)
            rr = rho * np.interp(ph, ph_e, r_e)
            x = rr * np.sin(ph); y = ay - rr * np.cos(ph)
            q = 1 - (x / c['rx']) ** 2 - ((y - c['cy']) / c['ry']) ** 2
            pts[(i, j)] = (x, y, c['cz'] + c['rz_top'] * np.sqrt(max(q, 0.0)))
    return pts

# ---------------- 조립 · 지퍼 ----------------
def boundary_loop_of_faces(faces):
    cnt = collections.Counter()
    for f in faces:
        for i in range(len(f)):
            cnt[(f[i], f[(i + 1) % len(f)])] += 1
    nxt = {a: b for (a, b) in cnt if (b, a) not in cnt}
    loops, seen = [], set()
    for s in list(nxt):
        if s in seen: continue
        L = [s]; seen.add(s); c = nxt[s]
        while c != s and c is not None and c not in seen:
            L.append(c); seen.add(c); c = nxt.get(c)
        loops.append(L)
    return loops

FACE_C = np.array([0.0, -0.07, 0.42])
def ang(P, L):
    q = P[L] - FACE_C
    return np.arctan2(q[:, 2], q[:, 0])

def zipper(A, H, P):
    A = list(A); H = list(H)
    j0 = int(np.argmin(((P[H] - P[A[0]]) ** 2).sum(1))); H = H[j0:] + H[:j0]
    Ar = [A[0]] + A[1:][::-1]
    def cum(L):
        a = np.unwrap(np.r_[ang(P, L), ang(P, L[:1])]); a = a - a[0]
        return a / a[-1]
    ta, th = cum(Ar), cum(H)
    assert (np.diff(ta) > -1e-9).all() and (np.diff(th) > -0.05).all(), "각도 단조성 실패"
    faces = []; i = j = 0; na, nh = len(Ar), len(H)
    while i < na or j < nh:
        ai, ai1 = Ar[i % na], Ar[(i + 1) % na]; hj, hj1 = H[j % nh], H[(j + 1) % nh]
        if (i < na) and (j >= nh or ta[i + 1] <= th[j + 1]):
            faces.append((ai, hj, ai1)); i += 1
        else:
            faces.append((ai, hj, hj1)); j += 1
    return faces

def build_arrays(Bp, patch_faces, ray_fn):
    Z, phis, AY, R, seq = build_prim_grid()
    K, J = R.shape
    O = np.stack([np.zeros(K * J), np.repeat(AY, J), np.repeat(Z, J)], 1)
    Dd = np.stack([np.tile(np.sin(phis), K), np.tile(-np.cos(phis), K), np.zeros(K * J)], 1)
    th = ray_fn(O, Dd).reshape(K, J); hit = np.isfinite(th)
    Rb, inside = blend_with_patch(R, hit, np.where(hit, th, 0.0))
    P = grid_points(Z, phis, AY, Rb)
    cap = cap_points(Z, phis, AY, Rb[-1], seq)
    verts = [tuple(v) for v in Bp]
    idx = -np.ones((K, J), int)
    for k in range(K):
        for j in range(J):
            if not inside[k, j]:
                idx[k, j] = len(verts); verts.append(tuple(P[k, j]))
    cap_idx = {}
    for key, p in cap.items():
        cap_idx[key] = len(verts); verts.append(p)
    bottom = len(verts); verts.append((0.0, float(AY[0]), 0.0))
    faces = [tuple(f) for f in patch_faces]
    for k in range(K - 1):
        for j in range(J):
            a, b, c, d = idx[k, j], idx[k, (j + 1) % J], idx[k + 1, (j + 1) % J], idx[k + 1, j]
            if min(a, b, c, d) >= 0: faces.append((a, b, c, d))
    n = NSIDE; gid = {key: idx[K - 1, m] for m, key in enumerate(seq)}; gid.update(cap_idx)
    for i in range(n):
        for j in range(n):
            faces.append((gid[(i, j)], gid[(i, j + 1)], gid[(i + 1, j + 1)], gid[(i + 1, j)]))
    for j in range(J):
        faces.append((idx[0, (j + 1) % J], idx[0, j], bottom))
    return np.array(verts), faces, dict(Z=Z, phis=phis, AY=AY, inside=inside, idx=idx, hit=hit)

def stitch(V, faces, outer_loop):
    loops = boundary_loop_of_faces(faces)
    A = [l for l in loops if set(l) == set(outer_loop)][0]
    H = max([l for l in loops if min(l) >= 1220], key=len)
    zf = zipper(A, H, V)
    Aset = set(zip(A, A[1:] + A[:1]))
    if any((f[i], f[(i + 1) % 3]) in Aset for f in zf for i in range(3)):
        zf = [tuple(reversed(f)) for f in zf]
    return zf, A, H

# ---------------- 띠 · 이완 · 그룹 ----------------
def adjacency(faces, n):
    nb = [set() for _ in range(n)]
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]; nb[a].add(b); nb[b].add(a)
    return nb

def vertex_normals(V, faces):
    N = np.zeros_like(V)
    for f in faces:
        p = V[list(f)]
        n = np.cross(p[1] - p[0], p[2] - p[0]) if len(f) == 3 else np.cross(p[2] - p[0], p[3] - p[1])
        for v in f: N[v] += n
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)

def relax_tangential(V, faces, movable, fixed, iters=40, lam=0.5, full_last=6):
    nb = adjacency(faces, len(V))
    mv = np.array([v for v in sorted(movable) if not fixed[v]]); nbl = [list(nb[v]) for v in mv]
    V = V.copy(); N = None
    for it in range(iters):
        if it % 5 == 0: N = vertex_normals(V, faces)
        d = np.array([V[ns].mean(0) for ns in nbl]) - V[mv]
        if it < iters - full_last:
            d = d - (d * N[mv]).sum(1, keepdims=True) * N[mv]
        V[mv] = V[mv] + lam * d
    return V

def neighbor_table(faces, n):
    nb = [set() for _ in range(n)]
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]; nb[a].add(b); nb[b].add(a)
    deg = np.array([len(x) for x in nb]); T = np.full((n, deg.max()), n, np.int64)
    for i, x in enumerate(nb):
        l = list(x); T[i, :len(l)] = l
    return T, deg, nb

def rings_from(seed, nb, k, lo=1220):
    band = set(seed); front = set(seed)
    for _ in range(k):
        nxt = {x for v in front for x in nb[v] if x >= lo} - band; band |= nxt; front = nxt
    return band

def bilaplacian_smooth(V, faces, free, iters=400, lam=0.04):
    """띠(free) 정점만 이중 라플라시안 흐름으로 평활 — 패치·바깥 셸 고정이라 경계에서 C1 에 가까운 이음."""
    n = len(V); T, deg, nb = neighbor_table(faces, n)
    band = np.array(sorted(free))
    s1 = set(free)
    for v in free: s1 |= nb[v]
    S1 = np.array(sorted(s1)); V = V.copy()
    for _ in range(iters):
        Vp = np.vstack([V, np.zeros((1, 3))])
        L = np.zeros((n + 1, 3))
        L[S1] = Vp[T[S1]].sum(1) / deg[S1, None] - V[S1]
        LL = L[T[band]].sum(1) / deg[band, None] - L[band]
        V[band] -= lam * LL
    return V

def project_to_patch_tangent(V, H, A, patch_faces):
    """구멍 경계 H 정점을 가장 가까운 패치 경계(두 꼭짓점 보간)의 접평면으로 투영 → 패치와 1차 연속."""
    Np = vertex_normals(V[:1220], [tuple(f) for f in patch_faces])
    Ab = np.array(A); P = V[Ab]; N = Np[Ab]
    V = V.copy()
    for h in H:
        d = np.linalg.norm(P - V[h], axis=1); i = int(np.argmin(d))
        j = (i + 1) % len(Ab) if d[(i + 1) % len(Ab)] < d[i - 1] else (i - 1) % len(Ab)
        wi = d[j] / max(d[i] + d[j], 1e-12)
        b = wi * P[i] + (1 - wi) * P[j]; n = wi * N[i] + (1 - wi) * N[j]; n /= np.linalg.norm(n)
        V[h] = V[h] - np.dot(V[h] - b, n) * n
    return V

def eye_band(V, loop, center, r):
    c = np.asarray(center); P = V[loop]
    d1 = P - c; d1 /= np.linalg.norm(d1, axis=1, keepdims=True); l1 = c + d1 * (r - 0.0002)
    d2 = (P - c) + np.array([0.0, 0.006, 0.0]); d2 /= np.linalg.norm(d2, axis=1, keepdims=True); l2 = c + d2 * (r - 0.0015)
    return l1, l2

def mouth_band(V, loop):
    P = V[loop]; c = P.mean(0)
    xs = np.abs(P[:, 0] - c[0]); xmax = xs.max()
    s = np.sign(P[:, 2] - c[2]); s[xs > xmax * 0.97] = 0.0
    corner = (xs / xmax) ** 4
    l1 = P + np.c_[np.zeros(len(P)), np.full(len(P), 0.0028), s * 0.0012]; l1[:, 0] = c[0] + (P[:, 0] - c[0]) * (1 - 0.04 * corner)
    l2 = P + np.c_[np.zeros(len(P)), np.full(len(P), 0.0068), s * 0.0032]; l2[:, 0] = c[0] + (P[:, 0] - c[0]) * (1 - 0.10 * corner)
    return l1, l2

def band_faces(loop, i1, i2):
    n = len(loop); F = []
    for i in range(n):
        a, b = loop[i], loop[(i + 1) % n]; a1, b1 = i1[i], i1[(i + 1) % n]; a2, b2 = i2[i], i2[(i + 1) % n]
        F.append((b, a, a1, b1)); F.append((b1, a1, a2, b2))
    return F

HAIRLINE = [(0, 0.508), (30, 0.503), (50, 0.49), (65, 0.47), (75, 0.44), (82, 0.43), (88, 0.448), (100, 0.448),
            (110, 0.43), (125, 0.40), (150, 0.385), (180, 0.38)]

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def azimuth_deg(V):
    ay = interp(V[:, 2], AXIS)
    return np.degrees(np.arctan2(V[:, 0], -(V[:, 1] - ay)))

def skin_weights(V):
    zz = V[:, 2] + 0.025 * np.clip((-V[:, 1] - 0.02) / 0.04, 0, 1) - 0.02 * np.clip((V[:, 1] - 0.02) / 0.04, 0, 1)
    w_root = 1 - smoothstep(0.235, 0.29, zz); w_head = smoothstep(0.305, 0.355, zz)
    return w_root, np.clip(1 - w_root - w_head, 0, 1), w_head

def groups(V, shell_idx, lid_idx, lip_idx):
    """영역 그룹(가중치 1) + 스킨 그룹(Root/Neck/Head). 'Neck' 은 계약 영역 이름이자 Neck 뼈 디폼 그룹 — 같은 그룹(가중치 = 목 뼈 스킨)."""
    out = {"ARKitFace": (np.arange(1220), np.ones(1220))}
    S = np.array(sorted(shell_idx)); ph = np.abs(azimuth_deg(V[S])); z = V[S, 2]
    hp = np.array(HAIRLINE); h = np.interp(ph, hp[:, 0], hp[:, 1])
    out["Scalp"] = (S[z > h], np.ones(int((z > h).sum())))
    sh = S[z < 0.265]; out["Shoulders"] = (sh, np.ones(len(sh)))
    out["LidInner"] = (np.array(lid_idx), np.ones(len(lid_idx)))
    out["LipInner"] = (np.array(lip_idx), np.ones(len(lip_idx)))
    wr, wn, wh = skin_weights(V); idx = np.arange(len(V))
    for name, w in (("Root", wr), ("Neck", wn), ("Head", wh)):
        m = w > 1e-4; out[name] = (idx[m], w[m])
    return out

# ---------------- Blender ----------------
def patch_data():
    ns = {}
    p = os.path.expanduser("~/Desktop/Chosang_Blender/build/bust_patch.py")
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    V, VT, F, FT = ns["parse_obj"](ns["SRC"])
    loops = ns["boundary_loops"](F)
    eyes = [l for l in loops if len(l) == 24]
    eyeL = [l for l in eyes if V[l][:, 0].mean() > 0][0]; eyeR = [l for l in eyes if V[l][:, 0].mean() < 0][0]
    mouth = [l for l in loops if len(l) == 36][0]; outer = [l for l in loops if len(l) == 56][0]
    cxy = V[eyeL][:, :2].mean(0); k = 64.0 / (2 * cxy[0]); R = (12.0 + 0.3) / k
    P = V[eyeL]; d2 = ((P[:, :2] - cxy) ** 2).sum(1); ok = d2 < R * R
    cz = float(np.mean(P[ok, 2] - np.sqrt(R * R - d2[ok])))
    s = k / 1000.0
    to_b = lambda X: np.stack([X[..., 0], -X[..., 2], X[..., 1]], -1)
    T = np.array([0.032, -0.0742, 0.44]) - to_b(np.array([cxy[0], cxy[1], cz])) * s
    B = to_b(V) * s + T
    quads = np.array(F, np.int32)
    meta = dict(obj_sha256=hashlib.sha256(open(ns["SRC"], "rb").read()).hexdigest(),
                patch_quads_sha256=hashlib.sha256(quads.astype('<i4').tobytes()).hexdigest(),
                obj_to_blender="b = (x, -z, y) * scale + translate  (OBJ mm)", scale_m_per_obj_mm=float(s), translate=T.tolist(),
                eye_loop_left=eyeL, eye_loop_right=eyeR, mouth_loop=mouth, outer_loop=outer,
                eyeball_center_left=[0.032, -0.0742, 0.44], eyeball_center_right=[-0.032, -0.0742, 0.44], eyeball_radius=0.012,
                eye_center_definition="eyeball center: xy = mean of the 24 lid-hole loop vertices, depth fitted so upper/lower lid vertices sit 0.3 mm outside a 12 mm sphere")
    return B, VT, F, meta

def bvh_ray_fn(B, F):
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    tree = BVHTree.FromPolygons([tuple(map(float, v)) for v in B], [tuple(f) for f in F], all_triangles=False)
    def fn(O, D):
        out = np.full(len(O), np.nan)
        for i in range(len(O)):
            loc, nrm, idx, dist = tree.ray_cast(Vector(O[i]), Vector(D[i]), 1.0)
            if loc is not None: out[i] = dist
        return out
    return fn

def build_bust():
    import bpy
    B, VT, F, meta = patch_data()
    V, faces, info = build_arrays(B, F, bvh_ray_fn(B, F))
    zf, A, H = stitch(V, faces, meta["outer_loop"])
    faces = faces + zf
    T_, deg_, nb_ = neighbor_table(faces, len(V))
    band6 = rings_from(H, nb_, 6)
    V = bilaplacian_smooth(V, faces, band6, iters=400, lam=0.04)          # 1) H 포함 평활
    fixed = np.zeros(len(V), bool); fixed[:1220] = True
    V = relax_tangential(V, faces, band6, fixed, iters=30, lam=0.5, full_last=0)   # 2) 간격 고르게
    V = project_to_patch_tangent(V, H, A, F)                              # 3) H 를 패치 경계 접평면으로(작은 보정)
    V = bilaplacian_smooth(V, faces, band6 - set(H), iters=250, lam=0.04) # 4) H 고정, 바깥 띠만 C1 이음
    nshell_end = len(V)
    newV, lid_idx, bf = [], [], []
    for loop, c in ((meta["eye_loop_left"], meta["eyeball_center_left"]), (meta["eye_loop_right"], meta["eyeball_center_right"])):
        l1, l2 = eye_band(V, loop, c, meta["eyeball_radius"])
        i1 = list(range(nshell_end + len(newV), nshell_end + len(newV) + len(loop))); newV += l1.tolist()
        i2 = list(range(nshell_end + len(newV), nshell_end + len(newV) + len(loop))); newV += l2.tolist()
        lid_idx += i1 + i2; bf += band_faces(loop, i1, i2)
    l1, l2 = mouth_band(V, meta["mouth_loop"])
    i1 = list(range(nshell_end + len(newV), nshell_end + len(newV) + len(l1))); newV += l1.tolist()
    i2 = list(range(nshell_end + len(newV), nshell_end + len(newV) + len(l2))); newV += l2.tolist()
    lip_idx = i1 + i2; bf += band_faces(meta["mouth_loop"], i1, i2)
    V = np.vstack([V, np.array(newV)]); faces = faces + bf
    old = bpy.data.objects.get("Bust"); mats = list(old.data.materials) if old else []
    if old:
        me_old = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if me_old.users == 0: bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new("Bust")
    me.from_pydata(V.tolist(), [], [tuple(int(i) for i in f) for f in faces]); me.update(calc_edges=True)
    ob = bpy.data.objects.new("Bust", me); bpy.data.collections["Chosang_Template"].objects.link(ob)
    for m in mats: me.materials.append(m)
    uv = me.uv_layers.new(name="UVMap")
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    UV = np.zeros((len(me.loops), 2), np.float32); pm = lv < 1220
    UV[pm] = np.c_[VT[lv[pm], 0], 0.5 * VT[lv[pm], 1]]
    uv.data.foreach_set("uv", UV.ravel())
    G = groups(V, range(1220, nshell_end), lid_idx, lip_idx)
    for name, (idx, w) in G.items():
        vg = ob.vertex_groups.new(name=name)
        for i, ww in zip(idx.tolist(), w.tolist()): vg.add([int(i)], float(ww), 'REPLACE')
    meta.update(patch_vertex_count=1220, shell_vertex_range=[1220, nshell_end], lid_inner=lid_idx, lip_inner=lip_idx,
                zipper_faces=len(zf), hole_loop_len=len(H))
    ob["chosang_patch"] = json.dumps(meta)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    assert np.abs(co[:1220] - B).max() < 1e-7, "패치 정점 위치가 바뀜"
    for i in range(1152):
        assert tuple(me.polygons[i].vertices) == tuple(F[i]), ("패치 면 순서가 바뀜", i)
    return ob, dict(verts=len(me.vertices), faces=len(me.polygons), zipper=len(zf), H=len(H), groups={k: len(v[0]) for k, v in G.items()})
