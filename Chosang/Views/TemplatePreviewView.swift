//
//  TemplatePreviewView.swift
//  초상
//
//  RealityView 로 BustEntity(bust.mesh → LowLevelMesh + LowLevelDeformation/CPU) 를 그린다. 3 플랫폼 공용(T-508 의 1차).
//  기본 템플릿이면 Template.usdz 엔티티도 함께 둔다(눈알·입안 = RealityKit 스킨/셰이프; Bust 파트는 투명 머티리얼로 숨김) — 같은 가중치로 구동.
//  매 프레임: ClipPlayer 가중치 ⊕ 슬라이더 가중치 → FaceRigComponent.clipWeights → FaceRigSystem → BustEntity.update / BlendShapeWeightsComponent.
//  프리비즈 카메라(T-701 준비): 조준 (0,0.41,0.09)·위치 (0,0.41,1.29)·수평 FOV 39.6°, 16:9.
//

import SwiftUI
import RealityKit
import ChosangCore
import ChosangRig

struct TemplatePreviewView: View {
    @Environment(AppModel.self) private var model
    @State private var holder = PreviewHolder()

    var body: some View {
        GeometryReader { geo in
            let previz = model.previzCamera
            let size = previz ? fit169(geo.size) : geo.size
            RealityView { content in
                let anchor = Entity()
                anchor.name = "PreviewAnchor"
                #if os(visionOS)
                // 2D 창의 RealityView: z<0 콘텐츠는 유리 배경 뒤에서 흐려지고, 불투명 배경을 두면 아예 가려진다(1차 "잘림"의 실제 원인).
                // 흉상 전체(z −0.12…0.128 × 0.55)가 창 평면 앞에 오도록 z +0.08, 배경 없음(PreviewScreen).
                anchor.position = SIMD3(0, -0.19, 0.08)
                anchor.scale = SIMD3(repeating: 0.55)
                #else
                anchor.position = .zero
                let camera = PerspectiveCamera()
                camera.name = "PreviewCamera"
                content.add(camera)
                holder.camera = camera
                let light = DirectionalLight()
                light.light.intensity = 2500
                light.look(at: .zero, from: SIMD3(0.5, 1.0, 1.2), relativeTo: nil)
                content.add(light)
                let fill = DirectionalLight()
                fill.light.intensity = 900
                fill.look(at: .zero, from: SIMD3(-1.0, 0.3, 0.8), relativeTo: nil)
                content.add(fill)
                #endif
                content.add(anchor)
                holder.anchor = anchor
                holder.rebuild(model: model)
                holder.applyCamera(previz: model.previzCamera)
                holder.subscription = content.subscribe(to: SceneEvents.Update.self) { ev in
                    holder.tick(dt: Float(ev.deltaTime), model: model)
                }
            } update: { _ in
                holder.rebuildIfNeeded(model: model)
                holder.applyCamera(previz: model.previzCamera)
            }
            .frame(width: size.width, height: size.height)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .gesture(DragGesture().onChanged { v in holder.dragYaw = Float(v.translation.width) * 0.01 })
        }
    }

    private func fit169(_ s: CGSize) -> CGSize {
        let w = min(s.width, s.height * 16 / 9)
        return CGSize(width: w, height: w * 9 / 16)
    }
}

/// RealityView 수명 밖에서 엔티티·플레이어를 쥔다.
@MainActor
@Observable
final class PreviewHolder {
    var anchor: Entity?
    var camera: Entity?
    var bust: BustEntity?
    var usdz: Entity?
    var subscription: EventSubscription?
    var player = ClipPlayer()
    var builtKey = ""
    var yaw: Float = 0
    var dragYaw: Float = 0
    var lastClip: String?
    var frameTimes: [Double] = []
    var lastTickNanos: UInt64 = 0
    var sheetClock: Double = 0
    var cameraMode = ""

    func key(_ model: AppModel) -> String {
        // sheetMode 는 자동 깜빡임·시선을 끄므로 키에 넣어 토글할 때 리그를 다시 만든다(끄고 나면 깜빡임이 돌아와야 한다).
        "\(model.templateSource.rawValue)|\(model.template.cacheKey)|\(model.identity?.scale ?? 0)|\(model.identity?.positions.first?.y ?? 0)|\(model.usdzEntity == nil)|\(model.sheetMode)|\(model.albedoTexture == nil)|\(model.useAlbedo)"
    }

    func rebuildIfNeeded(model: AppModel) { if key(model) != builtKey { rebuild(model: model) } }

    func rebuild(model: AppModel) {
        guard let anchor else { return }
        builtKey = key(model)
        anchor.children.removeAll()
        bust = nil; usdz = nil
        do {
            let b = try BustEntity(template: model.template, identity: model.identity, material: model.bustMaterial)
            var rig = FaceRigComponent()
            rig.autoBlink = !model.sheetMode
            rig.autoGaze = !model.sheetMode
            b.root.components.set(rig)
            b.root.components.set(BustBinding(bust: b))
            anchor.addChild(b.root)
            bust = b
            model.deformationPath = b.pathDescription
            model.vertexCount = model.template.vertexCount
            model.renderVertexCount = b.renderMesh.vertexCount
            if let e = model.usdzEntity {
                let clone = e.clone(recursive: true)
                var r2 = FaceRigComponent()
                r2.autoBlink = !model.sheetMode
                r2.autoGaze = false
                clone.components.set(r2)
                if model.templateSource == .defaultTemplate {
                    // 기본 템플릿: EyesMouth.usdz(Bust 없음) 오버레이. 없으면 Template.usdz 의 가장 큰 파트를 투명으로
                    if model.overlayHasBust { hideLargestPart(in: clone) }
                    clone.position = .zero
                } else {
                    clone.position = SIMD3(0.42, 0, 0)
                    b.root.position = SIMD3(-0.22, 0, 0)
                }
                anchor.addChild(clone)
                usdz = clone
            }
        } catch {
            model.loadError = "BustEntity 생성 실패: \(error.localizedDescription)"
        }
    }

    /// 모델 엔티티의 가장 큰 파트(Bust)를 투명 머티리얼로 숨긴다 — 눈알·입안·치아는 그대로.
    private func hideLargestPart(in root: Entity) {
        root.forEachDescendant { e in
            guard var mc = e.components[ModelComponent.self] else { return }
            var bestIndex = -1, bestCount = 0, partIndex = 0
            for model in mc.mesh.contents.models {
                for part in model.parts {
                    if part.positions.count > bestCount { bestCount = part.positions.count; bestIndex = partIndex }
                    partIndex += 1
                }
            }
            guard bestIndex >= 0, bestIndex < mc.materials.count else { return }
            var mat = UnlitMaterial(color: .clear)
            mat.blending = .transparent(opacity: .init(floatLiteral: 0))
            mc.materials[bestIndex] = mat
            e.components.set(mc)
        }
    }

    func applyCamera(previz: Bool) {
        #if !os(visionOS)
        guard let camera = camera as? PerspectiveCamera, let anchor else { return }
        let mode = previz ? "previz" : "orbit"
        guard mode != cameraMode else { return }
        cameraMode = mode
        if previz {
            let spec = PrevizCameraSpec.contract
            camera.camera.fieldOfViewInDegrees = spec.verticalFOVDegrees
            camera.position = SIMD3(spec.position[0], spec.position[1], spec.position[2])
            camera.look(at: SIMD3(spec.aim[0], spec.aim[1], spec.aim[2]), from: camera.position, relativeTo: nil)
            anchor.position = .zero
        } else {
            camera.camera.fieldOfViewInDegrees = 34
            camera.position = SIMD3(0, 0.02, 1.05)
            camera.look(at: .zero, from: camera.position, relativeTo: nil)
            anchor.position = SIMD3(0, -0.30, 0)
        }
        #endif
    }

    func tick(dt: Float, model: AppModel) {
        let now = DispatchTime.now().uptimeNanoseconds
        if lastTickNanos > 0 {
            let ms = Double(now - lastTickNanos) / 1_000_000
            frameTimes.append(ms)
            if frameTimes.count > 60 {
                frameTimes.removeFirst()
                let avg = frameTimes.reduce(0, +) / Double(frameTimes.count)
                model.frameMilliseconds = avg
                model.fps = avg > 0 ? 1000 / avg : 0
            }
        }
        lastTickNanos = now
        guard let anchor else { return }
        if model.turntable { yaw += dt * 0.5 }
        anchor.orientation = simd_quatf(angle: yaw + dragYaw, axis: [0, 1, 0])

        var base: ArkitWeights
        var pose = ClipPlayer.Pose.empty
        if model.sheetMode {
            // 셰이프 시트: 52 셰이프를 dwell 초마다 하나씩 1.0. **한 바퀴 돌면 스스로 멈춘다**(무한 반복이면 빠져나올 길이 없다).
            sheetClock += Double(dt)
            if sheetClock >= model.sheetDwell {
                sheetClock = 0
                let next = model.sheetIndex + 1
                if next >= ArkitShape.count {
                    model.sheetIndex = 0
                    model.sheetMode = false
                    model.weights = .zero
                } else {
                    model.sheetIndex = next
                }
            }
            base = ArkitWeights()
            if model.sheetMode { base[ArkitShape.allCases[model.sheetIndex]] = 1 }
        } else {
            if model.selectedClip != lastClip {
                lastClip = model.selectedClip
                if let name = model.selectedClip { player.play(model.clip(named: name)) } else { player.stop() }
            }
            pose = player.advance(dt)
            if player.isFinished, model.clipLoop, let name = model.selectedClip, !(player.current?.loop ?? true) { player.play(model.clip(named: name), crossfade: 0.1) }
            base = pose.weights
            base.add(model.weights)
        }
        for e in [bust?.root, usdz].compactMap({ $0 }) {
            if var rig = e.components[FaceRigComponent.self] {
                rig.clipWeights = base
                e.components.set(rig)
            }
        }
        bust?.applyHeadPose(pose.bones[.head], neck: pose.bones[.neck])
        if let u = usdz, model.templateSource == .defaultTemplate, let b = bust { u.transform = b.model.transform }
        if let b = bust { model.updateMilliseconds = b.lastUpdateMilliseconds; model.deformationPath = b.pathDescription }
    }
}
