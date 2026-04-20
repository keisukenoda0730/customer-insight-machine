import re
from tavily import TavilyClient
from typing import List, Dict, Tuple, Optional

DEFAULT_NEGATIVE_WORDS = ["辛い", "失敗", "限界", "相談", "やめたい"]

_GARBAGE_PATTERNS = [
    "JavaScriptが無効",
    "JavaScriptを有効",
    "JavaScript is disabled",
    "このページを表示するにはJavaScript",
    "ブラウザの設定でJavaScript",
]
_MIN_PLAIN_LENGTH = 150


def _clean_markdown(text: str) -> str:
    """マークダウン記法を除去してプレーンテキストにする"""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)           # 画像を除去
    text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text) # リンクをテキストのみに
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)  # 見出し記号を除去
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)  # 太字・斜体を除去
    text = re.sub(r'\n{3,}', '\n\n', text)                 # 連続空行を圧縮
    return text.strip()


def _is_garbage(text: str) -> bool:
    """本文としての価値がないコンテンツかを判定する"""
    if not text or len(text.strip()) < 50:
        return True
    if any(p in text for p in _GARBAGE_PATTERNS):
        return True
    # マークダウン除去後のプレーンテキストが少ない＝ナビゲーションリンクの羅列
    cleaned = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)
    cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', cleaned)
    if len(cleaned.strip()) < _MIN_PLAIN_LENGTH:
        return True
    return False


def build_queries(keyword: str, negative_words: List[str], deep_mode: bool) -> List[str]:
    queries = [keyword]
    if deep_mode:
        for word in negative_words:
            queries.append(f"{keyword} {word}")
    return queries


def collect_results(
    api_key: str,
    keyword: str,
    negative_words: List[str],
    deep_mode: bool,
    base_num: int,
    include_domains: Optional[List[str]] = None,
    max_chars: int = 2000,
) -> Tuple[List[Dict], int]:
    """Tavilyで複数クエリ検索し、重複排除した結果と実際のAPI呼び出し回数を返す"""
    client = TavilyClient(api_key=api_key)
    queries = build_queries(keyword, negative_words, deep_mode)
    seen_urls: set = set()
    all_results: List[Dict] = []
    api_call_count = 0

    search_kwargs: Dict = {
        "max_results": min(base_num, 20),
        "search_depth": "advanced",
        "include_raw_content": True,
    }
    if include_domains:
        search_kwargs["include_domains"] = include_domains

    for query in queries:
        try:
            response = client.search(query=query, **search_kwargs)
            api_call_count += 1
        except Exception as e:
            raise RuntimeError(f"Tavily API エラー: {e}") from e

        for item in response.get("results", []):
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            raw = item.get("raw_content") or ""
            snippet = item.get("content", "")

            # raw_contentのゴミ判定 → クリーニング → 再判定
            if raw and not _is_garbage(raw):
                cleaned = _clean_markdown(raw)
                if not _is_garbage(cleaned):
                    full_text = cleaned[:max_chars] if max_chars > 0 else cleaned
                    text_source = "フルテキスト（Tavily）"
                else:
                    full_text = snippet
                    text_source = "スニペット（Tavily）"
            else:
                full_text = snippet
                text_source = "スニペット（Tavily）"

            all_results.append({
                "query": query,
                "title": item.get("title", ""),
                "snippet": snippet,
                "full_text": full_text,
                "text_source": text_source,
                "url": url,
            })

    return all_results, api_call_count
