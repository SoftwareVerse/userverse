from app.utils.email.renderer import render_email_template
from app.utils.email.sender import send_email


class MailService:
    @staticmethod
    def send_template_email(to: str, subject: str, template_name: str, context: dict):
        html_body = render_email_template(template_name, context)
        send_email(
            to=to,
            subject=subject,
            html_body=html_body,
            reason=f"template:{template_name}",
            context={
                "subject": subject,
                "template_name": template_name,
                "template_context": context,
                "html_body": html_body,
            },
        )
