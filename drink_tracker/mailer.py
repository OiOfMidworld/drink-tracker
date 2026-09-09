from flask_mail import Mail, Message

mail = Mail()


def send_reminder_email(app, to_email, year, month, day):
    link = f"{app.config['APP_BASE_URL']}/calendar/{year}/{month}?open={day:02d}"
    body = (
        "Good morning!\n\n"
        "Did you have any drinks last night? Click the link below to record it:\n\n"
        f"{link}\n\n"
        "You can turn these emails off anytime from your account settings."
    )
    message = Message(subject="Log last night's drinks?", recipients=[to_email], body=body)
    mail.send(message)
