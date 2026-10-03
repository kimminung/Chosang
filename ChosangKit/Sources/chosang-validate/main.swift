//
//  chosang-validate — 블렌더 산출물 계약 검사 CLI (macOS)
//
//  사용법:
//    swift run chosang-validate <Template 폴더> [--with-usdz]   template.json + bust.mesh + library + clips + previz 검사 (+ Template.usdz 를 RealityKit 으로 읽어 교차 확인)
//    swift run chosang-validate --synthetic <출력 폴더>     합성 템플릿으로 Template/ 폴더를 만들고 검사(자체 테스트)
//    swift run chosang-validate --list-legacy-failures      소반 임시 USDZ 로는 어떤 검사가 실패하는지 목록(M1 T-105 우선순위)
//    swift run chosang-validate --make-fixture <파일.chosangcapture> [perturbed]   합성 캡처 번들 픽스처 생성 (Fixtures/)
//  종료 코드: 0 = 오류 없음, 1 = 오류 있음, 2 = 입력 오류.
//  USDZ 자체(RealityKit 로드)는 앱의 "검증" 탭에서 같은 규칙으로 검사한다(ChosangRig.TemplateLoader).
//

import Foundation
import ChosangCore
import ChosangIO
import ChosangValidate
import ChosangTexture
import ChosangFit
#if os(macOS)
import ChosangRig
import RealityKit
#endif

let args = CommandLine.arguments.dropFirst().filter { $0 != "--with-usdz" } + CommandLine.arguments.dropFirst().filter { $0 == "--with-usdz" }

#if os(macOS)
final class USDZBox: @unchecked Sendable { var done = false; var positions: [SIMD3<Float>]?; var shapes: [String]?; var summary = "" }
#endif

func run() -> Int32 {
    guard let first = args.first else {
        print("사용법: chosang-validate <Template 폴더> | --synthetic <폴더> | --list-legacy-failures")
        return 2
    }
    if first == "--list-legacy-failures" {
        // 소반 USDZ(DemoAvatar_Ethan / SplatPlaceholder_Bust)는 계약 메타가 없으므로 template.json 없이 돌리면 어떤 검사가 실패하는지 보여준다.
        var m = TemplateManifest(id: "soban-legacy", version: "0", vertexCount: 0, triangleCount: 0, patchTriangleHash: "0", landmarks: [:], groups: [:], shapeKeys: [])
        m.libraryObjects = []
        let issues = TemplateValidator.validate(ValidationInput(manifest: m, template: nil, clips: [], previzNames: [], library: [], hasUSDZ: true, hasBustMesh: false))
        print(TemplateValidator.report(issues, title: "소반 임시 USDZ (계약 메타 없음)"))
        print("\n→ 블렌더 작업 우선순위: ① ARFaceGeometry.obj 패치 + 그룹 ② 52 셰이프키 ③ 스켈레톤·랜드마크(template.json) ④ 클립 ⑤ 라이브러리 ⑥ previz")
        return 1
    }
    if first == "--make-fixture" {
        guard args.count >= 2 else { print("--make-fixture <출력.chosangcapture> [perturbed]"); return 2 }
        let url = URL(fileURLWithPath: args[args.startIndex + 1])
        let perturbed = args.count >= 3 && args[args.startIndex + 2] == "perturbed"
        let t = SyntheticTemplate.make()
        var opt = SyntheticCaptureOptions()
        opt.imageWidth = 1280; opt.imageHeight = 960; opt.depthWidth = 640; opt.depthHeight = 480
        let bundle = SyntheticCapture.makeBundle(template: t, userPositions: perturbed ? SyntheticTemplate.perturbed(t, .sample) : nil, options: opt)
        do { try CaptureBundleStore.archive(bundle, to: url) } catch { print("쓰기 실패: \(error)"); return 2 }
        let size = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int) ?? 0
        print("합성 번들 \(perturbed ? "(섭동 사용자)" : "(템플릿 그대로)") → \(url.path) (\(size / 1024) KB, 5컷 1280×960 + 깊이 640×480)")
        return 0
    }
    if first == "--texture" {
        // 실제 캡처 번들로 피팅 + 알베도 투영을 돌려 PNG 로 뽑는다 (텍스처 디버깅용).
        // 캡처 데이터는 커밋하지 않는다 — 출력도 저장소 밖에 쓴다.
        guard args.count >= 3 else { print("--texture <번들.chosangcapture> <출력.png> [크기]"); return 2 }
        let src = URL(fileURLWithPath: args[args.startIndex + 1])
        let out = URL(fileURLWithPath: args[args.startIndex + 2])
        let size = args.count >= 4 ? Int(args[args.startIndex + 3]) ?? 512 : 512
        do {
            let bundle = try CaptureBundleStore.readArchive(src)
            // CLI 는 앱 번들이 없으므로 저장소의 `Default.chosangtemplate` 를 직접 푼다 (4번째 인자로 다른 경로 지정 가능).
            let zip = args.count >= 5 ? URL(fileURLWithPath: args[args.startIndex + 4])
                                      : URL(fileURLWithPath: #filePath)
                                            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
                                            .appendingPathComponent("Chosang/Resources/Templates/Default.chosangtemplate")
            let dir = FileManager.default.temporaryDirectory.appendingPathComponent("tpl-\(UUID().uuidString)")
            defer { try? FileManager.default.removeItem(at: dir) }
            try ZipArchive.unzip(Data(contentsOf: zip), to: dir)
            let template = try TemplateStore.loadTemplate(from: dir)
            print("번들: \(bundle.meta.device) · 컷 \(bundle.shots.count) · sparse \(bundle.meta.sparse)")
            let identity = try FaceFitter.fit(bundle: bundle, template: template)
            let q = identity.quality
            print(String(format: "피팅: 패치 RMS %.2f mm · 스케일 %.3f · %.1f s", (q?.patchRMS ?? 0) * 1000, identity.scale, q?.elapsedSeconds ?? 0))
            let aligns = FaceFitter.alignments(bundle: bundle, template: template)
            let r = try CaptureTexturing.project(bundle: bundle, template: template, positions: identity.positions,
                                                 alignments: aligns, options: CaptureTexturing.deviceOptions(size: size))
            print(String(format: "텍스처: 관측 %.1f%% · 대칭 %.1f%% · 채움 %.1f%% · %.1f s · 컷 %@",
                         r.quality.observedRatio * 100, r.quality.mirroredRatio * 100, r.quality.filledRatio * 100,
                         r.quality.buildSeconds, r.usedShots.map(\.rawValue).joined(separator: "+")))
            // 랜드마크 UV → 래스터라이저 텍셀 좌표 (어느 쪽이 얼굴인지 확정용)
            let render = template.makeRenderMesh()
            for name in [LandmarkName.noseTip, .chin, .eyeLeftOuter, .mouthLeft] {
                guard let src = template.manifest.landmark(name), let i = render.sourceIndex.firstIndex(of: Int32(src)) else { continue }
                let uv = render.uvs[i]
                print(String(format: "  %@: uv(%.3f, %.3f) → 래스터 텍셀 y=%.0f/%d (%@)",
                             name.rawValue, uv.x, uv.y, (1 - uv.y) * Float(size), size,
                             (1 - uv.y) < 0.5 ? "이미지 위쪽" : "이미지 아래쪽"))
            }
            // 부위별 UV 세로 범위 (반전하면 어디로 가는지 판단용)
            func vRange(_ ids: [Int]) -> (Float, Float)? {
                var lo = Float.greatestFiniteMagnitude, hi = -Float.greatestFiniteMagnitude
                let set = Set(ids.map(Int32.init))
                for i in 0..<render.vertexCount where set.contains(render.sourceIndex[i]) {
                    lo = min(lo, render.uvs[i].y); hi = max(hi, render.uvs[i].y)
                }
                return lo <= hi ? (lo, hi) : nil
            }
            print("부위별 UV v 범위 (0 = 래스터 이미지 아래, 1 = 위):")
            if let f = vRange(Array(0..<template.patchCount)) { print(String(format: "  얼굴 패치(1220):  v %.3f…%.3f", f.0, f.1)) }
            for g in [VertexGroupName.scalp, .neck, .shoulders] {
                if let r2 = vRange(template.manifest.group(g)) { print(String(format: "  %-14@ v %.3f…%.3f", g.rawValue as NSString, r2.0, r2.1)) }
            }
            try ImageCodec.png(r.albedo).write(to: out)
            try? ImageCodec.png(r.mask).write(to: out.deletingPathExtension().appendingPathExtension("mask.png"))
            print("→ \(out.path)")
            return 0
        } catch {
            print("실패: \((error as? LocalizedError)?.errorDescription ?? error.localizedDescription)")
            return 2
        }
    }
    var root: URL
    if first == "--synthetic" {
        guard args.count >= 2 else { print("--synthetic <출력 폴더>"); return 2 }
        root = URL(fileURLWithPath: args[args.startIndex + 1])
        do { try TemplateFolder.writeSynthetic(to: root) } catch { print("합성 템플릿 쓰기 실패: \(error)"); return 2 }
        print("합성 템플릿을 \(root.path) 에 썼습니다.")
    } else {
        root = URL(fileURLWithPath: first)
    }
    do {
        let folder = try TemplateFolder(root: root)
        var usdzPositions: [SIMD3<Float>]? = nil
        var usdzShapes: [String]? = nil
        var usdzSummary = ""
        if args.contains("--with-usdz"), folder.hasUSDZ {
            #if os(macOS)
            let url = root.appendingPathComponent(TemplateFolder.usdzName)
            let box = USDZBox()
            Task { @MainActor in
                do {
                    let (t, r, _) = try await TemplateLoader.load(url: url, manifest: folder.manifest)
                    box.positions = t?.positions; box.shapes = r.blendShapeNames; box.summary = r.summary
                } catch { box.summary = "USDZ 로드 실패: \(error.localizedDescription)" }
                box.done = true
            }
            while !box.done { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
            usdzPositions = box.positions; usdzShapes = box.shapes; usdzSummary = box.summary
            #else
            print("--with-usdz 는 macOS 에서만 지원합니다")
            #endif
        }
        let issues = TemplateValidator.validate(folder.validationInput(usdzPositions: usdzPositions, usdzShapeNames: usdzShapes))
        if !usdzSummary.isEmpty { print("USDZ:\n" + usdzSummary + "\n") }
        print(TemplateValidator.report(issues, title: root.lastPathComponent))
        return TemplateValidator.hasErrors(issues) ? 1 : 0
    } catch {
        print("❌ 읽기 실패: \(error.localizedDescription)\n   template.json 이 있는 Template 폴더를 지정하세요.")
        return 2
    }
}

exit(run())
