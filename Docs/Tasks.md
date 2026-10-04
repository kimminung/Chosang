# 초상 (Chosang) — Tasks

상태: ✅ 완료 · 🔄 진행 · ⏳ 대기 · 🧪 실기기 검증 필요 · 🔬 스파이크(결과에 따라 설계 분기)

원칙: **M0 스파이크 4개가 끝나기 전에는 M3 이후 구현을 시작하지 않는다.** 각 마일스톤 끝에 4개 빌드(visionOS 기기·시뮬, iOS 시뮬, macOS) 통과 + 해당 체크리스트.

## M0 · 프로젝트 셋업 · 스파이크
| ID | 작업 | 상태 |
|---|---|---|
| T-001 | Xcode 프로젝트 `Chosang`: 단일 앱 타깃 3 플랫폼(xros/xrsimulator/iphoneos/iphonesimulator/macosx, family 1,2,7), 번들 `com.coulson.Chosang`, 배포 visionOS 27 · iOS 26 · macOS 26, 자동 서명 팀 5Z8G42AVKD, 엔타이틀먼트 없음 → 3차: `Chosang/Chosang.entitlements`(샌드박스·카메라·오디오 입력·사용자 선택 파일·네트워크; 샌드박스 Mac 앱은 카메라 엔타이틀먼트 없이는 AVCapture 불가) | ✅ 1차 — Xcode 타깃 이름은 `MyApp`(자동 생성), 제품/표시 이름 Chosang/초상. 10/3 저녁 사용자가 `Desktop/Chosang` 으로 이동하고 프로젝트·타깃·폴더를 `Chosang` 으로 변경(INFOPLIST_FILE 경로 수정). macOS 샌드박스 카메라·오디오 입력·네트워크(빌드 설정) |
| T-002 | 로컬 Swift Package `ChosangKit`(타깃: Core·Fit·Texture·Rig·Capture·IO·Validate, 테스트 타깃), 앱이 의존 | ✅ 1차 — + `chosang-validate` 실행 타깃. 함정: Xcode 가 프로젝트를 다시 저장하면 외부에서 넣은 패키지 참조가 지워진다(pbxproj 재적용 필요) |
| T-003 | Info.plist: 카메라(ARKit 얼굴 데이터 사용 고지)·로컬 네트워크·Bonjour `_chosang._tcp`, UTI `com.coulson.chosang.persona`/`.chosangcapture`, 문서 타입 | ✅ 1차 (+ 마이크 고지) |
| T-004 | 🔬 `Entity(named:)` 로 로드한 USDZ 의 `MeshResource.contents` 에서 `blendShapeOffsets(named:)` 52개·스킨 가중치·조인트가 읽히는지(소반 `DemoAvatar_Ethan.usdz` 로 즉시 확인). 안 되면 `bust.mesh` 경로 확정 | ✅ 1차 — 결과는 `Docs/Spikes.md` T-004. 결정: USDZ 를 1차 경로로 쓰되 `bust.mesh` 를 **항상 함께** 내보내 검증기가 교차 확인 |
| T-005 | 🔬 macOS ModelIO `MDLAsset.canExportFileExtension("usdz"/"usdc")` 와 실제 내보내기(메시+텍스처). 안 되면 자체 USDA+zip 설계 | ✅ 1차 — usdz ✗ · usdc/usda ✓ → **usdc + 자체 ZipArchive(64 B 정렬)** 로 usdz. `ChosangIO/USDExport`, `ZipArchive` |
| T-006 | 🔬 `LowLevelMesh` + `LowLevelDeformation`(blending 52 · skinning 5 · renormalizing) 를 소반 흉상에 적용해 시뮬레이터·Mac 에서 60 fps 확인. 뼈 클립을 `AnimationGraphResource` 로 돌릴지 자체 샘플러로 돌릴지 결정 | ✅ 1차 — **시뮬레이터 SDK 에 `LowLevelDeformation` 없음**(GaussianSplat 과 같은 패턴) → 기기·Mac 은 GPU, 시뮬레이터는 CPU 폴백. 뼈 클립 = 자체 `ClipPlayer`. 수치는 `Docs/Spikes.md` |
| T-007 | 🔬 iPhone: `ARFaceTrackingConfiguration` 에서 `capturedDepthData`·`intrinsics`·`faceAnchor.geometry.vertices`·`lightEstimate` 를 한 프레임에서 동시에 얻어 저장. 정점 수 1220·삼각형 해시 기록. Apple 샘플 `ARFaceGeometry.obj` 와 정점 순서 일치 확인 | ✅ 7차 실기기 (iPhone 16 / iOS 27.0.1) — 정점 **1220** · 삼각형 **2304** · 해시 **`67161fe4685cdd1e`**(→ `ARKitFaceTopology.referenceTriangleHash`) · 이미지 1440×1080(저장 1080×1440) · fx 966 fy 966 cx 715 cy 535 · 깊이 640×480 DepthFloat32(**프레임마다 오지 않음**) · ambient 978 lm 5933 K **방향 추정 없음** · 셰이프 52. 결정: M4 탈조명은 조명 방향 없이, 깊이는 최근 프레임 캐시로 보충 |
| T-008 | 소반에서 이식: `ArkitBlendShapes.swift`(52 이름·가중치·비셈 프리셋·어댑터), `HangulViseme`, `ThinPlateSpline`(폴백용), `AppearanceHints`(FoundationModels + 휴리스틱). 소반 리포는 **수정하지 않는다** | ✅ 1차 — Core(ArkitBlendShapes·HangulViseme·TPS) · Fit(AppearanceHints, 7개 분류로 확장) · Capture(MicLevelMeter) · Rig(FaceRig). 소반 리포 미수정 |
| T-009 | Fixtures: 소반 USDZ 흉상을 임시 템플릿으로, 합성 캡처 번들 1세트(템플릿 자체를 가상 카메라 5대로 렌더한 RGB·깊이·정점) → 파이프라인 끝까지 통과하는 "셀프 피팅" 테스트 | ✅ 1차 — 소반 USDZ 에는 셰이프·패치가 없어 **절차적 합성 템플릿**(`SyntheticTemplate`, 1220 패치 + 52 델타)으로 대체. `Fixtures/synthetic-{template,perturbed}.chosangcapture`, 셀프 피팅 RMS 0.011 mm, 섭동 피팅 패치 0.0005 mm·두상 중앙값 1.9 mm, CPU 텍스처 PSNR 24 dB(기준선 22) — `SelfFitTests` |
| T-010 | README · Docs(이 PRD·Tasks·Blender 계약 복사) · LICENSE(Apache-2.0) · .gitignore · `git init -b main` | ✅ 1차 (+ CLAUDE.md, NOTICE, Docs/Spikes.md, tools/blender/export_chosang.py) |

## M1 · 블렌더 에셋 계약 · 내보내기 · 검증기
| ID | 작업 | 상태 |
|---|---|---|
| T-101 | `Docs/Blender-요청.md` 확정(사용자 검토) → 흉상 토폴로지(ARKit 1220 패치 + 두상·목·어깨), UV 레이아웃, 스켈레톤, 52 셰이프키, 라이브러리, 클립 목록, 좌표계 | ✅ 2차 계약 — 1차 변경 제안 9건 모두 수용(§8), 블렌더 쪽 할 일 §9 |
| T-102 | `tools/blender/export_chosang.py`: `Template.usdz`(+`bust.mesh` 폴백), `clips/<name>.json`, `template.json`(랜드마크 정점 id ↔ Vision 76, scalp 집합, UV 영역, 대칭 맵), `previz/<clip>.mp4` 일괄 렌더. Blender 4.1+/5.x, Apply Modifiers OFF | ✅ 2차 — Chosang_Template.blend(5.2) 헤드리스 4.5 s. 커스텀 속성 4개 → template.json(스키마 2)·bust.mesh v2(코너 UV)·library.json·clips(슬롯 액션, 끝 프레임 포함)·library/<name>.usdz. USD forward 축 함정: 'Z' → 얼굴 −Z(180° 요), **NEGATIVE_Z** 가 맞음(교차 검증 0.0 mm) |
| T-103 | `chosang-validate` CLI: 정점 수·패치 순서(OBJ 해시)·셰이프키 52 이름·범위·중립 0·스켈레톤 이름·라이브러리 명명·UV 범위·클립 fps/길이/루프 일치·previz 존재. 실패 항목을 블렌더 쪽 문장으로 출력 | ✅ 2차 — template.json 기준 허용 오차, Apple OBJ 사각형/삼각형 SHA-256, OBJ 위치 대조, UV 겹침(루프 UV 텍셀), 수염 bustIndex, 어깨 Root/Neck, 클립 frames=L+1, 프리비즈 카메라, `--with-usdz` RealityKit 교차 확인(솔기 분할 허용). 1차 산출물: 오류 1(Shoulders_shirt 없음) → 10/3 저녁 갱신본: **오류 0 · 경고 0** |
| T-104 | `BustTemplate` 로더: USDZ + `template.json` → 정점·인덱스·UV·델타·스킨·랜드마크·대칭 맵, 1회 캐시, 버전 해시 | ✅ 2차 — 기하 = bust.mesh(`TemplateStore`, 번들 `Default.chosangtemplate` 30 MB → Application Support 캐시 1회, 0.54 s), 에셋 = Template.usdz(눈알·입안; 엔티티 월드 변환 적용). 렌더 메시는 솔기 분할(11,569 → 11,931) |
| T-105 | 블렌더 1차 산출물(사용자, Blender MCP + Claude) 수령 → 검증기 통과 → `Resources/Templates/Default/` | ✅ 1차 수령·반입(`Chosang_Blender/`) → 10/3 저녁 갱신(귀 v2 · `Shoulders_shirt` · 프리비즈 7종 재렌더) 로 **검증기 통과**. `Chosang/Resources/Templates/Default.chosangtemplate` 재생성(30,259 KB) |
| T-106 | 시뮬레이터: 템플릿 로드 → 52 셰이프 슬라이더 패널 → 각 셰이프 단독 1.0 스냅샷 시트(ARKit 레퍼런스 포즈와 육안 비교) | ✅ 2차 — `sheet=1`(52 순환 1.2 s, 프리비즈 카메라) → `Docs/screenshots/m1-shape-sheet.png`(macOS GPU). 육안 비교 메모는 TechPRD §13. 11차: 시트 모드에 **끄기 버튼**과 **한 바퀴 자동 종료**를 넣었다 — 패널·하단 바를 숨기는 모드라 빠져나올 길이 없었다 |

## M2 · 캡처 (iPhone)
| ID | 작업 | 상태 |
|---|---|---|
| T-201 | `FaceCaptureSession`: ARSession 수명, 프레임 → `CaptureFrame`(RGB·깊이·intrinsics·transform·정점·가중치·조명), 60 Hz 중 8프레임 평균 | ✅ 5차 — M0 에 만든 세션에 미리보기(백그라운드 델리게이트 큐, 절반 해상도 포트레이트 CGImage)·정점 투영·조도 경고를 더하고 프로브는 첫 프레임 1회로. **포트레이트 회전 버그 수정**(아래 T-203). iPhone 16 실기기 동작. **17차 수정(M3 에서 발견)**: ARKit `BlendShapeLocation.rawValue` 는 좌우 36개가 `mouthSmile_L` 꼴인데 `ArkitShape(rawValue:)` 로만 받아 **좌우 셰이프가 전부 0 으로 저장**됐다(실기기 번들: 깜빡임·미소 0, `mouthShrug`·`jawOpen` 만 남음) → `ArkitShape(arkitName:)`(두 표기 수용). 🧪 재촬영: 중립도 게이트(1.2)는 좌우 셰이프가 빠진 채 맞춘 값이라 다시 볼 것. 🧪 깊이 카메라 보정(`AVDepthData.cameraCalibrationData`)을 번들에 저장 — TrueDepth 깊이가 메시보다 ~25 mm 가깝다(§28) |
| T-202 | `CaptureGuide` 5컷 상태 기계(정면 중립·좌·우·위·미소), 중립도·각도·조도 게이트, 0.7 s 유지 자동 촬영, 건너뛰기, 재촬영 | ✅ 5차 — `ChosangCapture/CaptureGuide`(순수 로직: 현재 스텝·유지 타이머·건너뛰기·재촬영·완료, 테스트 3개). 게이트는 소스(`passesGate`). **iPhone 16 실기기에서 5컷 자동 촬영 확인**(0.7 s·허용각 그대로 쓸 만함) |
| T-203 | 캡처 UI: 카메라 미리보기 + 얼굴 메시 와이어 오버레이(ARKit 정점) + 각도 링 + 조도 배너, 한국어 안내 음성(선택) | ✅ 8차 — iPhone `GuidedCaptureView`: 전체 화면 카메라 · 정점 오버레이 · 단계 칩(촬영분 썸네일) · 각도 링 · 조도 배너 · 셔터/건너뛰기/ⓘ 진단 · 햅틱 · 한국어 음성(`SpeechGuide`, 기본 꺼짐). **거울 미리보기 기본 꺼짐**(안내의 좌/우와 화면이 반대라 헷갈린다는 사용자 피드백). 실기기 수정 3건: ① 투영 회전(§16) ② **자세는 `portraitCameraTransform` 기준** — 런타임 `camera.transform` 은 가로라 그대로 쓰면 좌우 회전이 pitch 로 샌다(실측 yaw −0.8°/pitch −33.8°). 저장 메타는 이미 회전된 값이라 재사용 시 더 돌리지 않는다(§18·§19) ③ 게이트 완화(±9°/±8°, 중립도 1.2, 시선 8 + 깜빡임 2 제외) + 진단에 중립도 기여 상위 3개. 테스트 8개(`FacePoseTests`) ④ **yaw 부호 반전**(`FacePoseConvention`) — raw yaw 는 자기 오른쪽 회전이 +라 규약(+ = 내 왼쪽)과 반대였다. 저장값은 그대로 두고 가이드 각도만 뒤집는다(§20). 테스트 11개. **19차 게이트 완화**(사용자: "원에 딱 닿고 가만있어야만 인정"): yaw ±14°·pitch ±12°(사진 폴백 ±12/±10) · 유지 0.5 s · `CaptureGuide` 이탈 **유예 0.35 s** · 링 점선 = 실제 허용치 타원(§30). 🧪 iPhone 체감 |
| T-204 | `CaptureBundle` 저장/로드, `.chosangcapture` zip, 썸네일 | ✅ 5차 — 저장 시 **썸네일**(긴 변 256 JPEG, `meta.thumbFile`) 자동 생성, `read(loadImages: false)` 면 썸네일만 읽는다, `CaptureBundleStore.list()` 로 폴더 목록(최신순), 앱에서 `ShareLink` 로 `.chosangcapture` 내보내기(iPhone·Mac). 테스트 1개(생성·메타·압축 왕복·목록) |
| T-205 | 폴백 캡처(TrueDepth 없음·Mac): AVCapture + Vision 76점, 번들에 `sparse = true` | ✅ 3차 (10/3 밤) — `ChosangCapture/PhotoCaptureSession`(AVCapture 1080p BGRA → `DetectFaceLandmarksRequest(.revision3)` 76점 + yaw/pitch/roll, 8프레임 평균, 겹침 방지 플래그) + `ChosangCore/SparseFaceGeometry`(핵심점 좌/우는 이미지 x 로, yaw 부호는 코끝 치우침으로, pitch 는 Vision 부호 반전, 가정 FOV 60° intrinsics, 눈 간격·IPD 63 mm 로 깊이) + 앱 `PhotoCaptureView`(macOS 캡처 탭 · iOS 는 `FaceCaptureSession.isSupported == false` 면 자동 폴백 · 사진 파일 불러오기). `CaptureShotMeta` 에 `landmarks2D`·`keyPoints2D`·`faceBox`·`poseEstimate`·`intrinsicsEstimated`(옵셔널, 옛 번들 호환). `FaceFitter` 는 sparse 번들을 `FitError.sparseBundle` 로 거부. **Mac 실기기 확인**: FaceTime HD 1920×1080, 76점 추적, 5컷 촬영·번들 저장, 왼쪽 30° 게이트 통과(yaw +30.9°) → `Docs/screenshots/m2-macos-photo-capture.png`. 테스트 5개(`SparseCaptureTests`). 🧪 남은 것: iPhone 폴백 경로(시뮬레이터는 카메라 없음 → 파일 불러오기만), pitch 부호는 Mac 관측 1회(아래로 볼 때 −)라 iPhone 에서 재확인 |
| T-206 | 실기기: 5컷 자동 촬영 완주 3회, 번들 크기·시간, 안경/마스크 착용 시 중립도 게이트 동작 | 🔄 🧪 — iPhone 16(전면 TrueDepth): 5컷 완주·저장·내보내기 ✅, 번들 1컷당 JPEG 약 0.4 MB + 깊이 1.2 MB. 1차 임계값에서는 좌·우·위 자동 촬영이 안 걸렸고(수치 근거 TechPRD §18) 깊이가 5컷 중 1컷만 담겼다 → 둘 다 고쳐 재설치. 남은 것: 완주 3회·안경/마스크·깊이 5/5 확인 |
| T-207 | 실기기 번들 3세트 수집 → `Fixtures/capture-{a,b,c}.chosangcapture`(사용자 동의, 저장소에는 넣지 않고 로컬 보관 경로 문서화) | ⏳ 🧪 |

## M3 · 피팅
| ID | 작업 | 상태 |
|---|---|---|
| T-301 | `Procrustes`(스케일 포함), 표정 중립화(사용자 메시 − Σ 델타×가중치), 컷 평균 | ✅ 17차 — M0 `FaceFitter` 1–2단계를 `ChosangFit/FacePatchSolver` 로 분리(`PatchSolution`: 사용자 패치·컷별 정렬 `alignments`(미소 포함)·컷별 RMS·s·눈알). 합성 셀프 피팅 패치 RMS 0.011 mm, 실기기 0.66–0.96 mm |
| T-302 | `FacePatchSolver`: 패치 치환, 스케일 `s`, 눈알 중심·반지름 추정(눈꺼풀 정점 링 피팅) | ✅ 17차 — `patchLoops.eye_left/right`(24점) 고리: Newell 법선·평면 반지름 ρ → 사전값(중심 = 고리 중심 − n·√(r²−ρ²), r = manifest×s) + 대수적 구 피팅(`Core/Math/SphereFit`)은 사전값과 모순 없을 때만 절반 반영. 고리가 거의 평면이라 구가 한 매개변수만큼 자유로워(ill-posed) 사전값이 필수. 결과는 `FitQuality.eyeFit`("ring"/"prior"/"landmark"/"manifest"). 실기기·합성 모두 prior 채택(구면 위 고리 테스트는 ring) |
| T-303 | `HeadPropagator`: 바이하모닉 RBF(경계 200 + 내부 100), Neck 감쇠, 어깨 스케일, 좌우 대칭 70% | ✅ 1차(M0) + 17차: `BiharmonicRBF` 입력 좌표 정규화(중심 무게중심·평균 거리) — m 단위 r³(≈1e-5)와 다항식 블록 1 이 섞여 중심이 적을 때 피벗비가 1e12 를 넘어 불필요한 λ 가 들어갔다. 보간은 평행이동·균일 스케일 불변이라 결과 동일, 조건만 개선(셀프 피팅 피벗비 8.1e6 → 8.1e4). `neckWeight` 공개(실루엣·희소가 공유) |
| T-304 | `SilhouetteFitter`: 깊이 → 포인트 클라우드(흉상 공간), 두피·귀·턱선 정점 당김(≤12 mm, GN 5회, 라플라시안 λ 0.1), 머리카락 포인트 제외(색 기준) | ✅ 17차 — `ChosangFit/SilhouetteFitter` + `Core/Math/ConjugateGradient`(야코비 PCG, 연산자 클로저). 계약대로 GN 5회·≤12 mm·λ 0.1 에 **셋을 더해야 돌았다**: ① 포인트 법선(깊이 중심 차분, 기준선 4 mm)과 정점 법선 코사인 ≥ 0.7 — 접힘(턱 밑 주름)의 다른 면 포인트 배제 ② **접선 고정 μ=1** — 점-평면 제약은 면 안 미끄러짐을 못 막아 1 mm 당김이 이웃 3–4 mm 미끄러짐이 됐다 ③ **깊이 → ARKit 메시 정합**(`DepthRegistration`, 컷별 상수 오프셋; 실기기 TrueDepth 가 메시보다 −21 … −30 mm). 두피 머리카락 = 컷별 피부 기준색(패치 정점이 찍힌 픽셀) 대비 색도·밝기. 실기기: 잔차 중앙값 1.6 mm · 대응 899 정점(목 552 · 턱 밑 223 · 귀 38 · 두피 86 — 머리카락). **19차 목 보정**(§30): 목도 피부색 포인트에만 대응 · 목 λ ×10(Lᵀ Λ L) · 목 최대 당김 6 mm — 셔츠 깃·머리카락·수염 잡음에 당겨진 세로 물결 제거(실기기 렌더 확인) |
| T-305 | 델타 보정(패치 그대로·밖은 `s`·`jawOpen` 진폭), `Identity` 직렬화 `identity.bin` | ✅ 17차 — `DeltaCalibrator.jawOpen`: 미소 컷(정렬) 관측 − 다른 셰이프 예측을 w·Δ_jaw 에 최소제곱 투영(턱 영역 = \|Δ\| ≥ 30 % max, w ≥ 0.08, 0.5–2.0 클램프). `Identity.shapeScales`(**identity.bin v2**, v1 읽기 호환) + `patchDeltas[.jawOpen]`; `runtimeDeltas` 가 패치 밖에 s×비율. 합성 1.3배 사용자 → ×1.323 복원, 미소 잔차 0.18 mm. 실기기 번들은 jawOpen 0.05 라 보정 안 함 |
| T-306 | 희소 폴백(Vision 76 ↔ `template.json` 랜드마크, 3D TPS) | ✅ 17차 — `ChosangFit/SparseFitter`: 정면 컷 `keyPoints2D` 8점(+`visionIndices` 가 있으면 76점) → 템플릿을 "눈 간격이 사진과 같아지는 깊이" 에 두고 각 랜드마크를 **같은 카메라 깊이에서 관측 픽셀 광선 위로** 옮긴 변위 → 좌우 대칭(랜드마크 단계) → 바이하모닉 r³(3D TPS) + 랜드마크 거리 감쇠 σ 8 cm + 목 감쇠. **s = 1 고정 — 단안 사진은 절대 크기를 알 수 없다**(형상은 눈 간격 대비 비율). `FaceFitter.fit` 이 sparse 번들을 자동 분기(`FitError.sparseBundle` 거부 제거), 랜드마크 부족은 `sparseInsufficientLandmarks`. 합성 턱 8 mm 연장 → 8.00 mm 복원(관측 "눈 중심" 은 코너 픽셀 평균이라 원근으로 ~1 % 좁다 — 템플릿 코너를 같은 식으로 투영해 깊이·중점을 반복 보정, 보정 전 9.03 mm). 🧪 Mac 실제 희소 번들로 육안 확인 |
| T-307 | 테스트: 합성 번들 셀프 피팅 RMS < 0.2 mm, 픽스처 3세트 패치 RMS < 1.5 mm·실루엣 잔차 중앙값 < 3 mm, 품질 지표 기록 | ✅ 합성(`FitTests` 11개): 셀프 전체 RMS 0.088 mm(실루엣 포함) · 섭동 두상 오차 1.92 → 1.89 mm(p90 2.70 → 2.68) · jawOpen · 희소 · 미소 렌더 · 구 피팅 · CG · ARKit 이름. 실기기 1세트(저장소 밖, `--fit`): 패치 RMS 0.96 · 실루엣 잔차 1.6 mm. 수치는 TechPRD §28. 🧪 **픽스처 3세트는 T-207 수집 후**(지금 번들은 좌우 셰이프가 0 인 M2 버그 번들) |
| T-308 | 미소 컷 검증 렌더(캡처 가중치 그대로) ↔ 사진 나란히 — 검수 화면 1차 | ✅ 17차 — `ChosangTexture/SmileVerification`: 미소 컷 가중치로 변형한 렌더 메시를 그 컷의 카메라(템플릿 공간)로 CPU 래스터(알베도 + 캡처 조명 방향) → 사진과 같은 크기, 나란히. 앱 미리보기 패널·iPhone 정보 시트에 "미소 검증" 두 장 + 캡션(가중치 합·상위 셰이프·잔차), CLI `--fit <번들> <out.png>`. 수치 지표 `smileResidualRMS`(변형 패치 vs 미소 ARKit 메시) + `smileNeutralRMS`(표정 없이) — 실기기 6.83 vs 6.89 mm: 번들에 좌우 셰이프가 없어(M2 버그) 미소가 `mouthShrug` 로만 기록돼 판정 보류. 🧪 수정 빌드로 재촬영 후 셰이프키 손질 우선순위(Blender §9-5) |

## M4 · 텍스처
| ID | 작업 | 상태 |
|---|---|---|
| T-401 | Metal: UV 공간 래스터(텍셀 → 위치·법선), 컷별 깊이 버퍼 렌더, 가시성 가중치 w | ✅ 18차 — `ChosangTexture/TextureBuilder`(5단계) + `TexelRaster`(삼각형 id + 무게중심 UInt16 = 8 B/텍셀, 부표본 n×n) + `Shaders/TextureKernels.metal`·`MetalTextureBackend`(리소스 소스를 런타임 컴파일, 없으면 CPU). 가시성 = 투영·cos>0.08·**자기 가림**(컷 카메라에서 변형 메시 깊이 버퍼 1/2 해상도 렌더)·**캡처 깊이**(`DepthRegistration` 으로 메시에 정합 → 허용치 35 → 15 mm 복귀, 깊이 없는 픽셀 = 배경 거부)·w = cos³ × 가장자리 × exp(−Δz²/tol²) × 페더. CPU↔Metal 256² 패리티 **평균 차 0.000/255**. 11차 1차(`CaptureTexturing`, 512² CPU)는 `--texture legacy=1` 로 남김 |
| T-402 | 다시점 투영 가중 평균 4096² RGBA16F, 미소 컷 입 주변 제외 마스크 | ✅ 18차 — 밴드(≈1M 텍셀) 단위 누적(float 누산 → RGBA8 출력; RGBA16F 저장은 안 함 — PNG 8비트 패키지라 이득 없음), 미소 컷 입 UV 반경 0.12 제외. 실기기 2k Metal **1.0 s**(CPU 2.5 s), 4k **2.0 s** |
| T-403 | 저주파 색 보정(32×32 격자 최소제곱) + 2 px 페더 접합 | ✅ 18차 — `TextureSeams`: 저해상도(256²) 투영에서 컷별 셀 평균 μ·가중치 W → 게인 g_s(c)(RGB) 최소제곱(겹침 쌍 + 이웃 평활 + 사전항, 정면 컷 앵커 λ 0.5) 을 `ConjugateGradient` 로. 합성 ±10 % 노출 → 단차 14.0 → 0.8/255. 실기기 31.4 → 8.4/255(저주파만 보정; 나머지는 정반사·정합 오차). 페더는 **저해상도 2셀**(2k 에서 16 텍셀) — 전체 해상도 2 px 는 두 번 지나야 해 생략, 넓은 페더가 접합에 더 낫다 |
| T-404 | 탈조명(주광 방향·강도 → 램버트 역보정, 슬라이더), 뺨 기준 재정규화 | ✅ 18차 — `TextureLighting`: ARKit 방향 대신 **얼굴에서 추정**(패치 정점 밝기 b ≈ a + d·n, 피부 색도 표본만, 그늘·이상치 제외 3회 반복) → 방향 ℓ + **주변광 비율 f = a/(a+|d|)**(컷 중앙값으로 통일). shade = f + (1−f)·max(0, n·ℓ)(밝은 면 = 1 → 그늘만 밝힌다). 합성: 방향 오차 0.8°, f 0.35(정답 0.35). 슬라이더 0 = 원본(테스트). **뺨 재정규화는 기본 끔** — 스칼라 램버트는 색도를 못 바꾸고 이 보정은 밝힌 그늘을 도로 어둡게 할 뿐(PSNR 20 → 13 dB) |
| T-405 | 채움: 대칭 복사 → pull-push 확산 → 두피 머리카락색; `mask.png` 출력 | ✅ 18차 — `TextureFill`: 대칭 복사는 **정점 단위 거울 UV**(거울 사각형이 반대 대각선으로 삼각분할돼 삼각형 매칭은 80/13360 뿐) → 13303/13360, 합성 정면+왼쪽 번들에서 오른쪽 뺨 복사 오차 2.6/255. 두피 = 관측 두피 텍셀 평균색(실기기 (95,76,56)). pull-push 는 S/2 피라미드(메모리 1/4). mask R/G/B = 관측/대칭/채움 |
| T-406 | 피부 가이드 양방향 필터, 눈 흰자·치아·입안 라이브러리 텍스처 명도 맞춤 | 🔄 18차 — 양방향 필터(σ_s 3 텍셀 · σ_c 0.08, 가로·세로 분리 근사, 얼굴 UV 영역의 관측·대칭 텍셀만) CPU + Metal. 눈 흰자·치아·입안 명도 맞춤은 **M5 라이브러리 부착 때**(EyesMouth.usdz 머티리얼을 만질 때 피부 명도로). **19차 얼굴 밖 정리**(`TextureRegions`, §30): 목·귀·머리 옆은 얼굴 피부 기준색 게이트 + 저주파화(σ 24 텍셀@2k), 두피는 하이라이트 제거 + 저주파화, LidInner/LipInner 는 관측 무시하고 피부·입술색으로 — 실기기 렌더의 목·눈 조각 제거. 테스트 4개 |
| T-407 | 2k/4k 설정, PNG 인코딩, 빌드 진행률(5단계) 콜백 | ✅ 18차 — `TextureBuildOptions.preset(size:)`, `TextureProgress`(단계·0…1) → 앱 패널 ProgressView, 앱에 **탈조명 슬라이더 · 2k/4k 피커 · "텍스처 다시 만들기"**(`AppModel.rebuildTexture`, 피팅 재사용), manifest `delightStrength`. 실기기(Mac M3) 2k 1.0 s / 4k 2.0 s |
| T-408 | 테스트: 합성 번들에서 알베도 ↔ 원본 텍스처 PSNR > 32 dB(관측 영역), 픽스처 관측 비율 > 70%, 접합선 색 단차 < 3/255 | ✅ 18차 — `TextureBuilderTests` 6개: 대역 제한 알베도(`SyntheticAlbedo.smooth`) **37.2 dB**(계단 알베도도 35.7), 관측 78 %, 접합 0.8/255, 탈조명 0 = 원본(비트 동일), 조명 추정 0.8°, 대칭 복사, Metal 패리티. 함정: 합성 템플릿 뒤통수는 정점 UV 와 코너 UV 가 u 축 1.31배 달라 합성 캡처 렌더를 렌더 메시(코너 UV)로 통일(얼굴 40 dB·두상 18 dB 였던 원인). 실기기 1세트 관측 83 %(목표 70) — 픽스처 3세트는 T-207 뒤 |
| T-409 | 실기기: iPhone 15 Pro 빌드 시간 < 60 s, 발열·메모리 | ⏳ 🧪 |

## M5 · 런타임 리그 · 클립 · 상황
| ID | 작업 | 상태 |
|---|---|---|
| T-501 | `BustEntity`: 템플릿 → `Identity` 치환 `LowLevelMesh`, `LowLevelDeformation` 매 프레임, PBR 머티리얼, 눈알·입안·라이브러리 자식(Head 뼈 부착) | ⏳ |
| T-502 | 폴백 경로(`MeshDeformerComponent` 또는 CPU 블렌드) + 자동 선택·UI 표시 | ⏳ |
| T-503 | `FaceRigSystem` 이식(externalWeights·비셈 큐·깜빡임·시선) → 블렌딩 가중치 버퍼 | ⏳ |
| T-504 | `ClipPlayer`: `clip.json` 로드·보간·루프·크로스페이드 250 ms; 뼈 트랙 경로(T-006 결정) | ⏳ |
| T-505 | 레이어 합성 규칙(클립 ⊕ 라이브 표정 영역 치환 ⊕ 비셈 가산 ⊕ 깜빡임, 뼈 가산·look-at ±25°) | ⏳ |
| T-506 | `SituationDirector` 상태 머신 + `SituationInput`(내 음성 레벨·상대 음성 레벨·이벤트), 소반 `Participant` 매핑 예시 | ⏳ |
| T-507 | 외형 라이브러리 부착: `Hair_<id>` 틴트(평균색·하이라이트)·두피 라인 스케일, `Glasses`, `Shoulders`; `AppearanceAnalyzer` 자동 선택 + 피커 | ⏳ |
| T-508 | 미리보기 뷰(3 플랫폼): 턴테이블, 클립 선택, 라이브 표정(iPhone ARKit)/마이크 비셈, 거울(visionOS) | ⏳ |
| T-509 | 성능: 흉상 2개 90 Hz(Vision Pro), GPU 변형 < 1 ms, 템플릿 캐시 후 로드 0.5 s | ✅ 🧪 12차 실기기 — 흉상 1개 기준 **`LowLevelDeformation (GPU)` · 변형 0.09 ms · 11.1 ms/90 fps · 템플릿 로드 0.24 s**. 모두 목표 충족. 흉상 2개 동시는 M5 에서 |

## M6 · 패키지 · 전송 · 내보내기 · 소반 어댑터
| ID | 작업 | 상태 |
|---|---|---|
| T-601 | `.chosang` 쓰기/읽기(manifest schema 1, identity.bin, albedo, mask, thumb), 템플릿 id·버전 검사, 캡처 번들 동봉 옵션 | ✅ 11차 — 미리보기 패널 **".chosang 저장"** → `AppModel.savePersona()`(manifest + identity.bin + albedo/mask) → zip, 그 자리에서 `ShareLink` 내보내기. 읽기는 받기 화면 "미리보기에서 열기"(`loadPersona`, 템플릿 id·정점 수 검사). 썸네일·캡처 번들 동봉은 남음 |
| T-602 | `PersonaLibrary`: `Documents/Personas/<uuid>/`, 활성, 이름 변경, 삭제, 재빌드(번들 있으면) | 🔄 6차 1차 — `ReceivedStore`(`Documents/Received/`, 이름 충돌 회피, 목록) + 받은 목록 UI + 받은 `.chosang` 을 미리보기에 적용(`AppModel.loadPersona`, 템플릿 id·정점 수 검사). 이름 변경·삭제·재빌드는 남음 10차: 받은 캡처 번들에 **"흉상 만들기"** 버튼(→ `AppModel.buildPersona(fromCapture:)` → `FaceFitter` → 미리보기), 미리보기 패널에 피팅 품질·"템플릿 원본으로" |
| T-603 | 전송: Network.framework `NWListener/NWBrowser/NWConnection`, Bonjour `_chosang._tcp`, TLS PSK 6자리, 청크·진행률·재개 | ✅ 6차 — `ChosangIO/ChosangTransfer`: `TransferFraming`(4바이트 BE 길이 + 헤더 JSON + 본문, 상한·검증), `ChosangReceiver`(광고·코드·진행률·저장), `ChosangSender`(검색·64 KB 청크·진행률), TLS PSK(`sec_protocol_options_add_pre_shared_key` + `TLS_PSK_WITH_AES_128_GCM_SHA256`), `includePeerToPeer`. 앱 "주고받기" 탭(`TransferView`) 전 플랫폼. **Mac 루프백 실측**: 광고 → 발견 → 300 KB 전송 1.1 s, 틀린 코드는 거부(테스트 2개). 재개(이어받기)는 미구현 |
| T-604 | 문서 열기: `fileImporter`·`onOpenURL`·AirDrop `.chosang`/`.chosangcapture` | ✅ 13차 — `onOpenURL` → `AppModel.open(_:)`(확장자로 갈라 페르소나 적용 / 캡처 피팅 → 미리보기). Info.plist 에 `UIFileSharingEnabled`·`LSSupportsOpeningDocumentsInPlace` 를 넣어 **파일 앱에서 앱 Documents 가 보인다**(저장 경로를 못 찾던 문제) |
| T-605 | `.sobanpersona` 내보내기 어댑터(정면 렌더 → body.png, 리그 좌표, `chosangRef`) | ⏳ |
| T-606 | USDZ 내보내기(macOS, T-005 결과대로), 3DGS PLY 는 v2 | ⏳ |
| T-607 | `ChosangSobanAdapter` 패키지: `ChosangBustAvatar: TableAvatar`(소반 프로토콜 복제본 기준), 소반 쪽 통합은 **별도 PR 로 소반 리포에서** | ⏳ |
| T-608 | 실기기: iPhone → Vision Pro 전송(12 MB) 시간, 코드 입력, 수신 후 로드 | ✅ 10차 — iPhone 에서 캡처 번들을 보내 **Vision Pro 가 받았다**(코드 6자리, `Documents/Received/`). 받은 번들로 **그 자리에서 밀집 피팅까지** 성공: 컷 4 · 패치 RMS **0.93 mm** · 0.4 s · 스케일 1.106. 전송 시간·12 MB 급 측정은 다음에 |

## M7 · 검수 화면 · 품질
| ID | 작업 | 상태 |
|---|---|---|
| T-701 | 프리비즈 비교(macOS·visionOS): AVPlayer ↔ 같은 카메라 렌더, 스크럽 동기화, 프레임 카운터, 차이 오버레이 | 🔄 카메라 프리셋만(2차): `PrevizCameraSpec.contract` 조준 (0,0.41,0.09)·위치 (0,0.41,1.29)·hFOV 39.6°(세로 22.9°)·16:9 — 미리보기 토글 `previz=1`. 비교 화면은 M7 |
| T-702 | 품질 카드(RMS·잔차·관측 비율·채움 비율·빌드 시간) + 임계 미달 경고·재촬영 안내 | ⏳ |
| T-703 | 렌더 스냅샷 회귀(정면·좌 30°, 픽셀 차이 < 2%) 를 테스트 타깃에 | ⏳ |
| T-704 | 접근성 라벨, 앱 아이콘, 한국어 문구 통일 | ⏳ |
| T-705 | 실기기 체크리스트(아래) 전항 통과 | ⏳ 🧪 |

## M8 · v2 — 메시 바인딩 스플랫
| ID | 작업 | 상태 |
|---|---|---|
| T-801 | 스플랫 바인딩 포맷(삼각형 id·무게중심·법선 오프셋·국소 회전), 변형 정점 → 스플랫 갱신 Metal 커널, `GaussianSplatResource` 버퍼 재기록 | ⏳ v2 |
| T-802 | 초기화(`mask.png` 관측 텍셀 + 머리카락 2겹) | ⏳ v2 |
| T-803 | 미분 가능 래스터라이저(Metal, 색·불투명도·스케일·오프셋만), 5컷 손실, 200 반복 < 90 s | ⏳ v2 |
| T-804 | 렌더 전환(메시 ↔ 스플랫), 시뮬레이터 폴백, PLY 내보내기 | ⏳ v2 |

## 블렌더 쪽 할 일 (2차 계약 §9 요약)
1. ~~`Shoulders_shirt` 오브젝트 추가(Library_Shoulders, Root/Neck 스킨) → 검증기 오류 0.~~ ✅ 10/3 저녁 반영.
2. (선택) `chosang_landmarks` 에 brow_inner_left/right.
3. 후속: 셰이프키 손질(funnel·pucker·press), 이마 이음 능선, 수염 경계 계단. 귀는 v2(`build/ears.py`, 실제 윤곽 스플라인·높이별 돌출각, 위상 동일) 로 반영됨 — 연골 주름은 여전히 단순.

## 실기기 체크리스트 (M0 — 🧪 지금 바로 확인 가능)
0. iPhone(TrueDepth): 캡처 탭 → 세션 시작 → "T-007 프로브" 에 정점 1220 · 삼각형 수 · 해시 · 깊이 640×480 DepthFloat32 · intrinsics · 조명 방향 표시 → 값을 `Docs/Spikes.md` T-007 과 `ARKitFaceTopology.referenceTriangleHash` 에 기록. 5컷 촬영 → 번들 저장 → 크기·시간.
0b. Vision Pro / iPhone 실기기: 미리보기 탭 "변형 경로" 가 `LowLevelDeformation (GPU)` 인지, 클립 `laugh` 재생 중 변형 ms·fps.
0d. ✅ iPhone 16(10/3 밤): 캡처 탭 가이드 화면 동작 — 게이트 통과 시 "유지하세요"·링 차오름·자동 촬영, 정면 완료 후 왼쪽 30° 안내로 전환(`Docs/screenshots/m2-iphone16-*.png`). 발견: 정점 오버레이가 턱 아래로 어긋남 → 포트레이트 회전 수정(T-203).
0e. 🧪 iPhone 16 재확인(회전 수정 후): 정점 오버레이가 얼굴에 붙는지, ⓘ 진단의 T-007 프로브 값(삼각형 해시·깊이 해상도·조명)을 `Docs/Spikes.md` T-007 과 `ARKitFaceTopology.referenceTriangleHash` 에 기록, 5컷 저장 번들 크기·시간.
0f. ✅ Vision Pro 실기기: 수신(T-608) · 받은 캡처로 피팅 · **텍스처까지 성공**(관측 83 %, 얼굴 제자리) · GPU 변형 0.09 ms · 90 fps · 2D 창 표시. 남은 것: 흉상 2개 동시 90 Hz.
0g. 🔄 🧪 iPhone 16(전면 TrueDepth, **9차 빌드 설치됨**): ① 좌·우·위 세 컷이 **자동으로** 찍히는지(왼쪽으로 돌리면 왼쪽 컷이 반응해야 한다), ② 5컷 모두 깊이가 담기는지, ③ 각도 링의 점이 고개 방향과 같은 축으로 움직이는지(거울 기본 꺼짐). 막히면 ⓘ 진단의 **중립도 기여 상위 3개**와 yaw/pitch 를 본다. 콘솔: `xcrun devicectl device process launch --device <UDID> --console --terminate-existing com.coulson.Chosang tab=capture` — 촬영마다 `자동/수동`·목표 대비 각도·중립도·깊이가 찍힌다.
0h. 🧪 **M3 재촬영(iPhone 16, 17차 빌드)**: ① ⓘ 진단의 상위 셰이프에 `eyeBlink_L`·`mouthSmile_L` 같은 좌우 셰이프가 뜨는지(17차 전에는 전부 0) ② 중립도 게이트가 좌우 셰이프를 더해도 정면·좌·우·위 컷을 통과시키는지(안 되면 `CaptureGate.neutrality` 상향) ③ 미소 컷에서 `mouthSmile_L/R` 이 0.5 이상 ④ 그 번들로 `swift run -c release chosang-validate --fit <번들> /tmp/smile.png` → 미소 잔차가 "표정 없이" 보다 작아야 한다(크면 템플릿 셰이프키 손질, Blender §9-5) · jawOpen 비율 · 실루엣 대응 수(귀) 기록 → `Fixtures` 대신 로컬 보관(T-207).
0i. 🧪 **19차 iPhone 16**: ① 캡처 탭에서 좌·우·위 컷이 링 점선 타원 안에서 0.5 s 안에 자동으로 찍히는지(잠깐 흔들려도 호가 유지되는지) ② 미리보기 ⓘ → "텍스처 다시 만들기" 뒤 목·귀·눈꺼풀 안쪽이 매끈한 피부톤인지(조각·흰 깃·하이라이트 없음), 두피는 머리카락색 ③ 품질 카드의 관측 비율은 76 % 그대로여야 한다 ④ 받은 번들로 흉상을 **다시 만들면**(피팅 변경) 목이 매끈한지(세로 물결 없음).
0c. ✅ Mac 실기기(T-205): 캡처 탭 → 카메라 권한 허용 → 76점 추적·5컷·번들 저장 확인(10/3 밤, MacBook Air FaceTime HD). 🧪 iPhone 16 실기기: 캡처 탭 화면(T-007 프로브 값 포함)을 `Docs/screenshots/m2-iphone16-truedepth-capture.png` 로 저장 → README 표 빈 칸. 🧪 iPhone 에서 pitch 부호(턱 들면 + 여야 함)·`videoFieldOfView` 로 `intrinsicsEstimated = false` 가 되는지.

## 실기기 체크리스트 (v1)
1. iPhone: 초상 캡처 → 5컷 자동 촬영 → 빌드 60 s 이내 → 미리보기에서 턴테이블·클립 `bow`·라이브 표정(내 얼굴 따라 움직임).
2. iPhone: 미소 검증 화면에서 사진과 렌더의 입꼬리·눈 모양이 일치.
3. iPhone → Vision Pro: 코드 입력 전송 → 거울에서 고개·입(마이크)·클립 `idle_breathe` 확인.
4. Mac: `chosang-validate Template.usdz` 통과, 비교 검수에서 `laugh` 클립 프레임 동기, USDZ 내보내기 → Quick Look.
5. 소반(별도): `.sobanpersona` 내보낸 파일을 소반 스튜디오에서 열어 두레반 착석.
