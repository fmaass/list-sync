#!/usr/bin/env python3
"""
Test script to verify SMTP email sending works
Run this inside the container to test email functionality
"""

import os
import sys
sys.path.insert(0, '/usr/src/app')

from list_sync.reports.email_sender import send_email

# Test email
subject = "🧪 Test Email - SMTP Verification"
body = """
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>✅ SMTP Test Successful!</h2>
    <p>This is a test email to verify SMTP configuration is working correctly.</p>
    <p><strong>SMTP Settings:</strong></p>
    <ul>
        <li>Host: {host}</li>
        <li>Port: {port}</li>
        <li>User: {user}</li>
        <li>From: {mail_from}</li>
        <li>To: {mail_to}</li>
    </ul>
    <p>If you received this email, SMTP is configured correctly! 🎉</p>
</body>
</html>
""".format(
    host=os.getenv("SMTP_HOST", "not set"),
    port=os.getenv("SMTP_PORT", "not set"),
    user=os.getenv("SMTP_USER", "not set"),
    mail_from=os.getenv("MAIL_FROM", "not set"),
    mail_to=os.getenv("MAIL_TO", "not set")
)

print("🧪 Testing SMTP email sending...")
print(f"SMTP_HOST: {os.getenv('SMTP_HOST')}")
print(f"SMTP_USER: {os.getenv('SMTP_USER')}")
print(f"MAIL_TO: {os.getenv('MAIL_TO')}")
print()

result = send_email(subject, body, html=True)

if result == "sent":
    print("✅ Email sent successfully!")
    print(f"Check inbox: {os.getenv('MAIL_TO')}")
elif result:
    print(f"📁 Email saved to outbox: {result}")
else:
    print("❌ Failed to send email")
    sys.exit(1)


