import time
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Callable

DEFAULT_EXCLUDE_DOMAINS = [
    "youtube.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "amazon.co.jp",
    "amazon.com",
    "rakuten.co.jp",
    "google.com",
    "wikipedia.org",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SCRAPE_TIMEOUT = 12


def is_excluded_domain(url: str, exclude_domains: List[str]) -> bool:
    try:
        netloc = urlparse(url).netloc.lower()
        return any(ex.lower() in netloc for ex in exclude_domains)
    except Exception:
        return False


def can_fetch(url: str) -> bool:
    """robots.txtを確認してスクレイピング可否を返す。確認できない場合は許可とみなす"""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def extract_text(url: str, max_chars: int = 3000) -> Optional[str]:
    """URLから本文テキストを抽出。失敗時はNoneを返す"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        text = "\n".join(
            p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
        )

        if not text:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""

        text = "\n".join(line for line in text.splitlines() if line.strip())

        if max_chars > 0:
            text = text[:max_chars]

        return text if text else None

    except Exception:
        return None


def scrape_all(
    results: List[Dict],
    exclude_domains: List[str],
    check_robots: bool,
    max_chars: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict]:
    """全URLをスクレイピングしてfull_textとtext_sourceを付与したリストを返す"""
    enriched: List[Dict] = []
    total = len(results)

    for i, item in enumerate(results):
        url = item["url"]
        enriched_item = dict(item)

        if progress_callback:
            progress_callback(i, total, url)

        # 除外ドメインチェック
        if is_excluded_domain(url, exclude_domains):
            enriched_item["full_text"] = item.get("snippet", "")
            enriched_item["text_source"] = "snippet（除外ドメイン）"
            enriched.append(enriched_item)
            continue

        # robots.txtチェック
        if check_robots and not can_fetch(url):
            enriched_item["full_text"] = item.get("snippet", "")
            enriched_item["text_source"] = "snippet（robots.txt禁止）"
            enriched.append(enriched_item)
            continue

        # スクレイピング実行
        text = extract_text(url, max_chars)
        if text and len(text) > len(item.get("snippet", "")):
            enriched_item["full_text"] = text
            enriched_item["text_source"] = "フルテキスト"
        else:
            enriched_item["full_text"] = item.get("snippet", "")
            enriched_item["text_source"] = "snippet（フォールバック）"

        enriched.append(enriched_item)
        # サーバー負荷対策（必須）
        time.sleep(3)

    return enriched
