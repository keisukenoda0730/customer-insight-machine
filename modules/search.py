from tavily import TavilyClient
from typing import List, Dict, Tuple, Optional

DEFAULT_NEGATIVE_WORDS = ["辛い", "失敗", "限界", "相談", "やめたい"]


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

            if raw:
                full_text = raw[:max_chars] if max_chars > 0 else raw
                text_source = "フルテキスト（Tavily）"
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
