//
//  MyApp.swift
//  초상 (Chosang)
//
//  단일 앱 타깃: visionOS(받기·확인·거울) · iOS(캡처·빌드·보내기) · macOS(검증·비교 검수). 플랫폼 분기는 #if os.
//  타깃 이름은 MyApp(Xcode 자동 생성)이지만 제품 이름·번들 id 는 Chosang / com.coulson.Chosang 이다.
//

import SwiftUI
import ChosangRig

@main
struct ChosangApp: App {
    @State private var model: AppModel

    init() {
        FaceRigSystem.register()
        _model = State(initialValue: AppModel(launch: LaunchOptions.current))
    }

    var body: some SwiftUI.Scene {
        WindowGroup {
            RootView()
                .environment(model)
                // T-604: AirDrop·파일 앱·공유 시트로 넘어온 `.chosang`/`.chosangcapture` 를 그대로 받는다.
                .onOpenURL { url in Task { await model.open(url) } }
        }
        #if os(visionOS)
        .defaultSize(width: 980, height: 760)
        #elseif os(macOS)
        .defaultSize(width: 1100, height: 760)
        #endif
    }
}
