//
//  ContentView.swift
//  초상
//
//  루트: 플랫폼별 탭 (visionOS 미리보기·받기·스파이크 / iOS 미리보기·캡처·스파이크 / macOS 미리보기·검증·스파이크).
//

import SwiftUI
import ChosangCore

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        TabView(selection: $model.tab) {
            ForEach(AppTab.platformTabs) { tab in
                Tab(tab.rawValue, systemImage: tab.systemImage, value: tab) {
                    content(for: tab)
                }
            }
        }
        #if os(macOS)
        .frame(minWidth: 900, minHeight: 640)
        #endif
    }

    @ViewBuilder
    private func content(for tab: AppTab) -> some View {
        switch tab {
        case .preview: PreviewScreen()
        case .spikes: SpikesView()
        case .capture:
            #if os(iOS)
            CaptureView()
            #else
            placeholder("캡처는 iPhone 에서")
            #endif
        case .validate:
            #if os(macOS)
            ValidateView()
            #else
            placeholder("검증은 Mac 에서")
            #endif
        case .receive:
            placeholder("받기 — M6 (Network.framework, Bonjour _chosang._tcp)")
        }
    }

    private func placeholder(_ text: String) -> some View {
        ContentUnavailableView(text, systemImage: "hourglass", description: Text("다음 마일스톤에서 구현됩니다."))
    }
}

/// 미리보기 화면: 3D 흉상 + 오른쪽 패널(템플릿·클립·셰이프 슬라이더·성능).
struct PreviewScreen: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        HStack(spacing: 0) {
            TemplatePreviewView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                // visionOS: 2D 창의 RealityView 는 콘텐츠를 창 평면 뒤에 그린다 → 불투명 배경이 흉상을 가린다(1차 "잘림"의 실제 원인)
                #if !os(visionOS)
                .background(Color.black.opacity(0.85))
                #endif
                .overlay(alignment: .topLeading) {
                    if model.sheetMode {
                        // 셰이프 시트(T-106): 현재 셰이프 이름을 타일에 새긴다
                        Text("\(model.sheetIndex + 1)/52  \(ArkitShape.allCases[model.sheetIndex].rawValue)")
                            .font(.system(size: 22, weight: .semibold, design: .monospaced))
                            .padding(8).background(.black.opacity(0.6)).foregroundStyle(.white).padding(10)
                    }
                }
            if model.sheetMode { EmptyView() } else {
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    GroupBox("템플릿") {
                        Picker("템플릿", selection: Binding(get: { model.templateSource }, set: { src in Task { await model.switchTemplate(to: src) } })) {
                            ForEach(TemplateSource.allCases) { Text($0.rawValue).tag($0) }
                        }
                        .pickerStyle(.menu)
                        .labelsHidden()
                        if let e = model.loadError { Text(e).font(.caption).foregroundStyle(.red) }
                        if model.templateSource == .synthetic {
                            HStack {
                                Button("템플릿 그대로") { model.applyFixture(perturbed: false) }
                                Button("섭동 사용자(1.05·코·턱)") { model.applyFixture(perturbed: true) }
                            }
                            .buttonStyle(.bordered)
                            .font(.caption)
                        }
                        Toggle("턴테이블", isOn: $model.turntable)
                        Text(model.templateStatus).font(.caption2).foregroundStyle(.secondary).lineLimit(2)
                        Text("정점 \(model.vertexCount) (렌더 \(model.renderVertexCount)) · \(model.deformationPath)")
                            .font(.caption).foregroundStyle(.secondary)
                        Text(String(format: "변형 %.2f ms · 프레임 %.1f ms (%.0f fps)", model.updateMilliseconds, model.frameMilliseconds, model.fps))
                            .font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                        #if !os(visionOS)
                        Toggle("프리비즈 카메라 (0,0.41,1.29 · hFOV 39.6°)", isOn: $model.previzCamera).font(.caption)
                        #endif
                        Toggle("셰이프 시트 (52 순환)", isOn: $model.sheetMode).font(.caption)
                    }
                    ClipPanel()
                    ShapeSlidersView()
                }
                .padding()
            }
            .frame(width: 340)
            }
        }
    }
}

#Preview {
    RootView().environment(AppModel(launch: LaunchOptions()))
}
