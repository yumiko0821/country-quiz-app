import streamlit as st
import pandas as pd
import random
from io import StringIO
import base64

# ====== 🔒 パスワード認証 ======
PASSWORD = "demo1030"
password_input = st.text_input("パスワードを入力してください", type="password")
if password_input != PASSWORD:
    st.stop()

# ====== 🧩 CSV自動修正関数 ======
def load_and_fix_csv(csv_path):
    fixed_lines = []
    expected_cols = 5  # 国名,人口,画像URL,首都,通貨
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            cols = line.strip().split(",")
            if len(cols) != expected_cols:
                # セル内の余計なカンマを置換
                line_fixed = line.replace(",", "・", line.count(",") - (expected_cols - 1))
                cols = line_fixed.strip().split(",")
                if len(cols) > expected_cols:
                    cols = cols[:expected_cols]
                elif len(cols) < expected_cols:
                    cols += [""] * (expected_cols - len(cols))
                fixed_lines.append(",".join(cols))
                print(f"⚠️ 修正: {line_no}行目を整形しました → {cols}")
            else:
                fixed_lines.append(line.strip())
    fixed_csv = "\n".join(fixed_lines)
    df = pd.read_csv(StringIO(fixed_csv))
    return df

# ====== CSV読み込み ======
try:
    df = load_and_fix_csv("country_quiz.csv")
    df.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
except Exception as e:
    st.error(f"CSV読み込みエラー: {e}")
    st.stop()

# ====== UI設定 ======
st.title("🌍 世界の国クイズアプリ")
st.write("好きなジャンルを選んでクイズに挑戦！")

genre_labels = {
    'capital': '🏙️ 首都クイズ',
    'currency': '💰 通貨クイズ',
    'population': '👪 人口クイズ'
}
genre_colors = {
    'capital': '#ccf2ff',
    'currency': '#d9fcd9',
    'population': '#fff2cc'
}
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

# ====== ジャンル選択 ======
mode = st.selectbox("クイズジャンルを選択してください", list(genre_labels.keys()), format_func=lambda x: genre_labels[x])
st.markdown(f"<div style='background-color:{genre_colors[mode]};padding:10px;border-radius:10px;'>ジャンル：{genre_labels[mode]}</div>", unsafe_allow_html=True)

# ====== クイズロジック ======
if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.q_index = 0
    st.session_state.correct = []

def play_audio(file_path):
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/wav")

def generate_question():
    correct = df.sample(1).iloc[0]
    options = [correct]
    while len(options) < 3:
        candidate = df.sample(1).iloc[0]
        if not any(candidate["国名"] == o["国名"] for o in options):
            options.append(candidate)
    random.shuffle(options)

    if mode == 'capital':
        question = f"{correct['国名']}の首都は？"
        answers = [c["首都"] for _, c in pd.DataFrame(options).iterrows()]
        correct_answer = correct["首都"]
    elif mode == 'currency':
        question = f"{correct['国名']}の通貨は？"
        answers = [c["通貨"] for _, c in pd.DataFrame(options).iterrows()]
        correct_answer = correct["通貨"]
    else:
        question = f"{correct['国名']}の人口は？"
        answers = [str(c["人口"]) for _, c in pd.DataFrame(options).iterrows()]
        correct_answer = str(correct["人口"])

    return correct, question, answers, correct_answer

if st.session_state.q_index < 5:
    q, question, options, correct_answer = generate_question()
    country_name = q["国名"]
    image_url = q["画像URL"]

import os

# 画像の存在確認とフォールバック処理
if isinstance(image_url, str) and os.path.exists(image_url):
    st.image(image_url, width=300)
else:
    st.warning(f"⚠️ 画像が見つかりませんでした：{image_url}")
    st.image("images/no_image.png", width=300)

    st.subheader(question)
    choice = st.radio("選択肢：", options)

    if st.button("回答！"):
        if choice == correct_answer:
            st.success("🎉 正解！")
            play_audio("sounds/correct.wav")
            st.image(feedback_images['correct'], width=100)
            st.session_state.score += 1
        else:
            st.error(f"❌ 不正解！正解は「{correct_answer}」でした。")
            play_audio("sounds/wrong.wav")
            st.image(feedback_images['wrong'], width=100)
        st.session_state.q_index += 1
        st.experimental_rerun()
else:
    st.balloons()
    play_audio("sounds/fanfare.wav")
    st.success(f"あなたのスコアは {st.session_state.score} / 5 です！")

    if st.session_state.score >= 5:
        comment = "🌟 パーフェクト！世界マスター！"
        image_path = result_images['perfect']
    elif st.session_state.score >= 4:
        comment = "👍 よくできました！"
        image_path = result_images['good']
    elif st.session_state.score >= 2:
        comment = "🙂 まずまず！"
        image_path = result_images['average']
    else:
        comment = "💡 まだまだこれから！"
        image_path = result_images['low']

    st.image(image_path, width=300)
    st.write(comment)

    if st.button("もう一度遊ぶ"):
        st.session_state.score = 0
        st.session_state.q_index = 0
        st.session_state.correct = []
        st.experimental_rerun()