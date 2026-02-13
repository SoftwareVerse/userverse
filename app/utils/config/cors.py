from app.configs import CorsSettings


class CorsConfig:
    """Compatibility wrapper around app.configs.CorsSettings."""

    CORS_DEFAULT = {
        "allowed": ["*"],
        "blocked": ["http://localhost:3000"],
    }

    @classmethod
    def get_cors(cls, configs: dict, environment: str = "development") -> dict:
        if environment == "test_environment":
            return cls.CORS_DEFAULT

        cors_config = configs.get("cors") or configs.get("cor_origins") or {}
        if not cors_config:
            return cls.CORS_DEFAULT

        cors = CorsSettings(**cors_config)
        return {
            "allowed": cors.allowed,
            "blocked": cors.blocked,
        }
