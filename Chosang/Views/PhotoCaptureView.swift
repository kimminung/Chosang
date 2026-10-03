//
//  PhotoCaptureView.swift
//  초상 (macOS)
//
//  T-205 희소 캡처 화면(데스크톱 레이아웃): Mac 내장 카메라 미리보기 + Vision 76점 오버레이 + 5컷 게이트 + 사진 파일 불러오기 → 번들 저장(sparse = true).
//  저장 이미지는 비반전, 미리보기만 거울처럼 보여 준다. iPhone 은 같은 세션을 `GuidedCaptureView` 로 쓴다.
//

#if os(macOS)
import SwiftUI
import simd
import UniformTypeIdentifiers
import ImageIO
import ChosangCore
import ChosangCapture
import ChosangIO

struct PhotoCaptureView: View {
    @Environment(AppModel.self) private var model
    @State private var session = PhotoCaptureSession()
    @State private var shots: [CaptureShot] = []
    @State private var message = ""
    @State private var importing = false
    @State private var importKind: ShotKind = .front
    @State private var mirror = true
    @State private var savedFolder: URL?
    @State private var exportURL: URL?

    var body: some View {
        HStack(spacing: 0) {
            preview.frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.black.opacity(0.9))
            Divider()
            ScrollView { panel.padding() }.frame(width: 360)
        }
        .onAppear(perform: autoStart)
        .onDisappear { session.stop() }
    }

    /// 실행 인자 `camera=1` 이면 자동 시작 (스크린샷 자동화).
    private func autoStart() {
        if model.launch.camera, PhotoCaptureSession.hasCamera, !session.isRunning { session.start() }
    }

    // MARK: 미리보기 + 오버레이

    private var preview: some View {
        GeometryReader { geo in
            ZStack {
                if let cg = session.preview {
                    let fitted = fit(CGSize(width: cg.width, height: cg.height), in: geo.size)
                    Group {
                    Image(decorative: cg, scale: 1).resizable().interpolation(.medium)
                        .frame(width: fitted.width, height: fitted.height).position(x: fitted.midX, y: fitted.midY)
                    Canvas { ctx, _ in
                        let sx = fitted.width / CGFloat(cg.width), sy = fitted.height / CGFloat(cg.height)
                        func map(_ p: SIMD2<Float>) -> CGPoint { CGPoint(x: fitted.minX + CGFloat(p.x) * sx, y: fitted.minY + CGFloat(p.y) * sy) }
                        if let b = session.previewBox {
                            let r = CGRect(x: fitted.minX + b.minX * sx, y: fitted.minY + b.minY * sy, width: b.width * sx, height: b.height * sy)
                            ctx.stroke(Path(roundedRect: r, cornerRadius: 6), with: .color(.green.opacity(0.8)), lineWidth: 1.5)
                        }
                        for p in session.previewLandmarks {
                            let q = map(p)
                            ctx.fill(Path(ellipseIn: CGRect(x: q.x - 1.5, y: q.y - 1.5, width: 3, height: 3)), with: .color(.yellow))
                        }
                        for (_, p) in session.previewKeyPoints {
                            let q = map(p)
                            ctx.stroke(Path(ellipseIn: CGRect(x: q.x - 4, y: q.y - 4, width: 8, height: 8)), with: .color(.cyan), lineWidth: 1.5)
                        }
                    }
                    }
                    .scaleEffect(x: mirror ? -1 : 1, y: 1)   // 거울 미리보기 — 영상·오버레이만 (저장 이미지는 비반전)
                } else {
                    ContentUnavailableView(PhotoCaptureSession.hasCamera ? "카메라 대기" : "카메라 없음", systemImage: "web.camera",
                                           description: Text(PhotoCaptureSession.hasCamera ? "'카메라 시작' 을 누르세요. TrueDepth 없이 Vision 76점으로 희소 캡처합니다." : "시뮬레이터에는 카메라가 없습니다. '사진 불러오기' 로 파일을 분석하세요."))
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .overlay(alignment: .topLeading) { statusBadge.padding(10) }
        }
    }

    private var statusBadge: some View {
        let s = session.status
        return VStack(alignment: .leading, spacing: 2) {
            Text(s.isTracked ? "얼굴 추적 중 (Vision \(s.landmarkCount)점)" : "얼굴 없음").bold()
            Text(String(format: "yaw %.1f° · pitch %.1f° · roll %.1f° · 밝기 %.2f · 얼굴 폭 %.0f %%", s.yaw, s.pitch, s.roll, s.brightness, s.faceWidthRatio * 100))
            Text(String(format: "Vision 원값 yaw %.1f° pitch %.1f° · %d×%d · %@", s.visionYaw, s.visionPitch, s.imageWidth, s.imageHeight, session.cameraName))
        }
        .font(.caption.monospacedDigit()).padding(8).background(.black.opacity(0.55)).foregroundStyle(.white).clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func fit(_ img: CGSize, in box: CGSize) -> CGRect {
        guard img.width > 0, img.height > 0, box.width > 0, box.height > 0 else { return .zero }
        let s = min(box.width / img.width, box.height / img.height)
        let w = img.width * s, h = img.height * s
        return CGRect(x: (box.width - w) / 2, y: (box.height - h) / 2, width: w, height: h)
    }

    // MARK: 패널

    private var panel: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("초상 캡처 — 사진 폴백 (TrueDepth 없음)").font(.title2.bold())
            Text("깊이·ARKit 메시 없이 사진 + Vision 76점만 기록합니다. 번들은 `sparse = true` 로 저장되며 M3 희소 피팅(T-306)의 입력이 됩니다.")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                Button(session.isRunning ? "카메라 정지" : "카메라 시작") { session.isRunning ? session.stop() : session.start() }
                    .buttonStyle(.borderedProminent)
                    .disabled(!PhotoCaptureSession.hasCamera)
                Toggle("거울", isOn: $mirror).toggleStyle(.switch).font(.caption)
            }
            if let e = session.errorText { Text(e).font(.caption).foregroundStyle(.red) }
            if let w = session.lightWarning {
                Label(w, systemImage: "sun.max.trianglebadge.exclamationmark").font(.caption).foregroundStyle(.orange)
            }
            GroupBox("가정값") {
                VStack(alignment: .leading, spacing: 4) {
                    Text(String(format: "수평 FOV %.0f° (%@) · 동공 거리 %.0f mm", session.assumedHorizontalFOV, session.fovIsMeasured ? "센서" : "가정", SparseFaceGeometry.assumedInterpupillary * 1000))
                    Text("깊이 = f·IPD·cos(yaw)/눈간격(px). intrinsics 는 `intrinsicsEstimated = true` 로 표시됩니다.")
                }
                .font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
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
                                if let shot = session.captureShot(kind: kind) { store(shot) } else { message = "프레임이 없습니다" }
                            }
                            .disabled(!session.isRunning || !session.status.isTracked)
                            Button("파일…") { importKind = kind; importing = true }.font(.caption)
                        }
                    }
                    HStack {
                        Button("번들 저장 (Documents/Captures)") { save() }.disabled(shots.isEmpty)
                        if let url = exportURL {
                            ShareLink(item: url) { Text("내보내기…") }
                        } else {
                            Button("내보내기 (.chosangcapture)") { export() }.disabled(savedFolder == nil)
                        }
                        Button("비우기") { shots.removeAll(); savedFolder = nil; exportURL = nil; message = "" }.disabled(shots.isEmpty)
                    }
                    Text(message).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                }
            }
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.image]) { result in
            guard case .success(let url) = result else { return }
            Task { await importPhoto(url, kind: importKind) }
        }
    }

    private func store(_ shot: CaptureShot) {
        shots.removeAll { $0.kind == shot.kind }
        shots.append(shot)
        let m = shot.meta
        let pose = m.poseEstimate ?? [0, 0, 0]
        message = String(format: "%@ — %d×%d · 랜드마크 %d · 평균 %d 프레임 · yaw %.1f° pitch %.1f° · 추정 깊이 %.2f m",
                         m.kind.title, m.imageWidth, m.imageHeight, m.landmarkArray.count, m.averagedFrames, pose[0], pose[1], -m.faceTransform.m.columns.3.z)
    }

    private func importPhoto(_ url: URL, kind: ShotKind) async {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
              let cg = CGImageSourceCreateImageAtIndex(src, 0, [kCGImageSourceShouldCache: false] as CFDictionary) else { message = "이미지를 열 수 없습니다: \(url.lastPathComponent)"; return }
        // EXIF 방향 보정은 ImageIO 썸네일 경로가 해 준다 — 원본 크기로 (긴 변 4032 이하면 그대로)
        let upright = CGImageSourceCreateThumbnailAtIndex(src, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true,
                                                                   kCGImageSourceThumbnailMaxPixelSize: max(cg.width, cg.height, 1)] as CFDictionary) ?? cg
        if let shot = await session.makeShot(kind: kind, from: upright) { store(shot) } else { message = "얼굴을 찾지 못했습니다: \(url.lastPathComponent)" }
    }

    private func save() {
        let meta = CaptureBundleMeta(device: PhotoCaptureSession.deviceDescription, sparse: true, arkitTriangleHash: nil, arkitVertexCount: 0, shots: shots.map(\.meta))
        let bundle = CaptureBundle(meta: meta, shots: shots)
        let folder = CaptureBundleStore.defaultFolder(for: meta.id)
        do { try CaptureBundleStore.write(bundle, to: folder); savedFolder = folder; exportURL = nil; message = "저장: \(folder.path)" }
        catch { message = "저장 실패: \(error.localizedDescription)" }
    }

    /// 저장된 폴더 → `.chosangcapture`(zip) 임시 파일 → 공유 (T-204).
    private func export() {
        guard let folder = savedFolder else { return }
        do {
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(folder.lastPathComponent).\(CaptureBundleStore.fileExtension)")
            try? FileManager.default.removeItem(at: url)
            try ZipArchive.zipFolder(folder).write(to: url)
            exportURL = url
            message = "내보내기 준비됨: \(url.lastPathComponent) — '내보내기…' 로 공유하세요"
        } catch { message = "내보내기 실패: \(error.localizedDescription)" }
    }
}
#endif
