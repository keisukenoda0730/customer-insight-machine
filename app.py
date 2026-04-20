import hashlib
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from modules.exporter import to_csv, to_markdown
from modules.search import DEFAULT_NEGATIVE_WORDS, collect_results

# ─────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────
st.set_page_config(
    page_title="顧客インサイト発掘マシーン",
    page_icon="🔍",
    layout="wide",
)

# ─────────────────────────────────────────
# プリセット定義
# ─────────────────────────────────────────
PRESET_DOMAINS = [
    ("Yahoo!知恵袋",  "chiebukuro.yahoo.co.jp", True),
    ("OKWAVE",        "okwave.jp",               True),
    ("教えて!goo",    "oshiete.goo.ne.jp",       True),
    ("発言小町",      "komachi.yomiuri.co.jp",   False),
    ("Quora JP",      "jp.quora.com",            False),
    ("Reddit",        "reddit.com",              False),
]

KEYWORD_HINTS = {
    "😢 人生・生き方の悩み": [
        "生きるのが辛い", "人生どうすればいい", "将来が不安", "自分が嫌い",
        "やる気が出ない", "何もしたくない", "孤独で辛い", "死にたい 相談",
    ],
    "💑 恋愛・婚活": [
        "婚活", "マッチングアプリ", "彼氏ができない", "彼女ができない",
        "結婚できない", "モテない", "片思い 辛い", "告白 失敗",
    ],
    "👨‍👩‍👧 家族・夫婦関係": [
        "夫婦喧嘩", "離婚 したい", "旦那 嫌い", "姑 関係", "親 うるさい",
        "実家 帰りたくない", "毒親", "家族 疲れた",
    ],
    "😰 メンタル・人間関係": [
        "職場 人間関係", "上司 嫌い", "友達できない", "コミュ障",
        "パワハラ", "いじめ 大人", "ストレス 限界", "うつ 仕事",
    ],
    "💼 仕事・キャリア": [
        "仕事 辞めたい", "転職 失敗", "就職できない", "仕事 続かない",
        "職場 馴染めない", "残業 きつい", "給料 低い", "リストラ 不安",
    ],
    "💰 副業・お金・節約": [
        "副業", "お金が貯まらない", "借金 返せない", "節約できない",
        "投資 失敗", "フリーランス 収入不安定", "在宅ワーク", "老後 お金",
    ],
    "🏢 起業・ビジネス": [
        "起業 失敗", "独立 不安", "開業 資金", "ビジネス うまくいかない",
        "集客できない", "売上が上がらない", "経営 苦しい",
    ],
    "🏋️ 健康・ダイエット": [
        "ダイエット", "体重が減らない", "リバウンド", "食欲が止まらない",
        "糖質制限 続かない", "筋トレ 効果ない", "過食 やめたい", "拒食症",
    ],
    "💊 病気・医療の悩み": [
        "病院 行けない", "原因不明 体調不良", "慢性疲労", "頭痛 毎日",
        "眠れない", "パニック障害", "自律神経 乱れ", "病気 不安",
    ],
    "💄 美容・ファッションの悩み": [
        "ニキビ 治らない", "肌荒れ", "髪の毛 薄い", "太って見える",
        "おしゃれ わからない", "老けて見られる", "シミ そばかす", "体臭",
    ],
    "📚 勉強・受験の悩み": [
        "勉強 続かない", "受験 失敗", "集中できない", "成績が上がらない",
        "英語 上達しない", "TOEIC スコア上がらない", "資格 受からない", "社会人 勉強",
    ],
    "✍️ 情報発信・出版": [
        "Kindle出版", "ブログ 稼げない", "YouTube 伸びない", "Instagram フォロワー増えない",
        "アフィリエイト うまくいかない", "SNS 続かない", "情報発信 怖い",
    ],
    "💻 IT・テクノロジーの悩み": [
        "プログラミング 挫折", "ITパスポート 難しい", "パソコン 苦手",
        "スマホ 使いこなせない", "AIツール わからない", "セキュリティ 不安",
    ],
    "👶 育児・子育ての悩み": [
        "育児疲れ", "夜泣き 続く", "イヤイヤ期 対処", "保育園 入れない",
        "ワンオペ育児 限界", "子供 発達 遅い", "育休 復帰 不安", "子育て 孤独",
    ],
    "🏫 学校・学生の悩み": [
        "不登校", "いじめ 相談", "友達できない 学校", "部活 やめたい",
        "先生 嫌い", "大学 行きたくない", "留年 どうすれば", "学校 怖い",
    ],
    "🏠 住まい・生活の悩み": [
        "一人暮らし 不安", "引っ越し 失敗", "隣人 トラブル", "家賃 高い",
        "断捨離 できない", "部屋 片付けられない", "ゴミ屋敷 脱出",
    ],
    "🍳 食事・料理の悩み": [
        "料理 苦手", "食費 節約できない", "外食 やめられない", "偏食 治したい",
        "お弁当 続かない", "栄養バランス わからない", "砂糖 やめられない",
    ],
    "🐕 ペットの悩み": [
        "犬 しつけ できない", "猫 問題行動", "ペット 病気 お金",
        "ペット 死 悲しい", "動物 アレルギー", "ペット 飼えなくなった",
    ],
    "✈️ 旅行・お出かけの悩み": [
        "旅行 一人 寂しい", "海外旅行 怖い", "旅行 お金 ない",
        "飛行機 怖い", "旅行 友達 いない", "国内旅行 どこがいい",
    ],
    "👴 老後・シニアの悩み": [
        "老後 お金 不安", "定年後 やることない", "介護 疲れた", "親 認知症",
        "年金 足りない", "老後 孤独", "終活 どうすれば", "健康寿命 延ばしたい",
    ],
}

# ─────────────────────────────────────────
# セッションステート初期化
# ─────────────────────────────────────────
_defaults = {
    "tavily_api_key": st.secrets.get("TAVILY_API_KEY", ""),
    "api_call_total": 0,
    "last_results": None,
    "last_params_hash": None,
    "last_keyword": "",
    "keyword_value": "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _make_cache_key(keyword, deep_mode, negative_words, base_num, include_domains) -> str:
    payload = json.dumps(
        {
            "keyword": keyword,
            "deep_mode": deep_mode,
            "negative_words": sorted(negative_words),
            "base_num": base_num,
            "include_domains": sorted(include_domains),
        },
        ensure_ascii=False,
    )
    return hashlib.md5(payload.encode()).hexdigest()


# ─────────────────────────────────────────
# サイドバー（API使用状況はプレースホルダーで末尾に描画）
# ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Tavily API設定")
    api_key_input = st.text_input(
        "Tavily APIキー",
        value=st.session_state.tavily_api_key,
        type="password",
        placeholder="tvly-...",
    )
    if api_key_input:
        st.session_state.tavily_api_key = api_key_input

    st.divider()
    st.header("🌐 検索対象サイト")
    st.caption("チェックしたサイト内のみを検索します。すべて外すと全ウェブが対象。")

    checked_domains = []
    for label, domain, default in PRESET_DOMAINS:
        if st.checkbox(label, value=default, key=f"domain_{domain}"):
            checked_domains.append(domain)

    with st.expander("＋ カスタムドメインを追加", expanded=False):
        custom_input = st.text_area(
            "ドメイン（1行1つ）",
            placeholder="example.com",
            height=80,
            label_visibility="collapsed",
        )
        custom_domains = [d.strip() for d in custom_input.splitlines() if d.strip()]

    include_domains = checked_domains + custom_domains
    if include_domains:
        st.caption(f"対象: {len(include_domains)}サイト")
    else:
        st.caption("⚠️ 全ウェブが対象です")

    st.divider()
    st.header("📡 API使用状況（本セッション）")
    # 検索後に正しい値を表示するためプレースホルダーを使用
    _api_counter_slot = st.empty()

# ─────────────────────────────────────────
# メイン画面
# ─────────────────────────────────────────
st.title("🔍 顧客インサイト発掘マシーン")
st.caption("悩みキーワードをTavilyで検索し、NotebookLM分析用データを自動生成します。")

# ── キーワードヒント ──
with st.expander("💡 キーワードが思いつかない方はここをクリック", expanded=False):
    st.caption("ジャンルを選んでキーワードをクリックすると自動入力されます。")
    category = st.selectbox(
        "ジャンル",
        options=list(KEYWORD_HINTS.keys()),
        label_visibility="collapsed",
    )
    hint_cols = st.columns(4)
    for i, kw in enumerate(KEYWORD_HINTS[category]):
        if hint_cols[i % 4].button(kw, key=f"hint_{kw}", use_container_width=True):
            st.session_state.keyword_value = kw
            st.rerun()

# ── キーワード入力 ──
keyword = st.text_input(
    "🎯 検索キーワード",
    value=st.session_state.keyword_value,
    placeholder="例: ダイエット、婚活、副業...",
)
st.session_state.keyword_value = keyword

# ── 深掘りモード ──
deep_mode = st.checkbox(
    "🔥 深掘り検索モード（ネガティブワードを自動掛け合わせ）",
    value=True,
)

if deep_mode:
    with st.expander("📝 ネガティブワードをカスタマイズ", expanded=False):
        neg_input = st.text_area(
            "ネガティブワード（1行1ワード）",
            value="\n".join(DEFAULT_NEGATIVE_WORDS),
            height=130,
            label_visibility="collapsed",
        )
        negative_words = [w.strip() for w in neg_input.splitlines() if w.strip()]
        if keyword:
            preview = [keyword] + [f"{keyword} {w}" for w in negative_words]
            st.caption("生成クエリ: " + "　/　".join(f"`{q}`" for q in preview))
else:
    negative_words = DEFAULT_NEGATIVE_WORDS

col_num, col_chars = st.columns(2)
with col_num:
    base_num = st.slider(
        "📊 ベース取得件数（1クエリあたり）",
        min_value=5, max_value=20, value=10, step=5,
        help="Tavilyは1リクエストあたり最大20件",
    )
with col_chars:
    max_chars = st.slider(
        "📄 本文の最大文字数",
        min_value=500, max_value=5000, value=2000, step=500,
        help="1件あたりのテキスト上限。NotebookLMのファイルサイズを抑制します。",
    )

if keyword:
    query_count = 1 + (len(negative_words) if deep_mode else 0)
    domain_count = max(1, len(include_domains))
    estimated_calls = query_count * domain_count
    st.info(
        f"📡 このリサーチのAPI消費目安: **{estimated_calls} 回** "
        f"（{query_count} クエリ × {domain_count} サイト）"
    )

st.divider()

# ── キャッシュ判定 ──
cache_key = (
    _make_cache_key(keyword, deep_mode, negative_words, base_num, include_domains)
    if keyword else ""
)
can_use_cache = bool(
    keyword
    and st.session_state.last_results
    and cache_key == st.session_state.last_params_hash
)
if can_use_cache:
    st.success(
        f"✅ 同じ条件の前回結果がキャッシュにあります（{len(st.session_state.last_results)}件）。"
        "「キャッシュを再利用」でAPI消費ゼロで再表示できます。"
    )

col_btn1, col_btn2 = st.columns([2, 1])
with col_btn1:
    run_button = st.button("🚀 リサーチ開始", type="primary", disabled=not keyword, use_container_width=True)
with col_btn2:
    use_cache_button = st.button("♻️ キャッシュを再利用", disabled=not can_use_cache, use_container_width=True)

# ─────────────────────────────────────────
# 実行ロジック
# ─────────────────────────────────────────
if (run_button or use_cache_button) and keyword:
    if not st.session_state.tavily_api_key:
        st.error("❌ サイドバーに Tavily API キーを入力してください。")
        st.stop()

    if use_cache_button and can_use_cache:
        st.info("♻️ キャッシュから結果を再表示しました（API消費なし）。")
    else:
        with st.status("🔍 リサーチ中...", expanded=True) as status:
            st.write("🔍 Tavily で検索中（本文取得も同時実行）...")
            try:
                results, api_calls = collect_results(
                    api_key=st.session_state.tavily_api_key,
                    keyword=keyword,
                    negative_words=negative_words,
                    deep_mode=deep_mode,
                    base_num=base_num,
                    include_domains=include_domains if include_domains else None,
                    max_chars=max_chars,
                )
                st.session_state.api_call_total += api_calls
            except RuntimeError as e:
                st.error(f"検索エラー: {e}")
                st.stop()

            if not results:
                st.warning("検索結果が 0 件でした。キーワードや API キーを確認してください。")
                st.stop()

            fulltext_count = sum(1 for r in results if "フルテキスト" in r.get("text_source", ""))
            st.write(f"✅ {len(results)} 件取得完了（フルテキスト {fulltext_count} 件 / スニペット {len(results) - fulltext_count} 件）")

            st.session_state.last_results = results
            st.session_state.last_params_hash = cache_key
            st.session_state.last_keyword = keyword

            status.update(label=f"✅ 完了！ {len(results)} 件取得", state="complete")

# ─────────────────────────────────────────
# 結果表示
# ─────────────────────────────────────────
results = st.session_state.last_results
if results:
    st.divider()
    display_keyword = st.session_state.last_keyword or keyword
    st.header(f"📊 取得結果: {len(results)} 件　（キーワード: {display_keyword}）")

    tab_list, tab_export = st.tabs(["📋 一覧プレビュー", "📥 エクスポート"])

    with tab_list:
        df_display = pd.DataFrame([
            {
                "クエリ": r.get("query", ""),
                "タイトル": r.get("title", "")[:50] + "…" if len(r.get("title", "")) > 50 else r.get("title", ""),
                "取得方法": r.get("text_source", ""),
                "本文（先頭100字）": r.get("full_text", "")[:100] + "…",
                "URL": r.get("url", ""),
            }
            for r in results
        ])
        st.dataframe(df_display, use_container_width=True)
        source_counts = df_display["取得方法"].value_counts()
        st.caption("取得内訳: " + "　".join(f"**{k}** {v}件" for k, v in source_counts.items()))

    with tab_export:
        st.subheader("ファイルをダウンロード")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_kw = display_keyword.replace(" ", "_")[:20]

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📊 CSV ダウンロード（スプレッドシート用）",
                data=to_csv(results),
                file_name=f"customer_insight_{safe_kw}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.caption("UTF-8 BOM付き。Excel で文字化けしません。")
        with col_dl2:
            md_bytes = to_markdown(results, display_keyword).encode("utf-8")
            st.download_button(
                label="🤖 Markdown ダウンロード（NotebookLM用）",
                data=md_bytes,
                file_name=f"notebooklm_{safe_kw}_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.caption("NotebookLM分析プロンプト付き。そのままアップロードできます。")

# ─────────────────────────────────────────
# サイドバーのAPIカウンターを最終値で描画
# ─────────────────────────────────────────
with _api_counter_slot.container():
    used = st.session_state.api_call_total
    st.metric("使用回数", f"{used} 回")
    st.progress(min(used / 1000, 1.0))
    st.caption(f"無料枠目安残り: {max(0, 1000 - used)} 回 / 月")
    if used >= 900:
        st.warning("無料枠の上限に近づいています！")
