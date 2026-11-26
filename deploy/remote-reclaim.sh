#!/usr/bin/env bash
# Reclaim disk headroom on the 8GB root volume so wppconnect can be pulled.
set -uo pipefail

echo "=== BEFORE ==="
df -h /

echo
echo "=== who owns libLLVM.so.19.1 ==="
dpkg -S /usr/lib/x86_64-linux-gnu/libLLVM.so.19.1 2>/dev/null || echo "(unowned / not in dpkg)"
ls -la /usr/lib/x86_64-linux-gnu/libLLVM.so* 2>/dev/null

echo
echo "=== 1. shrink swapfile 2048MB -> 1024MB ==="
if [ -f /swapfile ]; then
  cur=$(stat -c '%s' /swapfile)
  echo "current swapfile bytes: $cur"
  swapoff /swapfile 2>/dev/null && echo "swapoff ok" || echo "swapoff FAILED"
  rm -f /swapfile
  fallocate -l 1G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null 2>&1 && echo "mkswap ok"
  swapon /swapfile 2>/dev/null && echo "swapon ok" || echo "swapon FAILED"
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "swap now:"; free -h | grep -i swap
else
  echo "no /swapfile"
fi

echo
echo "=== 2. remove leftover deploy tarball ==="
rm -fv /home/ubuntu/ticket-fox-web/ticket-fox-web-deploy.tar.gz 2>/dev/null
find /home/ubuntu -maxdepth 2 -name '*.tar.gz' -size +10M -print -delete 2>/dev/null

echo
echo "=== 3. remove LLVM runtime lib (headless server, unused) ==="
rm -fv /usr/lib/x86_64-linux-gnu/libLLVM.so.19.1 2>/dev/null
rm -rf /usr/lib/llvm-19 2>/dev/null

echo
echo "=== 4. remove non-essential data/docs (SAFE list only) ==="
# NOTE: /usr/lib/systemd, /usr/lib/udev, /usr/lib/firmware and /usr/lib/gconv are
# deliberately NOT touched - they are required for boot, networking and locale.
rm -rf /usr/share/ieee-data /usr/share/tcltk /usr/share/X11 2>/dev/null
rm -rf /usr/share/perl5 /usr/share/terminfo 2>/dev/null
rm -rf /usr/lib/x86_64-linux-gnu/perl /usr/lib/x86_64-linux-gnu/perl-base 2>/dev/null
rm -rf /usr/lib/git-core 2>/dev/null
rm -rf /usr/libexec/fwupd /usr/libexec/udisks2 /usr/libexec/plymouth 2>/dev/null
rm -rf /usr/share/fwupd /usr/share/zoneinfo/right 2>/dev/null
rm -rf /usr/lib/python3/test /usr/lib/python3.12/test 2>/dev/null
rm -rf /usr/share/doc /usr/share/man /usr/share/locale 2>/dev/null

echo
echo "=== 5. apt + journal + docker cleanup ==="
apt-get clean 2>/dev/null
rm -rf /var/lib/apt/lists/* 2>/dev/null
journalctl --vacuum-size=8M 2>/dev/null | tail -2
rm -rf /var/log/*.gz /var/log/*.1 /var/log/apt/* 2>/dev/null
docker builder prune -af 2>/dev/null | tail -2
docker image prune -f 2>/dev/null | tail -2

echo
echo "=== AFTER ==="
df -h /
echo
free -h
echo
echo "=== DONE ==="
