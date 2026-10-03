# 초상 (Chosang) — 클로드에게 넘길 프롬프트 모음

사용 순서: ① 새 Xcode 프로젝트(visionOS App, 이름 `Chosang`)를 만들고 Xcode 에서 연다 → ② `Docs/handoff/` 네 문서를 새 프로젝트의 `Docs/` 로 복사 → ③ 아래 **킥오프 프롬프트**를 그대로 붙여 넣는다 → ④ 마일스톤마다 **후속 프롬프트**를 쓴다. `CLAUDE.md` 초안은 맨 아래.

---

## A. 킥오프 프롬프트 (첫 세션, 그대로 붙여 넣기)

```
너는 이 새 프로젝트 "초상(Chosang)" 의 구현 담당이다. 먼저 Docs/TechPRD.md, Docs/Tasks.md, Docs/Blender-요청.md 를 전부 읽어라.

배경: 이전 프로젝트 "소반" (/Users/coulson/Desktop/Soban, visionOS 두레반 모임 앱) 에서 사진 한 장 → 2.5D 카드/부조 스플랫 페르소나 + 블렌더 USDZ 얼굴 키트까지 만들었다. 한계(측면 없음, 키트가 떠 보임, 스플랫 미학습)를 소반 Docs/TechPRD.md §9 와 README 에서 확인해라. 이번 프로젝트의 핵심 전환은 "템플릿 우선" 이다: 블렌더 흉상이 기하의 진실, 사진은 형상 차이와 텍스처만 공급한다. 목표는 사진 3–5장으로 Vision Pro Persona 수준의 깔끔한 흉상 페르소나를 온디바이스에서 만들고, 블렌더 프리비즈 클립대로 움직이게 하는 것이다.

규칙:
1. 소반 리포는 읽기 전용 참고다. 수정하지 마라. 재사용할 코드(ArkitBlendShapes.swift, HangulViseme, ThinPlateSpline, AppearanceHints, VoiceEngine 의 MicLevelMeter)는 이 프로젝트로 복사해 와서 모듈 경계에 맞게 고쳐라.
2. Tasks.md 의 M0 를 먼저 끝내라. 특히 스파이크 T-004(USDZ 에서 blendShapeOffsets(named:) 읽기), T-005(macOS ModelIO USD 내보내기), T-006(LowLevelMesh + LowLevelDeformation 60fps), T-007(iPhone ARFaceTracking 에서 깊이·내부 파라미터·1220 정점·조명을 한 프레임에) 의 결과를 Docs/Spikes.md 에 기록하고, 결과에 따라 TechPRD §3·§6.7 의 분기를 확정한 뒤 M1 로 넘어가라. T-007 은 실기기가 필요하므로 코드와 측정 절차까지 준비하고 "🧪 실기기 확인 필요" 로 남겨라.
3. 모든 API 는 DocumentationSearch 로 visionOS 27 / iOS 26 / macOS 26 기준으로 확인하고 쓴다. 특히 RealityKit 의 LowLevelMesh, LowLevelDeformation, MeshDeformerComponent, BlendShapeWeightsComponent, AnimationGraphResource, BlendTreeAnimation, SkeletonResource, GaussianSplatComponent, ARKit 의 ARFaceGeometry/ARFaceTrackingConfiguration/capturedDepthData/lightEstimate 는 추측하지 말고 문서를 읽어라.
4. 구조: 앱 타깃 1개(visionOS·iOS·macOS 공용, #if os 분리) + 로컬 Swift Package ChosangKit(Core·Fit·Texture·Rig·Capture·IO·Validate + 테스트). 순수 모델·수학은 플랫폼 독립(CoreGraphics/Foundation/simd 만). Combine 금지, async/await. Swift Testing 사용.
5. 블렌더 산출물이 아직 없으므로 소반의 Soban/FaceAssets/DemoAvatar_Ethan.usdz 와 SplatPlaceholder_Bust.usdz 를 임시 템플릿으로 삼아 로더·변형·클립 플레이어를 먼저 돌려라. 동시에 tools/blender/export_chosang.py 와 chosang-validate 를 Blender-요청.md 계약대로 작성해라(블렌더 쪽은 내가 Blender MCP 로 진행한다). 계약에서 바꿔야 할 점이 생기면 Blender-요청.md 를 고치고 변경 이유를 적어라.
6. 각 마일스톤 끝에 4개 빌드(visionOS 기기·시뮬레이터, iOS 시뮬레이터, macOS)를 통과시키고, Tasks.md 상태를 갱신하고, Docs/TechPRD.md 에 "N차" 절을 소반 문서 형식으로 추가해라. 실기기가 필요한 항목은 체크리스트로 남겨라.
7. 질문이 생기면 작업을 멈추지 말고 가정을 명시한 채 진행하고, 가정 목록을 마지막에 정리해라. 단, 캡처 데이터(얼굴 사진·깊이·메시)를 저장소에 커밋하는 일은 하지 마라.

지금 할 일: M0 전체(T-001 ~ T-010). 끝나면 스파이크 결과 요약, 확정된 분기, 바뀐 문서, 다음 마일스톤(M1) 계획을 보고해라.
```

---

## B. 후속 프롬프트 (마일스톤별)

**M1 — 에셋 계약·내보내기·검증기**
```
Docs/Blender-요청.md 를 기준으로 T-101 ~ T-106 을 진행해라. export_chosang.py 는 Blender 4.1 과 5.x 양쪽 Python API 에서 돌아야 하고, 실행 방법을 스크립트 머리말에 적어라. chosang-validate 는 실패 항목을 "블렌더에서 무엇을 어떻게 고쳐라" 라는 한국어 문장으로 출력해라. 임시 템플릿(소반 USDZ)으로는 어떤 검사가 실패하는지 목록을 뽑아 블렌더 작업의 우선순위를 알려 줘라.
```

**M2 — 캡처 (iPhone)**
```
T-201 ~ T-205 를 구현해라. 중립도·각도·조도 게이트 임계값은 상수로 모으고 DEBUG 패널에서 조절 가능하게 해라. 캡처 번들의 모든 수치 단위와 좌표계를 CaptureBundle 의 문서 주석에 적어라(깊이 m, intrinsics 는 저장 이미지 해상도 기준, transform 은 ARKit 월드 → 카메라). 시뮬레이터용으로 합성 번들 생성기(템플릿을 가상 카메라 5대로 렌더)를 만들어 Fixtures 에 넣어라. 실기기 측정 절차는 Tasks T-206 체크리스트로.
```

**M3 — 피팅**
```
T-301 ~ T-308. 먼저 합성 번들 셀프 피팅으로 RMS < 0.2 mm 를 증명한 다음 픽스처로 넘어가라. RBF 는 바이하모닉(r³) 로 시작하고 수치 안정성(조건수) 문제가 있으면 정규화 λ 를 넣고 기록해라. 미소 컷 검증 렌더는 사진과 나란히 보여 주는 뷰까지 포함한다. 결과 수치는 Docs/TechPRD.md 의 N차 절에 표로 남겨라.
```

**M4 — 텍스처**
```
T-401 ~ T-408. Metal 커널은 ChosangTexture/Shaders/ 에 두고 Swift 쪽 래퍼는 테스트 가능하게(작은 해상도 256² 로 단위 테스트). 탈조명은 슬라이더 0 에서 원본과 동일해야 한다. 접합선 색 단차와 관측 비율을 자동으로 계산해 품질 카드 값으로 넘겨라. 4k 와 2k 두 설정의 빌드 시간을 기록해라.
```

**M5 — 런타임 리그·클립·상황**
```
T-501 ~ T-508. T-006 에서 확정한 경로(LowLevelDeformation 또는 폴백)로 BustEntity 를 만들고, 소반 FaceRigSystem 을 이식해 externalWeights·비셈·깜빡임을 연결해라. ClipPlayer 와 레이어 합성 규칙(TechPRD §6.7)을 그대로 구현하고, SituationDirector 는 순수 값 입력(SituationInput)으로 테스트 가능하게 해라. 미리보기 뷰는 3 플랫폼에서 같은 모습이어야 한다. 시뮬레이터에서 셰이프 시트(52 셰이프 각각 1.0 스냅샷)를 찍어 Docs/screenshots 에 넣어라.
```

**M6 — 패키지·전송·내보내기·어댑터**
```
T-601 ~ T-607. .chosang 은 폴더 패키지로 시작하고 zip 은 전송·AirDrop 용으로만. 전송은 처음부터 Network.framework(TN3213) 로 하고 MultipeerConnectivity 는 쓰지 마라. .sobanpersona 어댑터는 소반 Docs/TechPRD.md §5.2d 포맷을 정확히 따르되 소반 리포는 건드리지 말고, 소반 쪽에 필요한 변경(chosangRef 키 처리, ChosangBustAvatar 통합)은 Docs/SobanIntegration.md 에 패치 제안으로 적어라.
```

**M7 — 검수·품질**
```
T-701 ~ T-704. 프리비즈 비교 화면은 mp4 와 렌더의 카메라가 같다는 것을 숫자로 보여 줘라(FOV·거리·조준점). 렌더 스냅샷 회귀 테스트를 추가하고 기준 이미지 갱신 절차를 README 에 적어라. 실기기 체크리스트(Tasks 맨 아래)를 최신 상태로 정리해라.
```

**M8 — v2 스플랫 (선택)**
```
T-801 ~ T-804. 먼저 바인딩·갱신 커널과 GaussianSplatResource 재기록만으로 "메시를 따라 움직이는 스플랫" 을 보여 주고, 그 다음 최적화기를 붙여라. 최적화는 색·불투명도·스케일·법선 오프셋만, 위치·토폴로지는 고정. iPhone 15 Pro 90 s 예산을 넘기면 스플랫 수와 반복 수를 줄여 기록해라.
```

---

## C. `CLAUDE.md` 초안 (새 프로젝트 루트에)

```markdown
# 초상 (Chosang)

visionOS 27 · iOS 26 · macOS 26 단일 앱 타깃 + 로컬 패키지 `ChosangKit`. 문서: `Docs/TechPRD.md`(설계·결정), `Docs/Tasks.md`(상태), `Docs/Blender-요청.md`(에셋 계약), `Docs/Spikes.md`(스파이크 결과).

## 원칙
- 템플릿 우선: 블렌더 흉상이 기하의 진실. 사진은 형상 차이 + 텍스처만.
- 표정 표준은 ARKit 52 이름. 좌표계는 소반과 동일(m, Y-up, 얼굴 +Z, 왼쪽 +X).
- 좌표·형상은 결정적 기하(Vision/ARKit/수치해석)로. 언어 모델은 분류 힌트만.
- 캡처 데이터(사진·깊이·얼굴 메시)는 절대 커밋하지 않는다. `Fixtures/` 에는 합성 번들만.
- 소반 리포(`/Users/coulson/Desktop/Soban`)는 읽기 전용 참고. 수정 금지.

## 코드
- Swift 6 toolchain, Swift 5 언어 모드, 기본 MainActor 격리. Combine 금지, async/await.
- 플랫폼 분기는 `#if os(visionOS)` / `#if os(iOS)` / `#if os(macOS)`. 순수 모델·수학은 Foundation/simd/CoreGraphics 만.
- Metal 커널은 각 모듈 `Shaders/` 에, Swift 래퍼는 작은 해상도로 단위 테스트.
- Swift Testing. 회귀 수치(RMS·잔차·관측 비율·스냅샷 차이)는 테스트가 지킨다.
- API 는 DocumentationSearch 로 확인하고 쓴다. 추측 금지.

## 빌드·검증
- 마일스톤 끝: visionOS 기기·시뮬레이터, iOS 시뮬레이터, macOS 4개 빌드 통과.
- 시뮬레이터 자동 실행 인자: `fixture=<name> clip=<name> tab=<name>`.
- 실기기 항목은 `Docs/Tasks.md` 체크리스트로 남기고 🧪 표시.

## 문서 갱신
- 마일스톤마다 `Docs/TechPRD.md` 에 "N차" 절 추가(소반 형식), `Docs/Tasks.md` 상태 갱신.
```
