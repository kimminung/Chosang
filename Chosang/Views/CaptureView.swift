//
//  CaptureView.swift
//  초상 (iOS)
//
//  M0: ARFaceTracking 세션 시작/정지, 프레임 상태(yaw·pitch·중립도·조도·깊이), T-007 프로브, 5컷 수동 촬영 → Documents/Captures/<uuid>/.
//  카메라 미리보기·각도 링·자동 촬영 상태 기계는 M2(T-202/T-203).
//

#if os(iOS)
import SwiftUI
import ChosangCore
import ChosangCapture
import ChosangIO

struct CaptureView: View {
    @State private var session = FaceCaptureSession()
    @State private var shots: [CaptureShot] = []
    @State private var message = ""

    var body: some View {
        // TrueDepth/ARFaceTracking 이 없는 기기·시뮬레이터는 사진 폴백(T-205)으로 — 같은 번들 포맷, sparse = true
        if FaceCaptureSession.isSupported { arkitBody } else { PhotoCaptureView() }
    }

    private var arkitBody: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text("초상 캡처 (TrueDepth · ARKit)").font(.title2.bold())
                HStack {
                    Button(session.isRunning ? "세션 정지" : "세션 시작") { session.isRunning ? session.stop() : session.start() }
                        .buttonStyle(.borderedProminent)
                        .disabled(!FaceCaptureSession.isSupported)
                    if let e = session.errorText { Text(e).font(.caption).foregroundStyle(.red) }
                }
                GroupBox("프레임") {
                    let s = session.status
                    VStack(alignment: .leading) {
                        Text(s.isTracked ? "추적 중" : "얼굴 없음")
                        Text(String(format: "yaw %.1f° · pitch %.1f° · 중립도 %.2f · %.0f lm · 깊이 %@", s.yaw, s.pitch, s.neutrality, s.ambientLumens, s.hasDepth ? "O" : "X"))
                            .font(.caption.monospacedDigit())
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                GroupBox("T-007 프로브") {
                    Text(session.probe?.summary ?? "세션을 시작하면 첫 프레임에서 기록됩니다.")
                        .font(.caption.monospaced()).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
                GroupBox("5컷") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(ShotKind.allCases, id: \.self) { kind in
                            HStack {
                                Text(kind.title).frame(width: 90, alignment: .leading)
                                let gate = session.passesGate(for: kind)
                                Text(gate.reason).font(.caption).foregroundStyle(gate.ok ? .green : .secondary)
                                Spacer()
                                Button(shots.contains { $0.kind == kind } ? "다시" : "촬영") {
                                    if let shot = session.captureShot(kind: kind) {
                                        shots.removeAll { $0.kind == kind }
                                        shots.append(shot)
                                        message = "\(kind.title) 촬영 — 정점 \(shot.meta.faceVertexArray.count), 깊이 \(shot.depth.map { "\($0.width)×\($0.height)" } ?? "없음")"
                                    } else { message = "프레임이 없습니다" }
                                }
                                .disabled(!session.isRunning)
                            }
                        }
                        Button("번들 저장 (Documents/Captures)") {
                            let meta = CaptureBundleMeta(device: UIDevice.current.model, sparse: false,
                                                         arkitTriangleHash: session.probe?.triangleHash, arkitVertexCount: session.probe?.vertexCount ?? 0, shots: shots.map(\.meta))
                            let bundle = CaptureBundle(meta: meta, shots: shots)
                            let folder = CaptureBundleStore.defaultFolder(for: meta.id)
                            do { try CaptureBundleStore.write(bundle, to: folder); message = "저장: \(folder.lastPathComponent)" }
                            catch { message = "저장 실패: \(error.localizedDescription)" }
                        }
                        .disabled(shots.isEmpty)
                        Text(message).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            .padding()
        }
        .onDisappear { session.stop() }
    }
}
#endif
