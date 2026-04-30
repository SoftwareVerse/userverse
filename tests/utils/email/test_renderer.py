import pytest
from app.email.renderer import render_email_template


@pytest.mark.parametrize(
    "template_name, context",
    [
        (
            "user_registration.html",
            {"user_name": "Sandile", "verification_link": "123456"},
        ),
        ("reset_user_password.html", {"user_name": "Sandile", "otp": "123456"}),
        (
            "company_invite.html",
            {"invitee": "John", "company": "Oxillium", "role": "Engineer"},
        ),
    ],
)
def test_render_email_template_success(template_name, context):
    html = render_email_template(template_name, context)
    assert isinstance(html, str)
    assert "<html>" in html
    for value in context.values():
        assert str(value) in html


def test_render_email_template_invalid_template():
    with pytest.raises(
        Exception
    ):  # Could be jinja2.TemplateNotFound if Jinja2 is strict
        render_email_template("nonexistent_template.html", {"key": "value"})
