import requests

RESEND_API_URL = "https://api.resend.com/emails"


def send_reminder_email(app, to_email, year, month, day):
    link = f"{app.config['APP_BASE_URL']}/calendar/{year}/{month}?open={day:02d}"
    body = (
        "Good morning!\n\n"
        "Did you have any drinks last night? Click the link below to record it:\n\n"
        f"{link}\n\n"
        "You can turn these emails off anytime from your account settings."
    )

    if app.config.get("MAIL_SUPPRESS_SEND"):
        return

    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {app.config['RESEND_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "from": app.config["MAIL_DEFAULT_SENDER"],
            "to": [to_email],
            "subject": "Log last night's drinks?",
            "text": body,
        },
        timeout=10,
    )
    response.raise_for_status()
