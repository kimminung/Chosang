# 초상 (Chosang)

visionOS 27 · iOS 26 · macOS 26 단일 앱 타깃(Xcode 프로젝트·타깃·스킴 `Chosang`, 소스 폴더 `Chosang/`, 번들 `com.coulson.Chosang`; 10/3 저녁까지는 `MyApp`) + 로컬 패키지 `ChosangKit`. 리포 위치 `/Users/coulson/Desktop/Chosang`.
문서: `Docs/TechPRD.md`(설계·결정), `Docs/Tasks.md`(상태), `Docs/Blender-요청.md`(에셋 계약), `Docs/Spikes.md`(스파이크 결과), `Docs/Prompt.md`(마일스톤 프롬프트).

## 원칙
- 템플릿 우선: 블렌더 흉상이 기하의 진실. 사진은 형상 차이 + 텍스처만.
- 표정 표준은 ARKit 52 이름. 좌표계는 소반과 동일(m, Y-up, 얼굴 +Z, 왼쪽 +X).
- 좌표·형상은 결정적 기하(Vision/ARKit/수치해석)로. 언어 모델은 분류 힌트만.
- 캡처 데이터(사진·깊이·얼굴 메시)는 절대 커밋하지 않는다. `Fixtures/` 에는 합성 번들만.
- 소반 리포(`/Users/coulson/Desktop/Soban`)는 읽기 전용 참고. 수정 금지.

## 코드
- Swift 6 toolchain, Swift 5 언어 모드, 앱은 기본 MainActor 격리. Combine 금지, async/await.
- 플랫폼 분기는 `#if os(visionOS)` / `#if os(iOS)` / `#if os(macOS)`. 순수 모델·수학(ChosangCore)은 Foundation/simd/CoreGraphics 만.
- 모듈: Core(모델·포맷·수학) · Fit(피팅·외형 힌트) · Texture(투영·합성 캡처) · Rig(BustEntity·FaceRig·ClipPlayer) · Capture(ARKit·마이크) · IO(패키지·zip·PNG·USD) · Validate(계약 검사) + `chosang-validate` CLI.
- Metal 커널은 각 모듈 `Shaders/` 에, Swift 래퍼는 작은 해상도로 단위 테스트. (M4 부터)
- Swift Testing. 회귀 수치(RMS·잔차·관측 비율·스냅샷 차이)는 테스트가 지킨다: `cd ChosangKit && swift test`.
- API 는 DocumentationSearch 로 확인하고 쓴다. 추측 금지. 시그니처가 애매하면 `xcrun -sdk macosx swiftc -typecheck` 프로브로 확정한다(Docs/Spikes.md 참고).

## 빌드·검증
- 마일스톤 끝: visionOS 기기·시뮬레이터, iOS 시뮬레이터, macOS 4개 빌드 통과.
- Xcode 활성 대상이 실기기로 바뀌면 시뮬 빌드는 `xcodebuild -destination 'platform=visionOS Simulator,...' -derivedDataPath /tmp/chosang-dd CODE_SIGNING_ALLOWED=NO` 로 따로.
- 시뮬레이터 자동 실행 인자: `fixture=<synthetic|perturbed> clip=<name> tab=<preview|capture|validate|spikes|receive> template=<legacy|synthetic> camera=1`. Xcode 없이 macOS 앱을 띄울 때는 `open Chosang.app --env CHOSANG_ARGS="tab=capture camera=1"`(대시 없는 명령행 인자는 AppKit 이 "열 문서" 로 취급해 창이 안 뜬다). DerivedData 는 홈 아래로(`/tmp` 는 샌드박스 앱 실행 실패).
- Xcode 가 불안정하면(튕김) 파일 편집·빌드는 파일 도구 + `xcodebuild`/`swift test` 로. 엔타이틀먼트는 `Chosang/Chosang.entitlements`.
- 실기기 항목은 `Docs/Tasks.md` 체크리스트로 남기고 🧪 표시.
- 검증기: `cd ChosangKit && swift run chosang-validate <Template 폴더>` / `--synthetic <폴더>` / `--list-legacy-failures`.

## 문서 갱신
- 마일스톤마다 `Docs/TechPRD.md` 에 "N차" 절 추가(소반 형식), `Docs/Tasks.md` 상태 갱신, 계약 변경은 `Docs/Blender-요청.md` 에 이유와 함께.
