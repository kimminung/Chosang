//
//  FaceFitter.swift
//  ChosangFit
//
//  캡처 번들 → Identity (TechPRD §6.4). M0 범위: 정렬·중립화·컷 평균·패치 치환·두상 전파·대칭·어깨 스케일·눈알 추정·품질 지표.
//  M3 에서 추가: 실루엣 맞춤(SilhouetteFitter), jawOpen 진폭 보정, 희소 폴백(SparseFitter).
//
//  좌표 규약: 사용자 패치는 **눈 중심(안·바깥 꼬리 평균)의 중점이 템플릿 눈 중점에 오도록** 강체 정렬한다(치수는 사용자 것 유지).
//  두상 전파 = 전역 유사변환(패치 Procrustes, 스케일 포함) + 국소 잔차 RBF(바이하모닉 r³) × 경계 거리 감쇠(σ, 기본 5 cm).
//  — r³ 커널은 멀리서 선형으로 자라 뒤통수를 망치므로 잔차만 전파하고 감쇠한다(1차 측정: 감쇠 없이 중앙값 6 mm → 아래 테스트 참고).
//

import Foundation
import simd
import ChosangCore

public struct FitOptions: Sendable, Equatable {
    /// RBF 중심: 패치 경계 최대 개수, 내부 샘플 개수
    public var maxBoundaryCenters = 200
    public var interiorCenters = 100
    /// 좌우 대칭 보정 비율 (0 = 사용자 비대칭 그대로, 1 = 완전 대칭)
    public var symmetry: Float = 0.7
    /// 목 감쇠 구간 (y, m): 위 = 1, 아래 = 0
    public var neckFalloffTop: Float = 0.30
    public var neckFalloffBottom: Float = 0.22
    /// 국소 잔차 전파의 경계 거리 감쇠 σ (m). 0 이면 감쇠 없음(순수 RBF 외삽).
    public var propagationFalloff: Float = 0.05
    public var rbfLambda: Double = 0
    public init() {}
}

public enum FitError: Error, LocalizedError {
    case noNeutralShots
    case vertexCountMismatch(expected: Int, got: Int)
    case procrustesFailed(ShotKind)
    case rbfFailed
    case sparseBundle
    public var errorDescription: String? {
        switch self {
        case .noNeutralShots: "중립 컷이 없습니다 (정면·좌·우·위 중 하나 이상 필요)"
        case .vertexCountMismatch(let e, let g): "얼굴 정점 수가 다릅니다 (템플릿 \(e), 캡처 \(g))"
        case .procrustesFailed(let k): "\(k.title) 컷 정합에 실패했습니다"
        case .rbfFailed: "두상 전파(RBF) 풀이에 실패했습니다"
        case .sparseBundle: "사진만으로 만든 희소 번들(sparse)입니다 — ARKit 1220 정점이 없어 밀집 피팅을 할 수 없습니다. 희소 피팅(T-306, Vision 76 ↔ template.json 랜드마크)은 M3 에서 지원합니다"
        }
    }
}

public enum FaceFitter {
    /// 번들 전체 피팅.
    public static func fit(bundle: CaptureBundle, template t: BustTemplate, options: FitOptions = FitOptions()) throws -> Identity {
        let start = Date()
        let pc = t.patchCount
        let templatePatch = Array(t.patchPositions)
        let shots = bundle.neutralShots
        guard !shots.isEmpty else { throw FitError.noNeutralShots }
        guard !bundle.meta.sparse, !shots.allSatisfy({ $0.meta.isSparse }) else { throw FitError.sparseBundle }
        let templateAnchor = eyeMidpoint(templatePatch, manifest: t.manifest)

        // 1) 컷별 정렬 + 중립화 ---------------------------------------------------------
        var aligned: [[SIMD3<Float>]] = []
        for shot in shots {
            let raw = shot.meta.faceVertexArray
            guard raw.count == pc else { throw FitError.vertexCountMismatch(expected: pc, got: raw.count) }
            guard let T = Procrustes.fit(source: raw, target: templatePatch, allowScale: true) else { throw FitError.procrustesFailed(shot.kind) }
            // 사용자 치수 보존: 회전만 적용. 눈 중점을 템플릿 눈 중점에 맞춘다.
            var p = raw.map { T.rotation.act($0) }
            let anchor = eyeMidpoint(p, manifest: t.manifest)
            let shift = templateAnchor - anchor
            for i in p.indices { p[i] += shift }
            // 표정 제거: 템플릿 델타 × 그 컷의 가중치
            for (shape, deltas) in t.shapeDeltas {
                let w = shot.meta.blendShapes[shape]
                guard w > 1e-4, deltas.count >= pc else { continue }
                for i in 0..<pc { p[i] -= deltas[i] * w }
            }
            aligned.append(p)
        }

        // 2) 컷 평균 ---------------------------------------------------------------------
        var userPatch = [SIMD3<Float>](repeating: .zero, count: pc)
        for a in aligned { for i in 0..<pc { userPatch[i] += a[i] } }
        for i in 0..<pc { userPatch[i] /= Float(aligned.count) }
        var perShot: [String: Float] = [:]
        var worst: Float = 0
        for (k, a) in aligned.enumerated() {
            let r = Geometry.rms(a, userPatch)
            perShot[shots[k].kind.rawValue] = r
            worst = max(worst, r)
        }

        // 3) 스케일 s = 사용자 눈 간격 / 템플릿 눈 간격 -----------------------------------
        let s = eyeSpacing(userPatch, manifest: t.manifest) / max(1e-4, eyeSpacing(templatePatch, manifest: t.manifest))

        // 4) 패치 치환 + 두상 전파 --------------------------------------------------------
        let (positions, lambda, pivot) = try HeadPropagator.propagate(template: t, userPatch: userPatch, scale: s, options: options)

        // 5) 눈알 ---------------------------------------------------------------------------
        let eyeR = t.manifest.eyeRadius * s
        let (eL, eR) = eyeCenters(userPatch, manifest: t.manifest, radius: eyeR,
                                  fallbackL: SIMD3(t.manifest.eyeL[0], t.manifest.eyeL[1], t.manifest.eyeL[2]) * s,
                                  fallbackR: SIMD3(t.manifest.eyeR[0], t.manifest.eyeR[1], t.manifest.eyeR[2]) * s)

        let quality = FitQuality(patchRMS: worst, patchRMSPerShot: perShot, silhouetteResidualMedian: nil,
                                 rbfLambda: lambda, rbfPivotRatio: pivot, shotsUsed: shots.count, elapsedSeconds: Date().timeIntervalSince(start))
        return Identity(templateID: t.manifest.id, templateVersion: t.manifest.version, positions: positions, scale: s,
                        eyeCenterL: eL, eyeCenterR: eR, eyeRadius: eyeR, patchDeltas: [:], quality: quality)
    }

    static func eyeLandmarks(_ m: TemplateManifest, count: Int) -> (Int, Int, Int, Int)? {
        guard let oL = m.landmark(.eyeLeftOuter), let iL = m.landmark(.eyeLeftInner), let iR = m.landmark(.eyeRightInner), let oR = m.landmark(.eyeRightOuter),
              [oL, iL, iR, oR].allSatisfy({ $0 < count }) else { return nil }
        return (oL, iL, iR, oR)
    }

    /// 눈 중점 (랜드마크 없으면 패치 무게중심).
    static func eyeMidpoint(_ patch: [SIMD3<Float>], manifest m: TemplateManifest) -> SIMD3<Float> {
        guard let (oL, iL, iR, oR) = eyeLandmarks(m, count: patch.count) else { return patch.reduce(.zero, +) / Float(max(1, patch.count)) }
        return (patch[oL] + patch[iL] + patch[iR] + patch[oR]) / 4
    }

    /// 랜드마크(눈 안/바깥 꼬리)로 눈 간격. 랜드마크가 없으면 manifest 의 눈 중심 간격.
    static func eyeSpacing(_ patch: [SIMD3<Float>], manifest m: TemplateManifest) -> Float {
        guard let (oL, iL, iR, oR) = eyeLandmarks(m, count: patch.count) else {
            return simd_length(m.eyeCenterL - m.eyeCenterR)
        }
        let cL = (patch[oL] + patch[iL]) / 2, cR = (patch[oR] + patch[iR]) / 2
        return simd_length(cL - cR)
    }

    static func eyeCenters(_ patch: [SIMD3<Float>], manifest m: TemplateManifest, radius: Float,
                           fallbackL: SIMD3<Float>, fallbackR: SIMD3<Float>) -> (SIMD3<Float>, SIMD3<Float>) {
        guard let (oL, iL, iR, oR) = eyeLandmarks(m, count: patch.count) else { return (fallbackL, fallbackR) }
        // 눈꺼풀 표면 중심에서 안쪽(−Z)으로 반지름의 0.85 만큼 (각막이 표면 바로 뒤)
        let cL = (patch[oL] + patch[iL]) / 2 - SIMD3(0, 0, radius * 0.85)
        let cR = (patch[oR] + patch[iR]) / 2 - SIMD3(0, 0, radius * 0.85)
        return (cL, cR)
    }
}

/// 두상 전파: 전역 유사변환 + 국소 잔차 RBF(경계 거리 감쇠) + 목 감쇠 + 어깨 스케일 + 대칭.
public enum HeadPropagator {
    public static func propagate(template t: BustTemplate, userPatch: [SIMD3<Float>], scale s: Float, options: FitOptions)
        throws -> (positions: [SIMD3<Float>], lambda: Double, pivotRatio: Double) {
        let pc = t.patchCount
        precondition(userPatch.count == pc)
        let templatePatch = Array(t.patchPositions)

        // (a) 전역 유사변환: 템플릿 패치 → 사용자 패치
        let S = Procrustes.fit(source: templatePatch, target: userPatch, allowScale: true) ?? .identity
        let shoulders = Set(t.manifest.group(.shoulders))
        let neck = Set(t.manifest.group(.neck))
        var base = t.positions
        for i in base.indices {
            if shoulders.contains(i) {
                base[i] = SIMD3(base[i].x * s, base[i].y, base[i].z * s)     // 어깨: 가로·앞뒤 스케일만
            } else if neck.contains(i) {
                let w = smooth((base[i].y - options.neckFalloffBottom) / max(1e-4, options.neckFalloffTop - options.neckFalloffBottom))
                let sc = SIMD3(base[i].x * s, base[i].y, base[i].z * s)
                base[i] = S.apply(base[i]) * w + sc * (1 - w)
            } else {
                base[i] = S.apply(base[i])
            }
        }

        // (b) 국소 잔차 RBF
        let residual = (0..<pc).map { userPatch[$0] - base[$0] }
        var boundary = t.patchBoundaryVertices()
        if boundary.count > options.maxBoundaryCenters {
            let stride = Double(boundary.count) / Double(options.maxBoundaryCenters)
            boundary = (0..<options.maxBoundaryCenters).map { boundary[Int(Double($0) * stride)] }
        }
        let bset = Set(boundary)
        var interior: [Int] = []
        if options.interiorCenters > 0 {
            let stride = max(1, pc / options.interiorCenters)
            var i = stride / 2
            while i < pc && interior.count < options.interiorCenters { if !bset.contains(i) { interior.append(i) }; i += stride }
        }
        let centerIDs = boundary + interior
        let centers = centerIDs.map { base[$0] }
        guard let rbf = BiharmonicRBF(centers: centers, values: centerIDs.map { residual[$0] }, lambda: options.rbfLambda) else { throw FitError.rbfFailed }
        let boundaryPts = boundary.map { base[$0] }
        let sigma = options.propagationFalloff

        var d = [SIMD3<Float>](repeating: .zero, count: base.count)
        for i in pc..<base.count where !shoulders.contains(i) {
            var v = rbf.evaluate(base[i])
            if sigma > 0 {
                var dmin = Float.greatestFiniteMagnitude
                for b in boundaryPts { dmin = min(dmin, simd_length_squared(base[i] - b)) }
                v *= exp(-dmin / (sigma * sigma))
            }
            if neck.contains(i) {
                let w = smooth((base[i].y - options.neckFalloffBottom) / max(1e-4, options.neckFalloffTop - options.neckFalloffBottom))
                v *= w
            }
            d[i] = v
        }
        // (c) 좌우 대칭 보정 (패치 밖만)
        let sym = t.manifest.symmetryMap
        if options.symmetry > 0, sym.count == base.count {
            var dd = d
            for i in pc..<base.count {
                let j = Int(sym[i])
                guard j >= 0, j < base.count, j >= pc else { continue }
                let mirrored = SIMD3(-d[j].x, d[j].y, d[j].z)
                dd[i] = (d[i] + mirrored) / 2 * options.symmetry + d[i] * (1 - options.symmetry)
            }
            d = dd
        }
        var out = base
        for i in pc..<out.count { out[i] += d[i] }
        for i in 0..<pc { out[i] = userPatch[i] }
        return (out, rbf.lambda, rbf.pivotRatio)
    }

    static func smooth(_ x: Float) -> Float { let t = min(1, max(0, x)); return t * t * (3 - 2 * t) }
}
