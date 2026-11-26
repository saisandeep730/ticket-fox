from dataclasses import dataclass
import os

@dataclass
class Config:
    impersonate: str = os.getenv("IMPERSONATE", "safari18_0")
    user_agent: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
    )
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff: float = float(os.getenv("RETRY_BACKOFF", "1.0"))
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "15.0"))
    proxy_urls: str = os.getenv("PROXY_URLS", "")
    proxy_url: str = os.getenv("PROXY_URL", "")
    scraperapi_key: str = os.getenv("SCRAPERAPI_KEY", "")
