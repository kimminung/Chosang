# 초상(Chosang) 블렌더 작업 폴더

작업 파일 `Chosang_Template.blend` (Blender 5.2.2). 빌드 스크립트 `build/`, 텍스처 `textures/`, 원본 `source/ARFaceGeometry.obj`(Apple 샘플, `ARFaceGeometry_LICENSE.txt` 동봉 — 템플릿 배포 시 이 고지문 포함 필요).
처음부터 다시 만들기: `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P build/build_all.py -- <출력.blend>` (난수 없음, 같은 입력 → 같은 결과).

## 좌표계
블렌더 안: Z-up, 얼굴 −Y, 피사체 왼쪽 +X (소반과 동일). USD Up Axis = Y 로 내보내면 계약 좌표(m, Y-up, 얼굴 +Z, 왼쪽 +X): **USD (x, y, z) = 블렌더 (x, z, −y)**. 아래 수치는 계약(USD) 좌표.

## 상태
| 항목 | 내용 |
|---|---|
| Bust | 정점 11,569 (패치 0…1219 = OBJ 순서·위치 그대로, 셸 1220…10558, 눈꺼풀/입술 안쪽 띠 168, 귀 842), 면 11,696. 빌드 스크립트가 매번 패치 위치·앞 1152개 면 순서를 assert |
| 그룹 | ARKitFace 1220 · Scalp · EarL · EarR · Neck · Shoulders · LipInner 72 · LidInner 96 (+ 스킨용 Root · Head) |
| 셰이프키 | ARKit 52 전부(이름 그대로, 전부 실제 변형, 0…1). Mouth_Inner 에 jawOpen/jawLeft/jawRight/jawForward/tongueOut (Bust 값 드라이버) |
| 스켈레톤 | Root(0) > Spine(0.12) > Neck(0.30) > Head(0.36) > Eye_L/Eye_R(눈알 중심), 롤 0, 레스트 = 정면 중립 |
| 눈알·입안 | Eye_L/Eye_R(r 0.012, 흰자·홍채·동공 머티리얼), Mouth_Inner(위아래 치아·잇몸·혀·입안 주머니), 각각 뼈 100% |
| 라이브러리 | Beard_short 1,960, Beard_stubble 892, Glasses_round 1,090, Glasses_square 1,090, Glasses_thin 1,090, Hair_bald_cap 3,600, Hair_bangs_long 19,092, Hair_bangs_medium 18,676, Hair_bangs_short 17,970, Hair_buzz 3,600, Hair_long_straight 19,720, Hair_long_wave 19,720, Hair_medium_wave 19,720, Hair_short_crop 10,200, Hair_short_side 10,200, Hair_tied_high 13,564, Hair_tied_low 13,524, Shoulders_shirt 3,031, Shoulders_tee 2,859 |
| 클립 | clip_* 11종, 30 fps, 뼈 트랙 + 셰이프키 트랙 |
| 프리비즈 | `Template/previz/<clip>.mp4` (1920×1080, 30 fps, H.264, 맨 흉상) |

## 측정값 (계약 좌표)
- 눈알 중심 L/R: [0.032, 0.44, 0.0722] / [-0.032, 0.44, 0.0722], 반지름 0.012. 정의: xy = 눈꺼풀 구멍 24정점 평균, 깊이 = 위/아래 눈꺼풀이 구면 +0.3 mm 에 오도록 피팅 후, 구멍 24정점 전부가 구면+0.2 mm 바깥에 오도록 2.03 mm 뒤로.
- 입 중심(입 구멍 36정점 평균): [0.0, 0.3797, 0.0948] · 턱끝 0.334 · 패치 이마 끝 0.507 · 정수리 0.567.
- OBJ → 블렌더: b = (x, −z, y)·0.0009499 + [0.0, -0.04648, 0.41808] (OBJ mm).
- 해시: OBJ sha256 97d906e49264713f94e64992c7568a93bfe9fd7000457f0d0a6c07ae50ec6e37, 패치 사각형(OBJ 순서, int32 LE) sha256 a71869b9f260ce42d1065d29aacbdf427821c3b27a138e8f69fb7676bbec6334.

### 랜드마크 정점 id (Bust 커스텀 속성 `chosang_landmarks`)
| 이름 | 정점 | 위치 |
|---|---|---|
| eye_left_inner | 1081 | [0.0155, 0.438, 0.081] |
| eye_left_outer | 1069 | [0.0431, 0.4399, 0.078] |
| eye_right_inner | 1089 | [-0.0155, 0.438, 0.081] |
| eye_right_outer | 1101 | [-0.0431, 0.4399, 0.078] |
| nose_tip | 8 | [0.0, 0.4142, 0.1209] |
| mouth_left | 823 | [0.0205, 0.3793, 0.0889] |
| mouth_right | 393 | [-0.0205, 0.3793, 0.0889] |
| chin | 1047 | [0.0, 0.3339, 0.0812] |
| ear_top_left | 11016 | [0.074, 0.4448, -0.012] |
| ear_top_right | 11437 | [-0.074, 0.4448, -0.012] |
| shoulder_left | 2256 | [0.207, 0.195, -0.0201] |
| shoulder_right | 2312 | [-0.207, 0.195, -0.0201] |

## UV (4096 기준 한 장, Bust `chosang_uv_regions`)
얼굴 패치 = Apple UV 를 (u, 0.5·v) — 아래 절반. 두피·목 [0.005,0.505]–[0.775,0.795], 귀 L [0.785,0.655]–[0.995,0.795] · R [0.785,0.505]–[0.995,0.645], 어깨·가슴 [0.005,0.805]–[0.995,0.995], 눈꺼풀 안쪽 L/R·입술 안쪽 = 맨 아래 띠(v < 0.046). 솔기: 뒤통수 정중선, 목·어깨 경계(z 0.265), 패치 경계.

## 블렌더 쪽에서 내보내기 스크립트에 넘길 것
- Bust 커스텀 속성: `chosang_patch`(루프·밴드·범위·눈 중심·해시), `chosang_uv_regions`, `chosang_rig`(턱 피벗·각도·입 중심), `chosang_landmarks`.
- 클립: 액션 하나에 슬롯 2개(Blender 4.4+). 슬롯 식별자(예: KEKey.004)는 의미 없음 — `target_id_type` 이 'OBJECT' 인 슬롯 → Armature, 'KEY' → Bust 셰이프키. 4.1 호환이 필요하면 KEY 슬롯 채널을 별도 액션으로 복제.
- Mouth_Inner 셰이프키는 Bust 의 같은 이름 값을 드라이버로 따른다(USD 에는 드라이버가 없으므로 앱도 같은 이름 가중치를 그대로 넣으면 됨).
- 텍스처 채널: `T_Hair_Atlas_base`(RGB 그레이 + A 알파, 8칸) · `_mask`(R 하이라이트, G 뿌리→끝, B 가닥 id), `T_Hair_Buzz_*`(캡·수염 타일), `T_Cloth_*_base` + `_mask`(R = 색 바꿀 영역, 셔츠 단추 0). 머리카락 카드는 양면 렌더 필요.

## 알려진 한계
- 셰이프키는 절차적 1차본이다(눈꺼풀은 눈알 구면을 따라 닫힘, 턱은 TMJ 축 회전). 입 모양 계열(funnel·pucker·press 등)은 정면에서 변화가 작아 아티스트 손질 권장. mouthClose 는 ARKit 의미대로 jawOpen 과 함께 쓸 때 맞도록 만들었다(단독 1.0 은 입술이 겹침).
- 패치 위쪽(이마 끝) 이음에 약한 능선이 남아 있다(맨머리·buzz 에서 보임). 수염 셸 경계는 계단형.
- 귀 v2(10/3 수정): 실제 귀 윤곽 스플라인(넓고 둥근 위·둥근 귓불), 높이별 돌출각(귓불 13° → 가운데 19° → 위 22°), 귀뿌리 두께 4 mm, 윤곽은 호 길이 균등 샘플. 위상(정점 수·순서)은 v1 과 같다. 연골 주름은 여전히 단순화.
