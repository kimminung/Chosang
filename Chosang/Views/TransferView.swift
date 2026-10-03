//
//  TransferView.swift
//  초상 (visionOS · iOS · macOS)
//
//  M6 T-603 주고받기: Bonjour `_chosang._tcp` + TLS PSK 6자리 코드.
//  받기(주로 Vision Pro) — 코드를 띄우고 기다린다 → 진행률 → 저장 → 받은 목록에서 페르소나는 미리보기로 연다.
//  보내기(iPhone·Mac) — 근처 기기를 찾아 코드를 넣고 캡처 번들·페르소나를 보낸다.
//

import SwiftUI
import UniformTypeIdentifiers
import ChosangCore
import ChosangIO

struct TransferView: View {
    @Environment(AppModel.self) private var model
    @State private var mode: Mode = defaultMode

    enum Mode: String, CaseIterable, Identifiable {
        case receive = "받기", send = "보내기"
        var id: String { rawValue }
    }
    static var defaultMode: Mode {
        #if os(visionOS)
        .receive
        #else
        .send
        #endif
    }

    var body: some View {
        VStack(spacing: 0) {
            Picker("", selection: $mode) {
                ForEach(Mode.allCases) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .padding()
            Divider()
            switch mode {
            case .receive: ReceivePane()
            case .send: SendPane()
            }
        }
        .onAppear { if model.launch.browse { mode = .send } else if model.launch.receive { mode = .receive } }
    }
}

// MARK: - 받기

struct ReceivePane: View {
    @Environment(AppModel.self) private var model
    @State private var receiver = ChosangReceiver(deviceName: AppModel.localDeviceName)
    @State private var note = ""
    @State private var importing = false

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                switch receiver.phase {
                case .idle:
                    idleCard
                case .waiting:
                    codeCard
                case .connected(let who):
                    status("연결됨 — \(who)", systemImage: "link")
                case .receiving(let h, let got):
                    receivingCard(h, got)
                case .done(let url, let h):
                    doneCard(url, h)
                case .failed(let msg):
                    status(msg, systemImage: "exclamationmark.triangle", tint: .red)
                    Button("다시 대기") { receiver.start() }.buttonStyle(.borderedProminent)
                }
                if !note.isEmpty { Text(note).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center) }
                receivedList
            }
            .frame(maxWidth: 520)
            .frame(maxWidth: .infinity)
            .padding()
        }
        .onAppear { if model.launch.receive, case .idle = receiver.phase { receiver.start() } }
        .onDisappear { receiver.stop() }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.data]) { result in
            guard case .success(let url) = result else { return }
            note = "여는 중…"
            Task { note = await model.open(url) ?? "" }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { importing = true } label: { Label("파일 열기", systemImage: "folder") }
            }
        }
    }

    private var idleCard: some View {
        VStack(spacing: 14) {
            Image(systemName: "antenna.radiowaves.left.and.right").font(.system(size: 44)).foregroundStyle(.secondary)
            Text("다른 기기에서 보내기").font(.title2.bold())
            Text("이 기기를 수신 대기 상태로 두면 6자리 코드가 나옵니다. iPhone·Mac 의 \"보내기\" 에서 이 기기를 고르고 그 코드를 입력하세요. 같은 Wi‑Fi 또는 근거리(P2P)면 됩니다.")
                .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("수신 대기 시작") { receiver.start() }.buttonStyle(.borderedProminent).controlSize(.large)
            Divider().frame(maxWidth: 280)
            // 에어드랍·파일 앱으로 이미 받아 둔 파일을 직접 연다 (전송 없이)
            Button { importing = true } label: { Label("파일에서 불러오기", systemImage: "folder") }
                .buttonStyle(.bordered)
            Text("에어드랍이나 파일 앱으로 받은 `.chosangcapture`·`.chosang` 을 바로 열 수 있습니다.")
                .font(.caption2).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }
        .padding(20)
    }

    private var codeCard: some View {
        VStack(spacing: 14) {
            Text("이 기기 이름").font(.caption).foregroundStyle(.secondary)
            Text(receiver.deviceName).font(.headline)
            Text("코드").font(.caption).foregroundStyle(.secondary)
            Text(spaced(receiver.code))
                .font(.system(size: 44, weight: .bold, design: .monospaced))
                .textSelection(.enabled)
                .accessibilityLabel("코드 " + receiver.code.map(String.init).joined(separator: " "))
            ProgressView().controlSize(.small)
            Text("보내는 기기에서 이 코드를 입력하면 연결됩니다").font(.caption).foregroundStyle(.secondary)
            Button("중지") { receiver.stop() }.buttonStyle(.bordered)
        }
        .padding(20)
    }

    private func receivingCard(_ h: TransferHeader, _ got: Int) -> some View {
        VStack(spacing: 10) {
            Text("받는 중 — \(h.sender)").font(.headline)
            Text(h.name).font(.caption.monospaced())
            ProgressView(value: receiver.progress)
            Text(String(format: "%.1f / %.1f MB", Double(got) / 1_048_576, Double(h.byteCount) / 1_048_576))
                .font(.caption.monospacedDigit()).foregroundStyle(.secondary)
        }
        .padding(20)
    }

    private func doneCard(_ url: URL, _ h: TransferHeader) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill").font(.system(size: 44)).foregroundStyle(.green)
            Text("받았습니다 — \(h.kind.title)").font(.title3.bold())
            Text(url.lastPathComponent).font(.caption.monospaced()).textSelection(.enabled)
            Text(summary(of: url, kind: h.kind)).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            HStack {
                switch h.kind {
                case .persona:
                    Button("미리보기에서 열기") { open(url) }.buttonStyle(.borderedProminent)
                case .capture:
                    Button(model.isFitting ? "흉상 만드는 중…" : "이 캡처로 흉상 만들기") { build(url) }
                        .buttonStyle(.borderedProminent).disabled(model.isFitting)
                case .other:
                    EmptyView()
                }
                Button("또 받기") { receiver.start() }.buttonStyle(.bordered)
            }
            if model.isFitting { ProgressView().controlSize(.small) }
        }
        .padding(20)
    }

    private func status(_ text: String, systemImage: String, tint: Color = .secondary) -> some View {
        Label(text, systemImage: systemImage).font(.headline).foregroundStyle(tint).padding(20)
    }

    private var receivedList: some View {
        Group {
            if !receiver.received.isEmpty {
                GroupBox("받은 파일 \(receiver.received.count)") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(receiver.received, id: \.self) { url in
                            HStack {
                                Image(systemName: TransferItem.Kind.from(fileName: url.lastPathComponent) == .persona ? "person.crop.square" : "camera")
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(url.lastPathComponent).font(.caption.monospaced()).lineLimit(1)
                                    Text(summary(of: url, kind: .from(fileName: url.lastPathComponent))).font(.caption2).foregroundStyle(.secondary)
                                }
                                Spacer()
                                switch TransferItem.Kind.from(fileName: url.lastPathComponent) {
                                case .persona: Button("열기") { open(url) }.font(.caption)
                                case .capture: Button("흉상 만들기") { build(url) }.font(.caption).disabled(model.isFitting)
                                case .other: EmptyView()
                                }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func spaced(_ s: String) -> String {
        let a = Array(s)
        guard a.count == 6 else { return s }
        return String(a[0...2]) + " " + String(a[3...5])
    }

    /// 파일 한 줄 요약 (캡처 번들은 컷 수·기기, 페르소나는 템플릿·품질).
    private func summary(of url: URL, kind: TransferItem.Kind) -> String {
        let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize).map { String(format: "%.1f MB", Double($0) / 1_048_576) } ?? "—"
        switch kind {
        case .capture:
            if let b = try? CaptureBundleStore.readArchive(url, loadImages: false) {
                return "\(size) · 컷 \(b.shots.count) · \(b.meta.device)" + (b.meta.sparse ? " · 희소" : " · TrueDepth")
            }
            return size
        case .persona:
            let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("peek-\(UUID().uuidString)")
            defer { try? FileManager.default.removeItem(at: tmp) }
            if let _ = try? ChosangPackageStore.unarchive(url, to: tmp), let m = try? ChosangPackageStore.readManifest(from: tmp) {
                return "\(size) · 템플릿 \(m.templateID)@\(m.templateVersion)"
            }
            return size
        case .other: return size
        }
    }

    private func open(_ url: URL) {
        Task {
            note = await model.loadPersona(from: url) ?? ""
            if model.loadError == nil { model.tab = .preview }
        }
    }

    /// 캡처 번들 → 밀집 피팅 → 미리보기 (받은 걸 바로 내 흉상으로).
    private func build(_ url: URL) {
        note = "피팅 중… (1220 정점 패치 치환 + 두상 전파)"
        Task {
            note = await model.buildPersona(fromCapture: url) ?? ""
            if model.loadError == nil { model.tab = .preview }
        }
    }
}

// MARK: - 보내기

struct SendPane: View {
    @Environment(AppModel.self) private var model
    @State private var sender = ChosangSender(deviceName: AppModel.localDeviceName)
    @State private var code = ""
    @State private var selected: ChosangSender.Peer?
    @State private var picking = false
    @State private var file: (url: URL, name: String)?
    @State private var note = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                GroupBox("1. 보낼 파일") {
                    VStack(alignment: .leading, spacing: 8) {
                        if let file {
                            Label(file.name, systemImage: "doc").font(.callout)
                        } else {
                            Text("캡처 번들(.chosangcapture) 또는 페르소나(.chosang)").font(.caption).foregroundStyle(.secondary)
                        }
                        HStack {
                            Button("파일 고르기…") { picking = true }
                            if let latest = latestCapture {
                                Button("최근 캡처 쓰기") { Task { await useLatestCapture(latest) } }
                            }
                        }
                        .buttonStyle(.bordered)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                GroupBox("2. 받는 기기") {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Button(sender.peers.isEmpty ? "근처 기기 찾기" : "다시 찾기") { sender.startBrowsing() }.buttonStyle(.bordered)
                            if case .browsing = sender.phase { ProgressView().controlSize(.small) }
                        }
                        if sender.peers.isEmpty {
                            Text("받는 기기에서 \"받기 → 수신 대기 시작\" 을 먼저 누르세요.").font(.caption).foregroundStyle(.secondary)
                        } else {
                            ForEach(sender.peers) { peer in
                                HStack {
                                    Image(systemName: selected == peer ? "largecircle.fill.circle" : "circle")
                                    Text(peer.name)
                                    Spacer()
                                }
                                .contentShape(Rectangle())
                                .onTapGesture { selected = peer }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                GroupBox("3. 코드 6자리") {
                    VStack(alignment: .leading, spacing: 8) {
                        TextField("예: 123456", text: $code)
                            .textFieldStyle(.roundedBorder)
                            .font(.title3.monospaced())
                            #if os(iOS)
                            .keyboardType(.numberPad)
                            #endif
                            .onChange(of: code) { _, v in code = String(v.filter(\.isNumber).prefix(6)) }
                        Button("보내기") { send() }
                            .buttonStyle(.borderedProminent)
                            .disabled(file == nil || selected == nil || !TransferFraming.isValidCode(code))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                switch sender.phase {
                case .sending(let sent, let total):
                    VStack(alignment: .leading, spacing: 4) {
                        ProgressView(value: sender.progress)
                        Text(String(format: "%.1f / %.1f MB", Double(sent) / 1_048_576, Double(total) / 1_048_576)).font(.caption.monospacedDigit())
                    }
                case .done:
                    Label("보냈습니다", systemImage: "checkmark.circle.fill").foregroundStyle(.green)
                case .failed(let msg):
                    Label(msg, systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(.red)
                default: EmptyView()
                }
                if !note.isEmpty { Text(note).font(.caption).foregroundStyle(.secondary) }
            }
            .frame(maxWidth: 520)
            .frame(maxWidth: .infinity)
            .padding()
        }
        .fileImporter(isPresented: $picking, allowedContentTypes: [.data]) { result in
            guard case .success(let url) = result else { return }
            file = (url, url.lastPathComponent)
        }
        .onAppear { if model.launch.browse { sender.startBrowsing() } }
        .onDisappear { sender.stopBrowsing(); sender.cancel() }
    }

    /// 가장 최근에 저장한 캡처 폴더 (Documents/Captures)
    private var latestCapture: CaptureBundleMeta? { CaptureBundleStore.list().first }

    private func useLatestCapture(_ meta: CaptureBundleMeta) async {
        let folder = CaptureBundleStore.defaultFolder(for: meta.id)
        do {
            let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(meta.id.uuidString).\(CaptureBundleStore.fileExtension)")
            try? FileManager.default.removeItem(at: url)
            try ZipArchive.zipFolder(folder).write(to: url)
            file = (url, url.lastPathComponent)
            note = "최근 캡처 \(meta.shots.count)컷 준비됨"
        } catch { note = "묶기 실패: \(error.localizedDescription)" }
    }

    private func send() {
        guard let file, let peer = selected else { return }
        let scoped = file.url.startAccessingSecurityScopedResource()
        defer { if scoped { file.url.stopAccessingSecurityScopedResource() } }
        guard let data = try? Data(contentsOf: file.url) else { note = "파일을 읽지 못했습니다"; return }
        sender.send(TransferItem(name: file.name, data: data), to: peer, code: code)
    }
}
