#!/bin/zsh
# 블렌더 내보내기 결과(Template 폴더) → 앱 번들용 Default.chosangtemplate (stored zip, 라이브러리 USDZ·previz·source 제외)
# 사용: tools/make_default_template.sh <Template 폴더> [출력 경로]
set -e
SRC="${1:?Template 폴더}"
OUT="${2:-$(dirname "$0")/../Chosang/Resources/Templates/Default.chosangtemplate}"
TMP=$(mktemp -d)
mkdir -p "$TMP/t"
for f in template.json bust.mesh Template.usdz EyesMouth.usdz library.json; do [ -f "$SRC/$f" ] && cp "$SRC/$f" "$TMP/t/"; done
cp -R "$SRC/clips" "$TMP/t/clips"
mkdir -p "$TMP/t/textures" && cp "$SRC"/textures/*.png "$TMP/t/textures/" 2>/dev/null || true
mkdir -p "$TMP/t/source" && cp "$SRC"/source/ARFaceGeometry_LICENSE.txt "$TMP/t/source/" 2>/dev/null || true
# 검증기와 같은 ZipArchive(stored) 규격 — python zipfile ZIP_STORED
python3 - "$TMP/t" "$OUT" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
    for root, _, files in os.walk(src):
        for f in sorted(files):
            p = os.path.join(root, f); z.write(p, os.path.relpath(p, src))
print("wrote", out, os.path.getsize(out) // 1024, "KB")
PY
rm -rf "$TMP"
