from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path

templates_path = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


def render_email_template(template_name: str, context: dict) -> str:
    """
    Render a Jinja2 HTML template for email.
    """
    email_request = Request(scope={"type": "http"})
    return templates.get_template(template_name).render(
        {"request": email_request, **context}
    )
