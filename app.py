# app.py — 完全版（スタンプをふわっとせず静的に表示）
import streamlit as st
import pandas as pd
import random
import base64
import os
import io
import csv

# ------------------------------
# 設定
# ------------------------------
PASSWORD = "demo1030"
CSV_PATH = "country_quiz.csv"
TOTAL_QUESTIONS = 5
IMAGE_FALLBACK = "no_image.png"

# フィードバック画像 / 結果画像パス
FEEDBACK_IMAGES = {
    "correct": "correct_stamp.png",
    "wrong": "wrong_stamp.png"
}
RESULT_IMAGES = {
    "perfect": "j428_7_1.png",
    "good": "j428_6_1.png",
    "average": "j428_6_2.png",
    "low": "j428_7_2.png"
}

# ジャンルラベルと色
GENRE_LABELS = {
    "capital": "首都クイズ",
    "currency": "通貨クイズ",
    "population": "人口クイズ"
}
GENRE_COLORS = {
    "capital": "#007acc",
    "currency": "#009933",
    "population": "#cc9900"
}

# ------------------------------
# CSV読み込み
# ------------------------------
def load_country_data(csv_path=CSV_PATH, expected_cols=5):
    if not os.path.exists(csv_path):
        st.error(f"CSVファイルが見つかりません: {csv_path}")
        st.stop()

    with open(csv_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    try:
        df_try = pd.read_csv(io.StringIO(text), encoding="utf-8", engine="python")
        if len(df_try.columns) == expected_cols:
            df_try.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
            df_try["人口_num"] = pd.to_numeric(
                df_try["人口"].astype(str).str.replace(",", "").str.replace("、", ""),
                errors="coerce"
            )
            return df_try
    except Exception:
        pass

    rows = []
    with io.StringIO(text) as s:
        reader = csv.reader(s, delimiter=",", quotechar='"')
        for raw_row in reader:
            if len(raw_row) == 1 and "," in raw_row[0]:
                parts = [p.strip() for p in raw_row[0].split(",")]
            else:
                parts = [p.strip() for p in raw_row]
            if len(parts) < expected_cols:
                parts += [""] * (expected_cols - len(parts))
            elif len(parts) > expected_cols:
                first = parts[: expected_cols - 1]
                last = ",".join(parts[expected_cols - 1 :])
                parts = first + [last]
            rows.append(parts)

    header = rows[0]
    has_header = any("国名" in h or "name" in h for h in header)
    data_rows = rows[1:] if has_header else rows
    df = pd.DataFrame(data_rows, columns=["国名", "人口", "画像URL", "首都", "通貨"])
    df["人口_num"] = pd.to_numeric(df["人口"].astype(str).str.replace(",", "").str.replace("、", ""), errors="coerce")
    return df

# ------------------------------
# 効果音
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
# 認証
# ------------------------------
st.set_page_config(page_title="地理クイズ", page_icon="🌍", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🌍 地理クイズへようこそ！")
    pw = st.text_input("パスワードを入力してください", type="password")
    if pw:
        if pw == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# ------------------------------
# データ読み込み
# ------------------------------
df = load_country_data(CSV_PATH)

# ------------------------------
# セッション初期化
# ------------------------------
if "question_indices" not in st.session_state:
    n = len(df)
    cnt = min(TOTAL_QUESTIONS, n)
    st.session_state.question_indices = random.sample(range(n), cnt)
    st.session_state.qpos = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.last_correct = None
    st.session_state.current_question = None

# ------------------------------
# ジャンル選択
# ------------------------------
st.title("🌍 地理クイズ！")
genre = st.radio("ジャンルを選んでね", ["capital", "currency", "population"], format_func=lambda x: GENRE_LABELS[x])

st.markdown(
    f"<div style='background-color:{GENRE_COLORS[genre]};padding:10px;border-radius:10px;'>"
    f"<h3 style='text-align:center;color:white;margin:0;padding:0;'>{GENRE_LABELS[genre]}</h3></div>",
    unsafe_allow_html=True,
)

if "last_genre" not in st.session_state:
    st.session_state.last_genre = genre
if st.session_state.last_genre != genre:
    st.session_state.question_indices = random.sample(range(len(df)), min(TOTAL_QUESTIONS, len(df)))
    st.session_state.qpos = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.current_question = None
    st.session_state.last_genre = genre

# ------------------------------
# 問題生成
# ------------------------------
def make_question_from_index(idx, genre):
    row = df.iloc[idx]
    country = row["国名"]
    if genre == "capital":
        correct = row["首都"]
        pool = df["首都"].dropna().astype(str).tolist()
        text = f"🏙️ {country} の首都は次のうちどれ？"
    elif genre == "currency":
        correct = row["通貨"]
        pool = df["通貨"].dropna().astype(str).tolist()
        text = f"💰 {country} の通貨は次のうちどれ？"
    else:
        correct = str(row["人口"])
        pool = df["人口"].dropna().astype(str).tolist()
        text = f"👪 {country} の人口は次のうちどれ？"

    choices = random.sample(pool, 3) if len(pool) > 3 else pool.copy()
    if str(correct) not in choices:
        choices.append(str(correct))
    random.shuffle(choices)
    return {"country": country, "text": text, "correct": str(correct), "choices": choices, "image": row["画像URL"]}

if st.session_state.current_question is None:
    idx = st.session_state.question_indices[st.session_state.qpos]
    st.session_state.current_question = make_question_from_index(idx, genre)

# ------------------------------
# 問題表示
# ------------------------------
q = st.session_state.current_question
st.subheader(f"第 {st.session_state.qpos + 1} 問 / 全 {len(st.session_state.question_indices)} 問")
st.write(q["text"])

img = q.get("image", "")
if isinstance(img, str) and img.strip() != "":
    if os.path.exists(img):
        st.image(img, width=300)
    else:
        st.image(img, width=300)
else:
    if os.path.exists(IMAGE_FALLBACK):
        st.image(IMAGE_FALLBACK, width=300)

selected = st.radio("選択肢：", q["choices"], key=f"choice_{st.session_state.qpos}")

# ------------------------------
# 回答処理（ふわっと削除・画像をそのまま表示）
# ------------------------------
if not st.session_state.answered:
    if st.button("回答！", key=f"answer_btn_{st.session_state.qpos}"):
        is_correct = (str(selected) == str(q["correct"]))
        st.session_state.answered = True
        st.session_state.last_correct = is_correct
        if is_correct:
            st.success("✅ 正解！")
            if os.path.exists(FEEDBACK_IMAGES["correct"]):
                st.image(FEEDBACK_IMAGES["correct"], width=200)
            play_sound("correct.wav")
            st.session_state.score += 1
        else:
            st.error(f"❌ 不正解！ 正解は「{q['correct']}」です。")
            if os.path.exists(FEEDBACK_IMAGES["wrong"]):
                st.image(FEEDBACK_IMAGES["wrong"], width=200)
            play_sound("wrong.wav")

# ------------------------------
# 次へ・結果表示
# ------------------------------
if st.session_state.answered:
    if st.session_state.qpos + 1 < len(st.session_state.question_indices):
        if st.button("➡️ 次の問題へ", key=f"next_btn_{st.session_state.qpos}"):
            st.session_state.qpos += 1
            idx = st.session_state.question_indices[st.session_state.qpos]
            st.session_state.current_question = make_question_from_index(idx, genre)
            st.session_state.answered = False
            st.session_state.last_correct = None
            st.rerun()
    else:
        st.markdown("---")
        st.subheader("🎉 クイズ終了！")
        play_sound("fanfare.wav")
        st.write(f"あなたのスコアは **{st.session_state.score} / {len(st.session_state.question_indices)}** 点です。")

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

        if st.button("🔁 もう一度遊ぶ", key="restart_full"):
            st.session_state.question_indices = random.sample(range(len(df)), min(TOTAL_QUESTIONS, len(df)))
            st.session_state.qpos = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.session_state.last_correct = None
            st.session_state.current_question = None
            st.rerun()
