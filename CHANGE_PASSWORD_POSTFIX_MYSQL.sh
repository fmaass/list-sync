#!/bin/bash
# Commands to run on mail server (fabianmaass.de) to change SMTP password

# 1. Connect to MySQL and find the mail database
sudo mysql -u root -p

# Then run these SQL commands:
# SHOW DATABASES;
# USE mail;  # or postfix, or similar name
# SHOW TABLES;
# DESCRIBE mailbox;  # or users, or accounts table

# 2. Generate password hash (if using MySQL's password function)
# Or use openssl to generate MD5 hash:
# openssl passwd -1 'your_new_password'

# 3. Update password in MySQL
# UPDATE mailbox SET password = MD5('new_password') WHERE username = 'info@discomarder.live';
# OR if using encrypted:
# UPDATE mailbox SET password = ENCRYPT('new_password') WHERE username = 'info@discomarder.live';
# OR if stored as plain hash:
# UPDATE mailbox SET password = 'generated_hash' WHERE username = 'info@discomarder.live';

# 4. Flush privileges
# FLUSH PRIVILEGES;
# EXIT;

# 5. Restart Postfix
# sudo systemctl restart postfix


