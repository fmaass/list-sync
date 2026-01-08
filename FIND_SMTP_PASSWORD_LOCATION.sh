#!/bin/bash
# Diagnostic script to find where SMTP password is stored

echo "=== Checking Postfix Configuration ==="
sudo postconf | grep -E "virtual_mailbox|virtual_alias|sasl" | head -10

echo ""
echo "=== Checking Virtual Mailbox Files ==="
sudo ls -la /etc/postfix/virtual* 2>/dev/null || echo "No virtual files found"
sudo cat /etc/postfix/vmailbox 2>/dev/null | head -5 || echo "No vmailbox file"

echo ""
echo "=== Checking SASL Password File ==="
sudo ls -la /etc/postfix/sasl_passwd* 2>/dev/null || echo "No sasl_passwd file"
sudo cat /etc/postfix/sasl_passwd 2>/dev/null | grep info || echo "No info@ entry in sasl_passwd"

echo ""
echo "=== Checking System Users ==="
sudo grep info /etc/passwd || echo "No 'info' system user"
sudo grep info /etc/shadow || echo "No 'info' in shadow file"

echo ""
echo "=== Checking Postfix Main Config ==="
sudo grep -E "virtual|sasl|mysql|pgsql" /etc/postfix/main.cf | grep -v "^#" | head -10

echo ""
echo "=== Checking for PostfixAdmin ==="
sudo find /var/www -name "*postfixadmin*" -type d 2>/dev/null
sudo find /usr/share -name "*postfixadmin*" -type d 2>/dev/null

echo ""
echo "=== Checking Mail Database Files ==="
sudo find /etc -name "*mail*" -type f 2>/dev/null | grep -v ".dpkg" | head -10


