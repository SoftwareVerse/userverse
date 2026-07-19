import pytest
from app.email.renderer import render_email_template


@pytest.mark.parametrize(
    "template_name, context",
    [
        (
            "user_registration.html",
            {"user_name": "Sandile", "verification_link": "123456"},
        ),
        (
            "user_notification.html",
            {
                "template_name": "User Account Registration",
                "user_name": "Sandile",
                "app_name": "Userverse",
                "verification_link": "123456",
                "mode": "create",
            },
        ),
        (
            "user_notification.html",
            {
                "template_name": "Verify Your Email Address",
                "user_name": "Sandile",
                "app_name": "Userverse",
                "verification_link": "123456",
                "mode": "verify",
            },
        ),
        (
            "reset_user_password.html",
            {"user_name": "Sandile", "otp": "123456", "app_name": "Userverse"},
        ),
        (
            "company_invite.html",
            {
                "invitee": "John",
                "company": "Oxillium",
                "role": "Engineer",
                "app_name": "Userverse",
            },
        ),
    ],
)
def test_render_email_template_success(template_name, context):
    html = render_email_template(template_name, context)
    assert isinstance(html, str)
    assert "<html>" in html

    if template_name == "user_notification.html":
        assert context["user_name"] in html
        assert context["app_name"] in html
        assert context["verification_link"] in html
        assert "Verify Email" in html
        assert context["template_name"] not in html
        return

    for value in context.values():
        assert str(value) in html


def test_render_email_template_invalid_template():
    with pytest.raises(
        Exception
    ):  # Could be jinja2.TemplateNotFound if Jinja2 is strict
        render_email_template("nonexistent_template.html", {"key": "value"})
