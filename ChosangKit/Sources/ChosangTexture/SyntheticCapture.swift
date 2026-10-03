//
//  SyntheticCapture.swift
//  ChosangTexture
//
//  템플릿(또는 섭동한 "사용자")을 가상 카메라 5대로 렌더해 **합성 캡처 번들**을 만든다 (T-009, Fixtures).
//  실기기 번들과 같은 규약(CaptureBundle.swift 머리말)을 따른다: 깊이 m, intrinsics 이미지 해상도 기준, 카메라 −Z 전방, 얼굴 앵커 좌표계.
//

import Foundation
import simd
import ChosangCore

public struct SyntheticCaptureOptions: Sendable {
    public var imageWidth = 640, imageHeight = 480
    public var depthWidth = 640, depthHeight = 480
    public var distance: Float = 0.45
    public var verticalFOV: Float = 48 * .pi / 180
    /// 광원 진행 방향(월드)
    public var lightDirection = simd_normalize(SIMD3<Float>(0.3, -0.5, -0.8))
    /// 정점 노이즈 표준편차 (m). 0 = 없음
    public var vertexNoise: Float = 0
    /// 깊이 노이즈 표준편차 (m)
    public var depthNoise: Float = 0
    public var seed: UInt64 = 7
    public init() {}
}

public enum SyntheticCapture {
    /// 얼굴 앵커 원점 (흉상 공간). ARKit 은 "머리 뒤쪽 중심" 이지만 피팅은 상대 좌표만 쓰므로 눈 높이 중심으로 둔다.
    public static let faceAnchorOrigin = SIMD3<Float>(0, 0.44, 0)

    /// 컷별 표정 가중치.
    public static func expression(for kind: ShotKind) -> ArkitWeights {
        var w = ArkitWeights()
        switch kind {
        case .smile:
            w[.mouthSmileLeft] = 0.8; w[.mouthSmileRight] = 0.8; w[.jawOpen] = 0.15
            w[.eyeSquintLeft] = 0.25; w[.eyeSquintRight] = 0.25; w[.cheekSquintLeft] = 0.3; w[.cheekSquintRight] = 0.3
        case .left:
            w[.browInnerUp] = 0.1
        default: break
        }
        return w
    }

    /// 컷별 카메라 (흉상 공간). 피사체가 고개를 돌리는 대신 카메라가 돈다(상대 자세는 같다).
    public static func camera(for kind: ShotKind, options o: SyntheticCaptureOptions) -> RenderCamera {
        let target = SIMD3<Float>(0, 0.41, 0.03)
        let (yaw, pitch) = kind.targetYawPitch
        let ry = yaw * .pi / 180, rp = pitch * .pi / 180
        // yaw + = 피사체 왼쪽(+X) 뺨이 보이도록 카메라를 +X 쪽으로. pitch + = 턱 밑이 보이도록 카메라를 아래로.
        let dir = SIMD3<Float>(sin(ry) * cos(rp), -sin(rp), cos(ry) * cos(rp))
        let eye = target + dir * o.distance
        let K = Geometry.intrinsics(verticalFOV: o.verticalFOV, width: o.imageWidth, height: o.imageHeight)
        return RenderCamera(intrinsics: K, transform: Geometry.lookAt(from: eye, to: target))
    }

    /// 번들 생성. `userPositions` 는 템플릿 토폴로지의 "사용자" 정점(없으면 템플릿 그대로).
    public static func makeBundle(template t: BustTemplate, userPositions: [SIMD3<Float>]? = nil,
                                  kinds: [ShotKind] = ShotKind.allCases, options o: SyntheticCaptureOptions = SyntheticCaptureOptions(),
                                  albedo: (Float, Float) -> SIMD3<Float> = { SyntheticAlbedo.color(u: $0, v: $1) }) -> CaptureBundle {
        let base = userPositions ?? t.positions
        var rng = SplitMix64(seed: o.seed)
        var shots: [CaptureShot] = []
        let pc = t.patchCount
        for (i, kind) in kinds.enumerated() {
            let weights = expression(for: kind)
            let deformed = t.deformedPositions(weights: weights, base: base)
            let normals = Geometry.vertexNormals(positions: deformed, indices: t.indices)
            let cam = camera(for: kind, options: o)
            let l = -o.lightDirection
            let out = SoftwareRasterizer.render(positions: deformed, normals: normals, uvs: t.uvs, indices: t.indices,
                                                camera: cam, width: o.imageWidth, height: o.imageHeight) { uv, n, _ in
                albedo(uv.x, uv.y) * (0.35 + 0.65 * max(0, simd_dot(n, l)))
            }
            var depth = out.depth
            if o.depthWidth != o.imageWidth || o.depthHeight != o.imageHeight {
                depth = resample(depth, width: o.depthWidth, height: o.depthHeight)
            }
            if o.depthNoise > 0 {
                for k in depth.values.indices where depth.values[k] > 0 { depth.values[k] += Float(rng.gaussian()) * o.depthNoise }
            }
            // 얼굴 정점: 앵커 좌표계 (+ 노이즈)
            var face = (0..<pc).map { deformed[$0] - faceAnchorOrigin }
            if o.vertexNoise > 0 {
                for k in face.indices { face[k] += SIMD3(Float(rng.gaussian()), Float(rng.gaussian()), Float(rng.gaussian())) * o.vertexNoise }
            }
            var faceTransform = matrix_identity_float4x4
            faceTransform.columns.3 = SIMD4(faceAnchorOrigin, 1)
            let light = LightEstimate(ambientIntensity: 1000, ambientColorTemperature: 6500,
                                      primaryDirection: o.lightDirection.array, primaryIntensity: 1200)
            let meta = CaptureShotMeta(kind: kind, imageFile: "shot-\(i).jpg", depthFile: "depth-\(i).f32",
                                       imageWidth: o.imageWidth, imageHeight: o.imageHeight, depthWidth: depth.width, depthHeight: depth.height,
                                       intrinsics: cam.intrinsics, cameraTransform: cam.transform, faceTransform: faceTransform,
                                       faceVertices: face, blendShapes: weights, light: light, averagedFrames: 8, timestamp: Double(i))
            shots.append(CaptureShot(meta: meta, image: out.color, depth: depth))
        }
        let bmeta = CaptureBundleMeta(device: "synthetic", sparse: false,
                                      arkitTriangleHash: t.manifest.patchTriangleHash, arkitVertexCount: pc, shots: shots.map(\.meta))
        return CaptureBundle(meta: bmeta, shots: shots)
    }

    static func resample(_ d: DepthMap, width: Int, height: Int) -> DepthMap {
        var v = [Float](repeating: 0, count: width * height)
        for y in 0..<height { for x in 0..<width {
            let sx = Int((Float(x) + 0.5) / Float(width) * Float(d.width)), sy = Int((Float(y) + 0.5) / Float(height) * Float(d.height))
            v[y * width + x] = d[min(d.width - 1, sx), min(d.height - 1, sy)]
        } }
        return DepthMap(width: width, height: height, values: v)
    }
}

/// 결정적 난수 (테스트 재현용).
public struct SplitMix64: Sendable {
    var state: UInt64
    public init(seed: UInt64) { state = seed }
    public mutating func next() -> UInt64 {
        state &+= 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
    public mutating func uniform() -> Double { Double(next() >> 11) / Double(1 << 53) }
    public mutating func gaussian() -> Double {
        let u1 = max(1e-12, uniform()), u2 = uniform()
        return (-2 * log(u1)).squareRoot() * cos(2 * .pi * u2)
    }
}
