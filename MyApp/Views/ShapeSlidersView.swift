//
//  ShapeSlidersView.swift
//  초상
//
//  52 셰이프 슬라이더 패널 (T-106 의 1차). 영역별 그룹, "모두 0", 셰이프 시트는 M1.
//

import SwiftUI
import ChosangCore

struct ShapeSlidersView: View {
    @Environment(AppModel.self) private var model
    @State private var expanded: Set<String> = ["입·턱"]

    private var groups: [(String, [ArkitShape])] {
        [
            ("입·턱", ArkitShape.allCases.filter { $0.isMouthRegion }),
            ("눈", ArkitShape.allCases.filter { $0.isEyeRegion }),
            ("눈썹", ArkitShape.allCases.filter { $0.isBrowRegion }),
            ("볼·코", ArkitShape.allCases.filter { !$0.isMouthRegion && !$0.isEyeRegion && !$0.isBrowRegion }),
        ]
    }

    var body: some View {
        @Bindable var model = model
        GroupBox {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("셰이프 52").font(.headline)
                    Spacer()
                    Button("모두 0") { model.weights = .zero }.font(.caption)
                }
                ForEach(groups, id: \.0) { name, shapes in
                    DisclosureGroup(name, isExpanded: Binding(get: { expanded.contains(name) }, set: { if $0 { expanded.insert(name) } else { expanded.remove(name) } })) {
                        ForEach(shapes, id: \.self) { shape in
                            HStack(spacing: 6) {
                                Text(shape.rawValue).font(.caption2.monospaced()).frame(width: 140, alignment: .leading).lineLimit(1)
                                Slider(value: Binding(get: { Double(model.weights[shape]) }, set: { model.weights[shape] = Float($0) }), in: 0...1)
                                Text(String(format: "%.2f", model.weights[shape])).font(.caption2.monospacedDigit()).frame(width: 32)
                            }
                        }
                    }
                    .font(.subheadline)
                }
            }
        }
    }
}

/// 클립 선택 패널 (ClipPlayer · 절차적 클립).
struct ClipPanel: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        GroupBox(model.templateSource == .defaultTemplate && !model.clips.isEmpty ? "클립 (블렌더 clip_* \(model.clips.count)개)" : "클립 (절차적 — 블렌더 클립 대기)") {
            VStack(alignment: .leading, spacing: 6) {
                let names = SampledClip.contract.map(\.name)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 90))], spacing: 6) {
                    ForEach(names, id: \.self) { n in
                        Button(n) { model.selectedClip = model.selectedClip == n ? nil : n }
                            .buttonStyle(.bordered)
                            .tint(model.selectedClip == n ? .accentColor : .secondary)
                            .font(.caption)
                    }
                }
                Toggle("1회 클립 반복", isOn: $model.clipLoop).font(.caption)
            }
        }
    }
}
