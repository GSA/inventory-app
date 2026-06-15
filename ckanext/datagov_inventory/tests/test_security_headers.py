from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_nginx_sets_hsts_header_for_public_proxy():
    hsts_header = (
        'add_header Strict-Transport-Security '
        '"max-age=31536000; includeSubDomains; preload" always;'
    )

    nginx_config = (REPO_ROOT / "proxy" / "nginx.conf").read_text()

    assert hsts_header in nginx_config
    assert "proxy_hide_header Strict-Transport-Security;" in nginx_config
