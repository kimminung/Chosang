# 블렌더 작업 요청 — 초상(Chosang) 흉상 템플릿 · 라이브러리 · 프리비즈 클립 (2차 계약, 2026-10-03)

소반 때처럼 Blender MCP + Claude 로 만들되, **앱이 기계적으로 검사하는 계약**입니다. 아래 항목이 하나라도 어긋나면
`chosang-validate` 가 실패 항목을 문장으로 알려 주니, 그 문장을 그대로 블렌더 쪽 Claude 에게 넘기면 됩니다.
1차 산출물(`Chosang_Blender/`, Blender 5.2.2)의 변경 제안 9건을 검토해 **모두 수용**했고, 그 결과가 이 2차 계약입니다(§8 에 결정 기록, §9 에 블렌더 쪽 할 일).

## 0. 좌표계 (소반과 동일)

- 단위 m, **Y-up**, 얼굴 **+Z**, 왼쪽 = 피사체 기준 왼쪽 = **+X**. 블렌더 안은 Z-up·얼굴 −Y 로 작업하고 **USD(x, y, z) = 블렌더(x, z, −y)** 로 내보낸다(스크립트가 처리). 확인값: 코끝(정점 8) = (0, 0.4142, 0.1209), 왼눈알 중심 = (0.032, 0.44, 0.0722).
- 가슴 절단면 y = 0, **눈알 중심 y = 0.44 · x = ±0.032 (간격 0.064)** — 이 둘만 고정값. 입 중심(≈0.380)·턱끝(≈0.334)·정수리(≈0.567)는 ARKit 비율에서 나오는 **측정값**이며 `template.json` 에 기록되고 검증기는 그 값을 기준으로 검사한다(2차 #1).
- 셰이프키 값 0…1, 중립 0. Apply Modifiers **OFF**. Blender 4.4+ (슬롯 액션) 기준, 5.2 에서 확인.

## 1. 흉상 메시 `Bust` (가장 중요)

1. Apple 샘플 "Tracking and visualizing faces" 의 **`ARFaceGeometry.obj`**(1220 정점, **사각형 1152개**, v = vt 인덱스) 를 가져온다. 라이선스 고지(`ARFaceGeometry_LICENSE.txt`)를 `source/` 에 함께 둔다.
   - 정점 **순서를 바꾸지 않는다**(인덱스 0…1219). 병합·정리·리메시·데시메이트·삼각분할 금지. 앞 1152개 면도 OBJ 순서 그대로.
   - **패치 해시 = 사각형 1152개(OBJ 순서, int32 LE) SHA-256 `a71869b9…`** (2차 #4). 삼각형은 스크립트가 (a,b,c)+(a,c,d) 로 쪼갠다(SHA-256 `4a1e77ef…`). ARKit 런타임 삼각형 2304개의 대각선은 다를 수 있으므로 "기록" 만 한다(🧪 T-007).
   - 버텍스 그룹 `ARKitFace` 에 1220 정점 전부(가중치 1.0).
   - OBJ 를 흉상 좌표계로: 눈꺼풀 구멍(24정점 루프) 중심에 반지름 12 mm 눈알을 두고 두 눈알 중심 간격 0.064 가 되도록 균일 스케일, 왼눈알 중심 → (0.032, 0.44, z). 눈알 깊이는 구멍 24정점이 모두 구면 +0.2 mm 바깥에 오도록(1차: 2.03 mm 뒤, z = 0.0722) — 값은 `template.json` 의 `eyeL/eyeR` 가 진실(2차 #3).
2. 그 **바깥**으로 두피·귀·목·어깨를 이어 붙인다(패치 경계 56정점과 **공유 정점**으로, 새 정점은 1220 뒤에). 총 정점 10k–14k(1차 11,569). 눈구멍·입구멍은 그대로 두고 눈꺼풀 안쪽·입술 안쪽 띠를 1–2 루프 추가(`LidInner` 96 · `LipInner` 72).
3. 버텍스 그룹(검증 대상): `ARKitFace`, `Scalp`, `EarL`, `EarR`, `Neck`, `Shoulders`, `LipInner`, `LidInner` + 스킨 그룹 `Root`, `Head`.
   **`Neck` 은 영역 그룹이자 Neck 뼈 디폼 그룹**(2차 #2): 값 = Neck 뼈 스킨 가중치, 영역 집합 = 가중치 > 0. 나머지 영역 그룹은 가중치 1.
4. UV 한 장(4096 기준): 얼굴 패치 = Apple UV 를 **(u, 0.5·v)** 로 아래 절반. 두피·목 [0.005,0.505]–[0.775,0.795], 귀 L [0.785,0.655]–[0.995,0.795] · R [0.785,0.505]–[0.995,0.645], 어깨·가슴 [0.005,0.805]–[0.995,0.995], 눈꺼풀/입술 안쪽 띠 = 맨 아래 띠(v < 0.046). 박스는 `chosang_uv_regions` 에 기록. 검증기는 패치와 다른 아일랜드의 **겹침**을 텍셀로 검사한다(루프 UV 기준).
5. 머티리얼 `Skin` 1개(PBR, 베이스컬러 텍스처 슬롯 비워 둠). 어깨 옷은 `Shoulders_<id>` 오브젝트.
6. **Bust 에는 Armature 외 모디파이어를 두지 않는다**(USD 가 평가 메시를 쓰면 정점 수·셰이프키가 깨짐). 오브젝트 변환은 위치 0·회전 0·스케일 1.
7. Bust 커스텀 속성 4개(빌드 스크립트가 넣음, 내보내기 스크립트가 읽음): `chosang_patch`(루프·범위·눈알 중심·해시·OBJ→블렌더 변환), `chosang_uv_regions`, `chosang_rig`(턱 피벗·각도·입 중심), `chosang_landmarks`.

## 2. 셰이프키 — ARKit 52 (이름 그대로, 대소문자 그대로)

```
eyeBlinkLeft eyeLookDownLeft eyeLookInLeft eyeLookOutLeft eyeLookUpLeft eyeSquintLeft eyeWideLeft
eyeBlinkRight eyeLookDownRight eyeLookInRight eyeLookOutRight eyeLookUpRight eyeSquintRight eyeWideRight
jawForward jawLeft jawRight jawOpen
mouthClose mouthFunnel mouthPucker mouthLeft mouthRight mouthSmileLeft mouthSmileRight mouthFrownLeft mouthFrownRight
mouthDimpleLeft mouthDimpleRight mouthStretchLeft mouthStretchRight mouthRollLower mouthRollUpper mouthShrugLower mouthShrugUpper
mouthPressLeft mouthPressRight mouthLowerDownLeft mouthLowerDownRight mouthUpperUpLeft mouthUpperUpRight
browDownLeft browDownRight browInnerUp browOuterUpLeft browOuterUpRight
cheekPuff cheekSquintLeft cheekSquintRight noseSneerLeft noseSneerRight tongueOut
```

- 52개 **모두** 존재하고 실제 변형(1차: 전부 변형). 최대 변위는 보통 ≤ 40 mm(검증기 경고), 60 mm 넘으면 오류. jawOpen 30–40 mm 정상.
- 턱은 뼈가 아니라 `jawOpen` 셰이프(TMJ 축 회전 + 앞 이동, `chosang_rig` 에 피벗·각도 기록). `eyeLook*` 은 눈꺼풀이 따라가는 양만(눈알은 뼈로 돈다).
- `mouthClose` 는 ARKit 의미대로 jawOpen 과 함께 쓸 때 맞도록(단독 1.0 은 입술 겹침 허용).
- **`Mouth_Inner` 에도 셰이프키 5개** `jawOpen jawLeft jawRight jawForward tongueOut` (Bust 와 같은 이름, 블렌더 안에서는 드라이버로 따라감; 앱은 같은 가중치를 그대로 넣는다 — 2차 #8). USD 내보내기에서 이름이 `jawOpen2` 처럼 뒤에 숫자가 붙어도 앱이 숫자를 떼어 맞춘다.

## 3. 스켈레톤 `Armature`

- 뼈: `Root`(y 0) > `Spine`(0.12) > `Neck`(0.30) > `Head`(0.36) > `Eye_L`·`Eye_R`(눈알 중심 = `template.json` eyeL/eyeR, 머리 위치가 중심에 0.5 mm 안). 레스트 = 정면 중립, 롤 0.
- `Bust` 스킨: Root/Neck/Head 가중치(정점당 영향 ≤ 4, 합 1). 눈알 `Eye_L`/`Eye_R` 오브젝트(r 0.012, 흰자·홍채·동공 머티리얼)는 각 눈 뼈 100%. `Mouth_Inner`(위아래 치아·잇몸·혀·입안 주머니, 그룹 `MI_*`)는 Head 100%.

## 4. 라이브러리 (`Library` 컬렉션 아래 `Library_Hair/Glasses/Beard/Shoulders`)

| 이름 | 수 | 메모 |
|---|---|---|
| `Hair_<id>` | 10+ (1차 12: short_crop, short_side, medium_wave, long_straight, long_wave, tied_low, tied_high, bangs_short, bangs_medium, bangs_long, buzz, bald_cap) | 캡(Scalp 전체) + 알파 카드. 베이스 **그레이스케일 + 알파**(앱이 틴트), 마스크(R 하이라이트, G 뿌리→끝, B 가닥 id). Head 100%. 양면 렌더 |
| `Glasses_<id>` | 3 (round, square, thin) | 코 받침이 `nose_tip` 근처(`chosang_nose_bridge`). 렌즈 투명. Head 100% |
| `Beard_<id>` | 2 (stubble, short) | Bust 수염 영역을 띄운 셸 + 알파. Head 100%. **정점 속성 `chosang_bust_index`(INT, POINT) = 원본 Bust 정점** — 앱이 Bust 변형(jawOpen 등)을 복사해 따라가게 한다(2차 #5) |
| `Shoulders_<id>` | 2 (tee, shirt) | Bust 몸통 셸(목둘레 아래) + 목둘레 두께(+셔츠 칼라). **스킨 = Bust 의 Root/Neck 가중치 복사**(2차 #6). 베이스 텍스처 + 마스크(R = 색 바꿀 영역) |

오브젝트 커스텀 속성 `chosang_kind`, `chosang_bone`, `chosang_tint`(스크립트가 `library.json` 에 옮긴다). 라이브러리는 **오브젝트별 USDZ**(`library/<name>.usdz`, Armature 포함)로 나간다 — RealityKit 은 한 아마추어 아래 스킨 메시를 모델 하나(파트 여러 개)로 합치므로 한 파일에 넣으면 켜고 끌 수 없다.

## 5. 프리비즈 클립 (액션)

- 액션 이름 `clip_<name>`, 30 fps, **슬롯 2개**(2차 #7): `target_id_type` OBJECT 슬롯 → Armature(뼈 트랙 Neck·Head·Eye_L·Eye_R 의 rotation_quaternion + location), KEY 슬롯 → Bust 셰이프키. 4.1 호환이 필요하면 KEY 채널을 별도 액션으로 복제.
- 프레임 **0…L 끝 포함**(frames = L+1, 길이 L/fps). 루프 클립은 0 프레임 = L 프레임(+ Cyclic 모디파이어).

| name | 길이 | 루프 | 내용 |
|---|---|---|---|
| idle_breathe | 4 s | ✓ | 호흡 고개 미세 움직임, 2초마다 깜빡임 |
| listen | 3 s | ✓ | 상대 쪽으로 약간 기울임, 눈썹 살짝, 작은 끄덕임 1회 |
| nod | 1 s | ✗ | 끄덕임 2회 |
| talk_a / talk_b / talk_c | 2 s | ✓ | 입은 비우고(앱이 비셈으로 채움) 고개·눈썹 제스처만 다르게 |
| laugh | 1.5 s | ✗ | 고개 뒤로, 눈 감김, mouthSmile·jawOpen |
| surprise | 1 s | ✗ | eyeWide·browInnerUp·jawOpen 작게 |
| bow | 1.5 s | ✗ | 목례: Neck+Head 앞으로 25°, 눈은 내려봄, 복귀 |
| think | 3 s | ✓ | 시선 위·옆, browDown 한쪽, mouthPress |
| blink_set | 2 s | ✓ | 깜빡임만 |

- **프리비즈 렌더**(2차 #9): 라이브러리 없이 **맨 흉상**, `Previz_Camera` 조준점 (0, 0.41, 0.09)·위치 (0, 0.41, 1.29)·**수평 FOV 39.60°**(50 mm/36 mm), 1920×1080, 30 fps, H.264 → `previz/<name>.mp4`. 3점 조명(Key/Fill/Rim). 앱 비교 화면도 같은 카메라.

## 6. 내보내기 스크립트 `tools/blender/export_chosang.py`

앱 리포의 Claude 가 쓰고(`.blend` 는 손대지 않음), 블렌더 쪽은 실행만 한다:

```
/Applications/Blender.app/Contents/MacOS/Blender -b ~/Desktop/Chosang_Blender/Chosang_Template.blend \
  --python tools/blender/export_chosang.py -- --out ~/Desktop/Chosang_Blender/Template [--previz] [--no-usdz] [--version 1.0]
cd ChosangKit && swift run chosang-validate ~/Desktop/Chosang_Blender/Template --with-usdz
```

산출물:
```
Template/
  Template.usdz        # Armature + Bust + Eye_L/R + Mouth_Inner (좌표 변환됨)
  library/<name>.usdz  # 라이브러리 오브젝트별 (Armature 포함)
  bust.mesh            # CBM1 v2: 정점·법선·정점 UV·코너 UV·삼각형·52 델타·스킨·조인트 (ChosangCore/Formats.md)
  template.json        # 스키마 2: 수·해시·OBJ 변환·랜드마크·그룹(+가중치)·루프·UV 영역·대칭 맵·눈알·측정값·턱 리그·뼈·셰이프·Mouth_Inner·라이브러리·클립·previz·텍스처
  library.json         # 라이브러리 메타 (kind·bone·tint·텍스처·bustIndex·noseBridge·skinGroups)
  clips/<name>.json    # fps, frames, loop, bones{Neck,Head,Eye_L,Eye_R: [qx,qy,qz,qw,px,py,pz]×frames}, shapes{name:[w]×frames}
  textures/*.png · source/ARFaceGeometry.obj + ARFaceGeometry_LICENSE.txt · previz/<name>.mp4
```

## 7. 확인 방법

- Mac: `swift run chosang-validate Template/ --with-usdz` → 전부 ✅ 면 `tools/make_default_template.sh Template/` 로 앱 번들용 `Default.chosangtemplate` 생성.
- 앱(macOS/시뮬레이터) "셰이프 시트"(`sheet=1`): 52 셰이프를 하나씩 1.0 으로 렌더한 격자를 ARKit 레퍼런스 포즈 그림과 비교.
- "프리비즈 비교": `previz/<name>.mp4` ↔ 앱 렌더(프리비즈 카메라) 프레임 동기(M7).

## 8. 2차 계약 결정 기록 (1차 변경 제안 9건 → 모두 수용, 2026-10-03)

| # | 제안 | 결정 | 이유 |
|---|---|---|---|
| 1 | 입 중심 y 0.380 (계약 0.357) | **수용** — 입·턱·정수리는 측정값, 검증기는 template.json 기준 | 눈 간격 0.064 균일 스케일에서 ARKit 비율상 0.3797. 고정값은 눈 간격·눈 높이만 |
| 2 | `Neck` 그룹 = Neck 뼈 스킨 가중치 | **수용** — 영역 집합 = 가중치 > 0, `groupWeights.Neck` 에 가중치 기록 | 이름 충돌 제거. 앱의 목 감쇠는 어차피 높이 기반 |
| 3 | 눈알 중심 2.03 mm 뒤 (z 0.0722) | **수용** — template.json 값이 진실 | 구멍 정점이 눈알 안으로 들어가지 않아야 눈꺼풀이 구면을 따라 닫힘 |
| 4 | 패치 해시를 사각형 기준으로 | **수용** — `patchQuadsSHA256`(OBJ 순서) 계약, 삼각형 (a,b,c)+(a,c,d) 는 bust.mesh 규칙 | OBJ 는 사각형 1152개; ARKit 삼각형 대각선은 런타임 측정값으로만 |
| 5 | 수염 `chosang_bust_index` | **수용** — `library.json.bustIndex`, 앱이 Bust 변형 복사 | 셰이프키 없는 셸은 jawOpen 때 턱에서 떨어짐 |
| 6 | 어깨 옷 Root/Neck 가중치 복사 | **수용** | 목둘레가 목을 따라가야 함 |
| 7 | 슬롯 액션 | **수용** — OBJECT 슬롯 → Armature, KEY 슬롯 → Bust 키; 4.1 폴백은 스크립트 | Blender 4.4+ 구조 |
| 8 | Mouth_Inner 셰이프키 5개 | **수용** — 같은 이름, 앱이 같은 가중치 적용(USD 중복 접미 숫자 제거) | 아래 치아·혀가 턱을 따라감 |
| 9 | 프리비즈 맨 흉상 + 카메라 | **수용** — 조준 (0,0.41,0.09)·위치 (0,0.41,1.29)·hFOV 39.60°·1080p30 | 비교 화면이 같은 카메라를 쓴다(`PrevizCameraSpec.contract`) |

추가로 앱 쪽에서 정한 것: `bust.mesh` 는 항상 동봉(v2 에 **코너 UV** 포함 — 솔기 357 정점에서 UV 가 갈라지므로 앱이 정점을 분할해 렌더), 라이브러리는 오브젝트별 USDZ, 랜드마크 이름은 블렌더의 snake_case 를 계약으로 채택(`eye_left_inner … shoulder_right` 필수, `lip_upper_mid/lip_lower_mid` 는 스크립트가 입 루프에서 유도, `brow_inner_left/right` 선택).

T-004 재확인(Template.usdz, RealityKit 27): Bust 파트 11,931 정점(솔기 분할), **52/52 `blendShapeOffsets(named:)` 읽힘**, 조인트 6, 정점당 영향 3. 로더는 엔티티 변환(`transformMatrix(relativeTo: root)`)을 파트 좌표에 적용해야 흉상 공간이 된다.

## 9. 블렌더 쪽 할 일 (2026-10-03, 검증기 결과)

1. **`Shoulders_shirt` 가 없음** — `Library_Shoulders` 에 `Shoulders_tee` 만 있다(README 에는 3,031 정점으로 적혀 있음). `build/library_misc.py` 의 shirt 빌드가 작업 파일에 반영되지 않은 듯. 만들어 넣으면 검증기 `library.missing` 이 사라진다.
2. (선택) 랜드마크 `brow_inner_left/right` 를 `chosang_landmarks` 에 추가 — 없으면 앱이 눈 위 1.5 cm 로 추정한다.
3. 후속 과제로 기록만: 셰이프키 절차적 1차본(funnel·pucker·press 는 정면 변화 작음 → 아티스트 손질), 패치 위쪽(이마 끝) 이음 능선, 수염 셸 경계 계단, 귀 단순 모델.
4. 바꾸지 않아도 되는 것: `_QA_*`·`_Ref_Soban` 컬렉션(스크립트가 무시), Mouth_Inner 셰이프 USD 이름 접미 숫자(앱이 처리), 이미지 데이터블록 중복(`T_*.001`, 같은 파일).
