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
            #elseif os(macOS)
            PhotoCaptureView()   // T-205 사진 폴백 (Mac 카메라 · 사진 파일, sparse)
            #else
            placeholder("캡처는 iPhone·Mac 에서")
            #endif
        case .validate:
            #if os(macOS)
            ValidateView()
            #else
            placeholder("검증은 Mac 에서")
            #endif
        case .receive:
            TransferView()   // M6 T-603: Bonjour _chosang._tcp + TLS PSK 6자리
        }
    }

    private func placeholder(_ text: String) -> some View {
        ContentUnavailableView(text, systemImage: "hourglass", description: Text("다음 마일스톤에서 구현됩니다."))
    }
}

/// 미리보기 화면: 3D 흉상 + 오른쪽 패널(템플릿·클립·셰이프 슬라이더·성능). iPhone(가로 공간 compact)은 전체 화면 3D + 하단 글래스 바 + 시트.
struct PreviewScreen: View {
    @Environment(AppModel.self) private var model
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var sizeClass
    #endif

    var body: some View {
        #if os(iOS)
        if sizeClass == .compact { PhonePreviewScreen() } else { panelLayout }
        #else
        panelLayout
        #endif
    }

    private var panelLayout: some View {
        @Bindable var model = model
        return HStack(spacing: 0) {
            TemplatePreviewView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                // visionOS: 2D 창의 RealityView 는 콘텐츠를 창 평면 뒤에 그린다 → 불투명 배경이 흉상을 가린다(1차 "잘림"의 실제 원인)
                #if !os(visionOS)
                .background(Color.black.opacity(0.85))
                #endif
                .overlay(alignment: .topLeading) {
                    if model.sheetMode {
                        // 셰이프 시트(T-106): 현재 셰이프 이름을 타일에 새긴다.
                        // 이 모드에서는 오른쪽 패널을 숨기므로 **여기에 끄는 길을 둔다** — 없으면 빠져나올 수 없다.
                        HStack(spacing: 10) {
                            Text("\(model.sheetIndex + 1)/52  \(ArkitShape.allCases[model.sheetIndex].rawValue)")
                                .font(.system(size: 22, weight: .semibold, design: .monospaced))
                            Button {
                                model.sheetMode = false
                                model.weights = .zero
                            } label: {
                                Label("시트 끄기", systemImage: "xmark.circle.fill").font(.callout.bold())
                            }
                            .buttonStyle(.borderedProminent)
                            .keyboardShortcut(.escape, modifiers: [])
                        }
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
                        // 이 기기에서 찍은 캡처로 바로 흉상 만들기 (전송 없이) — iPhone·Mac
                        if model.fitSummary == nil, let latest = model.latestLocalCapture {
                            Button {
                                Task { await model.buildFromLatestCapture() }
                            } label: {
                                Label(model.isFitting ? "만드는 중…" : "내 캡처로 흉상 만들기 (컷 \(latest.shots.count))",
                                      systemImage: "person.crop.circle.badge.plus")
                            }
                            .font(.caption).disabled(model.isFitting)
                            if model.isFitting { ProgressView().controlSize(.small) }
                        }
                        if let fit = model.fitSummary {
                            // 받은 캡처로 만든 내 흉상 — 원본 템플릿과 바로 비교할 수 있게 되돌리기도 둔다
                            Divider()
                            Label("내 흉상 (피팅됨)", systemImage: "person.crop.circle.badge.checkmark").font(.caption.bold()).foregroundStyle(.green)
                            Text(fit).font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
                            if let tex = model.textureSummary {
                                Text(tex).font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
                                Toggle("내 피부 텍스처", isOn: $model.useAlbedo).font(.caption)
                                Toggle("알베도 상하 반전", isOn: $model.flipAlbedoV).font(.caption)
                                if let preview = model.albedoPreview {
                                    // UV 레이아웃을 눈으로 확인 — 얼굴이 제 위치에 찍혔는지 바로 보인다
                                    Image(decorative: preview, scale: 1).resizable().aspectRatio(1, contentMode: .fit)
                                        .frame(maxWidth: 160).clipShape(RoundedRectangle(cornerRadius: 6))
                                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(.secondary.opacity(0.4)))
                                }
                            }
                            HStack {
                                Button("템플릿 원본으로") {
                                    model.identity = Identity.fromTemplate(model.template)
                                    model.fitSummary = nil
                                    model.albedoTexture = nil
                                    model.textureSummary = nil
                                    model.lastAlbedo = nil; model.lastMask = nil; model.savedPersonaURL = nil
                                }
                                if let url = model.savedPersonaURL {
                                    ShareLink(item: url) { Text("내보내기") }
                                } else {
                                    Button(".chosang 저장") { Task { await model.savePersona() } }
                                }
                            }
                            .font(.caption)
                            if let url = model.savedPersonaURL {
                                Text("저장: \(url.lastPathComponent)").font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                            }
                        }
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

#if os(iOS)
/// iPhone 미리보기: 3D 가 화면 전체. 하단 글래스 바 = 템플릿 메뉴 · 턴테이블 · 표정(시트) · 정보(시트), 그 위에 클립 칩 가로 스크롤.
struct PhonePreviewScreen: View {
    @Environment(AppModel.self) private var model
    @State private var showShapes = false
    @State private var showInfo = false

    var body: some View {
        @Bindable var model = model
        ZStack(alignment: .bottom) {
            TemplatePreviewView()
                .background(Color.black)
                .ignoresSafeArea()
                .overlay(alignment: .top) {
                    if model.sheetMode {
                        // 하단 바를 숨기는 모드라 끄는 버튼을 여기 둔다 (없으면 빠져나올 수 없다)
                        HStack(spacing: 8) {
                            Text("\(model.sheetIndex + 1)/52  \(ArkitShape.allCases[model.sheetIndex].rawValue)")
                                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                            Button {
                                model.sheetMode = false
                                model.weights = .zero
                            } label: {
                                Label("끄기", systemImage: "xmark.circle.fill").font(.caption.bold())
                            }
                            .buttonStyle(.glassProminent)
                        }
                        .padding(8).glassEffect().padding(.top, 8)
                    } else if let e = model.loadError {
                        Text(e).font(.caption).foregroundStyle(.red).padding(8).glassEffect().padding()
                    }
                }
            if !model.sheetMode {
                VStack(spacing: 10) {
                    clipChips
                    GlassEffectContainer(spacing: 12) {
                        HStack(spacing: 12) {
                            Menu {
                                Picker("템플릿", selection: Binding(get: { model.templateSource }, set: { src in Task { await model.switchTemplate(to: src) } })) {
                                    ForEach(TemplateSource.allCases) { Text($0.rawValue).tag($0) }
                                }
                                if model.templateSource == .synthetic {
                                    Button("템플릿 그대로") { model.applyFixture(perturbed: false) }
                                    Button("섭동 사용자(1.05·코·턱)") { model.applyFixture(perturbed: true) }
                                }
                            } label: {
                                Label(shortTemplateName, systemImage: "cube").labelStyle(.titleAndIcon).lineLimit(1)
                            }
                            .buttonStyle(.glass)
                            Button { model.turntable.toggle() } label: { Image(systemName: model.turntable ? "rotate.3d.fill" : "rotate.3d") }
                                .buttonStyle(.glass).accessibilityLabel("턴테이블")
                            Button { showShapes = true } label: { Label("표정", systemImage: "slider.horizontal.3") }
                                .buttonStyle(.glassProminent)
                            Button { showInfo = true } label: { Image(systemName: "info.circle") }
                                .buttonStyle(.glass).accessibilityLabel("정보")
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 8)
            }
        }
        .sheet(isPresented: $showShapes) {
            NavigationStack {
                ScrollView { VStack(spacing: 14) { ClipPanel(); ShapeSlidersView() }.padding() }
                    .navigationTitle("표정 · 클립")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar { ToolbarItem(placement: .confirmationAction) { Button("닫기") { showShapes = false } } }
            }
            .presentationDetents([.medium, .large])
            .presentationBackgroundInteraction(.enabled(upThrough: .medium))
        }
        .sheet(isPresented: $showInfo) {
            NavigationStack {
                List {
                    Section("템플릿") {
                        Text(model.templateStatus).font(.caption)
                        Text("정점 \(model.vertexCount) (렌더 \(model.renderVertexCount))")
                        Text(model.deformationPath).font(.caption.monospaced())
                    }
                    Section("성능") {
                        Text(String(format: "변형 %.2f ms · 프레임 %.1f ms (%.0f fps)", model.updateMilliseconds, model.frameMilliseconds, model.fps)).font(.caption.monospacedDigit())
                    }
                    Section("내 흉상") {
                        if let latest = model.latestLocalCapture, model.fitSummary == nil {
                            Button(model.isFitting ? "만드는 중…" : "내 캡처로 흉상 만들기 (컷 \(latest.shots.count))") {
                                Task { await model.buildFromLatestCapture(); showInfo = false }
                            }
                            .disabled(model.isFitting)
                        }
                        if let fit = model.fitSummary {
                            Text(fit).font(.caption)
                            if let tex = model.textureSummary { Text(tex).font(.caption) }
                            Toggle("내 피부 텍스처", isOn: $model.useAlbedo)
                            Toggle("알베도 상하 반전", isOn: $model.flipAlbedoV)
                            Button("템플릿 원본으로") {
                                model.identity = Identity.fromTemplate(model.template)
                                model.fitSummary = nil; model.albedoTexture = nil; model.textureSummary = nil
                            }
                        }
                        if model.fitSummary == nil && model.latestLocalCapture == nil {
                            Text("캡처 탭에서 5컷을 찍고 번들을 저장하면 여기서 바로 만들 수 있습니다").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    Section("보기") {
                        Toggle("턴테이블", isOn: $model.turntable)
                        Toggle("프리비즈 카메라 (0,0.41,1.29 · hFOV 39.6°)", isOn: $model.previzCamera)
                        Toggle("셰이프 시트 (52 순환)", isOn: $model.sheetMode)
                        Toggle("1회 클립 반복", isOn: $model.clipLoop)
                    }
                }
                .navigationTitle("정보")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("닫기") { showInfo = false } } }
            }
            .presentationDetents([.medium, .large])
        }
    }

    private var shortTemplateName: String {
        switch model.templateSource {
        case .defaultTemplate: "기본 템플릿"
        case .synthetic: "합성"
        case .legacyBust: "소반 흉상"
        case .legacyEthan: "소반 데모"
        }
    }

    /// 클립 칩: 가로 스크롤, 선택은 토글.
    private var clipChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            GlassEffectContainer(spacing: 6) {
                HStack(spacing: 6) {
                    ForEach(SampledClip.contract.map(\.name), id: \.self) { n in
                        let on = model.selectedClip == n
                        Button(n) { model.selectedClip = on ? nil : n }
                            .font(.caption.weight(on ? .semibold : .regular))
                            .padding(.horizontal, 12).padding(.vertical, 7)
                            .foregroundStyle(on ? Color.accentColor : .primary)
                            .glassEffect(on ? .regular.tint(.accentColor.opacity(0.2)).interactive() : .regular.interactive())
                    }
                }
                .padding(.horizontal, 2)
            }
        }
    }
}
#endif

#Preview {
    RootView().environment(AppModel(launch: LaunchOptions()))
}
