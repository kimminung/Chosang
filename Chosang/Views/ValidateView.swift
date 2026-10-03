//
//  ValidateView.swift
//  초상 (macOS)
//
//  Template 폴더를 골라 chosang-validate 와 같은 규칙으로 검사한다. USDZ 가 있으면 TemplateLoader 로 읽어 메시 검사까지.
//

#if os(macOS)
import SwiftUI
import UniformTypeIdentifiers
import ChosangCore
import ChosangRig
import ChosangValidate

struct ValidateView: View {
    @State private var folderURL: URL?
    @State private var report = "Template 폴더(template.json 이 있는 폴더)를 고르세요. 합성 템플릿으로 자체 검사도 할 수 있습니다."
    @State private var showImporter = false
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Button("폴더 선택…") { showImporter = true }
                Button("합성 템플릿 자체 검사") { Task { await validateSynthetic() } }
                if let u = folderURL { Text(u.path).font(.caption).foregroundStyle(.secondary).lineLimit(1) }
                Spacer()
                if busy { ProgressView().controlSize(.small) }
            }
            ScrollView {
                Text(report).font(.caption.monospaced()).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding()
        .fileImporter(isPresented: $showImporter, allowedContentTypes: [.folder]) { result in
            if case .success(let url) = result { folderURL = url; Task { await validate(url) } }
        }
    }

    private func validate(_ url: URL) async {
        busy = true; defer { busy = false }
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        do {
            let folder = try TemplateFolder(root: url)
            var template = folder.bustMesh
            let usdz = url.appendingPathComponent(TemplateFolder.usdzName)
            if FileManager.default.fileExists(atPath: usdz.path) {
                let (t, r, _) = try await TemplateLoader.load(url: usdz, manifest: folder.manifest)
                report = "USDZ 로드:\n" + r.summary + "\n\n"
                if let t { template = t }
            } else { report = "" }
            let issues = TemplateValidator.validate(folder.validationInput(template: template))
            report += TemplateValidator.report(issues, title: url.lastPathComponent)
        } catch {
            report = "읽기 실패: \(error.localizedDescription)"
        }
    }

    private func validateSynthetic() async {
        busy = true; defer { busy = false }
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("chosang-synthetic-template")
        do {
            try? FileManager.default.removeItem(at: dir)
            try TemplateFolder.writeSynthetic(to: dir)
            let folder = try TemplateFolder(root: dir)
            let issues = TemplateValidator.validate(folder.validationInput())
            report = "합성 템플릿 → \(dir.path)\n\n" + TemplateValidator.report(issues, title: "synthetic")
        } catch { report = "실패: \(error.localizedDescription)" }
    }
}
#endif
