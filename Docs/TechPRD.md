# 초상 (Chosang) — Tech PRD

> 새 프로젝트 · visionOS 27 + iOS 26 + macOS 26 · Swift 6 toolchain (Swift 5 언어 모드, 기본 MainActor 격리)
> 작성일 2026-10-03 · 상태: v0.3 — M0(1차)·M1 2차(계약·내보내기·검증기·기본 템플릿 반입) 완료. 스파이크 `Spikes.md`, 분기 §3, 회차 기록 §12–13.
> 프로젝트 이름 "초상(肖像)" 은 작업명이다. 바꿔도 문서 구조는 그대로 쓴다.

## 1. 한 줄 요약

**블렌더에서 만든 흉상(어깨 위) 템플릿과 프리비즈 애니메이션**을 기준 기하로 삼고, 사용자가 iPhone 으로 찍은 **사진 3–5장**으로 그 흉상을 "내 얼굴" 로 맞추고 입혀서, Vision Pro 의 시스템 Persona 와 견줄 만큼 **깔끔한 나만의 흉상 페르소나**를 온디바이스에서 완성한다. 완성된 페르소나는 블렌더 프리비즈 클립(상황)대로 움직이고, ARKit 52 표정 신호와 음성으로 실시간 구동되며, 소반(두레반 모임 앱)에 그대로 공급된다.

## 2. 소반에서 배운 것 → 설계 전환

| 소반(현행) | 문제 | 초상(전환) |
|---|---|---|
| 사진 우선: 사진 픽셀을 카드/부조 스플랫으로 세우고 그 위에 USDZ 눈·입 키트를 덧붙임 | 측면·뒤통수가 없다. 키트가 떠 보인다. 스플랫은 초기화만 하고 학습하지 않아 경계가 거칠다 | **템플릿 우선**: 블렌더 흉상이 기하의 진실. 사진은 "형상 차이 + 텍스처" 만 공급한다 |
| Vision 76점 랜드마크로 2D TPS 변형 | 희소 대응점, 깊이는 추정 | 캡처 때 **ARKit 얼굴 메시(1220 정점, 고정 토폴로지)** 를 그대로 기록 → 템플릿 얼굴 영역과 **정점 1:1 대응** → 밀집 피팅 |
| 블렌더 에셋은 손으로 넘겨받음 | 이름·좌표·셰이프키 누락이 런타임에 드러남 | **에셋 계약 + 내보내기 스크립트 + 검증기**(`chosang-validate`) 로 블렌더 쪽 산출물을 기계적으로 검사 |
| 표정은 마이크 RMS + 한글 규칙 | 상황(인사·웃음·경청)이 없다 | **프리비즈 클립 라이브러리**(블렌더 액션 → 클립) + 레이어 합성(기본 클립 / 라이브 표정 / 시선 / 비셈) |
| 페르소나 = PNG + 부조 스플랫 | 다른 앱·툴에서 못 쓴다 | 패키지 `.chosang` + USDZ/`.sobanpersona` 내보내기, 소반 어댑터 |

**ARKit 52 는 그대로 표정 표준**이다(소반 `ArkitBlendShapes.swift` 재사용). 블렌더 흉상 좌표계(m, Y-up, 얼굴 +Z, 눈 y≈0.44·간격 0.064, 입 y≈0.357, 정수리 0.566, 가슴 절단면 y=0)도 유지해 소반 에셋과 호환한다.

## 3. 배경 제약 (사실 → 결정)

| 제약 | 사실 | 결정 |
|---|---|---|
| 카메라 | visionOS 는 서드파티에 카메라·얼굴 추적을 열지 않는다 | 캡처·피팅·텍스처는 **iPhone(TrueDepth)** 에서. Vision Pro 는 받아서 렌더(+ 캡처 번들을 받으면 재빌드도 가능) |
| 얼굴 대응 | `ARFaceGeometry` 는 정점 1220·삼각형·UV 가 모든 인스턴스에서 동일, 표정에 따라 `vertices` 만 바뀐다. Apple 샘플 "Tracking and visualizing faces" 에 중립 `ARFaceGeometry.obj` 가 들어 있다 | 블렌더 흉상의 얼굴 패치를 **이 OBJ 토폴로지 그대로** 쓴다(정점 순서 보존, 버텍스 그룹 `ARKitFace`). 피팅은 대응점 탐색이 아니라 **정점 치환 + 전파**가 된다 |
| 런타임 변형 | RealityKit 27: `MeshResource.contents` 의 `blendShapeOffsets(named:)` 로 USDZ 셰이프키 델타를 읽을 수 있다(**T-004 확인: 36/36 읽힘, 스킨·조인트 포함**). `LowLevelMesh` 로 자체 정점 포맷을 쓰고 `LowLevelDeformation`(Metal 컴퓨트) 이 블렌드셰이프·스키닝·재정규화를 해 준다. **시뮬레이터 SDK 에는 `LowLevelDeformation` 이 없다**(T-006) | 템플릿 USDZ → 델타 추출 → **사용자 형상으로 치환한 `LowLevelMesh`** → 기기·Mac 은 `LowLevelDeformation`(52 셰이프 + 목·머리·눈 뼈), 시뮬레이터·실패 시 CPU 블렌드 폴백. `bust.mesh` 는 항상 함께 내보내 검증기가 교차 확인(§12) |
| 애니메이션 | RealityKit 27: `SkeletonResource`, `AnimationGraphResource/Component`, `BlendTreeAnimation`, `SampledAnimation.convertToAdditive*`, `BlendMask` | **T-006 결정: 뼈 트랙도 `clip.json` 에 넣고 자체 `ClipPlayer` 가 52 가중치와 같은 타임라인·크로스페이드로 샘플링**한다(블렌더 클립이 USD SkelAnimation 으로 오지 않으므로). `AnimationGraphResource`/`BlendMask` 는 M5 스키닝 때 look-at·Neck 마스크 용도로 재검토 |
| USD 쓰기 | ModelIO `MDLAsset.export` — **T-005 확인: usdc/usda ✓, usdz ✗**(macOS 27.0.1) | 내보내기 USDZ 는 macOS 에서 **usdc + 자체 ZipArchive(64 B 정렬)** 로 만든다. 기기 간 교환은 `.chosang` 패키지 |
| 스플랫 | `GaussianSplatComponent` 는 기기·macOS SDK 에만 있다(시뮬레이터 없음). 버퍼를 참조하므로 매 프레임 갱신 가능 | v2 "부드러운 머리카락·피부" 는 메시에 바인딩한 스플랫. 시뮬레이터는 메시만 |
| 생성형 완성 | 온디바이스 생성 모델(FoundationModels)은 텍스트·분류용. 이미지 합성은 없다 | **v1 은 결정적 파이프라인**(투영·대칭·확산 채움·라이브러리). 힉스필드식 생성형 보정은 v3 옵션(사용자 동의, 외부 서비스) |
| 시뮬레이터 | TrueDepth·ARFaceTracking 없음. `LowLevelDeformation`·`GaussianSplatResource` 심볼도 없음 | 캡처 번들 **합성 2세트 + 실기기 3세트**(`Fixtures/`, 실기기 것은 로컬 보관)로 피팅·텍스처·렌더를 시뮬레이터·Mac 에서 회귀 테스트. 변형은 CPU 폴백으로 확인 |

## 4. 목표 / 비목표

**목표 (v1)**
1. 블렌더 흉상 템플릿 + 머리카락/안경 라이브러리 + 프리비즈 클립을 **계약대로** 내보내고 앱이 검증·로드한다.
2. iPhone 가이드 캡처 5컷(정면·좌·우·위·미소)으로 **캡처 번들** 생성(RGB·깊이·ARKit 얼굴 메시·내부 파라미터·조명 추정).
3. 캡처 번들 → **피팅**(얼굴 패치 치환 + 두상 전파 + 실루엣 맞춤) → **텍스처**(다시점 투영·접합·탈조명·미관측 채움) → **외형 라이브러리 선택**(머리카락·안경) → `.chosang` 패키지. iPhone 15 Pro 기준 60초 이내.
4. Vision Pro·iPhone·Mac 에서 같은 모습으로 렌더. 52 셰이프 + 목·머리·눈 뼈 + 클립 레이어 합성. 2개 흉상 동시 90 Hz.
5. **상황 플레이어**: idle · 경청 · 끄덕임 · 말하기 · 웃음 · 놀람 · 인사(목례) · 생각. 블렌더 프리비즈 렌더(mp4)와 **나란히 비교하는 검수 화면**.
6. 내보내기: `.sobanpersona`(소반 어댑터) · USDZ(macOS) · 3DGS PLY(v2). 소반이 `.chosang` 을 열어 `TableAvatar` 로 쓸 수 있는 어댑터 패키지 제공.

**비목표 (v1)**
- 전신, 옷 시뮬레이션, 손.
- 원격 서버·계정·클라우드 학습.
- 모임/네트워크(소반이 담당).
- 실사 머리카락 재구성(v2 스플랫에서 다룬다).

## 5. 사용자 흐름

```
[블렌더]  흉상 템플릿 · 라이브러리 · 클립 제작 ─▶ export_chosang.py ─▶ Template.usdz + clips/*.json + template.json
              └─▶ chosang-validate (CLI/Mac 앱) 통과해야 번들에 들어감

[iPhone]  초상 캡처 ─▶ 5컷 가이드(ARKit 얼굴 추적, 중립 유지 안내) ─▶ 캡처 번들 ─▶ 빌드(피팅·텍스처·힌트)
              ─▶ 다듬기(머리카락·안경·피부톤·탈조명 강도) ─▶ 미리보기(클립 재생·표정 라이브) ─▶ 저장 ─▶ Vision Pro 로 보내기

[Vision Pro]  받기 ─▶ 상황 플레이어로 확인(거울) ─▶ 소반에서 사용 / 내보내기
[Mac]  번들·템플릿 검증, 비교 검수(프리비즈 mp4 ↔ 앱 렌더), USDZ 내보내기
```

## 6. 시스템 구성

### 6.1 패키지 구조 (Swift Package + 앱 타깃)

| 모듈 | 역할 | 플랫폼 |
|---|---|---|
| `ChosangCore` | 모델(`BustTemplate`, `CaptureBundle`, `Identity`, `ChosangPackage`), 파일 포맷, ARKit 52 타입(소반에서 이식), 수학(RBF, 라플라시안, 쿼터니언) | 전 플랫폼, 순수 Swift |
| `ChosangFit` | 피팅(`FacePatchSolver`, `HeadPropagator`, `SilhouetteFitter`), Metal 커널 포함 | iOS·macOS·visionOS |
| `ChosangTexture` | 다시점 투영·접합·탈조명·채움(Metal), 피부 보정 | iOS·macOS·visionOS |
| `ChosangRig` | `BustEntity`(LowLevelMesh + LowLevelDeformation), `FaceRigSystem`, `ClipPlayer`, `SituationDirector`, 외형 라이브러리 부착 | 전 플랫폼 |
| `ChosangCapture` | ARFaceTracking 캡처 세션, 가이드, 번들 저장 | iOS |
| `ChosangIO` | `.chosang` 읽기/쓰기, `.sobanpersona` 어댑터, USDZ 내보내기(macOS), 전송(Network.framework) | 전 플랫폼 |
| `ChosangValidate` | 템플릿·클립 계약 검사 CLI(`swift run chosang-validate Template.usdz`) | macOS |
| 앱 `Chosang` | visionOS(받기·확인·거울·내보내기), iOS(캡처·빌드·다듬기·보내기), macOS(검증·비교 검수) 한 타깃 | 3 플랫폼 |

### 6.2 블렌더 에셋 계약 (요약 — 전문은 `Blender-요청.md`)

- **흉상 메시** `Bust`: 얼굴 패치 = Apple `ARFaceGeometry.obj` 1220 정점 **순서 그대로**(버텍스 그룹 `ARKitFace`, 정점 인덱스 0…1219 가 패치), 그 바깥으로 귀·두피·목·어깨를 이어 붙인다. 4k UV 한 장(얼굴 50%·두피/목 30%·어깨/옷 20%). 셰이프키 ARKit 52(중립 0, 1 = 최대). 눈알 `Eye_L/Eye_R`, 치아·혀·입안 `Mouth_Inner`, 눈꺼풀은 Bust 에 포함.
- **스켈레톤**: `Root > Spine > Neck > Head > {Eye_L, Eye_R}`. 가중치는 Neck/Head 만(어깨는 Root). jaw 는 뼈가 아니라 `jawOpen` 셰이프.
- **라이브러리**: `Hair_<id>`(10종 이상: 짧은/중간/긴/묶음/앞머리 조합, 머리카락 카드 + 알파, 틴트 가능한 그레이스케일 베이스), `Glasses_<id>`(3종), `Shoulders_<id>`(옷 2종). 모두 Head 뼈에 스킨.
- **클립**: 액션 이름 `clip_<name>` — idle_breathe · listen · nod · talk_a/b/c · laugh · surprise · bow · think · blink_set. 30 fps. 뼈 트랙(Neck/Head/Eye) + 셰이프키 트랙(52). 1초 이상, 루프 가능 클립은 첫/끝 프레임 일치.
- **프리비즈 렌더**: 각 클립을 같은 카메라(정면 50 mm, 1.2 m)로 mp4 렌더 → `previz/<clip>.mp4`. 앱 검수 화면의 비교 기준.
- **내보내기 스크립트** `tools/blender/export_chosang.py`(Blender 4.1+, Apply Modifiers OFF): `Template.usdz`, `clips/<name>.json`(52 가중치 × 프레임 + 뼈 쿼터니언/위치), `template.json`(랜드마크 정점 id: 눈 안/바깥 꼬리·코끝·입꼬리·턱끝·귀 위 ↔ Vision 76 인덱스, 머리카락 스캘프 정점 집합, UV 영역 박스, 어깨 폭 기준 정점), `previz/*.mp4`.

### 6.3 캡처 (`ChosangCapture`, iOS)

| 단계 | 구현 |
|---|---|
| 세션 | `ARSession` + `ARFaceTrackingConfiguration`(`isLightEstimationEnabled`, `maximumNumberOfTrackedFaces` 1). 전면 TrueDepth. `ARFrame.capturedImage` + `capturedDepthData` + `camera.intrinsics` + `camera.transform` |
| 가이드 | 5컷: 정면 중립 → 좌 30° → 우 30° → 위 15° → 정면 미소. 각 컷은 **표정 중립도**(52 가중치 합 < 0.6, 미소 컷 제외)·yaw/pitch 허용 범위·조도(lightEstimate ambientIntensity 300–1500 lm) 가 0.7초 유지되면 자동 촬영. 각 컷에서 **연속 8프레임**의 `faceAnchor.geometry.vertices` 를 평균(지터 제거) |
| 번들 | `CaptureBundle`: shots[5] { jpeg(4032 긴 변, EXIF 업라이트), depth(Float32, 640×480, 카메라 좌표), intrinsics(3×3, 이미지 해상도 기준), cameraTransform, faceTransform, faceVertices[1220], blendShapes[52], lightEstimate(ambient, 색온도, 방향 추정 `ARDirectionalLightEstimate` 는 Face 구성에서 제공) } + `meta.json`. 폴더 `Documents/Captures/<uuid>/`. 전송·테스트용 `.chosangcapture`(zip) |
| 폴백 | TrueDepth 없는 기기·Mac·사진 파일: `PhotoCaptureSession`(AVCapture + Vision 76점 revision 3 + 자세) → 같은 `CaptureBundle`(`sparse = true`, 깊이·1220 정점 없음, `landmarks2D`·`keyPoints2D`·`faceBox`·`poseEstimate`·`intrinsicsEstimated`) → `template.json` 랜드마크 대응으로 희소 피팅(M3 T-306, 품질 "기본" 표시). 기하 규약은 `SparseFaceGeometry`(§14) |

### 6.4 피팅 (`ChosangFit`)

1. **정렬**: 5컷 얼굴 메시를 정면 컷의 `faceTransform` 기준으로 모으고 Procrustes(스케일 포함)로 템플릿 얼굴 패치(중립)에 정합. 표정 제거: 각 컷의 ARKit 메시에서 템플릿 52 델타 × 그 컷의 가중치를 뺀다(중립화). 미소 컷은 **표정 검증용**(아래 6.8)으로만 쓴다.
2. **얼굴 패치 치환**: 템플릿 패치 정점 ← 중립화·평균된 사용자 정점. 사용자 머리 스케일 `s` = 사용자 눈 간격 / 템플릿 눈 간격(0.064).
3. **두상 전파** (`HeadPropagator`): 패치 변위 `d_i` 를 패치 밖 정점으로 **바이하모닉 RBF**(커널 r³, 중심 = 패치 경계 ~200점 + 내부 샘플 100점) 로 전파하되, Neck 아래는 감쇠 0, 어깨는 스케일 `s` 만 적용. 대칭 보정: 좌우 반사 평균 70%(사용자 비대칭 30% 보존).
4. **실루엣 맞춤** (`SilhouetteFitter`): 좌/우/위 컷의 깊이 → 카메라 좌표 포인트 → 흉상 공간. 두피·귀·턱선 정점을 가장 가까운 포인트 법선 방향으로 당김(최대 12 mm, 가우스-뉴턴 5회, 라플라시안 정규화 λ=0.1). 머리카락은 깊이가 두피보다 바깥에 있으므로 **두피 정점은 머리카락 포인트를 무시**(색이 피부가 아니면 제외).
5. **셰이프 델타 보정**: 52 델타는 템플릿 공간 → 사용자 공간으로 **국소 스케일**(패치 정점은 ARKit 대응으로 동일 토폴로지라 그대로, 밖은 `s`). `jawOpen` 은 사용자 미소/중립 컷 턱 길이로 진폭 보정.
6. **출력** `Identity`: 정점 위치 N(≈12k) float3, 스케일 `s`, 눈알 중심·반지름, 조정된 52 델타(패치만 저장, 나머지는 로드 시 재계산), 품질 지표(패치 RMS, 실루엣 잔차).

**정확도 목표**: 패치 RMS(정합 후 사용자 메시 대비) < 1.5 mm, 실루엣 잔차 중앙값 < 3 mm.

### 6.5 텍스처 (`ChosangTexture`, Metal)

| 단계 | 구현 |
|---|---|
| 가시성 | 컷마다 피팅된 메시를 그 컷의 카메라(intrinsics·transform)로 **UV 공간에 래스터**: 텍셀 → 월드 위치·법선 → 카메라 투영 → 깊이 테스트(깊이 버퍼 렌더 + 캡처 깊이와 ±15 mm 일치) → 가중치 w = cos(법선·시선)^3 × 가장자리 거리 × 깊이 일치 |
| 투영 | 5컷 가중 평균(미소 컷은 입 주변 제외). 4096² RGBA16F |
| 접합 | 컷별 **저주파 색 보정**(UV 32×32 격자에서 겹치는 영역의 색 차이를 최소제곱으로 풀어 노출·화이트밸런스 차이 제거) → 가중 평균 → 경계 2px 페더 |
| 탈조명 | `lightEstimate`(주광 방향·강도) 로 램버트 음영 추정 → 알베도 ≈ 색 / (0.35 + 0.65·max(0, n·l)) 클램프, 강도는 사용자 슬라이더 0–1 |
| 채움 | 미관측 텍셀: ① 좌우 대칭 복사(UV 대칭 맵은 템플릿에서 사전 계산) ② 그래도 비면 pull-push 확산 ③ 두피는 머리카락 평균색 |
| 피부 보정("깔끔하게") | 얼굴 영역 가이드 양방향 필터(σ 3px, 색 0.08), 잡티 제외는 안 함(정체성 보존). 눈 흰자·치아·입안은 **라이브러리 텍스처** + 사용자 피부톤에 맞춘 명도만 |
| 출력 | `albedo.png`(4k, 또는 2k 설정), `mask.png`(관측/대칭/채움 구분 — 디버그·v2 스플랫 초기화용), 선택 `normal.png`(깊이 고주파에서, v1.1) |

### 6.6 외형 라이브러리 선택 (`AppearanceHints` 이식 + 확장)

- 소반 `AppearanceAnalyzer`(FoundationModels `@Generable` + 휴리스틱) 를 이식. 분류 항목: 머리 길이·볼륨·앞머리·묶음·안경·수염·어깨 옷 종류.
- 결과 → `Hair_<id>` 선택 + 틴트(사용자 머리카락 평균색, 명도 분포로 하이라이트) + 두피 라인은 피팅된 `scalp` 정점 집합에 맞춰 스케일. 사용자가 피커로 바꿀 수 있다.
- 좌표는 절대 모델에 맡기지 않는다(소반 7차 결론 유지).

### 6.7 런타임 리그 (`ChosangRig`)

| 항목 | 구현 |
|---|---|
| `BustEntity` | `Template.usdz` 를 `Entity(named:)` 로 1회 로드 → `MeshResource.contents` 에서 정점·인덱스·UV·`blendShapeOffsets(named:)` 52개·스킨 가중치 추출 → `Identity` 정점으로 치환한 **`LowLevelMesh`**(위치·법선·UV·조인트 4) 생성. `LowLevelDeformation`(blending 52 + skinning 5 조인트 + renormalizing) 을 매 프레임 `encode(into:)`. 머티리얼 `PhysicallyBasedMaterial`(albedo, roughness 0.55, 피부 SSS 는 없음 → 약간 밝은 램버트 톤으로 보정). 눈알·입안·라이브러리는 자식 엔티티(Head 뼈에 부착) |
| 폴백 | `blendShapeOffsets` 가 비거나 `LowLevelDeformation` 미지원 환경: `MeshDeformerComponent`(`BlendShapeDeformer`+`SkinningDeformer`) 또는 CPU 블렌드(`LowLevelMesh.withUnsafeMutableBytes`, 12k 정점 × 52 는 CPU 로도 1 ms 안) |
| `FaceRigSystem` | 소반 8차 시스템 이식: `externalWeights`(ARKit 52 라이브) · 비셈 큐(`HangulViseme`, 오디오 엔벨로프) · 자동 깜빡임 · 시선 미세 움직임. 출력은 `ArkitWeights` 52 → 블렌딩 가중치 버퍼 |
| `ClipPlayer` | `clips/<name>.json` 을 `SampledClip`(52 가중치 + Neck/Head/Eye 트랜스폼, 30 fps) 로 로드. 보간·루프·크로스페이드(기본 250 ms). 뼈 트랙은 `AnimationGraphResource` 로도 구성(블렌드 트리·`BlendMask` 로 Neck 만 등) — 어느 쪽을 주 경로로 할지 스파이크 T-006 |
| 레이어 합성 | 가중치 = 기본 클립(상황) ⊕ 라이브 표정(있으면 입·눈썹·눈 영역을 클립 대신 100%) ⊕ 비셈(말할 때 입 영역 가산, 클립 입은 0.3 로 감쇠) ⊕ 깜빡임(클립에 blink 트랙 없을 때). 뼈 = 클립 + 라이브 고개(Vision Pro 디바이스 앵커 또는 iPhone faceTransform) 가산 + 시선 look-at(눈 뼈, 최대 ±25°) |
| `SituationDirector` | 상태 머신: idle ↔ listening(상대 음성 레벨) ↔ speaking(내 음성/TTS) → 이벤트(laugh/surprise/bow/think) 는 1회 재생 후 복귀. 소반이 `Participant` 상태로 구동할 수 있게 입력은 순수 값(`SituationInput`) |

### 6.8 검수 화면 (macOS·visionOS)

- **프리비즈 비교**: 왼쪽 `previz/<clip>.mp4`(AVPlayer), 오른쪽 같은 클립을 같은 카메라(정면 50 mm 상당, 1.2 m)로 재생. 프레임 스크럽 동기화, 30 fps 기준 ±1 프레임 허용. 다른 점은 **텍스처뿐**이어야 한다.
- **표정 검증**: 캡처의 미소 컷 가중치를 그대로 넣어 렌더 → 사진과 나란히(피팅·델타 보정이 맞는지).
- **품질 카드**: 패치 RMS, 실루엣 잔차, 관측 텍셀 비율, 채움 비율, 빌드 시간.

### 6.9 패키지·입출력 (`ChosangIO`)

- `.chosang`(폴더 또는 zip, UTI `com.coulson.chosang.persona`): `manifest.json`(schema 1, 이름, 템플릿 id·버전, 라이브러리 선택, 틴트, 품질 지표, 생성 기기), `identity.bin`(정점 float3 + 패치 델타), `albedo.png`, `mask.png`, `thumb.png`(정면 512), 선택 `splats.bin`(v2).
- 템플릿 의존: 패키지는 **템플릿 id+버전**을 가리킨다(정점 수·순서가 같아야 함). 템플릿이 바뀌면 재빌드가 필요하므로 캡처 번들을 함께 보관(기본 ON, 사용자 삭제 가능).
- 전송: Network.framework(Bonjour `_chosang._tcp`, TLS PSK 6자리 코드) — 소반의 MC 는 deprecated 라 처음부터 TN3213 패턴. AirDrop `.chosang` 도 지원.
- 내보내기: `.sobanpersona`(어댑터: 정면 렌더 → `body.png`, 리그 좌표는 템플릿 랜드마크에서, `faceKit = "none"`, `demoAvatar` 대신 새 키 `chosangRef`), USDZ(macOS, ModelIO 가 usd 내보내기를 지원하는 경우 — 스파이크 T-005; 안 되면 자체 USDA 직렬화 + `usdzip` 대체 구현), 3DGS PLY(v2).
- 소반 어댑터 패키지 `ChosangSobanAdapter`: `TableAvatar` 구현(`ChosangBustAvatar`) — 소반 `Soban/Persona/BustAvatars.swift` 의 프로토콜을 따른다.

### 6.10 v2 — 메시 바인딩 가우시안 스플랫 (부드러운 머리카락·피부)

- 스플랫을 흉상 삼각형에 바인딩(삼각형 id + 무게중심 + 법선 오프셋 + 국소 회전). 매 프레임 `LowLevelDeformation` 출력 정점으로 스플랫 위치·회전을 Metal 컴퓨트로 갱신 → `GaussianSplatResource` 버퍼(참조 유지) 재기록.
- 초기화: `mask.png` 의 관측 텍셀에서 색, 머리카락 영역은 `Hair_<id>` 표면에 2겹.
- 최적화: 캡처 5컷(알려진 카메라) 대비 **색·불투명도·스케일·법선 오프셋만** 학습하는 작은 미분 가능 래스터라이저(Metal, 타일 16×16, 스플랫 ≤ 80k, 200 반복). 목표 iPhone 15 Pro 90초 이내. 위치·토폴로지는 학습하지 않는다(리깅 보존).
- 시뮬레이터·구형 기기는 메시 렌더로 폴백.

## 7. 성능 예산

| 항목 | 예산 |
|---|---|
| 캡처 → 패키지 | iPhone 15 Pro 60 s, M2 Mac 25 s |
| 패키지 로드 → 첫 프레임 | Vision Pro 1.5 s(템플릿 캐시 후 0.5 s) |
| 프레임 | 흉상 2개 + 라이브러리, 90 Hz 유지, GPU 변형 < 1.0 ms/흉상 |
| 메모리 | 흉상당 albedo 4k RGBA8 64 MB(기본 2k 16 MB) + 메시 6 MB. 소반 6석 기준 2k 사용 |
| 패키지 크기 | 2k 알베도 기준 ≤ 12 MB, 캡처 번들 ≤ 40 MB |

## 8. 보안·프라이버시

- 모든 처리는 온디바이스. 캡처 번들(사진·깊이·얼굴 메시)은 기기 Documents 에만. 전송은 사용자가 시작하고 PSK 코드로 보호.
- 패키지에는 원본 사진이 들어가지 않는다(알베도·형상만). 캡처 번들 동봉은 선택.
- ARKit 얼굴 데이터 사용 고지(`NSCameraUsageDescription` 에 명시), 생체 식별 용도로 쓰지 않는다. v3 외부 생성형 보정은 별도 동의 화면 없이는 켜지지 않는다.

## 9. 검증 전략

- **단위(Swift Testing)**: RBF 전파(알려진 변위 재현), Procrustes, 클립 보간·루프, `.chosang` 라운드트립, `template.json` 검증기 규칙, 어댑터 리그 좌표.
- **픽스처 회귀**: `Fixtures/capture-{a,b,c}.chosangcapture`(실기기에서 한 번 수집) → 피팅 RMS·실루엣 잔차·관측 비율이 기준치 ±5% 안인지. 렌더 스냅샷(정면·좌 30°) 픽셀 차이 < 2%.
- **시뮬레이터**: 템플릿 로드·변형·클립 재생·레이어 합성·검수 화면(픽스처 패키지로).
- **Mac**: 검증기, 비교 검수(mp4 ↔ 렌더), USDZ 내보내기.
- **iPhone 실기기**: 5컷 가이드 자동 촬영, 빌드 시간, 미소 컷 검증 렌더, 전송.
- **Vision Pro 실기기**: 수신·로드 시간·90 Hz·거울·소반 어댑터로 두레반 착석.

## 10. 알려진 위험과 완화

| 위험 | 완화 |
|---|---|
| `blendShapeOffsets(named:)` 가 USDZ 로드 메시에서 비어 있음 | T-004 스파이크 최우선. 실패 시 `export_chosang.py` 가 `bust.mesh` 를 쓴다(계약에 이미 포함) |
| ARKit 얼굴 메시 토폴로지가 OS 업데이트로 바뀜 | `template.json` 에 정점 수·삼각형 해시 기록, 캡처 시 불일치면 희소 피팅 폴백 + 경고 |
| 템플릿 1종으로 다양한 얼굴을 못 덮음(눈 크기·턱 길이) | 패치는 사용자 정점 그대로이므로 얼굴은 정확. 두상·귀는 실루엣 맞춤이 보완. 필요 시 템플릿 2종(성별 체형) |
| 머리카락이 "라이브러리 티" 가 남 | v2 스플랫 머리카락. v1 은 틴트·하이라이트·두피 라인 맞춤으로 자연스러움 확보 |
| 탈조명이 피부톤을 바꿈 | 강도 슬라이더 + 정면 컷 뺨 평균색을 기준으로 재정규화 |
| 프리비즈와 앱 렌더가 안 맞음 | 같은 액션에서 mp4 와 clip.json 을 같은 스크립트가 내보냄, 검수 화면이 프레임 단위 비교 |

## 11. 다음 단계(v2 이후)

1. §6.10 스플랫 바인딩·최적화.
2. 오디오 → ARKit 52 온디바이스 모델(Core ML) — Vision Pro 에서 라이브 표정 대체(소반 T-1112 이어받음).
3. 템플릿 2종 + 어린이/노년 체형.
4. v3 생성형 보정(외부, 동의 기반): 미관측 영역 인페인팅, 머리카락 사진 기반 생성.


## 12. 1차 — M0 셋업·스파이크 (2026-10-03)

**한 것**: Xcode 프로젝트(타깃 `MyApp` → 제품 Chosang) + 로컬 패키지 `ChosangKit`(Core·Fit·Texture·Rig·Capture·IO·Validate + CLI + 테스트 17개), Info.plist(카메라·마이크·로컬 네트워크·Bonjour·UTI 2종·문서 타입), 소반 코드 이식(ArkitBlendShapes·HangulViseme·TPS·AppearanceHints·MicLevelMeter·FaceRig), 스파이크 4개(`Spikes.md`), 합성 템플릿·합성 캡처 번들·셀프 피팅·CPU 텍스처 투영, 검증기 30여 규칙, `export_chosang.py` 초안, 3 플랫폼 앱 셸(미리보기·스파이크·캡처·검증), 4개 빌드 통과(visionOS 기기·시뮬, iOS 시뮬, macOS).

**확정한 분기**
1. 런타임 변형: USDZ → `blendShapeOffsets` → `LowLevelMesh`(버퍼 0 위치/1 법선/2 UV) → `LowLevelDeformation`(기기·Mac) / CPU 블렌드(시뮬레이터). Mac 0.14 ms/변형.
2. 뼈 클립: `clip.json` + 자체 `ClipPlayer`. USD SkelAnimation·`AnimationGraphResource` 는 보류.
3. USDZ 내보내기: usdc + `ZipArchive`(64 B 정렬).
4. 두상 전파: 순수 r³ RBF 외삽은 뒤통수를 망친다(중앙값 6 mm) → **전역 유사변환(패치 Procrustes) + 잔차 RBF × 경계 거리 감쇠 σ 5 cm + 목 감쇠 + 어깨 x/z 스케일 + 대칭 70%** 로 중앙값 1.9 mm. 피팅 결과의 절대 위치 규약 = 사용자 눈 중점이 템플릿 눈 중점(0.44 m)에 오도록.
5. 캡처 번들 규약(단위·좌표계)은 `CaptureBundle.swift` 머리말에 고정: 깊이 m, intrinsics 저장 이미지 해상도 기준, 카메라 −Z 전방, 얼굴 좌표 ARKit 규약, 8프레임 평균.
6. `.chosang` 은 폴더 패키지(manifest schema 1·identity.bin·albedo·mask·thumb·선택 capture/), zip 은 전송용. 템플릿 id·버전·정점 수 불일치는 읽기에서 거부.

**측정** (상세 `Spikes.md` 부록): 셀프 피팅 0.011 mm, 섭동 피팅 패치 0.0005 mm·두상 1.9 mm, 텍스처 PSNR 24 dB(M0 기준선 22, M4 목표 32), 시뮬레이터 CPU 변형 7.5–9.2 ms(60–83 fps, 디버그).

**바뀐 계약** (`Blender-요청.md` §6b): `bust.mesh` 항상 동봉, 오브젝트 이름 고정, Bust 에 모디파이어 금지, 셰이프 액션 `clip_<name>_shapes`, 랜드마크는 스크립트 `LANDMARKS` 사전, template.json 추가 필드(symmetryMap·uvRegions·boneRest·libraryObjects·clips).

**함정**
- Xcode 가 프로젝트를 다시 저장(빌드 설정·Info.plist 도구 호출)하면 외부에서 넣은 로컬 패키지 참조가 **지워진다**. 순서: 모든 Xcode 측 설정 → 마지막에 pbxproj 패키지 참조 → 그 뒤로는 pbxproj 를 건드리는 도구 호출 금지(또는 재적용).
- 시뮬레이터 SDK 에 없는 심볼(`LowLevelDeformation`)은 문서·심볼 그래프에도 안 나온다. `xcrun -sdk macosx swiftc -typecheck` 프로브로 시그니처를 확정했다.
- 샌드박스 macOS 앱의 Documents 는 터미널에서 못 읽는다 → 수치는 창 스크린샷으로, 시뮬레이터는 `simctl get_app_container` 로.
- iOS 시뮬레이터 런타임이 이 Mac 에 없다(빌드만 가능). iOS 화면 확인은 실기기 또는 macOS 로.

**가정**
- Xcode 프로젝트 이름은 사용자가 만든 "Untitled Project/MyApp" 을 그대로 쓰고 제품·번들만 Chosang 으로 했다(프로젝트 이동·이름 변경은 사용자 몫, 소반 때와 같은 흐름).
- 합성 템플릿의 패치 토폴로지는 ARKit 과 **정점 수만** 같다. 실제 `ARFaceGeometry.obj` 해시는 🧪 T-007 뒤에 채운다.
- 캡처 이미지 방향·intrinsics 회전 규칙은 실기기 재투영으로 검증 전이다(M2 T-206).

**다음 (M1)**: Blender-요청.md 기준 T-101~T-106 — 블렌더 1차 산출물 수령 → `chosang-validate` 통과 → `Resources/Templates/Default/` → 템플릿 캐시(T-104) → 셰이프 시트(T-106). 스크립트는 블렌더 4.1/5.x 에서 1회 실행해 다듬는다.


## 13. 2차 — M1 블렌더 1차 산출물 반입 · 2차 계약 · 내보내기 · 검증기 (2026-10-03)

**받은 것**: `Chosang_Blender/`(Blender 5.2.2 작업 파일 + 결정적 빌드 스크립트 `build/` + 텍스처 + Apple OBJ/라이선스 + previz 11개 + 변경 제안 9건). 리포에 반입(LFS: .blend·png·mp4·mesh·chosangtemplate; `Template.usdz`·`library/*.usdz` 는 스크립트로 재생성 가능해 제외).

**계약(2차, `Blender-요청.md` §8)**: 9건 모두 수용. 핵심 — 입 중심 등은 측정값(검증 기준 = template.json), `Neck` = 뼈 가중치 그룹, 패치 해시 = OBJ 사각형 SHA-256, 수염 `chosang_bust_index`, Mouth_Inner 셰이프 5개, 슬롯 액션(끝 프레임 포함), 프리비즈 카메라 고정. 앱 쪽 추가 결정: bust.mesh v2 에 **코너 UV**(솔기 357 정점 → 렌더 메시 분할 11,931), 라이브러리는 **오브젝트별 USDZ**(RealityKit 이 한 아마추어 아래 스킨 메시를 모델 하나로 합치므로), 랜드마크 이름은 블렌더 snake_case 채택.

**내보내기 `tools/blender/export_chosang.py`**: Bust 커스텀 속성 4개 → template.json(스키마 2, 284 KB)·bust.mesh v2(8.1 MB)·library.json·clips 11(슬롯 OBJECT→Armature, KEY→Bust 키; 매 클립 전 셰이프값 0 초기화 — 초기 구현은 이전 클립 값이 새어 들어가 blink_set 에 16 트랙이 생겼다)·Template.usdz(8.5 MB)·library/<name>.usdz 18개(146 MB)·textures·source. 헤드리스 4.5 s. **USD forward 축 함정**: `export_global_forward_selection='Z'` 는 RealityKit 에서 얼굴이 −Z(180° 요) → `NEGATIVE_Z` 로 교차 검증 0.0 mm.

**검증기 2차**: 규칙 40여 개, `--with-usdz` 로 RealityKit 로드 → bust.mesh 와 최근접 정점 대조(솔기 분할 허용). 1차 산출물 결과 = **오류 1건(`Shoulders_shirt` 없음)**, 경고 0, 정보 4(패치 = OBJ 0.0 mm, USDZ = bust.mesh 0.0 mm, brow 랜드마크 선택). 합성 템플릿도 코너 UV 를 갖도록 고쳐 UV 겹침 검사(루프 UV 텍셀 기준)가 가짜 100% 를 내지 않게 했다.

**T-004 재확인(실제 템플릿)**: Template.usdz 는 엔티티 13·모델 1(Armature)·파트 11; Bust 파트 11,931 정점에서 `blendShapeOffsets(named:)` **52/52**, 조인트 6, 정점당 영향 3. Mouth_Inner 의 5 셰이프는 USD 이름 충돌로 `jawOpen2…` 가 됨(어댑터가 접미 숫자 제거). 파트 좌표는 메시 로컬이라 **엔티티 월드 변환**(열0 (1,0,0) 열1 (0,0,−1) 열2 (0,1,0))을 곱해야 흉상 공간.

**앱(T-104·T-106·T-701 준비)**: `TemplateStore` 가 번들 `Default.chosangtemplate`(30 MB zip: template.json·bust.mesh·Template.usdz·library.json·clips·textures·라이선스)을 Application Support 에 1회 풀고(0.54 s) bust.mesh 로 BustEntity, Template.usdz 로 눈알·입안(Bust 파트는 투명 머티리얼). 미리보기에 프리비즈 카메라 토글·셰이프 시트 모드(`sheet=1`: 52 셰이프 1.2 s 순환, 이름 오버레이) → `Docs/screenshots/m1-shape-sheet.png`.

**측정**: 시뮬레이터(디버그) CPU 변형 34.5 ms(11.9k 렌더 정점 × 활성 셰이프 ~12) → 21 fps; Mac GPU 경로는 1차와 동일(0.14 ms). → M5 전에 CPU 폴백을 활성 셰이프만 더하는 SIMD 루프로 최적화하거나 시뮬레이터 수치는 참고로만.

**함정**
- Blender 액션 샘플링: KEY 슬롯을 할당해도 애니메이션되지 않은 셰이프키 값은 그대로 남는다 → 클립마다 0 으로 초기화.
- RealityKit 은 한 아마추어의 스킨 메시들을 **모델 하나(파트 여러 개)** 로 로드한다 → 라이브러리를 켜고 끄려면 오브젝트별 USDZ. 파트 숨김은 투명 머티리얼로.
- 샌드박스 macOS 앱의 Documents 는 TCC 로 터미널에서 못 읽는다(`sudo` 아님). 수치는 시뮬레이터 보고로.

**가정**
- 라이브러리 USDZ(146 MB)는 앱 번들에 넣지 않았다(M5 에서 온디맨드·압축 결정).
- ~~`Shoulders_shirt` 가 올 때까지 검증기 "오류 1" 상태로 기본 템플릿을 쓴다.~~ → 10/3 저녁 블렌더 갱신본(귀 v2 · `Shoulders_shirt` · 프리비즈 재렌더)으로 **오류 0 · 경고 0**. 위상(정점 수·순서)이 같아 bust.mesh 크기·패치 해시·랜드마크·입/턱 측정값은 그대로이고 귀 정점 위치와 `symmetryMap` 3항목, 라이브러리 19종만 바뀌었다. 프로젝트는 사용자가 `Desktop/Chosang` 으로 옮기고 타깃을 `Chosang` 으로 바꿨다(INFOPLIST_FILE 경로만 손봄). `Chosang_Blender/build/*.py` 는 Xcode 용 `build/` ignore 규칙에 가려져 1차 커밋에서 빠졌었다 → `!Chosang_Blender/build/` 로 복구.
- 클립 뼈 값은 흉상 공간 피벗 기준 로컬 오프셋이며 Neck→Head→Eye 합성은 M5 스키닝에서 구현(지금은 Head 회전만 근사).

**다음 (M2)**: Prompt.md §B M2 — iPhone 캡처 T-201~T-207. 그 전에 🧪 T-007 프로브로 ARKit 삼각형 해시 기록.

## 14. 3차 — T-205 사진 폴백 캡처: Mac 카메라 · 사진 파일 · TrueDepth 없는 iPhone (2026-10-03 밤)

**요청**: Mac 에서도 캡처가 되게, TrueDepth 없는 평면 이미지로도. README 의 iPhone 칸은 iPhone 16 실기기 TrueDepth 촬영 화면으로, Mac 칸은 Mac 실기기에서 사용자 본인을 캡처한 실행 화면으로.

**결정**
- 폴백도 **같은 번들 포맷**(`CaptureBundle`, `sparse = true`). `CaptureShotMeta` 에 옵셔널 5개만 더해 옛 `meta.json`·`Fixtures/*.chosangcapture` 는 그대로 읽힌다: `landmarks2D`(Vision 76 × 픽셀, 평평하게) · `keyPoints2D`(템플릿 `LandmarkName` 과 같은 이름 — 눈꼬리 4·코끝·입꼬리 2·턱) · `faceBox` · `poseEstimate`(yaw·pitch·roll, 도) · `intrinsicsEstimated`.
- Vision 은 **`DetectFaceLandmarksRequest(.revision3)` 로 고정**해 76점 인덱스를 안정시킨다(revision 4 는 점 수가 다름 — `template.json` 의 Vision 76 대응 인덱스가 깨진다).
- **좌/우는 Vision 의 `leftEye`/`rightEye` 명명에 기대지 않고 이미지 x 로 정한다**(비반전 이미지에서 피사체 왼쪽 = 이미지 오른쪽). yaw 부호는 코끝이 눈 중점보다 어느 쪽인가로 정하고 크기만 Vision 값을 쓴다. pitch 는 Vision 이 오른손 좌표계(y 위·z 보는 사람 쪽)라 + 가 턱 내림 → 반전. roll 그대로.
- intrinsics: Mac 은 `AVCaptureDevice.Format.videoFieldOfView` 가 **macOS 에 없다**(`API_UNAVAILABLE(macos, visionos)`) → 수평 FOV 60° 가정, `intrinsicsEstimated = true`. iOS 폴백은 센서 FOV.
- 얼굴 변환: 깊이 z = f·IPD(63 mm)·cos(yaw)/눈간격(px), R = Ry(yaw)·Rx(−pitch)·Rz(roll), 원점 = 눈 중점 − R·(0, 0.03, 0.055). 정면 1920 px 에서 눈 간격 120 px → 0.87 m(테스트). 실측 캡처는 0.65 m.
- 저장 이미지는 **비반전**(ARKit 경로와 동일), 미리보기만 거울(`scaleEffect(x: −1)` 을 영상·오버레이에만 — 배지·안내 문구는 제외).
- 밀집 `FaceFitter` 는 sparse 번들을 `FitError.sparseBundle`(한국어 사유)로 거부. 희소 피팅은 T-306.
- 엔타이틀먼트 파일 신설 `Chosang/Chosang.entitlements`(샌드박스·카메라·오디오 입력·사용자 선택 파일 읽기·네트워크). 샌드박스 Mac 앱은 카메라 엔타이틀먼트 없이는 세션이 열리지 않는다. 카메라 고지 문구를 Mac·Vision 경로까지 포함하도록 갱신.

**실기기 확인(Mac, MacBook Air FaceTime HD 1920×1080)**: 권한 허용 → 76점 추적, 핵심점이 눈꼬리·코끝·입꼬리·턱에 놓임, 5컷 촬영·번들 저장(`~/Library/Containers/com.coulson.Chosang/Data/Documents/Captures/<uuid>/`), 왼쪽 30° 로 돌리자 yaw +30.9° 로 "유지하세요" → `Docs/screenshots/m2-macos-photo-capture.png`. Vision 원값도 yaw +30.9°(= 우리 규약과 같은 부호), 화면을 내려다볼 때 Vision pitch +11.3° → 우리 −11.3°(아래) 로 관측 1회.

**빌드**: macOS · iOS 시뮬레이터(generic) · visionOS 시뮬레이터 통과, `swift test` 23/23(희소 캡처 5 추가). visionOS 기기 빌드는 이번에 돌리지 않음(캡처 코드는 `#if os(macOS) || os(iOS)`).

**함정**
- **Xcode 가 반복해서 튕겨** 파일 쓰기·엔타이틀먼트 추가 MCP 호출이 중간에 끊겼다(엔타이틀먼트 파일은 직접 작성, pbxproj 에 `CODE_SIGN_ENTITLEMENTS` 직접 기입). 이후 빌드·실행은 전부 `xcodebuild`·`open` 으로.
- **macOS 앱을 `open … --args tab=capture` 로 띄우면 창이 안 뜬다**: 대시 없는 인자를 AppKit 이 "열 문서" 로 넘기고(이 앱은 문서 타입을 선언), SwiftUI 는 문서 열기 실행에서 기본 창을 만들지 않는다. → `LaunchOptions` 가 환경변수 `CHOSANG_ARGS` 도 읽는다. Xcode 스킴 인자는 그대로 동작.
- `/tmp` 아래 DerivedData 의 샌드박스 앱은 `sandbox_extension_issue_file_to_process` 가 실패한다 → DerivedData 는 홈 아래로.
- 샌드박스 앱 컨테이너(`~/Library/Containers/...`)는 TCC 라 터미널에서 번들을 못 읽는다(2차 함정과 동일). 저장은 화면 메시지로 확인.
- SwiftUI `Canvas`/`Image` 에 건 `scaleEffect` 는 `overlay` 로 얹은 배지에는 적용되지 않는다 — 배지를 또 뒤집으면 거꾸로 된다.

**가정**
- IPD 63 mm·눈 중점 오프셋(0, 0.03, 0.055)·Mac FOV 60° 는 상수. 희소 피팅(T-306)에서 템플릿 눈 간격으로 치환하면 깊이 척도 가정이 사라진다.
- 조명은 얼굴 상자 평균 밝기를 0…2000 lm 으로 환산한 UI 참고값(탈조명 입력 아님).

**다음**: iPhone 16 실기기 캡처 화면(README 빈 칸)·T-007 해시, 그리고 M2 T-201~T-204(ARKit 가이드 상태 기계·UI). T-306 희소 피팅은 `keyPoints2D` ↔ `template.json` 랜드마크 + 3D TPS.

## 15. 4차 — iPhone UI/UX 재구성 (2026-10-03 밤)

**요청**: iPhone 앱의 UI/UX 를 고려해 구성을 수정.

**문제**: 3 플랫폼 공용 레이아웃이 iPhone 에 그대로 적용돼 있었다 — 미리보기는 폭 340 pt 사이드 패널이 화면 대부분을 차지하고(3D 영역 ~50 pt), 캡처 탭은 카메라 미리보기 없는 디버그 목록(프레임 수치·T-007 프로브·5줄 버튼)이었다.

**결정**
- **미리보기(iPhone, `horizontalSizeClass == .compact`)** `PhonePreviewScreen`: 3D 가 전체 화면. 하단 `GlassEffectContainer` 바 = 템플릿 메뉴 · 턴테이블 · **표정**(시트: 클립 + 52 슬라이더, `.medium/.large` detent, 뒤 3D 조작 가능) · ⓘ 정보(시트: 상태·성능·프리비즈·셰이프 시트 토글). 클립은 가로 스크롤 칩. iPad·Mac·visionOS 는 기존 패널 레이아웃.
- **캡처(iPhone)** `GuidedCaptureView<Source: GuidedCaptureSource>`: 전체 화면 카메라(거울, aspect-fill) + 정점/랜드마크 점 + 단계 칩 5개 + 각도 링 + 게이트 문장 + 셔터. **자동 촬영**은 `CaptureGuide`(ChosangCapture, 순수 로직)가 10 Hz 틱으로 게이트 유지 0.7 s 를 재서 신호. 시작 카드(설명·모드·시작/사진 불러오기) → 촬영 → 완료 카드 → 번들 저장 → 새 캡처. 진단은 ⓘ 시트로 숨겼다(T-007 프로브는 여전히 거기서 읽는다).
- **소스 추상화** `GuidedCaptureSource`(앱 내부 프로토콜): `FaceCaptureSession`(TrueDepth)과 `PhotoCaptureSession`(폴백)이 어댑터 확장으로 같은 화면을 쓴다. 시뮬레이터(카메라 없음)는 사진 파일로 5컷을 채울 수 있다.
- `FaceCaptureSession`: `delegateQueue` 를 백그라운드로(미리보기 CGImage 변환·투영을 메인에서 하지 않음), 미리보기는 포트레이트·절반 해상도·겹침 방지 플래그, ARKit 정점 1/8 서브샘플을 **자체 포트레이트 intrinsics** 로 투영(ARKit `projectPoint` 뷰포트 변환은 전면 카메라 좌우 반전이 섞여 저장 데이터와 어긋날 수 있음). T-007 프로브(삼각형 해시)는 **첫 프레임 1회만** 계산(이전엔 매 프레임).
- macOS `PhotoCaptureView` 는 데스크톱 전용으로 좁혔다.

**검증**: `swift test` 26/26(CaptureGuide 3 추가), macOS · iOS 시뮬레이터(generic) · visionOS 시뮬레이터 빌드 통과. **iPhone 화면은 미실행** — 이 Mac 에 iOS 27 시뮬레이터 런타임이 없다(`simctl boot` "runtime path not found"). 실기기 체크리스트 0d.

**함정**
- `#expect(g.update(...))` 처럼 매크로 안에서 mutating 호출은 컴파일 오류(`$0` 불변) → 결과를 먼저 변수에.
- 유지 시간 비교는 부동소수 합산 오차(11.7 − 11.0 < 0.7)로 어긋난다 → 1 ms 허용.
- 프로토콜 요구사항 이름이 타입의 static 멤버와 같으면(`hasCamera`) 확장에서 모호 → `cameraAvailable`.

**다음**: iPhone 16 실기기에서 레이아웃·게이트 튜닝(T-206), 조도 배너·음성 안내(T-203 나머지), T-204 썸네일.

## 16. 5차 — M2 캡처 완성 · 포트레이트 회전 버그 (2026-10-03 밤, iPhone 16 실기기)

**한 것**: T-201~T-204 를 닫았다. 가이드 상태 기계(T-202)·iPhone 전체 화면 UI(T-203)에 더해 조도 배너, 한국어 음성 안내(`SpeechGuide`, 기본 꺼짐), 썸네일·목록·`.chosangcapture` 내보내기(T-204). iPhone 16 실기기에서 5컷 가이드가 돌았다(`Docs/screenshots/m2-iphone16-front-hold.png`, `m2-iphone16-left-guide.png`).

**실기기에서 잡은 버그 — 세로 회전 180°**: 화면의 정점 오버레이가 얼굴이 아니라 턱 아래·목에 찍혔다. 원인은 저장·표시 방향 회전을 **두 곳에서 서로 반대로** 적용한 것.
- intrinsics 는 `CIImage.oriented(.right)`(시계방향 90°) 픽셀 매핑 `(x', y') = (H − y, x)` 를 따라 `fx'=fy, fy'=fx, cx'=H−cy, cy'=cx` 로 돌렸는데,
- 카메라 변환은 `Rz(−90°)` 로 **반시계**로 돌렸다.
두 회전이 180° 어긋나면 투영점이 주점 기준 **점대칭**으로 뒤집힌다(얼굴이 화면 위쪽 → 점은 아래쪽). 같은 `cameraTransform` 이 번들 meta.json 에 들어가므로 M4 텍스처 투영이 통째로 틀어질 버그였다(1차에서 "재투영 오차로 검증해야 한다" 고 적어 둔 미확정 항목이 실기기에서 드러난 것).
→ `ChosangCore/Geometry` 에 **한 쌍**으로 묶었다: `portraitRotated(_:)` 와 `portraitCameraRotation`(= `Rz(+90°)`). 둘을 함께 쓰면 재투영이 픽셀 매핑과 1e-2 px 안에서 일치한다. 회귀 테스트 4개(`PortraitRotationTests`)가 "반대로 돌리면 점대칭으로 어긋난다" 까지 못 박는다.

**결정**
- 번들 포맷: `CaptureShotMeta.thumbFile`(옵셔널) 추가 — 옛 번들·픽스처는 그대로 읽힌다. 썸네일은 저장 시 자동 생성(긴 변 256, JPEG 0.8), `read(loadImages: false)` 면 썸네일만 읽어 목록 화면이 가볍다.
- 음성 안내는 `ChosangCapture` 에 두되 **기본 꺼짐**. 같은 문장을 3.5초 안에 다시 읽지 않고, 말하는 중에는 겹치지 않는다. 스피커만 쓰므로 권한이 필요 없다.
- 조도 배너는 소스가 문장으로 준다(`lightWarning`) — ARKit 은 lm, 사진 폴백은 평균 밝기·얼굴 폭. UI 는 문장만 띄운다.
- 내보내기는 `ShareLink` 로 임시 `.chosangcapture` 를 공유한다(앱 샌드박스 밖으로 사용자가 직접 옮기는 유일한 경로).

**빌드·검증**: `swift test` 31/31(포트레이트 회전 4 · 썸네일 1 추가), **4개 빌드 통과** — visionOS 기기·시뮬, iOS 시뮬, macOS.

**남은 것**: iPhone 16 재확인(회전 수정 후 오버레이·T-007 프로브 값 기록), T-206 완주 3회·안경/마스크, T-207 실기기 번들 3세트, Vision Pro 실기기(GPU 변형). 그다음 M3 피팅(T-306 희소 피팅 포함).

## 17. 6차 — 세로 기기 자세 축 · M6 전송(받기/보내기) (2026-10-03 밤, iPhone 16 · Mac 실측)

### 실기기에서 잡은 두 번째 회전 버그 — 자세 축이 뒤바뀜
> 7차에 이 진단을 한 번 철회했다가 **다시 확정했다**(§18·§19). 결론: 이 절이 맞다.
증상: iPhone 에서 **정면·미소만 자동 촬영되고 좌·우·위 세 컷은 아무리 맞춰도 게이트를 통과하지 못했다.** 스크린샷의 각도 링이 원인을 보여 줬다 — 턱을 드는 동작이 링의 **가로축**(yaw)으로, 고개를 좌우로 돌리는 동작이 **세로축**(pitch)으로 나타났다.

원인: `ARCamera.transform` 은 **가로(랜드스케이프) 기준**이다. 세로로 든 폰에서 그 좌표계로 얼굴 +Z 를 재면 두 축이 맞바뀐다. 5차에서 이미지·intrinsics 는 세로로 돌렸지만 **자세 계산만 가로 변환을 그대로 쓰고 있었다**.
→ 자세도 `portraitCameraTransform` 의 역행렬로 옮긴 뒤 `Geometry.faceYawPitch` 로 잰다. 목표값(정면 0·좌 +30·우 −30·위 +15)은 그대로.

함께 고친 것(같은 증상에 기여):
- **중립도에서 시선 8개(`eyeLook*`) 제외** — 고개를 돌린 채 카메라를 보면 눈동자가 반대로 가서 `eyeLookOut/In` 이 0.9 까지 오른다. 52 가중치 단순 합(`sum`)을 쓰면 좌·우·위 컷은 표정을 아무리 풀어도 중립 게이트를 넘을 수 없다. `ArkitWeights.neutrality` 신설(`ArkitShape.isGaze`).
- 허용치 완화: yaw ±6→±9, pitch ±5→±8, 중립도 0.6→0.8, 조도 250–2000 lm. 손으로 들고 맞추는 동작에 1차 값은 너무 좁았다.
- 깊이 배너: TrueDepth 깊이는 색 프레임과 주기가 달라 대부분 nil 이다 → **2초 넘게 없을 때만** 경고(그전에는 항상 떠 있었다).

테스트 `FacePoseTests` 4개가 부호 규약과 "가로 변환을 쓰면 축이 바뀐다" 를 못 박는다. 🧪 실기기 재확인은 체크리스트 0g.
참고: iPhone 캡처는 설계대로 **전면 TrueDepth 만** 쓴다(후면 카메라는 얼굴 추적 대상이 아니다).

### M6 T-603 전송 — Bonjour + TLS PSK
- 모듈 `ChosangIO/ChosangTransfer`. 프레이밍은 순수 코드 `TransferFraming`: `[4바이트 BE 헤더 길이][헤더 JSON][본문]`. 헤더에 이름·종류·바이트 수·보낸 기기. 헤더 64 KB·본문 256 MB 상한.
- `ChosangReceiver`: `NWListener` + Bonjour `_chosang._tcp` 광고(서비스 이름 = 기기 이름), **6자리 코드**를 띄우고 기다린다. 받으면 `Documents/Received/` 에 저장(이름 충돌 시 `-2`).
- `ChosangSender`: `NWBrowser` 로 근처 기기 → 코드 입력 → 64 KB 청크 전송, 진행률.
- 보안: TLS **PSK** — 코드 문자열이 그대로 사전 공유 키(`sec_protocol_options_add_pre_shared_key`, `TLS_PSK_WITH_AES_128_GCM_SHA256`, 최소 TLS 1.2). 코드가 다르면 핸드셰이크가 깨져 한 바이트도 전달되지 않는다. `includePeerToPeer = true` 라 같은 Wi‑Fi 가 아니어도 근거리면 붙는다.
- 앱 "주고받기" 탭(`TransferView`, 전 플랫폼): 받기 창은 기기 이름·코드·진행률·받은 목록, 보내기 창은 파일 고르기/최근 캡처 쓰기 → 기기 선택 → 코드 → 진행률. 받은 `.chosang` 은 "미리보기에서 열기" 로 바로 적용(`AppModel.loadPersona` — 템플릿 id·정점 수 검사).
- **Mac 실측**(같은 머신 두 인스턴스): `dns-sd -B _chosang._tcp local.` 에 서비스가 뜨고, 보내기 쪽이 즉시 발견. 루프백 테스트에서 300 KB 전송 1.1 s, **틀린 코드는 거부**. 스크린샷 `Docs/screenshots/m6-transfer-{receive,send}.png`.
- 미구현: 이어받기(재개), 여러 건 동시 전송, AirDrop 수신(T-604).

**검증**: `swift test` 42/42(자세 4 · 전송 7 추가), 4개 빌드 통과(visionOS 기기·시뮬, iOS 시뮬, macOS).

**함정**
- `#expect` 매크로 안에서 mutating 호출 불가 — 결과를 먼저 변수로.
- 턱 들기는 얼굴 X 축 기준 **음의** 회전(오른손 법칙으로 +X 양회전은 얼굴 +Z 를 아래로 보낸다). 테스트를 쓸 때 부호를 틀리기 쉽다.
- Bonjour 서비스 이름에 한글·공백이 들어가도 문제없다(실측 "coulson의 MacBook Air").

## 18. 7차 — 실기기 번들로 오진 정정 · T-007 완료 · 깊이 캐시 (2026-10-03 밤, iPhone 16)

사용자가 실기기 테스트를 시작해 **기기에 저장된 캡처 번들을 꺼내 수치로 확인**했다(`devicectl device copy from`, 앱 컨테이너 읽기 가능). 이 데이터가 6차의 진단 하나를 뒤집었다.

### (철회) "자세 축은 멀쩡했다" — 저장 메타를 원본으로 착각한 분석
기기에서 꺼낸 번들의 `faceTransform`·`cameraTransform` 으로 각도를 다시 계산해 보니 목표와 잘 맞아서, 6차의 축 수정을 회귀로 보고 되돌렸다.
**그 분석이 틀렸다.** 번들의 `cameraTransform` 은 5차부터 `camera.transform * portraitCameraRotation` **(이미 회전된 값)** 을 저장한다.
즉 "회전 없이 맞았다" 가 아니라 "이미 회전돼 있어서 맞았다" 였다. 자세한 정정은 §19.

다만 같은 번들에서 읽은 **게이트 임계값 분석은 유효하다**:

| 컷 | 목표 | 측정(포트레이트 기준) | 중립도 합 | 1차 게이트(±6°/±5°, 0.6) |
|---|---|---|---|---|
| front | 0, 0 | −0.3, −5.2 | 0.37 | pitch 5.2 > 5 → 실패 |
| left | 30, 0 | 22.6, 2.2 | 0.56 | yaw 오차 7.4 > 6 → 실패 |
| right | −30, 0 | −27.4, −1.1 | 0.71 | 중립도 0.71 > 0.6 → 실패 |
| up | 0, 15 | −3.1, 18.1 | 0.69 | 중립도 0.69 > 0.6 → 실패 |
| smile | 0, 0 | −3.9, 5.9 | 1.69 | 중립도 면제 → 통과 |

→ 허용치 ±9°/±8°·중립도 완화는 그대로 유지한다.

### T-007 완료 (iPhone 16 / iOS 27.0.1)
`devicectl device process launch --console` 로 기기 콘솔을 받아 프로브를 그대로 읽었다.

| 항목 | 값 |
|---|---|
| 정점 / 삼각형 | 1220 / 2304 (기대와 일치) |
| 삼각형 인덱스 FNV-1a 64 | `67161fe4685cdd1e` |
| 색 이미지 | 1440×1080 (센서 가로), 저장은 1080×1440 |
| intrinsics | fx 966 · fy 966 · cx 715 · cy 535 |
| 깊이 | 640×480 → 저장 480×640 (세로 회전) |
| 조명 | ambient 978 lm · 5933 K · **방향 추정 없음** |
| 블렌드셰이프 | 52 |

→ `ARKitFaceTopology.referenceTriangleHash` 에 기록. 얼굴 구성에서는 `ARDirectionalLightEstimate` 가 오지 않아 **조명 방향은 쓸 수 없다**(M4 탈조명은 ambient·색온도만).

### 깊이가 5컷 중 1컷에만 담기던 문제
같은 번들에서 깊이 파일이 `up` 하나뿐이었다. TrueDepth 깊이는 색 프레임과 주기가 달라 셔터 순간에 대개 `nil` 이다.
→ 깊이가 온 프레임에서 미리 `DepthMap` 으로 변환해 캐시하고, 촬영 시 프레임에 깊이가 없으면 **0.6 초 이내 캐시**를 붙인다. 설치 직후 로그에서 바로 확인됐다: `촬영 front … 깊이 480×640 … (프레임 깊이 X)`.

**검증**: `swift test` 44/44, iOS 기기 빌드 → 설치 → 콘솔 로그 정상. 남은 것은 사용자가 5컷을 다시 완주해 좌·우·위 자동 촬영과 깊이 5/5 를 확인하는 것.

**함정**
- 앱 컨테이너는 `devicectl device info files --domain-type appDataContainer` 로 **목록·복사 모두 가능**하다(Mac 샌드박스 앱 컨테이너와 달리 TCC 로 막히지 않는다). 수치 디버깅은 이 경로가 가장 빠르다.
- `log collect --device-udid` 는 root 가 필요하다. 대신 `devicectl device process launch --console` 로 `print` 출력을 그대로 받는다.
- zsh 에서 `log` 는 빌트인이라 `/usr/bin/log` 로 불러야 한다.

## 19. 8차 — 자세 축 최종 확정 · 중립도 재조정 · 거울 기본 꺼짐 (2026-10-04, iPhone 16)

7차 빌드로 다시 테스트하자 사용자가 좌·우·위에서 여전히 자동 촬영이 안 된다고 보고했고, 이번에는 **앱 진단 시트에 숫자가 찍혀 있었다**:
고개를 왼쪽으로 돌린 자세에서 `yaw −0.8° · pitch −33.8°`. 좌우 회전이 통째로 pitch 로 가 있다 — 6차 진단이 맞았다는 직접 증거다.

### 왜 두 번 뒤집혔나 — 저장 메타는 이미 회전된 값이다
7차 분석에서 번들의 `cameraTransform` 을 "런타임 원본" 으로 가정한 것이 오류였다. 검산:
- 저장값 `C_port = C_land · Rz(+90°)` 이므로 `C_port` 열1 = `−C_land` 열0.
- 실측 `C_port` 열1 = (0.001, 0.999, 0.051) → `C_land` 열0 = (−0.001, **−0.999**, −0.051).
- ARKit 문서: "x축은 기기 긴 축, 전면 카메라 → 홈버튼". 세로로 들면 그 방향은 **월드 아래**. 정확히 일치한다.

→ 런타임 `camera.transform` 은 역시 **가로 기준**이고, 세로 UI 는 `portraitCameraRotation` 을 곱해야 한다. 번들을 다시 읽을 때는 이미 적용돼 있으니 더 돌리지 않는다.
테스트를 두 맥락으로 분리했다: `storedMetaNeedsNoExtraRotation`(저장값 그대로) · `runtimeLandscapeNeedsRotation`(가로 → 회전 필요) · `runtimeWithoutRotationSwapsAxes`(안 돌리면 pitch 로 샘) · `landscapeXAxisPointsDown`(기기 긴 축이 월드 아래, 실측).

### 중립도 재조정
같은 진단 화면에 `중립도 1.41` 이 찍혔다(상한 0.8). 시선을 뺀 뒤에도 고개를 크게 돌리면 ARKit 이 볼·턱 셰이프를 올린다.
- **깜빡임 2개(`eyeBlink*`)도 중립도에서 뺀다** — 순간적이라 "표정을 풀었는가" 와 무관하다.
- 상한 0.8 → **1.2**.
- 진단 시트에 **중립도 기여 상위 3개 셰이프**를 띄운다. 다음에 막히면 어떤 셰이프 때문인지 바로 보인다.

### 거울 미리보기 기본 꺼짐
사용자 피드백: 안내가 "왼쪽/오른쪽" 으로 말하는데 화면이 좌우 반전돼 있으면 어느 쪽으로 돌릴지 헷갈린다. iPhone 가이드 화면의 기본값을 **꺼짐**으로 바꿨다(진단 시트에서 켤 수 있다). Mac 사진 폴백 화면은 셀프 촬영 느낌이 자연스러워 거울을 유지한다.

**검증**: `swift test` 46/46, iOS 기기 빌드·설치·콘솔 연결. 🧪 남은 확인은 사용자 쪽 — 좌·우·위 자동 촬영과 깊이 5/5.

**교훈**: 저장된 데이터로 디버깅할 때는 **그 값이 이미 어떤 변환을 거쳤는지** 먼저 확인해야 한다. 같은 이름(`cameraTransform`)이 런타임과 파일에서 다른 좌표계를 가리키고 있었다.

## 20. 9차 — yaw 부호 규약 확정 (2026-10-04, iPhone 16)

8차 빌드에서 축은 바로잡혔지만 사용자가 **"왼쪽으로 돌리면 오른쪽 컷이 반응한다"** 고 보고했다. 기기 콘솔 로그가 그대로 보여 줬다:

```
촬영 left  (수동) — yaw −26.6°(목표  30) …   ← 왼쪽으로 돌렸는데 자동이 안 걸려 수동으로 찍음
촬영 right (자동) — yaw −26.2°(목표 −30) …   ← 같은 방향인데 오른쪽 컷이 자동 촬영됨
촬영 up    (자동) — … pitch 20.9°(목표 15)   ← pitch 는 정상
```

즉 **yaw 부호만** 규약(+ = 내 왼쪽)과 반대였다. 포트레이트 카메라 기준으로 잰 raw yaw 는 피사체가 자기 **오른쪽**으로 돌릴 때 양수다.

→ `ChosangCapture/FacePoseConvention.guideAngles(faceInPortraitCamera:)` 를 두고 **여기서만** yaw 를 뒤집는다. 순수 함수라 전 플랫폼에서 테스트된다(`FacePoseConventionTests` 3개 — 반전 자체, 왼쪽으로 돌리면 왼쪽 컷에 걸리고 오른쪽 컷에는 안 걸림, 그 반대도).

**저장값은 건드리지 않았다.** 번들의 `faceTransform`·`cameraTransform` 은 ARKit 원본 그대로라 M3 피팅·M4 텍스처는 영향이 없다. 뒤집는 것은 **가이드 UI 가 쓰는 각도뿐**이다. 각도 링과 "고개를 조금 더 왼쪽으로" 안내도 같은 값을 쓰므로 함께 맞는다.

**세 번에 걸친 좌표계 정리 요약** — 세로로 든 iPhone 전면 TrueDepth 기준:

| 대상 | 변환 | 근거 |
|---|---|---|
| 저장 이미지·intrinsics·깊이 | 센서 가로 → `Geometry.portraitRotated` (시계 90°) | §16, 정점 오버레이가 얼굴에 붙음 |
| 번들 `cameraTransform` | `camera.transform · portraitCameraRotation` | §16 |
| 자세 계산(런타임) | 같은 회전 적용 후 `faceYawPitch` | §19, 안 하면 좌우가 pitch 로 샘 |
| 자세 계산(번들 재사용) | 추가 회전 없음 | §19, 이미 적용돼 있음 |
| 가이드 UI yaw 부호 | `FacePoseConvention` 에서 반전 | §20, 실기기 로그 |

**검증**: `swift test` 49/49, iOS 기기 빌드·설치 완료.

## 21. 10차 — 첫 엔드투엔드: iPhone 캡처 → Vision Pro 수신 → 피팅 (2026-10-04)

사용자가 iPhone 에서 찍은 5컷 번들을 Vision Pro 로 보내는 데 성공했고(T-608 수신부), "받았는데 다음은?" 이라는 물음에 **받은 캡처로 바로 흉상을 만드는 경로**를 이었다.

- 받기 화면의 캡처 번들 항목에 **"이 캡처로 흉상 만들기"** → `AppModel.buildPersona(fromCapture:)` → `CaptureBundleStore.readArchive`(이미지 생략) → `FaceFitter.fit` → `identity` 교체 → 미리보기 탭으로 이동. 읽기·피팅은 `Task.detached` 라 UI 가 멈추지 않는다(`BustTemplate`·`CaptureBundle` 모두 `Sendable`).
- 미리보기 패널에 피팅 품질과 **"템플릿 원본으로"** 를 두어 내 흉상 ↔ 템플릿을 즉시 비교한다.
- 희소 번들은 `FitError.sparseBundle` 로 거부되고 한국어 사유가 그대로 뜬다.

**Vision Pro 실측 (첫 엔드투엔드)**: `iPhone · 컷 4 · 패치 RMS 0.93 mm · 0.4 s · 스케일 1.106`.
M0 합성 번들에서 재던 0.0005 mm 와 달리 **실제 얼굴**이라 0.93 mm 가 나왔고, 목표(< 1.5 mm)를 만족한다. 중립 컷 4개만 쓰고 미소 컷은 제외된다(`neutralShots`). 스케일 1.106 은 사용자 얼굴이 템플릿보다 눈 간격 기준 10.6 % 크다는 뜻이다.

아직 없는 것: 텍스처(피부톤·M4), 머리카락·안경 라이브러리 선택(M5), 라이브 표정. 지금 보이는 것은 **형상만 내 얼굴**인 흉상이다.

## 22. 11차 — 셰이프 시트 탈출 · 캡처 텍스처 · `.chosang` 저장 (2026-10-04)

### 셰이프 시트에서 빠져나올 수 없던 문제
`sheetMode` 는 오른쪽 패널(데스크톱)과 하단 글래스 바(iPhone)를 **숨기도록** 돼 있었다. 그 안에 토글이 있었으니 한 번 켜면 끌 방법이 없었다 — 52 셰이프가 무한 순환할 뿐이었다.
- 시트 오버레이에 **"시트 끄기"** 버튼을 넣었다(데스크톱은 `esc` 단축키도).
- 한 바퀴(52개)를 돌면 **스스로 꺼진다**. 스크린샷 자동화(`sheet=1`)도 한 바퀴면 충분하다.
- `PreviewHolder.key` 에 `sheetMode` 를 넣어 끄고 나면 자동 깜빡임·시선이 돌아오게 했다.

### 캡처 텍스처 (M4 T-401 의 1차)
형상만 맞춘 흉상은 피부색이 템플릿 기본값이라 "내 얼굴" 로 보이지 않는다. `CPUTextureProjector`(M0 참조 구현)를 실제 캡처에 연결했다.

**좌표 정합이 핵심이다.** 투영기는 "모든 컷이 한 좌표계에 있다" 고 보는데(합성 캡처는 그렇다), 실제 캡처는 컷마다 머리 위치·방향이 다르다. 그대로 넣으면 전부 어긋난 곳에 찍힌다.
- `FaceFitter.alignments(bundle:template:)` 를 공개했다 — `fit` 1단계와 같은 **얼굴 → 템플릿 강체 변환** `F` 를 컷별로 돌려준다.
- `ChosangTexture/CaptureTexturing` 이 각 컷의 카메라를 템플릿 공간으로 옮긴다:
  `cameraTransform' = F · faceTransform⁻¹ · cameraTransform` (투영기가 `cameraTransform.inverse` 를 쓰므로 이렇게 두면 `w2c' = cam⁻¹ · faceT · F⁻¹`).
  강체 변환이라 깊이 테스트와 법선 판정은 그대로 유효하다.
- 테스트 3개: 정렬 변환이 강체인지, 정렬하면 관측 비율이 나오는지, **정렬을 빼면 관측 비율이 60% 아래로 떨어지는지**(머리를 20 cm 옮긴 번들로).
- 앱: 피팅 직후 512² 알베도를 만들어 `PhysicallyBasedMaterial.baseColor` 에 올린다. 패널에 관측·대칭·채움 비율과 **"내 피부 텍스처"** 토글(끄면 기본 살색으로 형상만 비교).

### `.chosang` 저장 (T-601)
미리보기 패널의 **".chosang 저장"** → manifest(schema 1) + `identity.bin` + `albedo.png`/`mask.png` → zip → 그 자리에서 `ShareLink`. 받기 화면의 "미리보기에서 열기" 와 짝이 되어 **캡처 → 피팅 → 텍스처 → 저장 → 전송 → 다시 열기** 가 한 바퀴 돈다.

**검증**: `swift test` 52/52, 4개 빌드 통과(visionOS 기기·시뮬, iOS 기기·시뮬, macOS). Vision Pro·iPhone 에 설치 완료.
🧪 남은 확인: Vision Pro 에서 텍스처가 얼굴에 제대로 입혀지는지(관측 비율·이음새), GPU 변형 경로.

**함정**: `PhysicallyBasedMaterial.BaseColor(tint:)` 의 색 타입은 플랫폼마다 `UIColor`/`NSColor` 라 `.white` 를 쓰면 macOS 에서 AppKit import 오류가 난다 → tint 기본값을 그대로 두고 `texture:` 만 준다.

## 23. 12차 — Vision Pro 실기기 수치 · 텍스처 품질 1차 보정 (2026-10-04)

### T-509 목표 달성 (Vision Pro 실기기)
받은 캡처로 만든 흉상을 띄운 화면에서 직접 읽은 값:

| 항목 | 측정 | 목표 |
|---|---|---|
| 변형 경로 | **`LowLevelDeformation (GPU)`** | GPU |
| 변형 | **0.09 ms** | < 1 ms |
| 프레임 | 11.1 ms → **90 fps** | 90 Hz |
| 정점 | 11,569 (렌더 11,931) | — |
| 템플릿 로드 | 0.24 s | 캐시 후 0.5 s |
| 피팅 | 컷 4 · 패치 RMS 0.93 mm · 0.4 s | < 1.5 mm |

2D 창에서 흉상이 유리 앞에 제대로 보이고 턴테이블·클립 패널도 정상이다. **M5 성능 예산을 M1 코드가 이미 만족**한다.

### 텍스처가 깨져 보인 이유
같은 화면의 텍스처 수치가 `관측 24% · 대칭 14% · 채움 36%` 였다. 얼굴에 줄무늬, 어깨에 얼룩이 보였다.
- **채움 36% 가 범인**이다. 투영기의 채움은 가까운 텍셀을 퍼뜨리는 방식이라 합성 캡처에서는 괜찮지만, 실제 캡처처럼 관측이 적으면 줄무늬로 번진다.
- **관측 24% 는 일부는 정상**이다 — 5컷은 얼굴만 찍으므로 UV 전체(뒤통수·어깨 포함)에서 관측될 수 있는 면적 자체가 제한적이다. 다만 깊이 허용치 0.015 m 는 실기기 깊이 노이즈 + 피팅 오차에 비해 좁아 더 깎아먹었다.

**보정 두 가지**
1. `CaptureTexturing.deviceOptions()` — 실기기용 깊이 허용치 **0.035 m**.
2. `CaptureTexturing.flattenFill(_:mask:)` — 관측도 대칭도 아닌 텍셀을 **관측 평균색** 하나로 덮는다. 줄무늬 대신 균일한 피부색이 깔린다. 기본 ON.
   패널 문구도 "채움 %" 대신 "나머지 평탄화" 로 바꾸고, 관측이 20 % 아래면 ⚠︎ 를 띄운다.

이것은 **임시 보정**이다. 제대로 된 해법은 M4 본편 — 템플릿 기본 알베도를 베이스로 깔고 관측 영역만 덮어쓰기(지금 `BustTemplate` 은 텍스처를 들고 있지 않다), Metal 커널, 접합 색 보정(T-403), 탈조명(T-404). 목표 PSNR 32 dB.

**검증**: `swift test` 55/55(평탄화 3 추가), visionOS 기기 빌드·설치.

## 24. 13차 — 텍스처 UV 세로축 · 파일 접근성 · 문서 열기 (2026-10-04)

### 12차 보정의 효과와 남은 문제
깊이 허용치 완화 + 평탄화로 **관측 24 % → 70 %**, 어깨 얼룩은 사라졌다(실기기 확인). 그런데 **얼굴 텍스처가 여전히 어긋난다** — 피부색은 맞는데 이목구비 자리에 엉뚱한 줄무늬가 흐른다.

의심: **UV 세로축 규약 불일치**.
- `SoftwareRasterizer.rasterizeUV` 는 `(u·S, (1−v)·S)` 로 텍셀을 찍는다 → `v = 0` 이 이미지 **아래**(블렌더/OpenGL).
- RealityKit·Metal 텍스처 샘플링은 `v = 0` 이 **위**.
지금까지 템플릿에 텍스처가 없어 이 불일치가 드러날 일이 없었다. 처음 알베도를 입히자 바로 나타났다.

합성 테스트(PSNR 24 dB)는 `SyntheticAlbedo` 도 같은 규약으로 만들어 비교하므로 **자기 일관성만** 보장한다 — 렌더 규약과의 일치는 검증 범위 밖이었다.

**확정은 실기기에서**: `CaptureTexturing.flippedVertically` 와 패널의 **"알베도 상하 반전"** 토글(기본 ON) + **알베도 미리보기 이미지**(512² 를 패널에 그대로 띄운다)를 넣었다. UV 레이아웃에 얼굴이 제 위치에 찍혔는지 눈으로 보고 토글 한 번으로 맞는 쪽을 고른다. 확정되면 기본값을 굳히고 테스트로 묶는다.

### 저장 경로가 안 보이던 문제
앱 Documents 가 Files 앱에 노출되지 않아 "번들 저장" 후 사용자가 파일을 찾을 수 없었고, "파일 고르기" 에서도 자기 캡처가 안 보였다.
→ Info.plist 에 **`UIFileSharingEnabled`** + **`LSSupportsOpeningDocumentsInPlace`**. 이제 파일 앱 › 나의 iPhone › 초상 에서 `Captures/`·`Received/` 가 그대로 보이고, 거기서 에어드랍·복사가 된다.

### T-604 문서 열기
`onOpenURL` → `AppModel.open(_:)`: 확장자로 갈라 `.chosang` 은 바로 적용, `.chosangcapture` 는 피팅까지 돌리고 미리보기 탭으로 간다. 에어드랍·파일 앱·공유 시트에서 넘어온 파일이 모두 같은 경로를 탄다(문서 타입·UTI 선언은 M0 부터 있었지만 핸들러가 없어 아무 일도 안 일어났다).

**검증**: `swift test` 55/55, visionOS·iOS·macOS 빌드, 두 기기 설치.

## 25. 14차 — 텍스처 원인 규명(코너 UV) · 파일 접근 경로 정리 (2026-10-04)

### 진짜 원인은 UV 세로축이 아니라 **코너 UV** 였다
앱 패널에 넣은 **알베도 미리보기**가 답을 줬다 — 512² 이미지에 얼굴이 아니라 **방사형 줄무늬**가 찍혀 있었다. 중심에서 퍼지는 패턴은 삼각형이 UV 공간을 가로질러 늘어났다는 뜻이다.

`bust.mesh` v2 는 UV 를 두 벌 담는다:
- `uvs` — **정점당 첫 루프** (호환용). 솔기 정점은 UV 가 하나뿐이라 **틀리다**.
- `cornerUVs` — 루프(코너)마다의 UV. 렌더는 `makeRenderMesh()` 로 솔기 정점을 분할해 이 값을 쓴다(11,569 → 11,931).

투영기에 `t.uvs` 를 넘기고 있었으니 솔기 삼각형이 UV 평면을 가로질러 뻗었다. → `CaptureTexturing` 이 **렌더 메시**(`makeRenderMesh()`)의 위치·법선·UV·인덱스를 쓰도록 고쳤다. 대칭 맵은 원본 정점 기준이라 분할 메시에 쓸 수 없어 대칭 복사는 끄고 평탄화로 메운다.

**사용자 실제 번들로 검증**(`--texture` CLI 신설): `관측 78.1 % · 대칭 0 % · 채움 7.8 %`, 뽑은 PNG 에 **눈·코·입이 선명하게** 찍혔다. 같은 번들이 수정 전에는 방사형 줄무늬였다.
→ CLI `swift run chosang-validate --texture <번들.chosangcapture> <out.png> [크기]` 로 피팅 + 투영을 한 번에 돌려 PNG 를 뽑는다. 실기기 왕복 없이 텍스처를 디버깅하는 가장 빠른 길이다(캡처 데이터는 저장소 밖에).

UV 세로축(상하 반전) 쪽은 여전히 실기기 확인이 필요해 토글로 남겨 둔다 — 래스터라이저는 `v=0` 을 아래로, RealityKit 은 위로 본다.

### 파일 접근 경로 정리 (사용자 보고 3건)
1. **"내보내기를 두 번 눌러야 한다"** — 첫 클릭이 zip 을 만들고 두 번째가 공유였다. 번들 저장 시 **zip 을 미리 만들어** 버튼이 처음부터 `ShareLink` 가 되게 했다(iPhone·Mac 모두).
2. **"저장 경로를 모르겠다"** — Info.plist 의 `UIFileSharingEnabled`·`LSSupportsOpeningDocumentsInPlace`(13차)로 파일 앱에 노출된다. 저장 메시지도 "파일 앱 › 나의 기기 › 초상 › Captures/…" 로 바꿨다.
3. **"Vision Pro 에서 에어드랍이 반응 없다"** — `onOpenURL`(13차)에 더해 **받기 화면에 "파일에서 불러오기"**(`fileImporter`)와 툴바 버튼을 넣었다. 에어드랍이 앱을 못 깨워도 파일 앱에서 직접 열 수 있다.

### Mac·iPhone 에서도 바로 흉상
미리보기 패널(데스크톱)과 정보 시트(iPhone)에 **"내 캡처로 흉상 만들기"** 를 넣었다 — 이 기기 `Documents/Captures` 의 최신 번들을 임시 zip 으로 묶어 같은 피팅 경로를 탄다. 전송 없이 캡처한 기기에서 바로 확인할 수 있다.
Mac 의 보내기·받기는 M6(T-603) 때부터 "주고받기" 탭에 있다 — macOS 탭 순서는 미리보기 · 캡처 · **주고받기** · 검증 · 스파이크.

**검증**: `swift test` 57/57(코너 UV 2 추가), iOS·macOS·visionOS 빌드, 두 기기 설치.

## 26. 15차 — UV 세로축 확정 (2026-10-04, Vision Pro)

14차에서 코너 UV 를 고쳐 알베도 자체는 제대로 나왔지만(관측 78 %, 얼굴 선명), 흉상에서는 **얼굴 색이 어깨로 내려가** 있었다. 사용자 표현 그대로 "얼굴면에 써야 될 부분을 다른 부위에 채워넣는" 상태.

원인은 `flipAlbedoV` **기본값**이었다. 추측으로 "RealityKit 은 v=0 이 위" 라고 보고 반전을 기본 ON 으로 뒀는데, 실제 템플릿 UV 를 찍어 보니 반대였다:

| 랜드마크 | UV v | 래스터 텍셀 y (512²) | 위치 |
|---|---|---|---|
| nose_tip | 0.260 | 379 | 아래쪽 |
| chin | 0.050 | 487 | 아래쪽 |
| eye_left_outer | 0.326 | 345 | 아래쪽 |
| mouth_left | 0.190 | 415 | 아래쪽 |

래스터라이저가 `y = (1 − v)·S` 로 찍으므로 **얼굴은 알베도 이미지 아래쪽**에 온다. RealityKit 이 같은 UV 로 샘플링할 때도 방향이 같아 **그대로 올려야 맞는다**. 뒤집으면 얼굴 텍셀이 어깨 UV 로 간다 — 화면에서 본 그대로다.

→ `flipAlbedoV` 기본값을 **false** 로. 토글은 템플릿 UV 규약이 바뀔 때를 위해 남긴다.
회귀 테스트 2개: 얼굴 랜드마크가 래스터 아래쪽에 오는지, 반전이 되돌릴 수 있는지. `--texture` CLI 도 랜드마크 UV 와 텍셀 위치를 함께 찍어 다음에는 바로 확인할 수 있다.

**교훈**: 좌표 규약을 추측으로 정하면 안 된다. 이번 세션에서만 회전·축·세로축으로 세 번 틀렸고, 매번 **실제 데이터(저장된 메타·랜드마크 UV·기기 로그)를 찍어 보는 것**이 결론을 냈다.

**검증**: `swift test` 59/59, visionOS 빌드·설치.

## 27. 16차 — 엔드투엔드 완성 (2026-10-04, Vision Pro)

세로축 기본값을 바로잡자 **얼굴이 제자리에 붙었다**. iPhone 캡처 → 전송 → 피팅 → 텍스처까지 한 번에 도는 첫 완성본이다.

| 항목 | 실측 |
|---|---|
| 피팅 | 패치 RMS 0.71–0.96 mm · 스케일 1.104–1.124 · 0.4 s |
| 텍스처 | 512² · 관측 **78–83 %** · 1.2–2.1 s |
| 렌더 | `LowLevelDeformation (GPU)` 0.09–0.25 ms · 11.1 ms(90 fps) |

스크린샷 3컷을 `Docs/screenshots/m4-visionpro-persona-{front,angle,side}.png` 로 넣고 README 를 다시 썼다 — 완성 결과와 시연 영상(YouTube 썸네일 링크)을 맨 위에, 캡처에서 흉상까지의 흐름을 mermaid 로, 남은 마일스톤을 표로.

**이 세션에서 좌표 규약을 세 번 틀렸다**. 공통점은 전부 추측으로 정했다는 것이고, 매번 **실제 데이터를 찍어** 바로잡았다:
① 투영 회전 — 기기 로그의 정점 오버레이 위치. ② 자세 축·yaw 부호 — 저장된 번들의 변환 행렬과 촬영 로그. ③ 코너 UV·세로축 — 알베도 PNG 와 랜드마크 UV 수치.
그래서 `--texture` CLI(알베도 + 랜드마크 UV + 부위별 UV 범위 출력)를 남겼다. 다음에 같은 의심이 들면 실기기 왕복 없이 끝난다.

**남은 품질 과제**: 접합선과 탈조명이 거칠고, 관측 밖(뒤통수·어깨 안쪽)은 평균색이다. M4 본편에서 템플릿 알베도 합성 · Metal 커널 · 접합 색 보정 · 탈조명으로 32 dB 를 노린다.

