import streamlit as st
import pandas as pd
import random
import base64
import os

# ===============================
# 🔒 パスワード認証
# ===============================
PASSWORD = "demo1030"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("パスワードを入力してください", type="password")
    if pwd == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_rerun()
    elif pwd:
        st.error("パスワードが違います")
    st.stop()

# ===============================
# 🎵 効果音再生
# ===============================
def play_sound(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
            <audio autoplay>
            <source src="data:audio/wav;base64,{b64}" type="audio/wav">
            </audio>
            """
            st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"音声の読み込みに失敗しました: {e}")

# ===============================
# 📊 データ読み込み
# ===============================
@st.cache_data
def load_data():
    return pd.read_csv("country_quiz.csv")

df = load_data()

# ===============================
# 🖼️ 画像パス定義
# ===============================
feedback_images = {
    'correct': 'images/correct_stamp.png',
    'wrong': 'images/wrong_stamp.png'
}

result_images = {
    'perfect': 'images/j428_7_1.png',
    'good': 'images/j428_6_1.png',
    'average': 'images/j428_6_2.png',
    'low': 'images/j428_7_2.png'
}

# ===============================
# 🎨 ジャンル設定
# ===============================
genre_labels = {
    'capital': '首都クイズ',
    'currency': '通貨クイズ',
    'population': '人口クイズ'
}

genre_colors = {
    'capital': '#ccf2ff',   # 青
    'currency': '#d9fcd9',  # 緑
    'population': '#fff2cc' # 黄
}

# ===============================
# 🎮 初期設定
# ===============================
MAX_QUESTIONS = 5
if "mode" not in st.session_state:
    st.session_state.mode = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "question_num" not in st.session_state:
    st.session_state.question_num = 1
if "question_row" not in st.session_state:
    st.session_state.question_row = None
if "correct_countries" not in st.session_state:
    st.session_state.correct_countries = []

# ===============================
# 🎨 背景色の変更（CSS）
# ===============================
def set_background(color):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {color};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ===============================
# 🎯 モード選択
# ===============================
if st.session_state.mode is None:
    st.title("🌍 世界の国クイズ")
    st.subheader("ジャンルを選んでください")

    col1, col2, col3 = st.columns(3)
    if col1.button("首都クイズ"):
        st.session_state.mode = "capital"
        st.experimental_rerun()
    if col2.button("通貨クイズ"):
        st.session_state.mode = "currency"
        st.experimental_rerun()
    if col3.button("人口クイズ"):
        st.session_state.mode = "population"
        st.experimental_rerun()
    st.stop()

# 背景色を設定
set_background(genre_colors[st.session_state.mode])

# ===============================
# 🎯 問題生成
# ===============================
if st.session_state.question_row is None:
    st.session_state.question_row = df.sample(1).iloc[0]

q = st.session_state.question_row
country_name = q["国名"]
flag_url = q.get("画像URL", None)

if st.session_state.mode == "capital":
    question_text = f"💡 問題：{country_name} の首都は？"
    correct_answer = q["首都"]
    choices = random.sample(df["首都"].dropna().tolist(), 3)
elif st.session_state.mode == "currency":
    question_text = f"💡 問題：{country_name} の通貨は？"
    correct_answer = q["通貨"]
    choices = random.sample(df["通貨"].dropna().tolist(), 3)
else:
    question_text = f"💡 問題：{country_name} の人口（千万単位）は？"
    correct_answer = q["人口（千万単位）"]
    choices = random.sample(df["人口（千万単位）"].dropna().tolist(), 3)

if correct_answer not in choices:
    choices[random.randint(0, 2)] = correct_answer
random.shuffle(choices)

# ===============================
# 🏁 結果画面
# ===============================
if st.session_state.question_num > MAX_QUESTIONS:
    play_sound("fanfare.wav")
    st.header("🎯 結果発表！")

    score = st.session_state.score
    st.subheader(f"あなたのスコアは {score} / {MAX_QUESTIONS} 点です！")

    if score == MAX_QUESTIONS:
        comment = "🌟 パーフェクト！世界マスター！"
        image_path = result_images['perfect']
    elif score >= 4:
        comment = "👍 よくできました！あと少しで満点！"
        image_path = result_images['good']
    elif score >= 2:
        comment = "🙂 まずまず！次はもっと高得点を目指そう！"
        image_path = result_images['average']
    else:
        comment = "💡 まだまだこれから！世界をもっと知ろう！"
        image_path = result_images['low']

    st.write(comment)
    if os.path.exists(image_path):
        st.image(image_path, width=350)

    # 正解した国の一覧（国旗付き）
    st.markdown("### ✅ 正解した国：")
    if st.session_state.correct_countries:
        for c in st.session_state.correct_countries:
            flag = df[df["国名"] == c]["画像URL"].values
            if len(flag) > 0 and isinstance(flag[0], str):
                st.image(flag[0], width=80)
            st.write(c)
    else:
        st.write("（正解なし）")

    if st.button("🔁 もう一度遊ぶ"):
        for key in ["mode", "score", "question_num", "question_row", "correct_countries"]:
            st.session_state[key] = None if key == "mode" else 0 if key == "score" else None
        st.experimental_rerun()

    st.stop()

# ===============================
# 🎯 問題表示
# ===============================
st.subheader(f"ジャンル：{genre_labels[st.session_state.mode]}")
st.subheader(f"第 {st.session_state.question_num} 問目 / {MAX_QUESTIONS} 問")

st.write(question_text)
if flag_url and isinstance(flag_url, str):
    st.image(flag_url, width=180)

choice = st.radio("選択肢を選んでください", choices)

# ===============================
# ✅ 回答処理
# ===============================
if st.button("答える！"):
    if choice == correct_answer:
        st.success("🎉 正解！すごい！")
        play_sound("correct.wav")
        if os.path.exists(feedback_images["correct"]):
            st.image(feedback_images["correct"], width=150)
        st.session_state.score += 1
        st.session_state.correct_countries.append(country_name)
    else:
        st.error(f"😢 残念！正解は {correct_answer} でした。")
        play_sound("wrong.wav")
        if os.path.exists(feedback_images["wrong"]):
            st.image(feedback_images["wrong"], width=150)

    st.session_state.question_row = df.sample(1).iloc[0]
    st.session_state.question_num += 1
    st.experimental_rerun()

st.write("---")
st.write(f"現在のスコア：{st.session_state.score} 点")
