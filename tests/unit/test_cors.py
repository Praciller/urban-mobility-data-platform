from apps.api.app.core.cors import DEFAULT_CORS_ORIGINS, get_allowed_origins


def test_default_origins_are_preserved() -> None:
    assert get_allowed_origins(None) == list(DEFAULT_CORS_ORIGINS)
    assert get_allowed_origins("") == list(DEFAULT_CORS_ORIGINS)


def test_configured_origins_are_exact_and_conservative() -> None:
    assert get_allowed_origins("https://dashboard.example, https://dashboard.example/") == [
        "https://dashboard.example"
    ]
    assert get_allowed_origins("*, https://ok.example/path, not-an-origin") == []


def test_malformed_origins_are_ignored_without_broadening_access() -> None:
    assert (
        get_allowed_origins(
            "https://user:password@example.com, https://example.com:invalid, https://[::1"
        )
        == []
    )
