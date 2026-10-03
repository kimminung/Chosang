# 초상 (Chosang)

**사진 3–5장으로 만드는 나만의 흉상 페르소나** — visionOS 27 · iOS 26 · macOS 26.
블렌더 흉상 템플릿이 기하의 진실이고, iPhone(TrueDepth) 캡처는 "내 얼굴의 형상 차이 + 텍스처"만 공급한다. 완성된 페르소나는 ARKit 52 표정과 프리비즈 클립으로 움직이고 [소반](https://github.com/)(두레반 모임 앱)에 그대로 공급된다.

> 상태: **M1 2차 완료** — 블렌더 템플릿(`Chosang_Blender/`, 10/3 저녁 갱신: 귀 v2·`Shoulders_shirt` 추가·프리비즈 재렌더) 반입, 2차 계약·내보내기 스크립트·검증기 완료. 앱은 번들 `Default.chosangtemplate`(bust.mesh + Template.usdz + EyesMouth.usdz) 로 돈다. 검증기 **오류 0 · 경고 0**.

| visionOS 시뮬레이터 (기본 템플릿) | macOS (기본 템플릿, GPU) |
|---|---|
| ![visionOS](Docs/screenshots/m1-visionos-sim-default-template.png) | ![macOS](Docs/screenshots/m1-macos-default-template.png) |

52 셰이프 시트(macOS, `sheet=1`): ![sheet](Docs/screenshots/m1-shape-sheet.png)

## 구조

```
Chosang/               앱 타깃 Chosang (번들 com.coulson.Chosang, 구 MyApp) — 3 플랫폼 한 타깃, #if os 분기
  App/                 ChosangApp · AppModel · LaunchOptions
  Views/               미리보기(RealityView + 52 슬라이더 + 클립) · 스파이크 · 캡처(iOS) · 검증(macOS)
  Resources/Templates/Legacy/   소반 USDZ(임시 템플릿)
ChosangKit/            로컬 Swift Package
  ChosangCore          모델(BustTemplate·CaptureBundle·Identity·SampledClip·manifest)·포맷(bust.mesh·identity.bin)·수학(Procrustes·RBF·TPS)·합성 템플릿/클립
  ChosangFit           FaceFitter(정렬·중립화·패치 치환·두상 전파)·AppearanceHints(FoundationModels)
  ChosangTexture       CPU 래스터라이저·합성 캡처 번들·CPU 투영 텍스처(참조 구현)
  ChosangRig           TemplateLoader(USDZ)·BustEntity(LowLevelMesh + LowLevelDeformation/CPU)·FaceRig·ClipPlayer
  ChosangCapture       FaceCaptureSession(iPhone ARKit)·MicLevelMeter
  ChosangIO            .chosang 패키지·캡처 번들·ZipArchive·PNG/JPEG·USD 내보내기 능력
  ChosangValidate      템플릿·클립 계약 검사 (+ `chosang-validate` CLI)
  Tests/               Swift Testing — 셀프 피팅·텍스처·검증기·포맷 왕복 (17 테스트)
tools/blender/export_chosang.py   블렌더 내보내기 (Template.usdz · library/*.usdz · bust.mesh v2 · template.json · library.json · clips · textures · source)
tools/make_default_template.sh    Template 폴더 → 앱 번들용 Default.chosangtemplate (stored zip)
Chosang_Blender/                  블렌더 작업 파일(.blend, LFS)·결정적 빌드 스크립트·텍스처·Apple OBJ(+라이선스)·Template/ 산출물(usdz 제외)
Fixtures/              합성 캡처 번들 2종 (.chosangcapture) — 실제 캡처 데이터는 절대 커밋하지 않음
Docs/                  TechPRD.md · Tasks.md · Blender-요청.md · Spikes.md · Prompt.md · screenshots/
```

## 시작하기

```bash
# 테스트 (Mac)
cd ChosangKit && swift test

# 블렌더 내보내기 (블렌더 쪽에서) + 계약 검증기
/Applications/Blender.app/Contents/MacOS/Blender -b ~/Desktop/Chosang_Blender/Chosang_Template.blend \
  --python tools/blender/export_chosang.py -- --out ~/Desktop/Chosang_Blender/Template
swift run chosang-validate ~/Desktop/Chosang_Blender/Template --with-usdz   # RealityKit 교차 확인 포함
swift run chosang-validate --synthetic /tmp/ChosangTemplate                 # 합성 템플릿으로 자체 검사
../tools/make_default_template.sh ~/Desktop/Chosang_Blender/Template         # 앱 번들 갱신
swift run chosang-validate --list-legacy-failures                # 소반 USDZ 로 실패하는 항목 = 블렌더 작업 우선순위
swift run chosang-validate --make-fixture ../Fixtures/x.chosangcapture [perturbed]

# 앱 (Xcode 에서 Chosang 스킴). 시뮬레이터 자동 실행 인자:
#   template=default|synthetic|legacy  clip=<idle_breathe|…|bow>  tab=preview|capture|validate|spikes|receive  fixture=perturbed  report=1  sheet=1  previz=1
```

## 지금 되는 것 (M1 2차)

- 기본 템플릿(블렌더, 11,569 정점 · 52 셰이프 · 뼈 6 · 클립 11 · 라이브러리 19) 미리보기 — bust.mesh 기하 + Template.usdz 눈알·입안, Mac GPU `LowLevelDeformation`.
- 2차 계약 검증기(규칙 40여 개, 한국어 수정 문장, `--with-usdz`), 내보내기 스크립트(헤드리스 4.5 s), 셰이프 시트, 프리비즈 카메라 프리셋.

## M0 에서 된 것

- 합성 템플릿(1220 패치 + 두상·목·어깨 6.7k 정점, 52 셰이프, 뼈 6) 미리보기 — Mac 은 `LowLevelDeformation` GPU 경로(0.14 ms), 시뮬레이터는 CPU 폴백.
- 절차적 클립 11종(계약과 같은 이름·길이·루프) 재생·크로스페이드, 52 슬라이더, 자동 깜빡임·시선.
- 소반 USDZ 로드 보고(T-004) — 셰이프 델타·스킨·조인트가 `MeshResource.contents` 에서 읽힌다.
- 합성 캡처 번들(5컷 RGB·깊이·1220 정점·52 가중치·조명) → 피팅 → Identity → CPU 텍스처 투영까지 한 번에 도는 테스트.
- `.chosang`/`.chosangcapture`/`bust.mesh`/`identity.bin`/`clip.json` 포맷과 왕복 테스트, 계약 검증기(한국어 수정 문장).

## 실기기에서 확인할 것 (🧪)

`Docs/Tasks.md` 맨 아래 체크리스트. 특히 iPhone T-007(ARKit 1220 정점·삼각형 해시·깊이·조명 한 프레임)과 Vision Pro 의 GPU 변형 경로.

## 라이선스

Apache-2.0 (`LICENSE`, `NOTICE`). 소반에서 이식한 코드도 같은 라이선스.
