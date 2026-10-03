# 초상 (Chosang) — M0 스파이크 결과

> 2026-10-03 · Xcode 27.0 (27A266a) · Swift 6.4 · macOS 27.0.1 · visionOS 27.0 시뮬레이터 · 측정 코드는 모두 리포에 있다(재현 명령 포함).
> 결론은 `TechPRD.md` §3 의 분기 확정과 §12(1차) 에 반영했다.

| 스파이크 | 결론 한 줄 | 상태 |
|---|---|---|
| T-004 USDZ 셰이프 델타 | `MeshResource.contents` → `part.blendShapeOffsets(named:)` **읽힌다**(36/36, 길이 = 정점 수). 스킨·조인트도 읽힌다. USDZ 가 1차 경로, `bust.mesh` 는 교차 검증·폴백 | ✅ |
| T-005 ModelIO USD 내보내기 | `usdz` 내보내기 **불가**(Unknown extension), `usdc`·`usda`·`obj` 가능 → usdc + 자체 zip(64 B 정렬) | ✅ |
| T-006 LowLevelMesh + LowLevelDeformation | Mac GPU 경로 **0.14 ms/변형, 60 fps**. 시뮬레이터 SDK 에는 `LowLevelDeformation` 심볼이 **없어** CPU 폴백(6.7k 정점 7–9 ms, 60–83 fps, 디버그 빌드). 뼈 클립은 자체 샘플러 | ✅ (실기기 수치 🧪) |
| T-007 iPhone ARKit 한 프레임 | 코드·측정 절차 준비. 실기기 필요 | 🧪 |

---

## T-004 — USDZ 에서 `blendShapeOffsets(named:)`·스킨·조인트 읽기

**방법**: `ChosangRig/TemplateLoader.load(url:)` — `Entity(contentsOf:)` → 모든 `ModelComponent` 순회 → `BlendShapeWeightsMapping(meshResource:)` 로 셰이프 이름 수집 → 각 파트에서 `blendShapeOffsets(named:)`(전체 경로 → 마지막 토큰 순으로) 를 읽어 길이가 정점 수와 같은지 확인 → `part.jointInfluences`·`contents.skeletons`.
앱의 "스파이크" 탭 T-004 또는 실행 인자 `report=1` 로 재현(시뮬레이터 Documents/chosang-report.txt).

**결과 (소반 `DemoAvatar_Ethan.usdz`, Blender 5.2 ARKit52 재내보내기, visionOS 27 시뮬레이터)**

| 메시 | 정점 | 셰이프 이름 | 오프셋 읽힘 | 스킨 |
|---|---|---|---|---|
| Demo_Ethan_Mouth | 528 | 16 | 16 | O (정점당 1) |
| Demo_Ethan_Eyelids | 1332 | 14 | 14 | O |
| Demo_Ethan_Brows | 108 | 5 | 5 | O |
| Demo_Ethan_Head | 16257 | 1 (jawOpen) | 1 | O |
| Demo_Ethan_Hair | 23042 | 0 | — | — |
| Demo_Ethan_Eye_L/R | 801 | 0 | — | — |

스켈레톤 1개(조인트 1), `jointInfluences` 528개(정점당 1). `SplatPlaceholder_Bust.usdz` 는 21,634 정점·UV O·셰이프 0.
읽힌 이름은 USD 경로 형태로 오므로 마지막 토큰으로 ARKit 이름을 맞춘다(`jawOpen`, `mouthSmileLeft`, …).

**확정**: TechPRD §3 "런타임 변형" 의 1차 경로(USDZ → 델타 추출 → LowLevelMesh) 를 그대로 간다. 단,
- 로더는 메시를 **이름 `Bust`** 로 고른다(없으면 셰이프가 가장 많은 메시 — 레거시에서는 머리카락 메시가 가장 커서 "가장 큰 메시" 규칙은 틀렸다).
- `bust.mesh` 는 폴백이 아니라 **항상 함께** 내보내 검증기가 정점 수·셰이프·스킨을 USDZ 와 교차 확인한다(Blender-요청.md §6b).
- 첫 로드는 시뮬레이터에서 0.5–13 s(캐시 전) → T-104 의 1회 캐시가 필요하다.

**2차 재확인 (실제 템플릿 `Template.usdz`, 2026-10-03 저녁)**: 엔티티 13 · 모델 1(`Armature`) · 파트 11(Bust + Eye_L 3 + Eye_R 3 + Mouth_Inner 4). Bust 파트 11,931 정점(원본 11,569 + UV/법선 솔기 분할) 에서 `blendShapeOffsets(named:)` **52/52 읽힘**(이름은 `eyeBlinkLeft` 처럼 짧은 토큰 그대로), 조인트 6, `jointInfluences` 35,793(정점당 3). Mouth_Inner 셰이프는 `jawOpen2…`(USD 중복 접미). 파트 좌표는 메시 로컬 → `entity.transformMatrix(relativeTo: nil)` 적용 후 bust.mesh 와 최대 차 **0.0 mm**(`chosang-validate --with-usdz`). 시뮬레이터 로드 8.3 s(캐시 전), Mac 1.0 s.

## T-005 — macOS ModelIO USD 내보내기

**방법**: `/tmp/mdl_spike.swift`(리포에는 `ChosangIO/USDExport.capability()` 로 같은 조회) — `MDLAsset.canExportFileExtension` + 박스 메시 실제 `export(to:)`.

```
usdz export: false  import: true
usdc export: true   import: true   → 2744 B
usda export: true   import: true   → 2640 B
obj/stl/ply/abc export: true
export usdz: FAILED MDLErrorDomain "Unknown extension on URL"
```

**확정**: USDZ = ModelIO 로 `usdc` 를 쓰고 `ChosangIO/ZipArchive`(stored, 64바이트 정렬 — `zipAlignment` 테스트) 로 텍스처 PNG 와 함께 묶는다. M6 T-606 에서 구현. 기기 간 교환은 `.chosang` 패키지.

## T-006 — LowLevelMesh + LowLevelDeformation 60 fps

**방법**: `ChosangRig/BustEntity` — 버퍼 0 위치(float3, 12 B)·1 법선·2 UV 의 `LowLevelMesh`; GPU 경로는 `LowLevelDeformationContext(device)` → `Pipeline.Descriptor { inputAttributes/outputAttributes = [position], blendShape = BlendShape(blendsOutputs: []) }` → `Descriptor(vertexCount:, blendShape: .init(targetCount: 52))` → 매 프레임 `output.setVertices(mesh.replace(bufferIndex: 0, using: cb))` + `blendShape.setWeights` + `encode(into:)`. CPU 경로는 `withUnsafeMutableBytes` 로 위치 = 기준 + Σ w·Δ(0 이 아닌 셰이프만).
API 시그니처는 문서가 성겨서 `xcrun -sdk macosx swiftc -typecheck` 프로브(`/tmp/lld_probe2.swift`)로 확정했다:
`VertexAttribute(semantic:format: MTLVertexFormat, stride:)`, `Pipeline.Descriptor.blendShape/skinning/renormalization(outputs:)`, `LowLevelDeformation.blendShape.setPositionOffsets/setWeights`, `input/output.setVertices(_:offset:semantic:)`, `LowLevelDeformationContext(_ device)`.

**결과** (합성 템플릿 6,721 정점 · 52 타깃 · 클립 `laugh` 재생 중, 디버그 빌드)

| 환경 | 경로 | 변형 시간 | 프레임 |
|---|---|---|---|
| Mac (M-시리즈, macOS 27.0.1) | LowLevelDeformation (GPU) | **0.14 ms** (CPU 측 인코딩) | 16.7 ms = 60 fps(vsync) |
| visionOS 27 시뮬레이터 | CPU 블렌드 (폴백) | 7.5–9.2 ms | 12–16.7 ms = 60–83 fps |
| Vision Pro / iPhone 실기기 | GPU 예정 | 🧪 | 🧪 (T-509: 흉상 2개 90 Hz) |

**발견**: `xrsimulator27.0`/`iphonesimulator27.0` SDK 에는 `LowLevelDeformation`/`LowLevelDeformationContext` 심볼이 없다(소반 8차의 `GaussianSplatResource` 와 같은 패턴). → `#if !targetEnvironment(simulator)` 로 GPU 엔진을 감싸고 시뮬레이터는 CPU 폴백(`BustEntity.isGPUPathCompiled`). macOS 27 SDK 의 textual swiftinterface/심볼 그래프에도 안 보이지만 컴파일·링크는 된다(바이너리 모듈에만 있음) — 문서 검색 + 컴파일 프로브가 유일한 확인 수단.

**확정**:
- 주 경로 = `LowLevelDeformation`(기기·Mac), 폴백 = CPU 블렌드(시뮬레이터·실패 시). `MeshDeformerComponent` 는 쓰지 않는다(자체 정점 포맷·Identity 치환과 맞지 않음).
- 뼈 클립은 **자체 샘플러 `ClipPlayer`** 로 돌린다: 52 가중치와 뼈 트랙을 같은 타임라인·크로스페이드(250 ms)로 다루고, 블렌더 클립이 `clip.json` 으로 오므로 USD SkelAnimation 이 없다. `AnimationGraphResource`/`BlendMask` 는 M5 에서 스키닝을 켤 때 look-at·Neck 마스크 용도로 재검토.
- M5 에서 켤 것: `pd.skinning`(조인트 6, 정점당 4) + `renormalization(outputs: [.normal])` + 법선 델타(`blendsOutputs: [.normal]`).

## T-007 — iPhone ARFaceTracking 한 프레임 (🧪 실기기 필요)

**코드**: `ChosangCapture/FaceCaptureSession` — `ARFaceTrackingConfiguration(isLightEstimationEnabled, maximumNumberOfTrackedFaces 1)`, 첫 프레임에서 `ARFaceProbeReport`(정점 수·삼각형 수·삼각형 인덱스 FNV-1a 해시·`capturedDepthData` 크기/포맷/타임스탬프 차·`camera.intrinsics`/`imageResolution`·`ARDirectionalLightEstimate` 유무·ambient/색온도·blendShapes 수). 앱 "캡처" 탭에 표시, "스파이크" 탭 T-007 에 안내.
문서 확인(DocumentationSearch): `ARFaceGeometry.vertices`(1220, 얼굴 좌표계) · `triangleIndices: [Int16]`(토폴로지 고정) · `ARFrame.capturedDepthData: AVDepthData?`(TrueDepth, 색 프레임과 다른 주기라 nil 일 수 있음 → `capturedDepthDataTimestamp`) · `lightEstimate as? ARDirectionalLightEstimate`(얼굴 구성에서 제공).

**측정 절차 (iPhone, TrueDepth)**
1. Xcode 에서 iPhone 실기기 선택 → 실행 → "캡처" 탭 → "세션 시작" → 카메라 권한 허용.
2. "T-007 프로브" 상자에 뜨는 값을 기록: `정점 1220` 인지, 삼각형 수, 해시(16진), 깊이 `640×480 DepthFloat32` 와 Δt, 이미지 해상도·fx/fy/cx/cy, 조명 방향 유무.
3. 해시를 `ChosangCore/ARKitFaceTopology.referenceTriangleHash` 에 넣고 삼각형 수를 `expectedTriangleCount` 와 비교. Apple 샘플 `ARFaceGeometry.obj` 를 Blender 로 가져온 뒤 `export_chosang.py` 가 쓴 `template.json.patchTriangleHash` 와 같아야 한다(다르면 OBJ 가져오기 정점 순서 보존 옵션 확인).
4. 5컷을 눌러 촬영 → "번들 저장" → Files 앱에서 `Documents/Captures/<uuid>/` 크기(목표 ≤ 40 MB)와 저장 시간을 적는다. 이 번들은 커밋하지 않는다.
5. 결과를 이 절과 `Tasks.md` 실기기 체크리스트 0 번에 적는다.

**알려진 미확정**: 저장 이미지 방향(센서 가로 → 포트레이트 회전)과 그에 맞춘 intrinsics 변환(`fx'=fy, fy'=fx, cx'=H−cy, cy'=cx`)·카메라 변환(Z 축 −90°)은 코드에 넣었지만 실기기에서 재투영 오차로 검증해야 한다(M2 T-206).

## T-205 — Vision 얼굴 자세 부호 · Mac 카메라 (Mac 실기기 관측, 2026-10-03)

**질문**: `FaceObservation.yaw/pitch/roll` 의 부호가 우리 규약(yaw + = 피사체 왼쪽, pitch + = 위, roll + = 반시계)과 맞는가. Mac 에서 센서 FOV 를 읽을 수 있는가.

**관측(MacBook Air FaceTime HD, `DetectFaceLandmarksRequest(.revision3)`)**
| 동작 | Vision 원값 | 우리 값(`SparseFaceGeometry.pose`) |
|---|---|---|
| 정면, 화면을 내려다봄 | yaw −1.5° · pitch +11.3° | yaw +1.5°(코끝 부호) · pitch −11.3°(아래) |
| 왼쪽 30° 로 고개 돌림 | yaw +30.9° · pitch −2.1° | yaw +30.9° · pitch +2.1° → "왼쪽 30°" 게이트 통과 |

→ Vision yaw 는 우리 규약과 **같은 부호**(코끝 치우침과 일치), pitch 는 **반대**(오른손 좌표계: + 가 턱 내림). 코드는 yaw 를 랜드마크 부호로 보정하고 pitch 를 반전한다. 🧪 iPhone(전면, 세로)에서 1회 더 확인.
`AVCaptureDevice.Format.videoFieldOfView` 는 `API_UNAVAILABLE(macos, visionos)` → Mac 은 FOV 60° 가정(`intrinsicsEstimated = true`). Vision 76점은 1080p 프레임에서 분석 겹침 없이(플래그로 프레임 버림) 실시간 추적됐다.

## 부록 — M0 에서 함께 측정한 수치 (SelfFitTests, `cd ChosangKit && swift test`)

| 항목 | 값 |
|---|---|
| 합성 템플릿 | 6,721 정점(패치 1220 + 두상·목·어깨), 52 델타, 뼈 6 |
| 셀프 피팅(템플릿 그대로) | 패치 RMS 0.011 mm · 전체 0.008 mm · s = 1.000 |
| 섭동 사용자(1.05·코 5 mm·턱 6 mm·광대 4 mm·비대칭 2 mm) | 패치 형상 RMS 0.0005 mm · s = 1.073 · 두상 전파 오차 중앙값 1.9 mm / p90 2.7 mm / 최대 18 mm(어깨 제외) |
| 두상 전파(감쇠 없는 순수 r³ RBF) | 중앙값 6.0 mm → **전역 유사변환 + 잔차 RBF × 경계 거리 감쇠(σ 5 cm)** 로 1.9 mm |
| CPU 텍스처 투영(1280×960 5컷 → 256²) | 관측 79.8% · PSNR 24.0 dB(기준선 22; 480×360 은 21.5) · 1.6 s |
| RBF 풀이 | 300 중심, 피벗비 8×10⁶, λ = 0 |
