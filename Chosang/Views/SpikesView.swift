//
//  SpikesView.swift
//  초상
//
//  M0 스파이크 4개를 앱 안에서 바로 돌려 본다. 결과는 Docs/Spikes.md 에 옮겨 적는다.
//   T-004 USDZ 셰이프 델타 읽기 · T-005 ModelIO USD 내보내기 능력 · T-006 LowLevelDeformation 성능 · T-007 iPhone ARKit 한 프레임 (🧪)
//

import SwiftUI
import ChosangCore
import ChosangRig
import ChosangIO
import ChosangValidate
#if os(iOS)
import ChosangCapture
#endif

struct SpikesView: View {
    @Environment(AppModel.self) private var model
    @State private var reports: [String: String] = [:]
    @State private var running = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("M0 스파이크").font(.title2.bold())
                spike("T-004", "USDZ → MeshResource.contents → blendShapeOffsets(named:)", key: "t004") {
                    var out: [String] = []
                    for name in ["DemoAvatar_Ethan", "SplatPlaceholder_Bust"] {
                        guard let url = Bundle.main.url(forResource: name, withExtension: "usdz") else { out.append("\(name).usdz 없음"); continue }
                        do {
                            let (t, r, _) = try await TemplateLoader.load(url: url)
                            out.append(r.summary)
                            if let t { out.append("→ BustTemplate 생성: 정점 \(t.vertexCount), 델타 \(t.shapeDeltas.count)개, 스켈레톤 \(t.skeleton?.jointNames.count ?? 0)") }
                            let readable = r.readableOffsets.filter { $0.value }.keys.sorted()
                            if !readable.isEmpty { out.append("읽힌 셰이프: \(readable.joined(separator: ", "))") }
                        } catch { out.append("\(name): 실패 \(error.localizedDescription)") }
                        out.append("")
                    }
                    return out.joined(separator: "\n")
                }
                spike("T-005", "ModelIO USD 내보내기 (이 플랫폼)", key: "t005") {
                    USDExport.capability().summary + "\n(macOS 27.0.1 측정: usdz ✗ · usdc ✓ 2744 B · usda ✓ · obj ✓ → usdc + 자체 zip 으로 usdz)"
                }
                spike("T-006", "LowLevelMesh + LowLevelDeformation 60 fps", key: "t006") {
                    """
                    현재 경로: \(model.deformationPath)
                    정점 \(model.vertexCount) · 변형 \(String(format: "%.3f", model.updateMilliseconds)) ms · 프레임 \(String(format: "%.1f", model.frameMilliseconds)) ms (\(String(format: "%.0f", model.fps)) fps)
                    → 미리보기 탭에서 클립을 재생하며 30초 이상 두면 평균이 안정됩니다. 시뮬레이터 수치는 참고용(실기기 T-509).
                    뼈 클립 결정: 자체 샘플러(ClipPlayer) — 52 가중치와 같은 타임라인·크로스페이드를 한 곳에서 다루고, USD SkelAnimation 이 아직 없음.
                    """
                }
                spike("T-007", "iPhone ARFaceTracking 한 프레임: 깊이·내부 파라미터·1220 정점·조명", key: "t007") {
                    #if os(iOS)
                    if FaceCaptureSession.isSupported {
                        return "지원 기기입니다. 캡처 탭 → 시작 → ⓘ 진단 시트에 첫 프레임 프로브(정점 1220·삼각형 해시·깊이·intrinsics·조명)가 기록됩니다. 🧪 실기기에서 확인."
                    } else {
                        return "이 기기/시뮬레이터는 ARFaceTracking 을 지원하지 않습니다(캡처 탭은 사진 폴백으로 뜹니다). 🧪 iPhone 실기기(TrueDepth)에서 캡처 탭 → 시작 → ⓘ 진단."
                    }
                    #else
                    return "iPhone 전용. 🧪 실기기 절차: 캡처 탭 → 세션 시작 → 프로브 보고(정점 1220·삼각형 해시·깊이 640×480 Float32·intrinsics·조명 방향) 를 Docs/Spikes.md 에 기록."
                    #endif
                }
                spike("검증기", "소반 임시 USDZ 로 실패하는 검사 목록 (M1 블렌더 우선순위)", key: "val") {
                    var m = TemplateManifest(id: "soban-legacy", version: "0", vertexCount: model.vertexCount, triangleCount: 0, patchTriangleHash: "0", landmarks: [:], groups: [:], shapeKeys: model.loadReport?.blendShapeNames ?? [])
                    m.libraryObjects = []
                    let issues = TemplateValidator.validate(ValidationInput(manifest: m, template: nil, clips: [], previzNames: [], library: [], hasUSDZ: true, hasBustMesh: false))
                    return TemplateValidator.report(issues, title: "소반 레거시")
                }
                if !model.spikeLog.isEmpty {
                    GroupBox("로그") { Text(model.spikeLog.joined(separator: "\n")).font(.caption.monospaced()).frame(maxWidth: .infinity, alignment: .leading) }
                }
            }
            .padding()
        }
    }

    private func spike(_ id: String, _ title: String, key: String, run: @escaping () async -> String) -> some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(id).font(.headline.monospaced())
                    Text(title).font(.subheadline)
                    Spacer()
                    Button("실행") { Task { running = true; reports[key] = await run(); running = false } }
                        .disabled(running)
                }
                if let r = reports[key] {
                    Text(r).font(.caption.monospaced()).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }
}
