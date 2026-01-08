# Change SMTP Password on Mail Server (mail.discomarder.live)

## Option 1: Using Webmail Interface (Easiest)

If you have Roundcube, SquirrelMail, or similar webmail:

```bash
# SSH to your mail server
ssh user@mail.discomarder.live

# Or access via browser:
# https://mail.discomarder.live/webmail
# Login with: info@discomarder.live
# Go to Settings > Password and change it
```

## Option 2: Using Postfix/Dovecot (Common Ubuntu Setup)

If your mail server uses Postfix/Dovecot:

```bash
# SSH to mail server
ssh user@mail.discomarder.live

# Change password using doveadm (Dovecot)
sudo doveadm pw -s SHA512-CRYPT
# Enter new password when prompted
# Copy the generated hash

# Edit the password file (location depends on your setup)
# Common locations:
sudo nano /etc/dovecot/users
# OR
sudo nano /etc/postfix/vmailbox
# OR if using MySQL/MariaDB:
sudo mysql -u root -p
USE mail;
UPDATE mailbox SET password = 'generated_hash_here' WHERE username = 'info@discomarder.live';
FLUSH PRIVILEGES;
EXIT;
```

## Option 3: Using chpasswd (System Users)

If the email account is a system user:

```bash
# SSH to mail server
ssh user@mail.discomarder.live

# Change password for the user
sudo chpasswd
# Then type: info:new_password_here
# Press Enter, then Ctrl+D
```

## Option 4: Using passwd Command

If info is a system user:

```bash
ssh user@mail.discomarder.live
sudo passwd info
# Enter new password twice when prompted
```

## Option 5: Using cPanel/WHM (If Applicable)

```bash
# Access WHM via browser:
# https://mail.discomarder.live:2087
# Login → Email Accounts → Modify → Change Password
```

## Option 6: Using DirectAdmin (If Applicable)

```bash
# Access DirectAdmin via browser:
# https://mail.discomarder.live:2222
# Email Accounts → info@discomarder.live → Change Password
```

## Option 7: Using MySQL/MariaDB (If Using Database)

```bash
ssh user@mail.discomarder.live

# Connect to database
sudo mysql -u root -p

# Find the mail database
SHOW DATABASES;
USE mail;  # or postfix, or similar

# Find the table
SHOW TABLES;
# Usually: mailbox, users, or accounts

# Update password (generate hash first with doveadm)
UPDATE mailbox SET password = 'generated_hash' WHERE username = 'info@discomarder.live';

# Or if using plain text (less secure):
UPDATE mailbox SET password = 'new_password' WHERE username = 'info@discomarder.live';

FLUSH PRIVILEGES;
EXIT;
```

## Option 8: Using PostfixAdmin (Web Interface)

```bash
# Access PostfixAdmin:
# https://mail.discomarder.live/postfixadmin
# Login → Virtual List → info@discomarder.live → Change Password
```

## Quick Diagnostic Commands

To find out what mail server software you're using:

```bash
ssh user@mail.discomarder.live

# Check if Postfix is running
sudo systemctl status postfix

# Check if Dovecot is running
sudo systemctl status dovecot

# Check mail server software
sudo postconf mail_version
sudo doveconf -v | head -20

# Check mail user database location
sudo find /etc -name "*mail*" -type f 2>/dev/null | grep -E "(passwd|users|vmailbox)"
```

## After Changing Password

1. **Restart mail services:**
```bash
sudo systemctl restart postfix
sudo systemctl restart dovecot
```

2. **Test the new password:**
```bash
# Test SMTP authentication
telnet localhost 25
# Or use swaks:
swaks --to info@discomarder.live --from test@test.com --server mail.discomarder.live --auth LOGIN --auth-user info@discomarder.live --auth-password new_password
```

3. **Update docker-compose on Saturn:**
```bash
ssh saturn.local
cd /volume1/docker-compose/stacks/kometa-listsync
sudo nano .env
# Update SMTP_PASSWORD=new_password
sudo docker-compose restart listsync
```

## Most Common: Postfix + Dovecot + MySQL

If you're using the most common setup (Postfix + Dovecot + MySQL):

```bash
# 1. Generate password hash
ssh user@mail.discomarder.live
sudo doveadm pw -s SHA512-CRYPT
# Enter new password, copy the hash (starts with $6$)

# 2. Update database
sudo mysql -u root -p
USE mail;
UPDATE mailbox SET password = '$6$generated_hash_here' WHERE username = 'info@discomarder.live';
FLUSH PRIVILEGES;
EXIT;

# 3. Restart services
sudo systemctl restart dovecot
sudo systemctl restart postfix

# 4. Test
sudo doveadm auth test info@discomarder.live
# Enter new password when prompted
```
