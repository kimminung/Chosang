//
//  Identity.swift
//  ChosangCore
//
//  피팅 결과 = "내 얼굴로 바뀐 템플릿" (TechPRD §6.4-6). 정점 전체 + 스케일 + 눈알 + 패치 델타(바뀐 것만) + 품질 지표.
//  `identity.bin` 바이너리: 매직 "CHID", 버전 1, little-endian.
//

import Foundation
import simd

public struct FitQuality: Codable, Sendable, Equatable {
    /// 정합 후 사용자 메시 대비 패치 RMS (m). 목표 < 1.5 mm
    public var patchRMS: Float
    /// 컷별 패치 RMS
    public var patchRMSPerShot: [String: Float]
    /// 실루엣 잔차 중앙값 (m). M3 전에는 nil
    public var silhouetteResidualMedian: Float?
    /// RBF 정규화·조건
    public var rbfLambda: Double
    public var rbfPivotRatio: Double
    /// 쓴 컷 수
    public var shotsUsed: Int
    public var elapsedSeconds: Double
    public init(patchRMS: Float, patchRMSPerShot: [String: Float], silhouetteResidualMedian: Float?, rbfLambda: Double, rbfPivotRatio: Double, shotsUsed: Int, elapsedSeconds: Double) {
        self.patchRMS = patchRMS; self.patchRMSPerShot = patchRMSPerShot; self.silhouetteResidualMedian = silhouetteResidualMedian
        self.rbfLambda = rbfLambda; self.rbfPivotRatio = rbfPivotRatio; self.shotsUsed = shotsUsed; self.elapsedSeconds = elapsedSeconds
    }
}

public struct Identity: Sendable, Equatable {
    public var templateID: String
    public var templateVersion: String
    public var positions: [SIMD3<Float>]
    /// 사용자 머리 스케일 (사용자 눈 간격 / 템플릿 눈 간격)
    public var scale: Float
    public var eyeCenterL: SIMD3<Float>
    public var eyeCenterR: SIMD3<Float>
    public var eyeRadius: Float
    /// 보정된 패치 델타 (셰이프 → 1220 × xyz). 없으면 템플릿 것을 `scale` 로 조정해 쓴다.
    public var patchDeltas: [ArkitShape: [SIMD3<Float>]]
    public var quality: FitQuality?

    public init(templateID: String, templateVersion: String, positions: [SIMD3<Float>], scale: Float,
                eyeCenterL: SIMD3<Float>, eyeCenterR: SIMD3<Float>, eyeRadius: Float,
                patchDeltas: [ArkitShape: [SIMD3<Float>]] = [:], quality: FitQuality? = nil) {
        self.templateID = templateID; self.templateVersion = templateVersion; self.positions = positions; self.scale = scale
        self.eyeCenterL = eyeCenterL; self.eyeCenterR = eyeCenterR; self.eyeRadius = eyeRadius
        self.patchDeltas = patchDeltas; self.quality = quality
    }

    /// 템플릿 그대로 (사용자 없음) — 미리보기·테스트용.
    public static func fromTemplate(_ t: BustTemplate) -> Identity {
        Identity(templateID: t.manifest.id, templateVersion: t.manifest.version, positions: t.positions, scale: 1,
                 eyeCenterL: SIMD3(t.manifest.eyeL[0], t.manifest.eyeL[1], t.manifest.eyeL[2]),
                 eyeCenterR: SIMD3(t.manifest.eyeR[0], t.manifest.eyeR[1], t.manifest.eyeR[2]),
                 eyeRadius: t.manifest.eyeRadius)
    }

    /// 런타임용 52 델타: 패치는 `patchDeltas`(있으면) 또는 템플릿 그대로, 바깥은 템플릿 × scale.
    public func runtimeDeltas(template: BustTemplate) -> [ArkitShape: [SIMD3<Float>]] {
        var out: [ArkitShape: [SIMD3<Float>]] = [:]
        let pc = template.patchCount
        for (shape, d) in template.shapeDeltas {
            var arr = d
            if arr.count == positions.count {
                for i in pc..<arr.count { arr[i] *= scale }
            }
            if let p = patchDeltas[shape], p.count == pc, arr.count >= pc {
                for i in 0..<pc { arr[i] = p[i] }
            }
            out[shape] = arr
        }
        return out
    }

    // MARK: identity.bin

    static let magic: UInt32 = 0x4449_4843 // "CHID" little-endian

    public func serialized() throws -> Data {
        var d = Data()
        func put<T>(_ v: T) { withUnsafeBytes(of: v) { d.append(contentsOf: $0) } }
        func putString(_ s: String) { let u = Array(s.utf8); put(UInt32(u.count)); d.append(contentsOf: u) }
        put(Identity.magic); put(UInt32(1))
        putString(templateID); putString(templateVersion)
        put(UInt32(positions.count))
        for p in positions { put(p.x); put(p.y); put(p.z) }
        put(scale)
        for v in [eyeCenterL, eyeCenterR] { put(v.x); put(v.y); put(v.z) }
        put(eyeRadius)
        put(UInt32(patchDeltas.count))
        for (shape, arr) in patchDeltas.sorted(by: { $0.key.index < $1.key.index }) {
            putString(shape.rawValue); put(UInt32(arr.count))
            for p in arr { put(p.x); put(p.y); put(p.z) }
        }
        if let q = quality {
            let json = try JSONEncoder().encode(q)
            put(UInt32(json.count)); d.append(json)
        } else { put(UInt32(0)) }
        return d
    }

    public init(serialized data: Data) throws {
        var off = 0
        func take<T>(_: T.Type) throws -> T {
            let n = MemoryLayout<T>.size
            guard off + n <= data.count else { throw IdentityError.truncated }
            defer { off += n }
            return data.subdata(in: off..<(off + n)).withUnsafeBytes { $0.loadUnaligned(as: T.self) }
        }
        func takeString() throws -> String {
            let n = Int(try take(UInt32.self))
            guard off + n <= data.count else { throw IdentityError.truncated }
            defer { off += n }
            return String(decoding: data.subdata(in: off..<(off + n)), as: UTF8.self)
        }
        func takeVec() throws -> SIMD3<Float> { SIMD3(try take(Float.self), try take(Float.self), try take(Float.self)) }
        guard try take(UInt32.self) == Identity.magic else { throw IdentityError.badMagic }
        guard try take(UInt32.self) == 1 else { throw IdentityError.unsupportedVersion }
        templateID = try takeString(); templateVersion = try takeString()
        let n = Int(try take(UInt32.self))
        var pos: [SIMD3<Float>] = []; pos.reserveCapacity(n)
        for _ in 0..<n { pos.append(try takeVec()) }
        positions = pos
        scale = try take(Float.self)
        eyeCenterL = try takeVec(); eyeCenterR = try takeVec()
        eyeRadius = try take(Float.self)
        let dc = Int(try take(UInt32.self))
        var deltas: [ArkitShape: [SIMD3<Float>]] = [:]
        for _ in 0..<dc {
            let name = try takeString()
            let c = Int(try take(UInt32.self))
            var arr: [SIMD3<Float>] = []; arr.reserveCapacity(c)
            for _ in 0..<c { arr.append(try takeVec()) }
            if let s = ArkitShape(rawValue: name) { deltas[s] = arr }
        }
        patchDeltas = deltas
        let qn = Int(try take(UInt32.self))
        if qn > 0 {
            guard off + qn <= data.count else { throw IdentityError.truncated }
            quality = try JSONDecoder().decode(FitQuality.self, from: data.subdata(in: off..<(off + qn)))
            off += qn
        } else { quality = nil }
    }
}

public enum IdentityError: Error, LocalizedError {
    case badMagic, unsupportedVersion, truncated
    public var errorDescription: String? {
        switch self {
        case .badMagic: "identity.bin 매직이 다릅니다"
        case .unsupportedVersion: "identity.bin 버전을 지원하지 않습니다"
        case .truncated: "identity.bin 이 잘렸습니다"
        }
    }
}
