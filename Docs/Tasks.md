# 초상 (Chosang) — Tasks

상태: ✅ 완료 · 🔄 진행 · ⏳ 대기 · 🧪 실기기 검증 필요 · 🔬 스파이크(결과에 따라 설계 분기)

원칙: **M0 스파이크 4개가 끝나기 전에는 M3 이후 구현을 시작하지 않는다.** 각 마일스톤 끝에 4개 빌드(visionOS 기기·시뮬, iOS 시뮬, macOS) 통과 + 해당 체크리스트.

## M0 · 프로젝트 셋업 · 스파이크
| ID | 작업 | 상태 |
|---|---|---|
| T-001 | Xcode 프로젝트 `Chosang`: 단일 앱 타깃 3 플랫폼(xros/xrsimulator/iphoneos/iphonesimulator/macosx, family 1,2,7), 번들 `com.coulson.Chosang`, 배포 visionOS 27 · iOS 26 · macOS 26, 자동 서명 팀 5Z8G42AVKD, 엔타이틀먼트 없음 | ✅ 1차 — Xcode 타깃 이름은 `MyApp`(자동 생성), 제품/표시 이름 Chosang/초상. macOS 샌드박스 카메라·오디오 입력·네트워크(빌드 설정) |
| T-002 | 로컬 Swift Package `ChosangKit`(타깃: Core·Fit·Texture·Rig·Capture·IO·Validate, 테스트 타깃), 앱이 의존 | ✅ 1차 — + `chosang-validate` 실행 타깃. 함정: Xcode 가 프로젝트를 다시 저장하면 외부에서 넣은 패키지 참조가 지워진다(pbxproj 재적용 필요) |
| T-003 | Info.plist: 카메라(ARKit 얼굴 데이터 사용 고지)·로컬 네트워크·Bonjour `_chosang._tcp`, UTI `com.coulson.chosang.persona`/`.chosangcapture`, 문서 타입 | ✅ 1차 (+ 마이크 고지) |
| T-004 | 🔬 `Entity(named:)` 로 로드한 USDZ 의 `MeshResource.contents` 에서 `blendShapeOffsets(named:)` 52개·스킨 가중치·조인트가 읽히는지(소반 `DemoAvatar_Ethan.usdz` 로 즉시 확인). 안 되면 `bust.mesh` 경로 확정 | ✅ 1차 — 결과는 `Docs/Spikes.md` T-004. 결정: USDZ 를 1차 경로로 쓰되 `bust.mesh` 를 **항상 함께** 내보내 검증기가 교차 확인 |
| T-005 | 🔬 macOS ModelIO `MDLAsset.canExportFileExtension("usdz"/"usdc")` 와 실제 내보내기(메시+텍스처). 안 되면 자체 USDA+zip 설계 | ✅ 1차 — usdz ✗ · usdc/usda ✓ → **usdc + 자체 ZipArchive(64 B 정렬)** 로 usdz. `ChosangIO/USDExport`, `ZipArchive` |
| T-006 | 🔬 `LowLevelMesh` + `LowLevelDeformation`(blending 52 · skinning 5 · renormalizing) 를 소반 흉상에 적용해 시뮬레이터·Mac 에서 60 fps 확인. 뼈 클립을 `AnimationGraphResource` 로 돌릴지 자체 샘플러로 돌릴지 결정 | ✅ 1차 — **시뮬레이터 SDK 에 `LowLevelDeformation` 없음**(GaussianSplat 과 같은 패턴) → 기기·Mac 은 GPU, 시뮬레이터는 CPU 폴백. 뼈 클립 = 자체 `ClipPlayer`. 수치는 `Docs/Spikes.md` |
| T-007 | 🔬 iPhone: `ARFaceTrackingConfiguration` 에서 `capturedDepthData`·`intrinsics`·`faceAnchor.geometry.vertices`·`lightEstimate` 를 한 프레임에서 동시에 얻어 저장. 정점 수 1220·삼각형 해시 기록. Apple 샘플 `ARFaceGeometry.obj` 와 정점 순서 일치 확인 | 🧪 코드·절차 준비됨 — `ChosangCapture/FaceCaptureSession`(`ARFaceProbeReport`) + 앱 캡처 탭. 실기기 절차는 `Docs/Spikes.md` T-007 |
| T-008 | 소반에서 이식: `ArkitBlendShapes.swift`(52 이름·가중치·비셈 프리셋·어댑터), `HangulViseme`, `ThinPlateSpline`(폴백용), `AppearanceHints`(FoundationModels + 휴리스틱). 소반 리포는 **수정하지 않는다** | ✅ 1차 — Core(ArkitBlendShapes·HangulViseme·TPS) · Fit(AppearanceHints, 7개 분류로 확장) · Capture(MicLevelMeter) · Rig(FaceRig). 소반 리포 미수정 |
| T-009 | Fixtures: 소반 USDZ 흉상을 임시 템플릿으로, 합성 캡처 번들 1세트(템플릿 자체를 가상 카메라 5대로 렌더한 RGB·깊이·정점) → 파이프라인 끝까지 통과하는 "셀프 피팅" 테스트 | ✅ 1차 — 소반 USDZ 에는 셰이프·패치가 없어 **절차적 합성 템플릿**(`SyntheticTemplate`, 1220 패치 + 52 델타)으로 대체. `Fixtures/synthetic-{template,perturbed}.chosangcapture`, 셀프 피팅 RMS 0.011 mm, 섭동 피팅 패치 0.0005 mm·두상 중앙값 1.9 mm, CPU 텍스처 PSNR 24 dB(기준선 22) — `SelfFitTests` |
| T-010 | README · Docs(이 PRD·Tasks·Blender 계약 복사) · LICENSE(Apache-2.0) · .gitignore · `git init -b main` | ✅ 1차 (+ CLAUDE.md, NOTICE, Docs/Spikes.md, tools/blender/export_chosang.py) |

## M1 · 블렌더 에셋 계약 · 내보내기 · 검증기
| ID | 작업 | 상태 |
|---|---|---|
| T-101 | `Docs/Blender-요청.md` 확정(사용자 검토) → 흉상 토폴로지(ARKit 1220 패치 + 두상·목·어깨), UV 레이아웃, 스켈레톤, 52 셰이프키, 라이브러리, 클립 목록, 좌표계 | ✅ 2차 계약 — 1차 변경 제안 9건 모두 수용(§8), 블렌더 쪽 할 일 §9 |
| T-102 | `tools/blender/export_chosang.py`: `Template.usdz`(+`bust.mesh` 폴백), `clips/<name>.json`, `template.json`(랜드마크 정점 id ↔ Vision 76, scalp 집합, UV 영역, 대칭 맵), `previz/<clip>.mp4` 일괄 렌더. Blender 4.1+/5.x, Apply Modifiers OFF | ✅ 2차 — Chosang_Template.blend(5.2) 헤드리스 4.5 s. 커스텀 속성 4개 → template.json(스키마 2)·bust.mesh v2(코너 UV)·library.json·clips(슬롯 액션, 끝 프레임 포함)·library/<name>.usdz. USD forward 축 함정: 'Z' → 얼굴 −Z(180° 요), **NEGATIVE_Z** 가 맞음(교차 검증 0.0 mm) |
| T-103 | `chosang-validate` CLI: 정점 수·패치 순서(OBJ 해시)·셰이프키 52 이름·범위·중립 0·스켈레톤 이름·라이브러리 명명·UV 범위·클립 fps/길이/루프 일치·previz 존재. 실패 항목을 블렌더 쪽 문장으로 출력 | ✅ 2차 — template.json 기준 허용 오차, Apple OBJ 사각형/삼각형 SHA-256, OBJ 위치 대조, UV 겹침(루프 UV 텍셀), 수염 bustIndex, 어깨 Root/Neck, 클립 frames=L+1, 프리비즈 카메라, `--with-usdz` RealityKit 교차 확인(솔기 분할 허용). 1차 산출물: 오류 1(Shoulders_shirt 없음) |
| T-104 | `BustTemplate` 로더: USDZ + `template.json` → 정점·인덱스·UV·델타·스킨·랜드마크·대칭 맵, 1회 캐시, 버전 해시 | ✅ 2차 — 기하 = bust.mesh(`TemplateStore`, 번들 `Default.chosangtemplate` 30 MB → Application Support 캐시 1회, 0.54 s), 에셋 = Template.usdz(눈알·입안; 엔티티 월드 변환 적용). 렌더 메시는 솔기 분할(11,569 → 11,931) |
| T-105 | 블렌더 1차 산출물(사용자, Blender MCP + Claude) 수령 → 검증기 통과 → `Resources/Templates/Default/` | 🔄 1차 수령·반입(`Chosang_Blender/`) — 검증기 오류 1건(Shoulders_shirt) 남음. 통과 전이지만 `Default.chosangtemplate` 로 앱에 들어감 |
| T-106 | 시뮬레이터: 템플릿 로드 → 52 셰이프 슬라이더 패널 → 각 셰이프 단독 1.0 스냅샷 시트(ARKit 레퍼런스 포즈와 육안 비교) | ✅ 2차 — `sheet=1`(52 순환 1.2 s, 프리비즈 카메라) → `Docs/screenshots/m1-shape-sheet.png`(macOS GPU). 육안 비교 메모는 TechPRD §13 |

## M2 · 캡처 (iPhone)
| ID | 작업 | 상태 |
|---|---|---|
| T-201 | `FaceCaptureSession`: ARSession 수명, 프레임 → `CaptureFrame`(RGB·깊이·intrinsics·transform·정점·가중치·조명), 60 Hz 중 8프레임 평균 | ⏳ |
| T-202 | `CaptureGuide` 5컷 상태 기계(정면 중립·좌·우·위·미소), 중립도·각도·조도 게이트, 0.7 s 유지 자동 촬영, 건너뛰기, 재촬영 | ⏳ |
| T-203 | 캡처 UI: 카메라 미리보기 + 얼굴 메시 와이어 오버레이(ARKit 정점) + 각도 링 + 조도 배너, 한국어 안내 음성(선택) | ⏳ |
| T-204 | `CaptureBundle` 저장/로드, `.chosangcapture` zip, 썸네일 | ⏳ |
| T-205 | 폴백 캡처(TrueDepth 없음·Mac): AVCapture + Vision 76점, 번들에 `sparse = true` | ⏳ |
| T-206 | 실기기: 5컷 자동 촬영 완주 3회, 번들 크기·시간, 안경/마스크 착용 시 중립도 게이트 동작 | ⏳ 🧪 |
| T-207 | 실기기 번들 3세트 수집 → `Fixtures/capture-{a,b,c}.chosangcapture`(사용자 동의, 저장소에는 넣지 않고 로컬 보관 경로 문서화) | ⏳ 🧪 |

## M3 · 피팅
| ID | 작업 | 상태 |
|---|---|---|
| T-301 | `Procrustes`(스케일 포함), 표정 중립화(사용자 메시 − Σ 델타×가중치), 컷 평균 | ⏳ |
| T-302 | `FacePatchSolver`: 패치 치환, 스케일 `s`, 눈알 중심·반지름 추정(눈꺼풀 정점 링 피팅) | ⏳ |
| T-303 | `HeadPropagator`: 바이하모닉 RBF(경계 200 + 내부 100), Neck 감쇠, 어깨 스케일, 좌우 대칭 70% | ⏳ |
| T-304 | `SilhouetteFitter`: 깊이 → 포인트 클라우드(흉상 공간), 두피·귀·턱선 정점 당김(≤12 mm, GN 5회, 라플라시안 λ 0.1), 머리카락 포인트 제외(색 기준) | ⏳ |
| T-305 | 델타 보정(패치 그대로·밖은 `s`·`jawOpen` 진폭), `Identity` 직렬화 `identity.bin` | ⏳ |
| T-306 | 희소 폴백(Vision 76 ↔ `template.json` 랜드마크, 3D TPS) | ⏳ |
| T-307 | 테스트: 합성 번들 셀프 피팅 RMS < 0.2 mm, 픽스처 3세트 패치 RMS < 1.5 mm·실루엣 잔차 중앙값 < 3 mm, 품질 지표 기록 | ⏳ |
| T-308 | 미소 컷 검증 렌더(캡처 가중치 그대로) ↔ 사진 나란히 — 검수 화면 1차 | ⏳ |

## M4 · 텍스처
| ID | 작업 | 상태 |
|---|---|---|
| T-401 | Metal: UV 공간 래스터(텍셀 → 위치·법선), 컷별 깊이 버퍼 렌더, 가시성 가중치 w | ⏳ |
| T-402 | 다시점 투영 가중 평균 4096² RGBA16F, 미소 컷 입 주변 제외 마스크 | ⏳ |
| T-403 | 저주파 색 보정(32×32 격자 최소제곱) + 2 px 페더 접합 | ⏳ |
| T-404 | 탈조명(주광 방향·강도 → 램버트 역보정, 슬라이더), 뺨 기준 재정규화 | ⏳ |
| T-405 | 채움: 대칭 복사 → pull-push 확산 → 두피 머리카락색; `mask.png` 출력 | ⏳ |
| T-406 | 피부 가이드 양방향 필터, 눈 흰자·치아·입안 라이브러리 텍스처 명도 맞춤 | ⏳ |
| T-407 | 2k/4k 설정, PNG 인코딩, 빌드 진행률(5단계) 콜백 | ⏳ |
| T-408 | 테스트: 합성 번들에서 알베도 ↔ 원본 텍스처 PSNR > 32 dB(관측 영역), 픽스처 관측 비율 > 70%, 접합선 색 단차 < 3/255 | ⏳ |
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
| T-509 | 성능: 흉상 2개 90 Hz(Vision Pro), GPU 변형 < 1 ms, 템플릿 캐시 후 로드 0.5 s | ⏳ 🧪 |

## M6 · 패키지 · 전송 · 내보내기 · 소반 어댑터
| ID | 작업 | 상태 |
|---|---|---|
| T-601 | `.chosang` 쓰기/읽기(manifest schema 1, identity.bin, albedo, mask, thumb), 템플릿 id·버전 검사, 캡처 번들 동봉 옵션 | ⏳ |
| T-602 | `PersonaLibrary`: `Documents/Personas/<uuid>/`, 활성, 이름 변경, 삭제, 재빌드(번들 있으면) | ⏳ |
| T-603 | 전송: Network.framework `NWListener/NWBrowser/NWConnection`, Bonjour `_chosang._tcp`, TLS PSK 6자리, 청크·진행률·재개 | ⏳ |
| T-604 | 문서 열기: `fileImporter`·`onOpenURL`·AirDrop `.chosang`/`.chosangcapture` | ⏳ |
| T-605 | `.sobanpersona` 내보내기 어댑터(정면 렌더 → body.png, 리그 좌표, `chosangRef`) | ⏳ |
| T-606 | USDZ 내보내기(macOS, T-005 결과대로), 3DGS PLY 는 v2 | ⏳ |
| T-607 | `ChosangSobanAdapter` 패키지: `ChosangBustAvatar: TableAvatar`(소반 프로토콜 복제본 기준), 소반 쪽 통합은 **별도 PR 로 소반 리포에서** | ⏳ |
| T-608 | 실기기: iPhone → Vision Pro 전송(12 MB) 시간, 코드 입력, 수신 후 로드 | ⏳ 🧪 |

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
1. `Shoulders_shirt` 오브젝트 추가(Library_Shoulders, Root/Neck 스킨) → 검증기 오류 0.
2. (선택) `chosang_landmarks` 에 brow_inner_left/right.
3. 후속: 셰이프키 손질(funnel·pucker·press), 이마 이음 능선, 수염 경계 계단, 귀 모델.

## 실기기 체크리스트 (M0 — 🧪 지금 바로 확인 가능)
0. iPhone(TrueDepth): 캡처 탭 → 세션 시작 → "T-007 프로브" 에 정점 1220 · 삼각형 수 · 해시 · 깊이 640×480 DepthFloat32 · intrinsics · 조명 방향 표시 → 값을 `Docs/Spikes.md` T-007 과 `ARKitFaceTopology.referenceTriangleHash` 에 기록. 5컷 촬영 → 번들 저장 → 크기·시간.
0b. Vision Pro / iPhone 실기기: 미리보기 탭 "변형 경로" 가 `LowLevelDeformation (GPU)` 인지, 클립 `laugh` 재생 중 변형 ms·fps.

## 실기기 체크리스트 (v1)
1. iPhone: 초상 캡처 → 5컷 자동 촬영 → 빌드 60 s 이내 → 미리보기에서 턴테이블·클립 `bow`·라이브 표정(내 얼굴 따라 움직임).
2. iPhone: 미소 검증 화면에서 사진과 렌더의 입꼬리·눈 모양이 일치.
3. iPhone → Vision Pro: 코드 입력 전송 → 거울에서 고개·입(마이크)·클립 `idle_breathe` 확인.
4. Mac: `chosang-validate Template.usdz` 통과, 비교 검수에서 `laugh` 클립 프레임 동기, USDZ 내보내기 → Quick Look.
5. 소반(별도): `.sobanpersona` 내보낸 파일을 소반 스튜디오에서 열어 두레반 착석.
