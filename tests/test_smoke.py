"""Smoke tests: Django boots, the relocated skills package imports cleanly,
and the LLM service no longer relies on the old sys.path hack or a hardcoded
machine-specific log path.
"""


def test_skills_package_imports() -> None:
    """weather/news skills must be importable as a proper package after the move."""
    from skills.news_skill import get_realtime_news
    from skills.weather_skill import get_realtime_weather

    assert callable(get_realtime_weather)
    assert callable(get_realtime_news)


def test_django_settings_configured() -> None:
    from django.conf import settings

    assert settings.SECRET_KEY


def test_llm_service_skill_flag_loaded() -> None:
    from core.services import llm_service

    assert hasattr(llm_service, "SKILLS_LOADED")
    assert llm_service.SKILLS_LOADED is True


def test_token_log_path_is_project_local() -> None:
    """Default path must be the project-local backend/data/token_usage.md,
    not the old hardcoded shared ``Token记录/token.md`` constant."""
    from core.services import llm_service

    assert llm_service.TOKEN_MD_PATH.replace("\\", "/").endswith("backend/data/token_usage.md")


def test_token_log_path_env_override(monkeypatch) -> None:
    """TOKEN_LOG_PATH must override the default location."""
    import importlib

    from core.services import llm_service

    custom = "/tmp/soulmate_custom_token_log.md"
    monkeypatch.setenv("TOKEN_LOG_PATH", custom)
    try:
        importlib.reload(llm_service)
        assert llm_service.TOKEN_MD_PATH == custom
    finally:
        monkeypatch.delenv("TOKEN_LOG_PATH", raising=False)
        importlib.reload(llm_service)
