# app.py — 完全版（すべての修正を統合）
import streamlit as st
import pandas as pd
import random
import base64
import os
import io
import csv

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def path(*parts):
    return os.path.join(BASE_DIR, *parts)


# ------------------------------
# 設定
# ------------------------------
PASSWORD = "demo1030"
CSV_PATH = "country_quiz.csv"
TOTAL_QUESTIONS = 5  # 出題数（必要なら変更）
IMAGE_FALLBACK = "no_image.png"


# フィードバック画像 / 結果画像パス
FEEDBACK_IMAGES = {
    "correct": st.image(path("images/correct_stamp.png")),
    "wrong": st.image(path("images/wrong_stamp.png"))
}
RESULT_IMAGES = {
    "perfect": "j428_7_1.png",
    "good": "j428_6_1.png",
    "average": "j428_6_2.png",
    "low": "j428_7_2.png"
}

# ジャンル表示ラベル & 色（濃めにして白文字を映えさせる）
GENRE_LABELS = {
    "capital": "首都クイズ",
    "currency": "通貨クイズ",
    "population": "人口クイズ"
}
GENRE_COLORS = {
    "capital": "#007acc",    # 濃い青
    "currency": "#009933",   # 濃い緑
    "population": "#cc9900"  # 濃い金
}

# ------------------------------
# ユーティリティ：頑強なCSV読み込み
# ------------------------------
def load_country_data(csv_path=CSV_PATH, expected_cols=5):
    """
    いろんな壊れ方に対応して DataFrame を返す。
    - "a,b,c" のように行全体がダブルクォートで囲まれている
    - 通常のカンマ区切り
    - 一部行で列数が多い／少ない -> 自動で補正（多すぎる場合は余りを最後の列に結合）
    """
    if not os.path.exists(csv_path):
        st.error(f"CSVファイルが見つかりません: {csv_path}")
        st.stop()

    # 生テキスト読み込み
    with open(csv_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # まず通常読み込みを試みる（python engine で柔軟に）
    try:
        df_try = pd.read_csv(io.StringIO(text), encoding="utf-8", engine="python")
        if len(df_try.columns) == expected_cols:
            df_try.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
            # 追加：人口数値カラム
            df_try["人口_num"] = pd.to_numeric(df_try["人口"].astype(str).str.replace(",", "").str.replace("、", ""), errors="coerce")
            return df_try
    except Exception:
        pass

    # csv.reader を使って堅牢にパース（quotechar を尊重）
    rows = []
    with io.StringIO(text) as s:
        reader = csv.reader(s, delimiter=",", quotechar='"')
        for raw_row in reader:
            # raw_row が ['国名,人口,画像URL,...'] のような1要素になっている場合は分割
            if len(raw_row) == 1 and "," in raw_row[0]:
                parts = [p.strip() for p in raw_row[0].split(",")]
            else:
                parts = [p.strip() for p in raw_row]

            # 調整：列数が足りない場合は空文字で埋める、多すぎる場合は余分を最後に結合
            if len(parts) < expected_cols:
                parts += [""] * (expected_cols - len(parts))
            elif len(parts) > expected_cols:
                first = parts[: expected_cols - 1]
                last = ",".join(parts[expected_cols - 1 :])
                parts = first + [last]

            rows.append(parts)

    if len(rows) == 0:
        st.error("CSVが空です。")
        st.stop()

    # ヘッダー判定：1行目に '国名' などが含まれていればそれをヘッダーとして使用
    header = rows[0]
    header_lower = [h.lower() for h in header]
    has_header = any("国名" in h or "name" in h for h in header_lower)

    if has_header:
        data_rows = rows[1:]
    else:
        # もしヘッダーがないなら、 assume first row is header-like? but we will treat as data
        data_rows = rows

    # DataFrame 作成
    df = pd.DataFrame(data_rows, columns=["国名", "人口", "画像URL", "首都", "通貨"])

    # 人口数値列を追加（数字化）
    df["人口_num"] = pd.to_numeric(df["人口"].astype(str).str.replace(",", "").str.replace("、", ""), errors="coerce")

    return df

# ------------------------------
# 音声再生（base64埋め込み）
# ------------------------------
def play_sound(sound_path):
    if os.path.exists(sound_path):
        with open(sound_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            st.markdown(
                f"<audio autoplay><source src='data:audio/wav;base64,{b64}' type='audio/wav'></audio>",
                unsafe_allow_html=True,
            )

# ------------------------------
# セットアップ / 認証
# ------------------------------
st.set_page_config(page_title="地理クイズ", page_icon="🌍", layout="centered")

# パスワード認証（セッション）
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🌍 地理クイズへようこそ！")
    pw = st.text_input("パスワードを入力してください", type="password", key="pw_input")
    if pw:
        if pw == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# ------------------------------
# データ読み込み（頑強）
# ------------------------------
df = load_country_data(CSV_PATH)

# ------------------------------
# セッション初期化（出題リストなど）
# ------------------------------
if "question_indices" not in st.session_state:
    # ランダムに重複なしで出題インデックスを作る
    n = len(df)
    cnt = min(TOTAL_QUESTIONS, n)
    st.session_state.question_indices = random.sample(range(n), cnt)
    st.session_state.qpos = 0  # 現在の何問目か（0始まり）
    st.session_state.score = 0
    st.session_state.answered = False  # 回答済みフラグ
    st.session_state.last_correct = None
    st.session_state.current_question = None  # dictで保持

# ------------------------------
# UI: ジャンル選択（ジャンル変更でリセット）
# ------------------------------
st.title("🌍 地理クイズ！")
genre = st.radio("ジャンルを選んでね", ["capital", "currency", "population"], format_func=lambda x: GENRE_LABELS[x], key="genre_radio")

# ジャンル色（見やすく）
st.markdown(
    f"<div style='background-color:{GENRE_COLORS[genre]};padding:10px;border-radius:10px;'>"
    f"<h3 style='text-align:center;color:white;margin:0;padding:0;'>{GENRE_LABELS[genre]}</h3></div>",
    unsafe_allow_html=True,
)

# ジャンルが変わったらクイズをリセット（別のジャンルで遊び直す想定）
if "last_genre" not in st.session_state:
    st.session_state.last_genre = genre
if st.session_state.last_genre != genre:
    st.session_state.question_indices = random.sample(range(len(df)), min(TOTAL_QUESTIONS, len(df)))
    st.session_state.qpos = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.last_correct = None
    st.session_state.current_question = None
    st.session_state.last_genre = genre

# ------------------------------
# 問題の生成 / 取得（セッション保持）
# ------------------------------
def make_question_from_index(idx, genre):
    row = df.iloc[idx]
    country = row["国名"]
    if genre == "capital":
        correct = row["首都"]
        pool = df["首都"].dropna().astype(str).tolist()
        question_text = f"🏙️ {country} の首都は次のうちどれ？"
    elif genre == "currency":
        correct = row["通貨"]
        pool = df["通貨"].dropna().astype(str).tolist()
        question_text = f"💰 {country} の通貨は次のうちどれ？"
    else:  # population
        correct = str(row["人口"])
        pool = df["人口"].dropna().astype(str).tolist()
        question_text = f"👪 {country} の人口は次のうちどれ？"

    # 選択肢作成（pool からランダムに3個、重複排除）
    choices = []
    # pool が小さい場合のガード
    if len(pool) <= 3:
        choices = pool.copy()
    else:
        # sample 3
        choices = random.sample(pool, 3)
    if str(correct) not in choices:
        choices.append(str(correct))
    random.shuffle(choices)

    return {
        "country": country,
        "text": question_text,
        "correct": str(correct),
        "choices": choices,
        "image": row["画像URL"]
    }

# current question が未設定なら作る
if st.session_state.current_question is None and st.session_state.qpos < len(st.session_state.question_indices):
    idx = st.session_state.question_indices[st.session_state.qpos]
    st.session_state.current_question = make_question_from_index(idx, genre)
    st.session_state.answered = False
    st.session_state.last_correct = None

# ------------------------------
# 問題表示
# ------------------------------
q = st.session_state.current_question

if q is None:
    st.error("問題を生成できませんでした。CSVの行数や設定を確認してください。")
    st.stop()

st.subheader(f"第 {st.session_state.qpos + 1} 問 / 全 {len(st.session_state.question_indices)} 問")
st.write(q["text"])

# 画像表示（ローカルパス or URL）。存在確認して安全に表示
img = q.get("image", "")
if isinstance(img, str) and img.strip() != "":
    if os.path.exists(img):
        st.image(img, width=300)
    else:
        # URL の場合は直接渡してみて、ダメならフォールバック
        try:
            st.image(img, width=300)
        except Exception:
            if os.path.exists(IMAGE_FALLBACK):
                st.image(IMAGE_FALLBACK, width=300)
else:
    if os.path.exists(IMAGE_FALLBACK):
        st.image(IMAGE_FALLBACK, width=300)

# 選択肢ラジオ（キーをユニークに）
choice_key = f"choice_{st.session_state.qpos}"
selected = st.radio("選択肢：", q["choices"], key=choice_key)

# ------------------------------
# 回答処理（回答後は結果を表示し、次へはボタンで進む）
# ------------------------------
answer_btn_key = f"answer_btn_{st.session_state.qpos}"
next_btn_key = f"next_btn_{st.session_state.qpos}"

if not st.session_state.answered:
    if st.button("回答！", key=answer_btn_key):
        # 回答処理
        is_correct = (str(selected) == str(q["correct"]))
        st.session_state.answered = True
        st.session_state.last_correct = is_correct
        if is_correct:
            st.success("✅ 正解！")
            if os.path.exists(FEEDBACK_IMAGES["correct"]):
                # CSSアニメでふわっと出す（HTML挿入）
                st.markdown(
                    """
                    <style>
                    @keyframes fadeInOut {
                        0% {opacity: 0; transform: scale(0.6);}
                        30% {opacity: 1; transform: scale(1.05);}
                        70% {opacity: 1; transform: scale(1.0);}
                        100% {opacity: 0; transform: scale(0.6);}
                    }
                    .stamp {animation: fadeInOut 1.2s ease-in-out; text-align:center; margin-top:10px;}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"<div class='stamp'><img src='{FEEDBACK_IMAGES['correct']}' width='200'></div>", unsafe_allow_html=True)
            play_sound("correct.wav")
            st.session_state.score += 1
        else:
            st.error(f"❌ 不正解！ 正解は「{q['correct']}」です。")
            if os.path.exists(FEEDBACK_IMAGES["wrong"]):
                st.markdown(
                    """
                    <style>
                    @keyframes fadeInOut {
                        0% {opacity: 0; transform: scale(0.6);}
                        30% {opacity: 1; transform: scale(1.05);}
                        70% {opacity: 1; transform: scale(1.0);}
                        100% {opacity: 0; transform: scale(0.6);}
                    }
                    .stamp {animation: fadeInOut 1.2s ease-in-out; text-align:center; margin-top:10px;}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"<div class='stamp'><img src='{FEEDBACK_IMAGES['wrong']}' width='200'></div>", unsafe_allow_html=True)
            play_sound("wrong.wav")

# 回答済みなら「次へ」か終了処理のUIを出す
if st.session_state.answered:
    if st.session_state.qpos + 1 < len(st.session_state.question_indices):
        if st.button("➡️ 次の問題へ", key=next_btn_key):
            # 次の問題へ：qpos を進めて current_question を差し替え
            st.session_state.qpos += 1
            idx = st.session_state.question_indices[st.session_state.qpos]
            st.session_state.current_question = make_question_from_index(idx, genre)
            st.session_state.answered = False
            st.session_state.last_correct = None
            # ラジオ選択の key が変わるので自動で選択肢は新しくなる
            st.rerun()
    else:
        # 最終問題を回答済み → 結果表示
        st.markdown("---")
        st.subheader("🎉 クイズ終了！")
        play_sound("fanfare.wav")
        st.write(f"あなたのスコアは **{st.session_state.score} / {len(st.session_state.question_indices)}** 点です。")

        # 結果画像とコメント
        score = st.session_state.score
        if score == len(st.session_state.question_indices):
            comment = "🌟 パーフェクト！世界マスター！"
            result_img = RESULT_IMAGES["perfect"]
        elif score >= int(len(st.session_state.question_indices) * 0.8):
            comment = "👍 よくできました！"
            result_img = RESULT_IMAGES["good"]
        elif score >= int(len(st.session_state.question_indices) * 0.4):
            comment = "🙂 まずまず！"
            result_img = RESULT_IMAGES["average"]
        else:
            comment = "💡 まだまだこれから！"
            result_img = RESULT_IMAGES["low"]

        if os.path.exists(result_img):
            st.image(result_img, width=380)
        st.write(comment)

        # もう一度遊ぶボタン（キー指定）
        if st.button("🔁 もう一度遊ぶ", key="restart_full"):
            # セッション状態リセット（ジャンルは保持）
            st.session_state.question_indices = random.sample(range(len(df)), min(TOTAL_QUESTIONS, len(df)))
            st.session_state.qpos = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.session_state.last_correct = None
            st.session_state.current_question = None
            st.rerun()