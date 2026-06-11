from pathlib import Path


def test_nginx_sets_hsts_header_for_public_proxy():
    hsts_header = (
        'add_header Strict-Transport-Security '
        '"max-age=31536000; includeSubDomains; preload" always;'
    )

    nginx_config = Path("proxy/nginx.conf").read_text()

    assert hsts_header in nginx_config
    assert "proxy_hide_header Strict-Transport-Security;" in nginx_config
