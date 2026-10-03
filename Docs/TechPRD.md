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
| 폴백 | TrueDepth 없는 기기·Mac: Vision 76점 + 사진만 → `template.json` 랜드마크 대응으로 희소 피팅(품질 "기본" 표시) |

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
- `Shoulders_shirt` 가 올 때까지 검증기 "오류 1" 상태로 기본 템플릿을 쓴다.
- 클립 뼈 값은 흉상 공간 피벗 기준 로컬 오프셋이며 Neck→Head→Eye 합성은 M5 스키닝에서 구현(지금은 Head 회전만 근사).

**다음 (M2)**: Prompt.md §B M2 — iPhone 캡처 T-201~T-207. 그 전에 🧪 T-007 프로브로 ARKit 삼각형 해시 기록.
