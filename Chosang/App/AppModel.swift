//
//  AppModel.swift
//  초상
//
//  앱 상태(@Observable). 템플릿 소스(기본 블렌더 템플릿 / 합성 / 소반 레거시 USDZ), 셰이프 가중치, 클립, 성능 수치, 스파이크 보고.
//

import Foundation
import Observation
import RealityKit
import ChosangCore
import ChosangRig
import ChosangIO

enum TemplateSource: String, CaseIterable, Identifiable {
    case defaultTemplate = "기본 템플릿 (블렌더)"
    case synthetic = "합성 템플릿"
    case legacyBust = "소반 흉상 USDZ"
    case legacyEthan = "소반 데모 아바타 USDZ"
    var id: String { rawValue }

    var resourceName: String? {
        switch self {
        case .defaultTemplate, .synthetic: nil
        case .legacyBust: "SplatPlaceholder_Bust"
        case .legacyEthan: "DemoAvatar_Ethan"
        }
    }
}

enum AppTab: String, CaseIterable, Identifiable {
    case preview = "미리보기", capture = "캡처", validate = "검증", spikes = "스파이크", receive = "받기"
    var id: String { rawValue }
    var systemImage: String {
        switch self {
        case .preview: "person.crop.rectangle"
        case .capture: "camera.viewfinder"
        case .validate: "checkmark.seal"
        case .spikes: "testtube.2"
        case .receive: "antenna.radiowaves.left.and.right"
        }
    }
    static var platformTabs: [AppTab] {
        #if os(visionOS)
        [.preview, .receive, .spikes]
        #elseif os(iOS)
        [.preview, .capture, .spikes]
        #else
        [.preview, .capture, .validate, .spikes]
        #endif
    }
}

@MainActor
@Observable
final class AppModel {
    let launch: LaunchOptions
    var tab: AppTab
    var templateSource: TemplateSource = .defaultTemplate
    /// 현재 템플릿
    var template: BustTemplate
    var identity: Identity?
    var loadReport: TemplateLoadReport?
    var loadError: String?
    /// USDZ 원본 엔티티 (기본 템플릿: 눈알·입안 표시 + 셰이프/스킨 비교, 레거시: 전체)
    var usdzEntity: Entity?
    /// 기본 템플릿 캐시 폴더 (Template.usdz · clips · library.json)
    var templateFolder: URL?
    /// 오버레이 USDZ 에 Bust 파트가 들어 있는가 (EyesMouth.usdz 가 없을 때만 true → 가장 큰 파트 숨김 시도)
    var overlayHasBust = true
    var clips: [SampledClip] = []
    var library: [LibraryEntry] = []
    var templateStatus = "로드 전"

    // 표정·클립
    var weights = ArkitWeights()
    var selectedClip: String? = nil
    var clipLoop = true
    var turntable = true
    /// 프리비즈 카메라(2차 계약 #9) — macOS/iOS 미리보기에서 카메라를 조준 (0,0.41,0.09)·위치 (0,0.41,1.29)·수평 FOV 39.6° 로
    var previzCamera = false
    /// 셰이프 시트 모드: 52 셰이프를 차례로 1.0 (T-106)
    var sheetMode = false
    var sheetIndex = 0
    var sheetDwell: Double = 0.6

    // 성능 (미리보기 뷰가 기록)
    var deformationPath = "—"
    var updateMilliseconds: Double = 0
    var frameMilliseconds: Double = 0
    var fps: Double = 0
    var vertexCount = 0
    var renderVertexCount = 0

    // 스파이크
    var spikeLog: [String] = []

    init(launch: LaunchOptions) {
        self.launch = launch
        tab = AppTab.platformTabs.first { $0.rawValue == launch.tab || $0.rawValueASCII == launch.tab } ?? .preview
        template = SyntheticTemplate.make()
        identity = Identity.fromTemplate(template)
        vertexCount = template.vertexCount
        if let c = launch.clip { selectedClip = c }
        switch launch.template {
        case "legacy": templateSource = .legacyBust
        case "synthetic": templateSource = .synthetic
        default: templateSource = .defaultTemplate
        }
        if launch.fixture == "perturbed" {
            var id = Identity.fromTemplate(template)
            id.positions = SyntheticTemplate.perturbed(template, .sample)
            id.scale = 1.05
            identity = id
        }
        if launch.sheet { sheetMode = true; turntable = false; previzCamera = true; sheetDwell = 1.2; selectedClip = nil }
        if launch.previz { previzCamera = true; turntable = false }
        scheduleReportIfRequested()
        if templateSource != .synthetic { Task { await switchTemplate(to: templateSource) } }
    }

    func log(_ s: String) { spikeLog.append(s); print("[초상] \(s)") }

    /// 템플릿 소스 전환.
    func switchTemplate(to source: TemplateSource) async {
        templateSource = source
        loadError = nil
        usdzEntity = nil
        loadReport = nil
        switch source {
        case .synthetic:
            template = SyntheticTemplate.make()
            identity = Identity.fromTemplate(template)
            clips = SyntheticClips.all()
            vertexCount = template.vertexCount
            templateStatus = "합성 템플릿"
        case .defaultTemplate:
            await loadDefaultTemplate()
        case .legacyBust, .legacyEthan:
            guard let name = source.resourceName, let url = Bundle.main.url(forResource: name, withExtension: "usdz") else { loadError = "번들에 USDZ 가 없습니다"; return }
            await loadUSDZ(url: url, manifest: nil, keepTemplate: true)
            clips = SyntheticClips.all()
        }
    }

    /// 기본 템플릿: Default.chosangtemplate → 캐시 → bust.mesh(기하) + Template.usdz(눈알·입안·교차 확인).
    func loadDefaultTemplate() async {
        do {
            let t0 = Date()
            let folder = try TemplateStore.prepareDefault()
            templateFolder = folder
            let t = try TemplateStore.loadTemplate(from: folder)
            template = t
            identity = Identity.fromTemplate(t)
            vertexCount = t.vertexCount
            clips = TemplateStore.loadClips(from: folder)
            library = TemplateStore.loadLibrary(from: folder)
            templateStatus = String(format: "%@@%@ · bust.mesh %d 정점 · 클립 %d · 라이브러리 %d · %.2f s", t.manifest.id, t.manifest.version, t.vertexCount, clips.count, library.count, Date().timeIntervalSince(t0))
            log("기본 템플릿: " + templateStatus)
            if clips.isEmpty { clips = SyntheticClips.all() }
            if launch.usdzOverlay {
                // T-004 보고는 Template.usdz(Bust 포함)로, 화면 오버레이는 EyesMouth.usdz(Bust 제외)로
                await loadUSDZ(url: folder.appendingPathComponent("Template.usdz"), manifest: t.manifest, keepTemplate: true)
                let eyes = folder.appendingPathComponent("EyesMouth.usdz")
                if FileManager.default.fileExists(atPath: eyes.path), let e = try? await Entity(contentsOf: eyes) {
                    usdzEntity = e
                    overlayHasBust = false
                } else { overlayHasBust = true }
            }
        } catch {
            loadError = "기본 템플릿 로드 실패: \(error.localizedDescription) — 합성 템플릿으로 대체"
            template = SyntheticTemplate.make()
            identity = Identity.fromTemplate(template)
            clips = SyntheticClips.all()
            templateStatus = "합성(기본 템플릿 없음)"
        }
    }

    /// USDZ 로드 (T-004 보고 + 엔티티). `keepTemplate` 이 false 면 USDZ 에서 만든 BustTemplate 으로 교체(레거시 흉상 미리보기).
    func loadUSDZ(url: URL, manifest: TemplateManifest?, keepTemplate: Bool) async {
        do {
            let (t, report, root) = try await TemplateLoader.load(url: url, manifest: manifest)
            loadReport = report
            usdzEntity = root
            log("T-004 \(url.lastPathComponent): \(report.summary)")
            if !keepTemplate || templateSource == .legacyBust || templateSource == .legacyEthan {
                if let t { template = t; identity = Identity.fromTemplate(t); vertexCount = t.vertexCount }
                else { loadError = "메시를 읽지 못했습니다: \(report.notes.joined(separator: ", "))" }
            }
        } catch {
            loadError = error.localizedDescription
        }
    }

    /// 선택 클립 데이터 (기본 템플릿 클립 → 없으면 절차적).
    func clip(named name: String) -> SampledClip { clips.first { $0.name == name } ?? SyntheticClips.make(name) }

    /// 합성 템플릿 + 선택 사항 섭동으로 Identity 재설정.
    func applyFixture(perturbed: Bool) {
        var id = Identity.fromTemplate(template)
        if perturbed, templateSource == .synthetic { id.positions = SyntheticTemplate.perturbed(template, .sample); id.scale = 1.05 }
        identity = id
    }

    /// DEBUG 자동 보고: 실행 인자 `report=1` 이면 10 초 뒤 Documents/chosang-report.txt 에 수치를 쓴다.
    func scheduleReportIfRequested() {
        guard launch.report else { return }
        Task { @MainActor in
            try? await Task.sleep(for: .seconds(10))
            var lines: [String] = []
            lines.append("초상 자동 보고 \(Date())")
            lines.append("템플릿: \(templateSource.rawValue) · \(templateStatus) · 정점 \(vertexCount) (렌더 \(renderVertexCount))")
            lines.append("변형 경로: \(deformationPath) · GPU 경로 컴파일됨: \(BustEntity.isGPUPathCompiled)")
            lines.append(String(format: "변형 %.3f ms · 프레임 %.2f ms · %.1f fps · 클립 %@", updateMilliseconds, frameMilliseconds, fps, selectedClip ?? "-"))
            if let r = loadReport { lines.append("--- T-004 USDZ\n" + r.summary); lines.append("읽힌 오프셋: " + r.readableOffsets.filter { $0.value }.keys.sorted().joined(separator: ", ")) }
            if let e = loadError { lines.append("오류: " + e) }
            lines.append("--- T-005 " + USDExport.capability().summary)
            lines.append(spikeLog.joined(separator: "\n"))
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            try? lines.joined(separator: "\n").write(to: docs.appendingPathComponent("chosang-report.txt"), atomically: true, encoding: .utf8)
            log("보고 작성: \(docs.path)/chosang-report.txt")
        }
    }
}

private extension AppTab {
    var rawValueASCII: String {
        switch self {
        case .preview: "preview"; case .capture: "capture"; case .validate: "validate"; case .spikes: "spikes"; case .receive: "receive"
        }
    }
}
