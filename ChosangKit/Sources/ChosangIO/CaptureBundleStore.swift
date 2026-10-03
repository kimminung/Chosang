//
//  CaptureBundleStore.swift
//  ChosangIO
//
//  캡처 번들 폴더 읽기/쓰기 + `.chosangcapture`(stored zip). 포맷은 ChosangCore/Formats.md.
//  캡처 데이터는 저장소에 커밋하지 않는다 — Fixtures 에는 합성 번들만.
//

import Foundation
import ChosangCore

public enum CaptureBundleStore {
    public static let metaName = "meta.json"
    public static let fileExtension = "chosangcapture"

    public static func write(_ bundle: CaptureBundle, to folder: URL, jpegQuality: Double = 0.92) throws {
        let fm = FileManager.default
        try fm.createDirectory(at: folder, withIntermediateDirectories: true)
        var meta = bundle.meta
        meta.shots = []
        for shot in bundle.shots {
            var m = shot.meta
            if let img = shot.image {
                try ImageCodec.jpeg(img, quality: jpegQuality).write(to: folder.appendingPathComponent(m.imageFile))
                m.imageWidth = img.width; m.imageHeight = img.height
            }
            if let d = shot.depth {
                let name = m.depthFile ?? "depth-\(meta.shots.count).f32"
                m.depthFile = name
                m.depthWidth = d.width; m.depthHeight = d.height
                try d.values.withUnsafeBytes { Data($0) }.write(to: folder.appendingPathComponent(name))
            }
            meta.shots.append(m)
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        enc.dateEncodingStrategy = .iso8601
        try enc.encode(meta).write(to: folder.appendingPathComponent(metaName))
    }

    public static func read(from folder: URL, loadImages: Bool = true) throws -> CaptureBundle {
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        let meta = try dec.decode(CaptureBundleMeta.self, from: Data(contentsOf: folder.appendingPathComponent(metaName)))
        var shots: [CaptureShot] = []
        for m in meta.shots {
            var image: RGBAImage? = nil
            if loadImages, let data = try? Data(contentsOf: folder.appendingPathComponent(m.imageFile)) {
                image = try? ImageCodec.decode(data)
            }
            var depth: DepthMap? = nil
            if let df = m.depthFile, let w = m.depthWidth, let h = m.depthHeight,
               let data = try? Data(contentsOf: folder.appendingPathComponent(df)), data.count == w * h * 4 {
                let vals = data.withUnsafeBytes { Array($0.bindMemory(to: Float.self)) }
                depth = DepthMap(width: w, height: h, values: vals)
            }
            shots.append(CaptureShot(meta: m, image: image, depth: depth))
        }
        return CaptureBundle(meta: meta, shots: shots)
    }

    /// `.chosangcapture` 로 묶기.
    public static func archive(_ bundle: CaptureBundle, to url: URL) throws {
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("chosang-bundle-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: tmp) }
        try write(bundle, to: tmp)
        try ZipArchive.zipFolder(tmp).write(to: url)
    }

    /// `.chosangcapture` 풀어서 읽기.
    public static func readArchive(_ url: URL, loadImages: Bool = true) throws -> CaptureBundle {
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("chosang-bundle-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: tmp) }
        try ZipArchive.unzip(Data(contentsOf: url), to: tmp)
        return try read(from: tmp, loadImages: loadImages)
    }

    /// 기본 보관 위치 Documents/Captures/<uuid>/
    public static func defaultFolder(for id: UUID) -> URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent("Captures", isDirectory: true).appendingPathComponent(id.uuidString, isDirectory: true)
    }
}
