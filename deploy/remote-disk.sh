#!/usr/bin/env bash
# Disk headroom analysis + wppconnect image size survey.
set -uo pipefail

echo "=== DF ==="
df -h /

echo
echo "=== BIGGEST FILES (>40M) ==="
find / -xdev -type f -size +40M -printf '%s %p\n' 2>/dev/null \
  | sort -rn | head -25 \
  | while read -r size path; do
      printf '%6s MB  %s\n' "$((size / 1024 / 1024))" "$path"
    done

echo
echo "=== /usr/lib breakdown ==="
du -xh --max-depth=1 /usr/lib 2>/dev/null | sort -rh | head -12

echo
echo "=== /usr/lib/x86_64-linux-gnu top 15 ==="
du -xh --max-depth=1 /usr/lib/x86_64-linux-gnu 2>/dev/null | sort -rh | head -15

echo
echo "=== /usr/bin top 15 ==="
du -xh --max-depth=1 /usr/bin 2>/dev/null | sort -rh | head -15

echo
echo "=== /usr/libexec ==="
du -xh --max-depth=1 /usr/libexec 2>/dev/null | sort -rh | head -10

echo
echo "=== /usr/share ==="
du -xh --max-depth=1 /usr/share 2>/dev/null | sort -rh | head -10

echo
echo "=== python3 size ==="
du -sh /usr/lib/python3 /usr/lib/python3.12 /usr/bin/python3* 2>/dev/null

echo
echo "=== kernel modules ==="
du -sh /usr/lib/modules 2>/dev/null
ls /usr/lib/modules 2>/dev/null

echo
echo "=== wppconnect tags on Docker Hub ==="
for tag in latest v2.10.0 v2.8.0 v2.6.0 v2.4.0 v1.0.0; do
  out=$(timeout 25 docker manifest inspect "wppconnect/wppconnect-server:${tag}" 2>/dev/null)
  if [ -n "$out" ]; then
    total=$(printf '%s' "$out" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("?"); raise SystemExit
layers=[]
if "layers" in d:
    layers=d["layers"]
elif "manifests" in d:
    for m in d["manifests"]:
        if m.get("platform",{}).get("architecture")=="amd64":
            print("multi-arch"); raise SystemExit
    print("multi-arch"); raise SystemExit
s=sum(l.get("size",0) for l in layers)
print(f"{s/1024/1024:.0f} MB")
' 2>/dev/null)
    echo "  ${tag}: ${total}"
  else
    echo "  ${tag}: (not found)"
  fi
done

echo
echo "=== alternative images ==="
for img in "wppconnect/wppconnect-server:latest" "wppconnect/wppconnect-server:v2.10.0"; do
  echo "  $img"
done

echo
echo "=== DONE ==="
