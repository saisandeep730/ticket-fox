#!/usr/bin/env bash
# TicketFox — host diagnostics: IAM role, instance identity, disk, image sizes.
set -uo pipefail

TOKEN="$(curl -s -X PUT 'http://169.254.169.254/latest/api/token' \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"

md() {
  curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" "http://169.254.169.254/latest/meta-data/$1"
}

echo "--- instance id ---"
md instance-id; echo
echo "--- instance type ---"
md instance-type; echo
echo "--- availability zone ---"
md placement/availability-zone; echo
echo "--- iam role ---"
ROLE="$(md iam/security-credentials/)"
if [ -z "$ROLE" ]; then
  echo "NONE (no instance profile attached)"
else
  echo "$ROLE"
fi

echo
echo "--- disk ---"
df -h /

echo
echo "--- block devices ---"
lsblk

echo
echo "--- wppconnect tag sizes (compressed) ---"
curl -s 'https://hub.docker.com/v2/repositories/wppconnect/wppconnect-server/tags?page_size=30' \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
for t in d.get("results", []):
    print(f"  {t[\"name\"]:<28} {t[\"full_size\"]/1048576:8.1f} MB")
'

echo
echo "--- local images ---"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'
