#!/usr/bin/env bash
# First setup of PicWise's server (OVHcloud VPS-4, Ubuntu 24.04): security only
# (owner's «ναι», 2026-10-25). Nothing of the site is installed here.
#
# Run as root by .github/workflows/server-setup.yml, which copies it to the server
# over SSH. Safe to run again: each step leaves the same state.
#   1. the system brought up to date; from then on, security updates installed every
#      day by unattended-upgrades, with a reboot at 03:30 UTC when one needs it;
#   2. SSH by key only: no password, no root login;
#   3. a firewall that lets in SSH (22) and the site (80, 443) only;
#   4. fail2ban, which bans an address after repeated failed logins.
# Before 2 and 3 a rollback is armed that undoes them in 10 minutes; the workflow
# cancels it once a fresh login works, so a mistake here cannot lock the server out.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
# needrestart only lists what to restart, so no service restarts in the middle of the
# run; the workflow reboots afterwards when an update asks for it.
export NEEDRESTART_MODE=l

SSHD_DROPIN=/etc/ssh/sshd_config.d/10-picwise.conf

apt_get() {
  apt-get -q -y -o DPkg::Lock::Timeout=600 \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold "$@"
}

echo "== 1. updates"
apt_get update
apt_get full-upgrade
apt_get install ufw fail2ban python3-systemd unattended-upgrades

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
cat > /etc/apt/apt.conf.d/52picwise-unattended-upgrades <<'EOF'
// PicWise: when a security update needs a reboot, reboot by itself at night (UTC).
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:30";
EOF
systemctl enable --now apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service

echo "== rollback armed: SSH and firewall undone in 10 minutes unless cancelled"
systemctl stop picwise-rollback.timer 2>/dev/null || true
systemctl reset-failed picwise-rollback.timer picwise-rollback.service 2>/dev/null || true
systemd-run --quiet --unit=picwise-rollback --on-active=10min /bin/sh -c \
  "rm -f $SSHD_DROPIN; systemctl try-reload-or-restart ssh.service; ufw --force disable"

echo "== 2. SSH by key only"
cat > "$SSHD_DROPIN" <<'EOF'
# PicWise: log in with a key only. sshd keeps the first value it reads, and this
# file is read before 50-cloud-init.conf and before sshd_config's own lines.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
EOF
mkdir -p /run/sshd
if ! sshd -t; then
  rm -f "$SSHD_DROPIN"
  echo "sshd refused the new settings; they were removed" >&2
  exit 1
fi
systemctl try-reload-or-restart ssh.service

echo "== 3. firewall"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "== 4. fail2ban"
cat > /etc/fail2ban/jail.d/picwise.conf <<'EOF'
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable fail2ban
systemctl restart fail2ban
# The service counts as started as soon as it forks; wait until it answers.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  fail2ban-client ping >/dev/null 2>&1 && break
  sleep 1
done
fail2ban-client ping

echo "== done"
