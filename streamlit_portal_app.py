"""
そ賭ポータル by あかれく  (Streamlit)
====================================
- Run: `streamlit run streamlit_portal_app.py`
- Admin URL: `?admin`
- Data:
    - 抽選履歴      → `./data/history.csv`
    - 更新履歴      → `./data/updates.csv`
    - 管理者コメント → `./data/comment.txt`

変更点 (2025-05-26 8th)
----------------------
### 🎨 SNS ボタンをブランドカラー化
| サービス | 色コード |
|----------|----------|
| **X (旧 Twitter)** | `#1DA1F2` |
| **YouTube** | `#FF0000` |
| **Twitch** | `#9146FF` |
| **ツイキャス** | `#00A2E8` |

`st.link_button` では色を変えられないため、CSS 付き `st.markdown` で疑似ボタンを実装。
"""

import os
import datetime as dt
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────
# ページ設定
# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="そ賭ポータル by あかれく", page_icon="🎲", layout="wide")

# ────────────────────────────────────────────────────────────────
# 定数 & パス
# ────────────────────────────────────────────────────────────────
DATA_DIR = "data"
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
UPDATES_CSV = os.path.join(DATA_DIR, "updates.csv")
COMMENT_TXT = os.path.join(DATA_DIR, "comment.txt")
CATEGORIES = ["勝ち", "負け", "ゴール負け"]

os.makedirs(DATA_DIR, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# I/O ヘルパ
# ────────────────────────────────────────────────────────────────

def _ensure_csv(path: str, cols: list[str]):
    if not os.path.exists(path):
        pd.DataFrame(columns=cols).to_csv(path, index=False)


def load_history() -> pd.DataFrame:
    _ensure_csv(HISTORY_CSV, ["開催日時", "結果"])
    return pd.read_csv(HISTORY_CSV, parse_dates=["開催日時"])


def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_CSV, index=False)


def load_updates() -> pd.DataFrame:
    _ensure_csv(UPDATES_CSV, ["日付", "内容"])
    return pd.read_csv(UPDATES_CSV, parse_dates=["日付"])


def save_updates(df: pd.DataFrame):
    df.to_csv(UPDATES_CSV, index=False)


def load_comment() -> str:
    return open(COMMENT_TXT, encoding="utf-8").read() if os.path.exists(COMMENT_TXT) else ""


def save_comment(text: str):
    with open(COMMENT_TXT, "w", encoding="utf-8") as f:
        f.write(text)

# ────────────────────────────────────────────────────────────────
# 統計関数
# ────────────────────────────────────────────────────────────────

def calc_probabilities(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {c: 1 / len(CATEGORIES) for c in CATEGORIES}
    counts = df["結果"].value_counts().reindex(CATEGORIES, fill_value=0)
    return (counts / counts.sum()).to_dict()


def expected_value(bet_amount: int, pool: Dict[str, int], probs: Dict[str, float]):
    ev, payout = {}, {}
    base = sum(pool.values())
    for c in CATEGORIES:
        total = base + bet_amount
        win_pool = pool[c] + bet_amount
        ratio = total / win_pool if win_pool else 0
        payout[c] = ratio * bet_amount if win_pool else 0
        ev[c] = probs[c] * payout[c] - bet_amount
    return ev, payout

# ────────────────────────────────────────────────────────────────
# UI ヘルパ: カラーボタンリンク
# ────────────────────────────────────────────────────────────────

def colored_link(label: str, url: str, bg: str, fg: str = "#FFFFFF"):
    """ブランドカラーで塗ったボタン風リンク"""
    st.markdown(
        f"""
        <a href="{url}" target="_blank" style="text-decoration:none;">
            <div style="background:{bg}; color:{fg}; padding:8px 12px; border-radius:6px; text-align:center; font-weight:bold; margin-bottom:6px;">{label}</div>
        </a>
        """,
        unsafe_allow_html=True,
    )

BRAND_COLORS = {
    "X": "#1DA1F2",
    "YouTube": "#FF0000",
    "Twitch": "#9146FF",
    "ツイキャス": "#00A2E8",
}

# ────────────────────────────────────────────────────────────────
# データロード
# ────────────────────────────────────────────────────────────────
IS_ADMIN = "admin" in st.query_params
history_df = load_history()
updates_df = load_updates()
admin_comment = load_comment()
# sort history ascending for further processing
history_df_sorted = history_df.sort_values("開催日時")
history_df_sorted["レコード"] = history_df_sorted.index + 1

# ────────────────────────────────────────────────────────────────
# 左サイドバー (目次)
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📑 目次")
    toc = {
        "▶ トップ": "#そ賭ポータル-by-あかれく",
        "▶ 統計的予想": "#🔮-次回の統計的予想",
        "▶ リターン予測": "#💰-リターン予測",
        "▶ 履歴": "#📜-過去の抽選履歴",
        "▶ 更新履歴": "#🆕-更新履歴",
    }
    for label, anchor in toc.items():
        st.markdown(f"- [{label}]({anchor})")

# ────────────────────────────────────────────────────────────────
# 管理者ページ (省略表示)
# ────────────────────────────────────────────────────────────────
if IS_ADMIN:
    st.title("管理者ページ 🛠️")
    st.caption("抽選履歴・更新履歴・管理者コメントを管理します")

    tabs = st.tabs(["抽選履歴", "更新履歴", "管理者コメント"])

    # ----- 抽選履歴タブ -----
    with tabs[0]:
        st.subheader("🎫 抽選履歴の追加")
        c1, c2, c3 = st.columns([1, 1, 1])
        date_val = c1.date_input("開催日", dt.date.today())
        time_val = c2.time_input("開催時間", dt.time(19, 0))
        result_val = c3.selectbox("結果", CATEGORIES)
        if st.button("追加", key="add_hist"):
            new = {"開催日時": dt.datetime.combine(date_val, time_val), "結果": result_val}
            history_df = pd.concat([history_df, pd.DataFrame([new])], ignore_index=True)
            save_history(history_df)
            st.success("追加しました！")
            st.rerun()

        st.divider()
        st.subheader("📝 履歴一覧 (直接編集可)")
        edited_hist = st.data_editor(
            history_df.sort_values("開催日時", ascending=False),
            num_rows="dynamic",
            use_container_width=True,
        )
        if st.button("保存", key="save_hist"):
            save_history(edited_hist)
            st.success("保存しました")
            st.rerun()

    # ----- 更新履歴タブ -----
    with tabs[1]:
        st.subheader("🆕 更新履歴の追加")
        u1, u2 = st.columns([1, 3])
        upd_date = u1.date_input("日付", dt.date.today(), key="upd_date")
        upd_text = u2.text_area("内容", key="upd_text")
        if st.button("追加", key="add_update"):
            new_upd = {"日付": upd_date, "内容": upd_text}
            updates_df = pd.concat([updates_df, pd.DataFrame([new_upd])], ignore_index=True)
            save_updates(updates_df)
            st.success("追加しました！")
            st.rerun()

        st.divider()
        st.subheader("📋 更新履歴一覧 (直接編集可)")
        edited_upd = st.data_editor(
            updates_df.sort_values("日付", ascending=False),
            num_rows="dynamic",
            use_container_width=True,
        )
        if st.button("保存", key="save_update"):
            save_updates(edited_upd)
            st.success("保存しました")
            st.rerun()

    # ----- コメントタブ -----
    with tabs[2]:
        st.subheader("💬 管理者コメント")
        new_comment = st.text_area("コメント", value=admin_comment, height=120)
        if st.button("コメントを保存"):
            save_comment(new_comment)
            st.success("保存しました")
            st.rerun()

    st.info("左上の ❌ またはブラウザバックでメインページに戻れます。")

# ────────────────────────────────────────────────────────────────
# メインページ
# ────────────────────────────────────────────────────────────────
else:
    main_col, right_col = st.columns([5, 1], gap="large")

    # -------------------- 右サイドバー (SNS) --------------------
    with right_col:
        st.header("“そ” SNS")
        so_links = {
            "X": "https://x.com/solea_ch",
            "YouTube": "https://www.youtube.com/channel/UCagxuf72ZEruUZzZ4seKDJQ",
            "Twitch": "https://twitch.tv/solea_ch",
            "ツイキャス": "https://twitcasting.tv/solea_ch",
        }
        for name, url in so_links.items():
            colored_link(name, url, BRAND_COLORS[name])

        st.divider()
        st.header("あかれく SNS")
        ak_links = {
            "X": "https://x.com/asterizerrrrrr",
            "YouTube": "https://www.youtube.com/channel/UCCPEBsxFiZjycJKjbyOW1aQ",
            "Twitch": "https://www.twitch.tv/akarec_ch",
            "ツイキャス": "https://twitcasting.tv/asterizerrrrrr",
        }
        for name, url in ak_links.items():
            colored_link(name, url, BRAND_COLORS[name])

    # -------------------- メインカラム --------------------
    with main_col:
        st.markdown("## そ賭ポータル by あかれく 🎲")
        st.info("ここはジョークサイトです。\n“そ”さん本人の黙認は得ていますが、黙認を得ているだけです。\nつまり、黙認を得ているだけです。")
        # 配信リンクを “そ” のツイキャスへ
        colored_link("📺 配信はこちらから！", "https://twitch.tv/solea_ch", BRAND_COLORS["Twitch"])

        # 日付 & 累計
        c1, c2 = st.columns(2)
        c1.metric("本日の日付", dt.date.today().isoformat())
        c2.metric("累計『賭』回数", len(history_df))

        # 統計的予測
        st.divider()
        st.subheader("🔮 次回の予想")
        probs = calc_probabilities(history_df)
        best_cat = max(probs, key=probs.get)
        st.markdown(f"最有力カテゴリー **{best_cat}**（{probs[best_cat]:.1%}）  ")
        st.caption("※ 過去の結果出現頻度に基づく単純予測です。")
        st.caption("※ 今後、独自AIを搭載するよ！(どうして？？？)")
        pie_df = pd.DataFrame({"カテゴリ": list(probs.keys()), "確率": list(probs.values())})
        st.altair_chart(
            alt.Chart(pie_df)
            .mark_arc(innerRadius=40)
            .encode(theta="確率", color="カテゴリ", tooltip=["カテゴリ", "確率"])
            .properties(width=260, height=260),
            use_container_width=True,
        )

        # リターン予測
        
        st.divider()
        st.subheader("💰 リターン予測")
        pool_cols = st.columns(3)
        pool = {c: pool_cols[i].number_input(c, 0, step=1) for i, c in enumerate(CATEGORIES)}
        sel_cat = st.radio("どのカテゴリに賭けますか？", CATEGORIES, horizontal=True)
        bet_amount = st.number_input("Bet 金額", 0, step=1)
        ev, payout = expected_value(bet_amount, pool, probs)
        st.json(ev, expanded=False)
        st.json(payout, expanded=False)

        # 履歴テーブル
        st.divider()
        st.subheader("📜 過去の抽選履歴")
        if "show_rows" not in st.session_state:
            st.session_state.show_rows = 5
        max_rows = len(history_df_sorted)
        show_n = min(st.session_state.show_rows, max_rows)
        show_df = history_df_sorted.head(show_n)
        if show_df.empty:
            st.info("履歴がまだありません")
        else:
            show_tbl = show_df.assign(
                開催年=show_df["開催日時"].dt.year,
                開催月=show_df["開催日時"].dt.month,
                開催日=show_df["開催日時"].dt.day,
                開催時間=show_df["開催日時"].dt.strftime("%H:%M"),
            )
            st.table(show_tbl[["レコード", "開催年", "開催月", "開催日", "開催時間", "結果"]])
        # --- ボタン後のリロード ---
        if show_n < max_rows and st.button("もっとみる (+20)"):
            st.session_state.show_rows = min(st.session_state.show_rows + 20, max_rows)
            st.rerun()

        # --- 推移グラフ（step-after） ---

        # 推移グラフ
        st.divider()
        st.subheader("📈 カテゴリ推移")
        if history_df_sorted.empty:
            st.info("データがありません")
        else:
            # レコード順に並べ替え確定
            history_df_sorted = history_df_sorted.sort_values("レコード")
            onehot = pd.get_dummies(history_df_sorted["結果"]).reindex(columns=CATEGORIES, fill_value=0)
            cum_counts = onehot.cumsum()
            cum_counts["レコード"] = history_df_sorted["レコード"].values
            cum_counts = cum_counts.sort_values("レコード")
            cum_long = cum_counts.melt(id_vars="レコード", var_name="カテゴリ", value_name="累計回数")

            line_counts = (
                alt.Chart(cum_long)
                .mark_line(interpolate="step-after")
                .encode(x="レコード:Q", y="累計回数:Q", color="カテゴリ:N")
                .properties(title="累計回数の推移", width=600)
            )
            st.altair_chart(line_counts, use_container_width=True)

            # 累計割合
            cum_ratio = cum_counts[CATEGORIES].div(cum_counts[CATEGORIES].sum(axis=1).replace(0, 1), axis=0)
            cum_ratio["レコード"] = cum_counts["レコード"]
            ratio_long = cum_ratio.melt(id_vars="レコード", var_name="カテゴリ", value_name="割合")
            line_ratio = (
                alt.Chart(ratio_long)
                .mark_line(interpolate="step-after")
                .encode(
                    x="レコード:Q",
                    y=alt.Y("割合:Q", axis=alt.Axis(format=".0%")),
                    color="カテゴリ:N",
                )
                .properties(title="割合の推移", width=600)
            )
            st.altair_chart(line_ratio, use_container_width=True)


        # 更新履歴
        st.divider()
        st.subheader("🆕 更新履歴")
        if updates_df.empty:
            st.info("まだ更新履歴がありません")
        else:
            for _, r in updates_df.sort_values("日付", ascending=False).head(10).iterrows():
                st.markdown(f"- {r['日付'].strftime('%Y-%m-%d')}: {r['内容']}")


        # ----- admin comment -----
        st.divider()
        st.subheader("💬 管理者の一言")
        st.markdown(admin_comment or "(コメントはまだありません)")
