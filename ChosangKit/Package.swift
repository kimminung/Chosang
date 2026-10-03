// swift-tools-version: 6.0
// 초상(Chosang) 로컬 패키지. 앱 타깃이 `ChosangKit` 라이브러리 제품에 의존한다.
// 모듈 경계(TechPRD §6.1):
//   ChosangCore     모델·포맷·ARKit 52 타입·수학 (Foundation/simd/CoreGraphics 만, 전 플랫폼)
//   ChosangFit      피팅 (Procrustes·패치 치환·RBF 전파·실루엣), 외형 힌트(FoundationModels)
//   ChosangTexture  다시점 투영·접합·탈조명·채움 (M0: CPU 참조 구현 + 합성 캡처 렌더러)
//   ChosangRig      BustEntity(LowLevelMesh + LowLevelDeformation / CPU 폴백), FaceRig, ClipPlayer
//   ChosangCapture  iPhone ARFaceTracking 캡처 세션 (iOS), MicLevelMeter (전 플랫폼)
//   ChosangIO       .chosang / 캡처 번들 읽기·쓰기, PNG, USD 내보내기(macOS), 전송
//   ChosangValidate 템플릿·클립 계약 검사 (CLI `chosang-validate` 가 사용)
import PackageDescription

let package = Package(
    name: "ChosangKit",
    defaultLocalization: "ko",
    platforms: [
        .visionOS("27.0"),
        .iOS("26.0"),
        .macOS("26.0"),
    ],
    products: [
        .library(
            name: "ChosangKit",
            targets: ["ChosangCore", "ChosangFit", "ChosangTexture", "ChosangRig", "ChosangCapture", "ChosangIO", "ChosangValidate"]
        ),
        .executable(name: "chosang-validate", targets: ["chosang-validate"]),
    ],
    targets: [
        .target(
            name: "ChosangCore",
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangFit",
            dependencies: ["ChosangCore"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangTexture",
            dependencies: ["ChosangCore"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangRig",
            dependencies: ["ChosangCore"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangCapture",
            dependencies: ["ChosangCore"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangIO",
            dependencies: ["ChosangCore"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .target(
            name: "ChosangValidate",
            dependencies: ["ChosangCore", "ChosangIO"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .executableTarget(
            name: "chosang-validate",
            dependencies: ["ChosangCore", "ChosangIO", "ChosangValidate", "ChosangTexture", "ChosangRig"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
        .testTarget(
            name: "ChosangKitTests",
            dependencies: ["ChosangCore", "ChosangFit", "ChosangTexture", "ChosangIO", "ChosangValidate"],
            swiftSettings: [.swiftLanguageMode(.v5)]
        ),
    ]
)
