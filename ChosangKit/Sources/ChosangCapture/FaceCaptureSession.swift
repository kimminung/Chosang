//
//  FaceCaptureSession.swift
//  ChosangCapture
//
//  iPhone ARFaceTracking 캡처 (TechPRD §6.3, T-201). M0 범위: 세션 수명 + 프레임 → `CaptureShot`(RGB·깊이·intrinsics·transform·1220 정점·52 가중치·조명)
//  + 8프레임 평균 + T-007 스파이크 프로브. 가이드 상태 기계·UI 는 M2.
//  🧪 실기기 필요: 시뮬레이터에는 TrueDepth/ARFaceTracking 이 없다(`ARFaceTrackingConfiguration.isSupported == false`).
//

import Foundation
import simd
import ChosangCore
#if os(iOS)
import ARKit
import CoreImage
import Observation

/// T-007 스파이크 보고: 한 프레임에서 깊이·내부 파라미터·정점·조명이 동시에 나오는가.
public struct ARFaceProbeReport: Sendable, Equatable {
    public var vertexCount: Int
    public var triangleCount: Int
    public var triangleHash: String
    public var hasDepth: Bool
    public var depthWidth: Int
    public var depthHeight: Int
    public var depthFormat: String
    public var depthTimestampDelta: Double
    public var imageWidth: Int
    public var imageHeight: Int
    public var intrinsics: Geometry.Intrinsics
    public var hasDirectionalLight: Bool
    public var ambientIntensity: Float
    public var colorTemperature: Float
    public var primaryDirection: [Float]?
    public var blendShapeCount: Int

    public var summary: String {
        """
        ARKit 얼굴: 정점 \(vertexCount) (기대 1220) · 삼각형 \(triangleCount) · 해시 \(triangleHash)
        깊이: \(hasDepth ? "\(depthWidth)×\(depthHeight) \(depthFormat) (Δt \(String(format: "%.1f", depthTimestampDelta * 1000)) ms)" : "없음")
        이미지: \(imageWidth)×\(imageHeight) · fx \(Int(intrinsics.fx)) fy \(Int(intrinsics.fy)) cx \(Int(intrinsics.cx)) cy \(Int(intrinsics.cy))
        조명: \(hasDirectionalLight ? "방향 추정 있음" : "방향 추정 없음") · ambient \(Int(ambientIntensity)) lm · \(Int(colorTemperature)) K
        블렌드셰이프: \(blendShapeCount)개
        """
    }
}

/// 프레임 요약 (가이드 UI 용).
public struct FaceFrameStatus: Sendable, Equatable {
    public var isTracked = false
    public var yaw: Float = 0       // 도, + = 피사체 왼쪽으로 고개 돌림
    public var pitch: Float = 0     // 도, + = 위
    public var neutrality: Float = 0 // 52 가중치 합 (작을수록 중립)
    public var ambientLumens: Float = 0
    public var hasDepth = false
}

/// 캡처 게이트 임계값 (M2 에서 DEBUG 패널로 노출).
public struct CaptureGate: Sendable, Equatable {
    public var neutralitySumMax: Float = 0.6
    public var yawTolerance: Float = 6
    public var pitchTolerance: Float = 5
    public var lumensRange: ClosedRange<Float> = 300...1500
    public var holdSeconds: Double = 0.7
    public var framesToAverage = 8
    public init() {}
}

@MainActor
@Observable
public final class FaceCaptureSession: NSObject, ARSessionDelegate {
    public private(set) var status = FaceFrameStatus()
    public private(set) var probe: ARFaceProbeReport?
    public private(set) var errorText: String?
    public private(set) var isRunning = false
    public var gate = CaptureGate()

    private let session = ARSession()
    private let ciContext = CIContext(options: [.cacheIntermediates: false])
    /// 평균용 링 버퍼 (최근 N 프레임의 정점·가중치)
    private var recentVertices: [[SIMD3<Float>]] = []
    private var recentWeights: [ArkitWeights] = []
    private var latestFrame: ARFrame?
    private var latestAnchor: ARFaceAnchor?

    public static var isSupported: Bool { ARFaceTrackingConfiguration.isSupported }

    public override init() { super.init() }

    public func start() {
        guard Self.isSupported else { errorText = "이 기기는 얼굴 추적(TrueDepth)을 지원하지 않습니다. 사진 폴백 캡처를 쓰세요."; return }
        let config = ARFaceTrackingConfiguration()
        config.isLightEstimationEnabled = true
        config.maximumNumberOfTrackedFaces = 1
        session.delegate = self
        session.run(config, options: [.resetTracking, .removeExistingAnchors])
        isRunning = true
        errorText = nil
    }

    public func stop() {
        session.pause()
        isRunning = false
        recentVertices.removeAll(); recentWeights.removeAll()
        latestFrame = nil; latestAnchor = nil
    }

    // MARK: ARSessionDelegate

    nonisolated public func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard let anchor = frame.anchors.compactMap({ $0 as? ARFaceAnchor }).first else {
            Task { @MainActor in self.status.isTracked = false }
            return
        }
        let verts = anchor.geometry.vertices
        let weights = ArkitWeights(named: Dictionary(uniqueKeysWithValues: anchor.blendShapes.map { ($0.key.rawValue, $0.value.floatValue) }))
        // 얼굴 자세: 카메라 기준 yaw/pitch
        let camToWorld = frame.camera.transform
        let faceInCam = camToWorld.inverse * anchor.transform
        let fwd = faceInCam.columns.2   // 얼굴 +Z (카메라 좌표)
        let yaw = atan2(fwd.x, fwd.z) * 180 / .pi
        let pitch = atan2(fwd.y, (fwd.x * fwd.x + fwd.z * fwd.z).squareRoot()) * 180 / .pi
        let ambient = Float(frame.lightEstimate?.ambientIntensity ?? 0)
        let hasDepth = frame.capturedDepthData != nil
        let needProbe = self.probeNeeded
        let report: ARFaceProbeReport? = needProbe ? Self.makeProbe(frame: frame, anchor: anchor) : nil
        Task { @MainActor in
            self.latestFrame = frame
            self.latestAnchor = anchor
            self.recentVertices.append(verts)
            self.recentWeights.append(weights)
            if self.recentVertices.count > self.gate.framesToAverage { self.recentVertices.removeFirst(); self.recentWeights.removeFirst() }
            self.status = FaceFrameStatus(isTracked: anchor.isTracked, yaw: yaw, pitch: pitch, neutrality: weights.sum, ambientLumens: ambient, hasDepth: hasDepth)
            if let report, self.probe == nil { self.probe = report }
        }
    }

    nonisolated private var probeNeeded: Bool { true }

    nonisolated static func makeProbe(frame: ARFrame, anchor: ARFaceAnchor) -> ARFaceProbeReport {
        let geo = anchor.geometry
        let tris = geo.triangleIndices
        let hash = ARKitFaceTopology.hash(arkitTriangleIndices: tris)
        var dw = 0, dh = 0, fmt = "-"
        if let d = frame.capturedDepthData {
            dw = CVPixelBufferGetWidth(d.depthDataMap); dh = CVPixelBufferGetHeight(d.depthDataMap)
            let t = CVPixelBufferGetPixelFormatType(d.depthDataMap)
            fmt = t == kCVPixelFormatType_DepthFloat32 ? "DepthFloat32" : (t == kCVPixelFormatType_DepthFloat16 ? "DepthFloat16" : (t == kCVPixelFormatType_DisparityFloat32 ? "DisparityFloat32" : String(format: "%08x", t)))
        }
        let res = frame.camera.imageResolution
        let K = Geometry.Intrinsics(matrix: frame.camera.intrinsics, width: Int(res.width), height: Int(res.height))
        let dir = frame.lightEstimate as? ARDirectionalLightEstimate
        return ARFaceProbeReport(vertexCount: geo.vertices.count, triangleCount: tris.count / 3, triangleHash: ARKitFaceTopology.hexString(hash),
                                 hasDepth: frame.capturedDepthData != nil, depthWidth: dw, depthHeight: dh, depthFormat: fmt,
                                 depthTimestampDelta: frame.capturedDepthDataTimestamp > 0 ? frame.timestamp - frame.capturedDepthDataTimestamp : 0,
                                 imageWidth: Int(res.width), imageHeight: Int(res.height), intrinsics: K,
                                 hasDirectionalLight: dir != nil, ambientIntensity: Float(frame.lightEstimate?.ambientIntensity ?? 0),
                                 colorTemperature: Float(frame.lightEstimate?.ambientColorTemperature ?? 0),
                                 primaryDirection: dir.map { [$0.primaryLightDirection.x, $0.primaryLightDirection.y, $0.primaryLightDirection.z] },
                                 blendShapeCount: anchor.blendShapes.count)
    }

    // MARK: 촬영

    /// 최근 N 프레임 평균으로 한 컷을 만든다. 이미지는 **센서 방향 그대로** 가로 버퍼를 세로(포트레이트)로 돌려 저장하고 intrinsics 도 함께 돌린다.
    public func captureShot(kind: ShotKind) -> CaptureShot? {
        guard let frame = latestFrame, let anchor = latestAnchor, !recentVertices.isEmpty else { return nil }
        let n = recentVertices.count
        var avg = [SIMD3<Float>](repeating: .zero, count: recentVertices[0].count)
        for v in recentVertices { for i in avg.indices { avg[i] += v[i] } }
        for i in avg.indices { avg[i] /= Float(n) }
        var w = ArkitWeights()
        for r in recentWeights { w.add(r, scale: 1 / Float(n)) }

        // RGB: BGRA 로 렌더 후 90° 회전(포트레이트 업라이트, 전면 카메라는 좌우 반전하지 않음)
        let ci = CIImage(cvPixelBuffer: frame.capturedImage).oriented(.right)
        let width = Int(ci.extent.width), height = Int(ci.extent.height)
        var image: RGBAImage? = nil
        if let cg = ciContext.createCGImage(ci, from: ci.extent) {
            var buf = [UInt8](repeating: 0, count: width * height * 4)
            let ok = buf.withUnsafeMutableBytes { raw -> Bool in
                guard let ctx = CGContext(data: raw.baseAddress, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4,
                                          space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
                ctx.draw(cg, in: CGRect(x: 0, y: 0, width: width, height: height))
                return true
            }
            if ok { image = RGBAImage(width: width, height: height, bytes: buf) }
        }
        // 가로 → 세로 회전에 맞춘 intrinsics: (x', y') = (H_land − y, x) → fx'=fy, fy'=fx, cx'=H−cy, cy'=cx
        let res = frame.camera.imageResolution
        let K = frame.camera.intrinsics
        let intr = Geometry.Intrinsics(fx: K.columns.1.y, fy: K.columns.0.x, cx: Float(res.height) - K.columns.2.y, cy: K.columns.2.x, width: width, height: height)
        // 카메라 변환도 같은 회전(카메라 좌표계를 Z 축 기준 −90° 회전)
        let rot = simd_float4x4(simd_quatf(angle: -.pi / 2, axis: [0, 0, 1]))
        let camT = frame.camera.transform * rot

        var depth: DepthMap? = nil
        if let d = frame.capturedDepthData {
            let conv = d.converting(toDepthDataType: kCVPixelFormatType_DepthFloat32)
            let pb = conv.depthDataMap
            CVPixelBufferLockBaseAddress(pb, .readOnly)
            let dw = CVPixelBufferGetWidth(pb), dh = CVPixelBufferGetHeight(pb), stride = CVPixelBufferGetBytesPerRow(pb) / 4
            if let base = CVPixelBufferGetBaseAddress(pb)?.assumingMemoryBound(to: Float.self) {
                // 가로 깊이 → 세로로 회전 (x' = dh−1−y, y' = x)
                var vals = [Float](repeating: 0, count: dw * dh)
                for y in 0..<dh { for x in 0..<dw { vals[x * dh + (dh - 1 - y)] = base[y * stride + x] } }
                depth = DepthMap(width: dh, height: dw, values: vals)
            }
            CVPixelBufferUnlockBaseAddress(pb, .readOnly)
        }
        let le = frame.lightEstimate
        let dir = le as? ARDirectionalLightEstimate
        let light = LightEstimate(ambientIntensity: Float(le?.ambientIntensity ?? 1000), ambientColorTemperature: Float(le?.ambientColorTemperature ?? 6500),
                                  primaryDirection: dir.map { [$0.primaryLightDirection.x, $0.primaryLightDirection.y, $0.primaryLightDirection.z] },
                                  primaryIntensity: dir.map { Float($0.primaryLightIntensity) })
        let meta = CaptureShotMeta(kind: kind, imageFile: "shot-\(kind.rawValue).jpg", depthFile: depth == nil ? nil : "depth-\(kind.rawValue).f32",
                                   imageWidth: width, imageHeight: height, depthWidth: depth?.width, depthHeight: depth?.height,
                                   intrinsics: intr, cameraTransform: camT, faceTransform: anchor.transform,
                                   faceVertices: avg, blendShapes: w, light: light, averagedFrames: n, timestamp: frame.timestamp)
        return CaptureShot(meta: meta, image: image, depth: depth)
    }

    /// 지금 프레임이 게이트를 통과하는가.
    public func passesGate(for kind: ShotKind) -> (ok: Bool, reason: String) {
        guard status.isTracked else { return (false, "얼굴을 찾는 중") }
        let (ty, tp) = kind.targetYawPitch
        if abs(status.yaw - ty) > gate.yawTolerance { return (false, status.yaw < ty ? "고개를 조금 더 왼쪽으로" : "고개를 조금 더 오른쪽으로") }
        if abs(status.pitch - tp) > gate.pitchTolerance { return (false, status.pitch < tp ? "턱을 조금 들어 주세요" : "턱을 조금 내려 주세요") }
        if kind.isNeutralRequired, status.neutrality > gate.neutralitySumMax { return (false, "표정을 풀어 주세요") }
        if !gate.lumensRange.contains(status.ambientLumens) { return (false, status.ambientLumens < gate.lumensRange.lowerBound ? "조금 더 밝은 곳으로" : "너무 밝습니다") }
        return (true, "유지하세요")
    }
}
#endif
