# project-access

## 📧 Email Configuration

This project uses email (SMTP) to send OTP verification codes.

An `email_config.json` file is already included in the project.
You only need to update it with your own email credentials.

---

## ⚙️ Step 1: Open `email_config.json`

Locate the file in the project root and replace the placeholder values:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your_email@gmail.com",
  "password": "your_app_password"
}
```

---

## 🔐 Step 2: Generate an App Password (Gmail)

If you are using Gmail:

1. Enable **2-Step Verification** on your Google account
2. Go to **App Passwords**
3. Generate a password for "Mail"
4. Copy the generated password
5. Paste it into `"password"` in `email_config.json`

⚠️ Do NOT use your normal Gmail password.

---

## ▶️ Step 3: Run the application

```bash
python app.py
```

---

## ⚠️ Security Note

* Do NOT share your real credentials
* It is recommended to add `email_config.json` to `.gitignore` after setup
* Keep only a template version in the repository if needed

---

## ✅ Expected Result

* The app sends OTP codes via email
* Users can verify login using the received code
