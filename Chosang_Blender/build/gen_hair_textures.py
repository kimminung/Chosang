
"""초상 머리카락 텍스처 생성기 (결정적, seed 고정).
산출: textures/T_Hair_Atlas_base.png (RGB=그레이스케일 베이스, A=알파)
      textures/T_Hair_Atlas_mask.png (R=하이라이트 마스크, G=뿌리→끝 그라디언트(뿌리 1), B=가닥 랜덤 id, A=1)
      textures/T_Hair_Buzz_base.png / _mask.png (1024² 타일, 짧은 머리·수염 공용)
아틀라스: 2048×2048, 가로 8칸(각 256px). 각 칸 = 카드 한 종류, 뿌리 = 위(v=1), 끝 = 아래(v=0).
  0 straight_dense 1 straight_medium 2 wavy 3 coarse_wave 4 flyaway 5 bangs_blunt 6 tied_bunch 7 short_clump
"""
import numpy as np, bpy, os
OUT = os.path.expanduser("~/Desktop/Chosang_Blender/textures")
H, W, N = 2048, 256, 8

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

class Canvas:
    def __init__(s, h, w):
        s.h, s.w = h, w
        s.A = np.zeros((h, w), np.float32); s.C = np.zeros((h, w), np.float32)
        s.Hl = np.zeros((h, w), np.float32); s.G = np.zeros((h, w), np.float32); s.I = np.zeros((h, w), np.float32)
    def strand(s, rows, xc, wid, a, gray, hl, grad, sid, wrap=False):
        offs = np.arange(-3, 4)
        xi = np.floor(xc)[:, None].astype(np.int32) + offs[None, :]
        d = (xi + 0.5 - xc[:, None]) / np.maximum(wid[:, None] * 0.5, 0.25)
        cov = (a[:, None] * np.exp(-0.5 * d * d)).astype(np.float32)
        rr = np.broadcast_to(rows[:, None], xi.shape)
        if wrap:
            xi = xi % s.w; rr = rr % s.h
        else:
            ok = (xi >= 0) & (xi < s.w) & (rr >= 0) & (rr < s.h)
            cov = np.where(ok, cov, 0); xi = np.clip(xi, 0, s.w - 1); rr = np.clip(rr, 0, s.h - 1)
        inv = 1 - cov
        s.A[rr, xi] = cov + s.A[rr, xi] * inv
        s.C[rr, xi] = (gray if np.isscalar(gray) else gray[:, None]) * cov + s.C[rr, xi] * inv
        s.Hl[rr, xi] = hl[:, None] * cov + s.Hl[rr, xi] * inv
        s.G[rr, xi] = grad[:, None] * cov + s.G[rr, xi] * inv
        s.I[rr, xi] = sid * cov + s.I[rr, xi] * inv

def card_variant(cv, x_off, kind, rng):
    cfg = dict(straight_dense=(460, 0.0, 0, 1.0), straight_medium=(290, 0.0, 0, 1.0), wavy=(320, 7.0, 2.2, 1.0),
               coarse_wave=(280, 11.0, 3.4, 1.0), flyaway=(90, 3.0, 1.3, 0.8), bangs_blunt=(400, 1.5, 1.0, 1.0),
               tied_bunch=(330, 2.0, 1.0, 1.0), short_clump=(380, 2.0, 1.5, 1.0))[kind]
    count, amp, freq, alpha_mul = cfg
    for i in range(count):
        x0 = np.clip(rng.normal(W / 2, W / 3.6), 4, W - 5)
        r0 = int(rng.uniform(0, 0.03) * H)
        if kind == 'bangs_blunt':
            L = H * (0.88 + rng.normal(0, 0.025))
        elif kind == 'short_clump':
            L = H * rng.uniform(0.35, 0.6)
        elif kind == 'flyaway':
            L = H * rng.uniform(0.5, 1.0)
        else:
            L = H * (1.0 - abs(rng.normal(0, 0.12)))
        r1 = int(min(H, r0 + L))
        rows = np.arange(r0, r1)
        t = (rows - r0) / max(1, (r1 - r0))
        ph = rng.uniform(0, 2 * np.pi); f = freq * rng.uniform(0.85, 1.15)
        drift = rng.normal(0, 6.0)
        lowf = np.interp(t, np.linspace(0, 1, 6), rng.normal(0, 1.6, 6))
        xc = x0 + amp * rng.uniform(0.6, 1.2) * np.sin(2 * np.pi * f * t + ph) + drift * t + lowf
        if kind == 'tied_bunch':
            xc = xc + (W / 2 - xc) * 0.62 * smooth(0.0, 1.0, t) ** 1.2
        if kind == 'flyaway':
            xc = xc + rng.normal(0, 18) * t ** 2
        wid = rng.uniform(1.1, 2.3) * (1 - 0.65 * smooth(0.75, 1.0, t))
        tip = 1 - smooth(0.82 if kind != 'bangs_blunt' else 0.94, 1.0, t)
        edge = smooth(0, 0.14 * W, x0) * smooth(0, 0.14 * W, W - x0)
        a = rng.uniform(0.55, 1.0) * alpha_mul * tip * smooth(0.0, 0.02, t) * (0.35 + 0.65 * edge)
        gray = float(np.clip(rng.normal(0.66, 0.11), 0.3, 0.95))
        g_line = gray * (0.72 + 0.28 * smooth(0.0, 0.35, t))   # 뿌리 쪽 약간 어둡게
        hc = rng.uniform(0.22, 0.42); hw = rng.uniform(0.035, 0.07)
        hl = np.exp(-0.5 * ((t - hc) / hw) ** 2) * rng.uniform(0.55, 1.0)
        cv.strand(rows, xc + x_off, wid, a.astype(np.float32), g_line.astype(np.float32), hl.astype(np.float32),
                  (1 - t).astype(np.float32), float(rng.uniform()))

def save(name, rgba, noncolor):
    h, w = rgba.shape[:2]
    old = bpy.data.images.get(name)
    if old: bpy.data.images.remove(old)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'   # 픽셀 쓰기 전에 설정(생성 이미지는 색공간 변경 시 버퍼가 초기화됨)
    img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).ravel())   # 블렌더 픽셀 원점은 왼쪽 아래
    path = os.path.join(OUT, name + ".png")
    img.filepath_raw = path; img.file_format = 'PNG'
    img.save()
    img.source = 'FILE'; img.filepath = path; img.reload()
    chk = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(chk)
    assert chk.reshape(-1, 4)[:, 3].mean() > 0.0 and chk.reshape(-1, 4)[:, :3].max() > 0.05, "PNG 저장 검증 실패: " + name
    return img

def build_atlas():
    rng = np.random.default_rng(20261003)
    kinds = ['straight_dense', 'straight_medium', 'wavy', 'coarse_wave', 'flyaway', 'bangs_blunt', 'tied_bunch', 'short_clump']
    big = Canvas(H, W * N)
    for k, kind in enumerate(kinds):
        sub = Canvas(H, W)
        card_variant(sub, 0.0, kind, rng)
        sl = slice(k * W, (k + 1) * W)
        for nm in ('A', 'C', 'Hl', 'G', 'I'):
            getattr(big, nm)[:, sl] = getattr(sub, nm)
    A = np.clip(big.A, 0, 1); den = np.maximum(A, 1e-4)
    gray = np.where(A > 1e-4, big.C / den, 0.6)
    base = np.dstack([gray, gray, gray, A]).astype(np.float32)
    mask = np.dstack([big.Hl / den, big.G / den, big.I / den, np.ones_like(A)]).astype(np.float32)
    mask[..., :3] = np.where(A[..., None] > 1e-4, mask[..., :3], 0)
    save("T_Hair_Atlas_base", np.clip(base, 0, 1), False)
    save("T_Hair_Atlas_mask", np.clip(mask, 0, 1), True)
    return kinds

def build_buzz(n=1024, count=52000, seed=7):
    rng = np.random.default_rng(seed)
    cv = Canvas(n, n)
    for i in range(count):
        L = int(rng.uniform(18, 40)); r0 = int(rng.uniform(0, n)); x0 = rng.uniform(0, n)
        rows = np.arange(r0, r0 + L); t = (rows - r0) / L
        xc = x0 + rng.normal(0, 0.35) * (rows - r0) + rng.normal(0, 0.6) * t * t * L * 0.1
        wid = rng.uniform(0.9, 1.6) * (1 - 0.6 * t)
        a = rng.uniform(0.6, 1.0) * (1 - smooth(0.7, 1.0, t)) * smooth(0, 0.1, t)
        gray = float(np.clip(rng.normal(0.6, 0.1), 0.3, 0.9))
        cv.strand(rows, xc, wid.astype(np.float32), a.astype(np.float32), gray, (np.exp(-0.5 * ((t - 0.4) / 0.2) ** 2) * 0.7).astype(np.float32),
                  (1 - t).astype(np.float32), float(rng.uniform()), wrap=True)
    A = np.clip(cv.A, 0, 1); den = np.maximum(A, 1e-4)
    gray = np.where(A > 1e-4, cv.C / den, 0.6)
    save("T_Hair_Buzz_base", np.dstack([gray, gray, gray, A]).astype(np.float32), False)
    save("T_Hair_Buzz_mask", np.dstack([cv.Hl / den, cv.G / den, cv.I / den, np.ones_like(A)]).clip(0, 1).astype(np.float32), True)
    return float(A.mean())
