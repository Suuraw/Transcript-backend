import requests
from requests.adapters import HTTPAdapter
from requests.sessions import Session

def patch_requests_with_proxy_url(proxy_user, proxy_pass, proxy_host, proxy_port):
    proxy_auth = f"{proxy_user}:{proxy_pass}@" if proxy_pass else f"{proxy_user}@"
    proxy_url = f"http://{proxy_auth}{proxy_host}:{proxy_port}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }

    session = requests.Session()
    session.proxies.update(proxies)

    # Optional: mimic browser
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    # monkey-patch
    requests.request = session.request
