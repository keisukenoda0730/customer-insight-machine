import io
import pandas as pd
from datetime import datetime
from typing import List, Dict

NOTEBOOKLM_PROMPT = """\
# NotebookLM 分析用プロンプト
以下のドキュメントは、ターゲット層の「生の声（悩み・相談）」を集めたものです。
このデータから、以下の3点を深く分析し、レポートを作成してください。

1. **根源的な恐怖と欲求**: 表面的な悩みではなく、彼らが本当に恐れていること、本当はどうなりたいのか。
2. **頻出する特徴的な感情表現**: ターゲットが好んで使うネガティブなキーワードや言い回し（コピーライティングに使用するため）。
3. **解決策のコンセプト案**: この深い悩みを解決するために、どのような切り口の商品・サービスを提供すべきか、3つのアイデア。

---
"""


def to_csv(results: List[Dict]) -> bytes:
    """UTF-8 BOM付きCSVを生成"""
    rows = [
        {
            "検索クエリ": r.get("query", ""),
            "タイトル": r.get("title", ""),
            "本文(フルテキストor概要)": r.get("full_text", r.get("snippet", "")),
            "テキスト取得方法": r.get("text_source", ""),
            "URL": r.get("url", ""),
        }
        for r in results
    ]
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def to_markdown(results: List[Dict], keyword: str) -> str:
    """NotebookLM用Markdownを生成（分析プロンプト付き）"""
    lines = [
        NOTEBOOKLM_PROMPT,
        f"# 検索キーワード: {keyword}",
        f"",
        f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"総件数: {len(results)}件",
        f"",
        "---",
        "",
    ]

    for i, r in enumerate(results, 1):
        lines += [
            f"## {i}件目",
            f"- **検索クエリ**: {r.get('query', '')}",
            f"- **タイトル**: {r.get('title', '')}",
            f"- **URL**: {r.get('url', '')}",
            f"- **テキスト取得方法**: {r.get('text_source', '')}",
            f"- **悩みの詳細（本文）**:",
            f"",
            r.get("full_text", r.get("snippet", "")),
            "",
            "---",
            "",
        ]

    return "\n".join(lines)
