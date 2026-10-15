#!/usr/bin/env bash
# Builds a signed SmartHomeApp APK without Gradle.
# Needs (Debian/Ubuntu): android-sdk-platform-23 aapt dalvik-exchange zipalign apksigner + JDK.
set -euo pipefail
cd "$(dirname "$0")"

ANDROID_JAR="${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}"
OUT=build
APK="$OUT/SmartHome.apk"

rm -rf "$OUT"
mkdir -p "$OUT/gen" "$OUT/classes"

echo "==> Resources"
aapt package -f -m -J "$OUT/gen" -M AndroidManifest.xml -S res -I "$ANDROID_JAR" \
    -F "$OUT/unsigned.apk"

echo "==> Java"
javac -nowarn -Xlint:-options --release 8 -encoding UTF-8 \
    -classpath "$ANDROID_JAR" -d "$OUT/classes" \
    $(find src "$OUT/gen" -name '*.java')

echo "==> Dex"
dalvik-exchange --dex --min-sdk-version=21 --output="$OUT/classes.dex" "$OUT/classes"
(cd "$OUT" && aapt add unsigned.apk classes.dex >/dev/null)

echo "==> Align + sign"
zipalign -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
apksigner sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias androiddebugkey --out "$APK" "$OUT/aligned.apk"
apksigner verify "$APK"

echo "==> $APK ($(du -h "$APK" | cut -f1))"
