//
//  AppModel.swift
//  초상
//
//  앱 상태(@Observable). 템플릿 소스(기본 블렌더 템플릿 / 합성 / 소반 레거시 USDZ), 셰이프 가중치, 클립, 성능 수치, 스파이크 보고.
//

import Foundation
import Observation
import CoreGraphics
import RealityKit
import ChosangCore
import ChosangRig
import ChosangIO
import ChosangFit
import ChosangTexture
#if os(iOS) || os(visionOS)
import UIKit
#endif

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
    case preview = "미리보기", capture = "캡처", validate = "검증", spikes = "스파이크", receive = "주고받기"
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
        [.preview, .capture, .receive, .spikes]
        #else
        [.preview, .capture, .receive, .validate, .spikes]
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

    // 피팅 (받은 캡처 번들 → 내 흉상)
    var isFitting = false
    /// 텍스처 빌드 진행 (단계 이름 · 0…1)
    var buildStage: String?
    var buildProgress: Double = 0
    /// 텍스처 설정 (M4 T-407): 2k/4k, 탈조명 강도. 바꾸면 "텍스처 다시 만들기" 로 재빌드
    var albedoSize = 2048
    var delightStrength: Float = 0.5
    /// 마지막 피팅의 입력 (텍스처만 다시 만들 때 재사용)
    var lastCaptureURL: URL?
    /// 마지막 피팅 품질 요약 (미리보기 패널·정보 시트에 표시)
    var fitSummary: String?
    /// 캡처에서 만든 알베도 — 있으면 흉상에 입힌다 (M4 1차, CPU 투영)
    var albedoTexture: TextureResource?
    var textureSummary: String?
    /// 저장용 원본 (RealityKit 텍스처와 별개로 들고 있는다)
    var lastAlbedo: RGBAImage?
    var lastMask: RGBAImage?
    var lastTextureQuality: TextureQuality?
    /// 마지막으로 저장한 `.chosang`
    var savedPersonaURL: URL?
    /// 미소 컷 검증 (T-308): 캡처 가중치 그대로 렌더한 흉상 ↔ 사진
    struct SmileCheck {
        var photo: CGImage
        var render: CGImage
        var caption: String
    }
    var smileCheck: SmileCheck?
    /// 진단용 알베도 이미지 (UV 레이아웃을 눈으로 확인)
    var albedoPreview: CGImage?
    /// 텍스처를 입힐지 (끄면 기본 살색으로 — 형상만 비교할 때)
    var useAlbedo = true
    /// 알베도 상하 반전 (UV 세로축 규약). **기본 꺼짐 — 실기기 확정**.
    /// 템플릿 랜드마크 UV 는 코끝 v=0.260 · 턱 v=0.050 이고 래스터라이저는 `y=(1−v)·S` 로 찍으므로 얼굴이 이미지 **아래쪽**에 온다.
    /// 이 상태 그대로 올려야 흉상 얼굴에 얼굴이 붙는다(뒤집으면 얼굴 색이 어깨로 내려간다 — Vision Pro 에서 확인).
    /// 토글은 템플릿 UV 규약이 바뀔 때를 위해 남겨 둔다.
    var flipAlbedoV = false { didSet { if oldValue != flipAlbedoV { applyAlbedo(lastAlbedo, quality: lastTextureQuality) } } }

    /// 흉상 머티리얼 (알베도가 있으면 텍스처, 없으면 BustEntity 기본값)
    var bustMaterial: Material? {
        guard useAlbedo, let tex = albedoTexture else { return nil }
        var m = PhysicallyBasedMaterial()
        // tint 기본값(흰색)을 그대로 두어 텍스처 색이 그대로 나오게 한다 — `.white` 는 플랫폼마다 UIColor/NSColor 라 쓰지 않는다.
        m.baseColor = .init(texture: .init(tex))
        m.roughness = .init(floatLiteral: 0.75)
        m.metallic = .init(floatLiteral: 0)
        m.specular = .init(floatLiteral: 0.2)
        return m
    }

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

    /// 전송 화면에 띄울 이 기기 이름 (Bonjour 서비스 이름으로도 쓴다).
    static var localDeviceName: String {
        #if os(iOS) || os(visionOS)
        UIDevice.current.name
        #else
        Host.current().localizedName ?? "Mac"
        #endif
    }

    /// 받은 `.chosang` 을 현재 템플릿 위에 올린다 (M6 T-603 수신 → 미리보기).
    /// 템플릿 id·버전이 다르면 경고만 하고 형상은 적용하지 않는다 — 정점 수·순서가 달라 섞으면 깨진다.
    @discardableResult
    func loadPersona(from url: URL) async -> String? {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("persona-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: tmp) }
        do {
            try ChosangPackageStore.unarchive(url, to: tmp)
            let pkg = try ChosangPackageStore.read(from: tmp, expectedTemplate: template.manifest)
            guard pkg.identity.positions.count == template.vertexCount else {
                loadError = "페르소나 정점 수(\(pkg.identity.positions.count))가 현재 템플릿(\(template.vertexCount))과 다릅니다"
                return loadError
            }
            identity = pkg.identity
            loadError = nil
            let msg = "페르소나 적용: \(url.lastPathComponent) · 템플릿 \(pkg.manifest.templateID)@\(pkg.manifest.templateVersion) · 정점 \(pkg.identity.positions.count)"
            log(msg)
            return msg
        } catch {
            loadError = "페르소나 로드 실패: \(error.localizedDescription)"
            return loadError
        }
    }

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

    /// 이 기기에 저장된 가장 최근 캡처 (iPhone·Mac 에서 "바로 흉상 만들기" 에 쓴다).
    var latestLocalCapture: CaptureBundleMeta? { CaptureBundleStore.list().first }

    /// 로컬 캡처 폴더로 바로 피팅 (전송 없이). 폴더를 임시 zip 으로 묶어 같은 경로를 탄다.
    @discardableResult
    func buildFromLatestCapture() async -> String? {
        guard let meta = latestLocalCapture else {
            loadError = "이 기기에 저장된 캡처가 없습니다 — 캡처 탭에서 5컷을 찍고 번들을 저장하세요"
            return loadError
        }
        let folder = CaptureBundleStore.defaultFolder(for: meta.id)
        do {
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(meta.id.uuidString).\(CaptureBundleStore.fileExtension)")
            try? FileManager.default.removeItem(at: url)
            try ZipArchive.zipFolder(folder).write(to: url)
            defer { try? FileManager.default.removeItem(at: url) }
            return await buildPersona(fromCapture: url)
        } catch {
            loadError = "최근 캡처를 읽지 못했습니다: \(error.localizedDescription)"
            return loadError
        }
    }

    /// 밖에서 넘어온 파일 열기 (T-604: AirDrop · 파일 앱 · 공유 시트 · `onOpenURL`).
    /// 확장자로 갈라 페르소나면 바로 적용, 캡처 번들이면 피팅까지 돌린다. 어느 쪽이든 미리보기 탭으로 간다.
    @discardableResult
    func open(_ url: URL) async -> String? {
        let ext = url.pathExtension.lowercased()
        let result: String?
        switch ext {
        case ChosangPackageStore.fileExtension:      // .chosang
            result = await loadPersona(from: url)
        case CaptureBundleStore.fileExtension:       // .chosangcapture
            result = await buildPersona(fromCapture: url)
        default:
            loadError = "열 수 없는 파일입니다: \(url.lastPathComponent) (.chosang 또는 .chosangcapture)"
            return loadError
        }
        if loadError == nil { tab = .preview }
        return result
    }

    /// 받은(또는 저장된) 캡처 번들로 **내 흉상**을 만든다 — `FaceFitter` → `Identity` → 미리보기.
    /// ARKit 번들은 밀집 피팅(패치 치환 · 두상 전파 · 실루엣 · jawOpen 보정), 희소 번들(사진 폴백)은 `SparseFitter`(M3 T-306, 품질 "기본").
    /// 미소 컷이 있으면 검증 렌더(T-308)도 만든다.
    @discardableResult
    func buildPersona(fromCapture url: URL) async -> String? {
        guard !isFitting else { return nil }
        isFitting = true
        defer { isFitting = false }
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        let template = self.template
        struct BuildResult: Sendable {
            var identity: Identity; var meta: CaptureBundleMeta
            var albedo: RGBAImage?; var mask: RGBAImage?; var textureQuality: TextureQuality?; var textureSummary: String?
            var smilePhoto: RGBAImage?; var smileRender: RGBAImage?; var smileCaption: String?
        }
        var texOptions = TextureBuildOptions.preset(size: albedoSize)
        texOptions.delight = delightStrength
        let progress: TextureProgress = { [weak self] stage, f in
            Task { @MainActor in self?.buildStage = stage.title; self?.buildProgress = (Double(stage.rawValue) + f) / Double(TextureStage.allCases.count) }
        }
        buildStage = "피팅"; buildProgress = 0
        defer { buildStage = nil }
        do {
            // 읽기·피팅·텍스처는 메인 밖에서 (1220 패치 + RBF 300 중심 + 실루엣 CG + 2k 텍스처라 몇 초 걸린다)
            let r: BuildResult = try await Task.detached(priority: .userInitiated) {
                let bundle = try CaptureBundleStore.readArchive(url)      // 텍스처에 쓸 사진까지 읽는다
                let identity = try FaceFitter.fit(bundle: bundle, template: template)
                var out = BuildResult(identity: identity, meta: bundle.meta)
                // 피팅된 정점 + 컷별 정렬로 알베도 (M4 TextureBuilder: 깊이 정합·가림·접합·탈조명·채움·필터).
                // 희소(사진 폴백) 번들도 SparseFitter 가 컷별 정렬을 만들어주므로(FaceFitter.alignments) 텍스처가 생긴다 — 다만 깊이가 없어
                // 배경 거부 검사가 빠지고 조명 추정도 꺼진 채로 돌아간다(TextureBuilder 쪽 가드에 맡긴다).
                let aligns = FaceFitter.alignments(bundle: bundle, template: template)
                if let t = try? TextureBuilder.build(bundle: bundle, template: template, identity: identity, alignments: aligns, options: texOptions, progress: progress) {
                    out.albedo = t.albedo; out.mask = t.mask; out.textureQuality = t.quality; out.textureSummary = t.summary
                }
                // 희소 컷은 ARKit 블렌드셰이프가 전부 0 이라(표정을 저장하지 않음) 미소 검증 카드가 "중립 렌더 vs 웃는 사진" 처럼
                // 늘 가중치 합 0 으로 뜬다 — 의미가 없으니 숨긴다.
                if let v = SmileVerification.make(bundle: bundle, template: template, identity: identity, alignments: aligns, albedo: out.albedo, width: 320),
                   v.weightSum > 0.01 {
                    out.smilePhoto = v.photo; out.smileRender = v.render
                    let top = v.topShapes.map { "\($0.0.rawValue) \(String(format: "%.2f", $0.1))" }.joined(separator: " · ")
                    out.smileCaption = String(format: "%@ 컷 · 가중치 합 %.2f · %@", v.kind.title, v.weightSum, top)
                        + (identity.quality?.smileResidualRMS.map { String(format: " · 잔차 %.1f mm", $0 * 1000) } ?? "")
                }
                return out
            }.value
            identity = r.identity
            loadError = nil
            let q = r.identity.quality
            let summary = "\(r.meta.device) · " + (q?.summaryLine ?? "") + String(format: " · 스케일 %.3f", r.identity.scale)
            fitSummary = summary
            log("피팅: " + summary)
            if let n = q?.notes { log("피팅 메모: " + n) }
            lastAlbedo = r.albedo; lastMask = r.mask; lastTextureQuality = r.textureQuality; savedPersonaURL = nil
            lastCaptureURL = url
            applyAlbedo(r.albedo, quality: r.textureQuality)
            if let s = r.textureSummary { textureSummary = s; log("텍스처: " + s) }
            if let p = r.smilePhoto, let rd = r.smileRender, let pc = ImageCodec.cgImage(p), let rc = ImageCodec.cgImage(rd) {
                smileCheck = SmileCheck(photo: pc, render: rc, caption: r.smileCaption ?? "")
            } else { smileCheck = nil }
            return summary + (textureSummary.map { "\n" + $0 } ?? "")
        } catch {
            let msg = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            loadError = "피팅 실패: \(msg)"
            fitSummary = nil
            return loadError
        }
    }

    /// 지금 흉상(형상 + 알베도)을 `.chosang` 으로 저장한다 (T-601). 보내기·다시 열기에 쓸 수 있는 완결된 파일.
    /// 반환: 만들어진 파일 URL.
    func savePersona(name: String = "내 흉상") async -> URL? {
        guard let identity else { loadError = "저장할 형상이 없습니다 — 먼저 캡처로 흉상을 만드세요"; return nil }
        let t = template
        let albedo = lastAlbedo
        let mask = lastMask
        let device = Self.localDeviceName
        let fitQ = identity.quality
        let texQ = lastTextureQuality
        let delight = delightStrength
        do {
            let url: URL = try await Task.detached(priority: .userInitiated) {
                var manifest = ChosangManifest(name: name, createdOn: device,
                                               templateID: t.manifest.id, templateVersion: t.manifest.version, vertexCount: t.vertexCount)
                manifest.quality = fitQ
                manifest.textureQuality = texQ
                manifest.albedoSize = albedo?.width ?? 0
                manifest.delightStrength = delight
                let pkg = ChosangPackage(manifest: manifest, identity: identity, albedo: albedo, mask: mask, thumbnail: nil)
                let folder = FileManager.default.temporaryDirectory.appendingPathComponent("persona-\(manifest.id.uuidString)")
                defer { try? FileManager.default.removeItem(at: folder) }
                try ChosangPackageStore.write(pkg, to: folder)
                let out = ChosangPackageStore.defaultFolder(for: manifest.id)
                    .deletingLastPathComponent()
                    .appendingPathComponent("\(name)-\(manifest.id.uuidString.prefix(6)).\(ChosangPackageStore.fileExtension)")
                try FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)
                try? FileManager.default.removeItem(at: out)
                try ChosangPackageStore.archive(folder: folder, to: out)
                return out
            }.value
            let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize).map { Double($0) / 1_048_576 } ?? 0
            log(String(format: "페르소나 저장: %@ · %.1f MB", url.lastPathComponent, size))
            savedPersonaURL = url
            return url
        } catch {
            loadError = "페르소나 저장 실패: \(error.localizedDescription)"
            return nil
        }
    }

    /// 투영한 알베도를 RealityKit 텍스처로 올린다. 실패하면 조용히 기본 머티리얼을 쓴다.
    func applyAlbedo(_ image: RGBAImage?, quality: TextureQuality?) {
        guard let raw = image else { albedoTexture = nil; textureSummary = nil; albedoPreview = nil; return }
        let image = flipAlbedoV ? CaptureTexturing.flippedVertically(raw) : raw
        guard let cg = ImageCodec.cgImage(image) else { albedoTexture = nil; textureSummary = nil; albedoPreview = nil; return }
        albedoPreview = cg
        do {
            albedoTexture = try TextureResource(image: cg, options: .init(semantic: .color, mipmapsMode: .allocateAndGenerateAll))
            if let q = quality {
                // 얼굴만 찍으므로 관측은 UV 전체의 일부다. 20 % 아래면 정합·깊이 쪽을 의심해야 한다.
                let warn = q.observedRatio < 0.2 ? " ⚠︎ 관측 낮음" : ""
                textureSummary = String(format: "텍스처 %d² · 관측 %.0f%% · 대칭 %.0f%% · 채움 %.0f%% · 접합 %.1f/255%@ · %.1f s",
                                        image.width, q.observedRatio * 100, q.mirroredRatio * 100, q.filledRatio * 100, q.seamDelta, warn, q.buildSeconds)
            } else {
                textureSummary = "텍스처 \(image.width)²"
            }
            log(textureSummary ?? "")
        } catch {
            albedoTexture = nil
            textureSummary = "텍스처 생성 실패: \(error.localizedDescription)"
        }
    }

    /// 선택 클립 데이터 (기본 템플릿 클립 → 없으면 절차적).
    func clip(named name: String) -> SampledClip { clips.first { $0.name == name } ?? SyntheticClips.make(name) }

    /// 텍스처만 다시 만든다 (2k/4k · 탈조명 강도 변경 후). 피팅 결과는 그대로.
    @discardableResult
    func rebuildTexture() async -> String? {
        guard !isFitting, let identity, let url = lastCaptureURL else { return nil }
        isFitting = true
        defer { isFitting = false; buildStage = nil }
        let template = self.template
        var o = TextureBuildOptions.preset(size: albedoSize)
        o.delight = delightStrength
        let progress: TextureProgress = { [weak self] stage, f in
            Task { @MainActor in self?.buildStage = stage.title; self?.buildProgress = (Double(stage.rawValue) + f) / Double(TextureStage.allCases.count) }
        }
        do {
            let r: TextureBuildResult = try await Task.detached(priority: .userInitiated) {
                let bundle = try CaptureBundleStore.readArchive(url)
                let aligns = FaceFitter.alignments(bundle: bundle, template: template)
                return try TextureBuilder.build(bundle: bundle, template: template, identity: identity, alignments: aligns, options: o, progress: progress)
            }.value
            lastAlbedo = r.albedo; lastMask = r.mask; lastTextureQuality = r.quality; savedPersonaURL = nil
            applyAlbedo(r.albedo, quality: r.quality)
            textureSummary = r.summary
            log("텍스처 재빌드: " + r.summary)
            return r.summary
        } catch {
            loadError = "텍스처 재빌드 실패: \((error as? LocalizedError)?.errorDescription ?? error.localizedDescription)"
            return loadError
        }
    }

    /// 피팅 결과를 버리고 템플릿 원본으로 (미리보기 패널 "템플릿 원본으로").
    func resetToTemplate() {
        identity = Identity.fromTemplate(template)
        fitSummary = nil
        albedoTexture = nil; textureSummary = nil; albedoPreview = nil
        lastAlbedo = nil; lastMask = nil; lastTextureQuality = nil; savedPersonaURL = nil
        smileCheck = nil
    }

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
