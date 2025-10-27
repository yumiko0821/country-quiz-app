import streamlit as st
import pandas as pd
import random
import base64
import os
import time

# ==============================
# 📥 CSV読み込み（自動修正版）
# ==============================
def load_country_data():
    try:
        df = pd.read_csv("country_quiz.csv", encoding="utf-8")

        # 1列しかなくカンマ区切りの場合の修正
        if len(df.columns) == 1 and "," in df.columns[0]:
            from io import StringIO
            csv_text = "\n".join(df.iloc[:, 0].astype(str))
            df = pd.read_csv(StringIO(csv_text), encoding="utf-8")

        # 列名が正しくない場合に修正
        if len(df.columns) == 5:
            df.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
        else:
            st.error("❌ CSVの列数が5ではありません。")
            st.stop()

        st.caption(f"データ行数: {len(df)} / 列: {list(df.columns)}")
        return df

    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        st.stop()


# ==============================
# 🔐 パスワード保護
# ==============================
PASSWORD = "demo1030"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🌍 地理クイズへようこそ！")
    pw = st.text_input("パスワードを入力してください", type="password")
    if pw == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif pw:
        st.error("パスワードが違います。")
    st.stop()


# ==============================
# 🎵 音声再生関数
# ==============================
def play_sound(sound_file):
    if os.path.exists(sound_file):
        with open(sound_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
                <audio autoplay>
                <source src="data:audio/wav;base64,{b64}" type="audio/wav">
                </audio>
            """
            st.markdown(md, unsafe_allow_html=True)


# ==============================
# 🎨 ジャンル別設定
# ==============================
genre_labels = {
    "capital": "首都クイズ",
    "currency": "通貨クイズ",
    "population": "人口クイズ"
}

genre_colors = {
    "capital": "#b3e6ff",     # 少し濃くして白文字でも見やすく
    "currency": "#b3ffb3",
    "population": "#ffe699"
}


# ==============================
# 🎯 クイズクラス
# ==============================
class QuizGame:
    def __init__(self, df):
        self.df = df
        self.score = 0
        self.total_questions = 5
        self.current_question = 0

        self.feedback_images = {
            "correct": "images/correct_stamp.png",
            "wrong": "images/wrong_stamp.png"
        }

        self.result_images = {
            "perfect": "images/j428_7_1.png",
            "good": "images/j428_6_1.png",
            "average": "images/j428_6_2.png",
            "low": "images/j428_7_2.png"
        }

    def generate_question(self, genre):
        q = self.df.sample(1).iloc[0]
        country = q["国名"]
        correct = ""
        choices = []

        if genre == "capital":
            correct = q["首都"]
            choices = list(self.df["首都"].dropna().sample(3))
            question_text = f"🏙️ {country}の首都は次のうちどれ？"
        elif genre == "currency":
            correct = q["通貨"]
            choices = list(self.df["通貨"].dropna().sample(3))
            question_text = f"💰 {country}の通貨は次のうちどれ？"
        elif genre == "population":
            correct = str(q["人口"])
            choices = list(self.df["人口"].dropna().astype(str).sample(3))
            question_text = f"👪 {country}の人口は次のうちどれ？"

        if correct not in choices:
            choices.append(correct)
        random.shuffle(choices)

        return {
            "country": country,
            "question_text": question_text,
            "correct": correct,
            "choices": choices,
            "image": q["画像URL"]
        }


# ==============================
# 🚀 Streamlit アプリ本体
# ==============================
st.set_page_config(page_title="地理クイズ", page_icon="🌍", layout="centered")

df = load_country_data()

if "game" not in st.session_state:
    st.session_state.game = QuizGame(df)
if "genre" not in st.session_state:
    st.session_state.genre = "capital"

game = st.session_state.game

st.title("🌍 地理クイズ！")
genre = st.radio("ジャンルを選んでね", ["capital", "currency", "population"],
                 format_func=lambda x: genre_labels[x])

# ジャンルタイトル（見やすい白文字）
st.markdown(
    f"<div style='background-color:{genre_colors[genre]};padding:10px;border-radius:10px;'>"
    f"<h3 style='text-align:center;color:black;'>{genre_labels[genre]}</h3></div>",
    unsafe_allow_html=True
)

question = game.generate_question(genre)

st.subheader(f"第 {game.current_question + 1} 問")
st.write(question["question_text"])

# 画像表示
image_url = question["image"]
if isinstance(image_url, str) and os.path.exists(image_url):
    st.image(image_url, width=300)
else:
    st.image("images/no_image.png", width=300)

# 回答選択
answer = st.radio("答えを選んでください：", question["choices"], key=f"q_{game.current_question}")

# 回答ボタン（キー指定で重複回避）
if st.button("回答！", key=f"answer_{game.current_question}"):
    if answer == question["correct"]:
        st.success("✅ 正解！")
        st.image(game.feedback_images["correct"], width=150)
        play_sound("correct.wav")
        game.score += 1
    else:
        st.error(f"❌ 不正解！正解は「{question['correct']}」です。")
        st.image(game.feedback_images["wrong"], width=150)
        play_sound("wrong.wav")

    # フワッと1秒後に切り替え
    time.sleep(1)
    game.current_question += 1

    # クイズ終了判定
    if game.current_question >= game.total_questions:
        st.subheader("🎉 クイズ終了！")
        play_sound("fanfare.wav")
        st.write(f"あなたのスコアは {game.score}/{game.total_questions} 点！")

        if game.score >= 9:
            comment = "🌟 パーフェクト！世界マスター！"
            image_path = game.result_images["perfect"]
        elif game.score >= 6:
            comment = "👍 よくできました！あと少しで満点！"
            image_path = game.result_images["good"]
        elif game.score >= 3:
            comment = "🙂 まずまず！次はもっと高得点を目指そう！"
            image_path = game.result_images["average"]
        else:
            comment = "💡 まだまだこれから！世界をもっと知ろう！"
            image_path = game.result_images["low"]

        st.image(image_path, width=400)
        st.write(comment)

        if st.button("🔁 もう一度遊ぶ", key="restart_button"):
            st.session_state.game = QuizGame(df)
            st.experimental_rerun()
    else:
        st.experimental_rerun()
