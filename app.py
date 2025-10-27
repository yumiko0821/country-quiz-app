import streamlit as st
import pandas as pd
import random
import base64
import os
import io

# ==============================
# 📊 CSV読み込み関数（自動修正つき）
# ==============================
def load_country_data():
    CSV_PATH = "country_quiz.csv"

    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # 1列にまとまっている（"国名,人口,..."）パターン対応
        if content.startswith('"国名') or content.startswith("国名,"):
            lines = [line.strip('"') for line in content.splitlines()]
            csv_text = "\n".join(lines)
            df = pd.read_csv(io.StringIO(csv_text))
        else:
            df = pd.read_csv(io.StringIO(content))

        # 列数チェック
        if len(df.columns) != 5:
            st.error("❌ CSVの列数が5ではありません。")
            st.stop()

        df.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
        return df

    except Exception as e:
        st.error(f"❌ CSV読み込みエラー: {e}")
        st.stop()


# ==============================
# 🎯 クイズクラス定義
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
        question = self.df.sample(1).iloc[0]
        country_name = question["国名"]
        correct_answer = ""
        choices = []

        if genre == "capital":
            correct_answer = question["首都"]
            choices = list(self.df["首都"].dropna().sample(3))
        elif genre == "currency":
            correct_answer = question["通貨"]
            choices = list(self.df["通貨"].dropna().sample(3))
        elif genre == "population":
            correct_answer = str(question["人口"])
            choices = list(self.df["人口"].dropna().astype(str).sample(3))

        if correct_answer not in choices:
            choices.append(correct_answer)
        random.shuffle(choices)

        return {
            "country": country_name,
            "correct": correct_answer,
            "choices": choices,
            "genre": genre,
            "image": question["画像URL"]
        }


# ==============================
# 🔐 パスワード保護
# ==============================
PASSWORD = "demo1030"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🌍 世界クイズへようこそ！")
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
# 🚀 Streamlitアプリ本体
# ==============================
st.set_page_config(page_title="世界クイズ", page_icon="🌍", layout="centered")

# ✅ CSV読み込み
df = load_country_data()

# ✅ 初期化
if "game" not in st.session_state:
    st.session_state.game = QuizGame(df)
if "genre" not in st.session_state:
    st.session_state.genre = "capital"

# ==============================
# 🎨 ジャンル設定
# ==============================
genre_labels = {
    "capital": "首都クイズ",
    "currency": "通貨クイズ",
    "population": "人口クイズ"
}

genre_colors = {
    "capital": "#ccf2ff",
    "currency": "#d9fcd9",
    "population": "#fff2cc"
}

# ==============================
# 🧠 ゲーム本体
# ==============================
st.title("🌍 世界クイズ！")
genre = st.radio("ジャンルを選んでね", ["capital", "currency", "population"],
                 format_func=lambda x: genre_labels[x])

st.markdown(
    f"<div style='background-color:{genre_colors[genre]};padding:10px;border-radius:10px;'>"
    f"<h3 style='text-align:center;'>{genre_labels[genre]}</h3></div>",
    unsafe_allow_html=True
)

game = st.session_state.game
question = game.generate_question(genre)

st.subheader(f"第 {game.current_question + 1} 問")
st.write(f"🌏 この国はどこ？ → **{question['country']}**")

# 画像表示（存在チェックあり）
image_url = question["image"]
if isinstance(image_url, str) and os.path.exists(image_url):
    st.image(image_url, width=300)
else:
    st.warning(f"⚠️ 画像が見つかりませんでした：{image_url}")
    st.image("images/no_image.png", width=300)

answer = st.radio("答えを選んでください：", question["choices"])

if st.button("回答！"):
    if answer == question["correct"]:
        st.success("✅ 正解！")
        st.image(game.feedback_images["correct"], width=150)
        play_sound("correct.wav")
        game.score += 1
    else:
        st.error(f"❌ 不正解！正解は「{question['correct']}」です。")
        st.image(game.feedback_images["wrong"], width=150)
        play_sound("wrong.wav")

    game.current_question += 1

    if game.current_question >= game.total_questions:
        st.subheader("🎉 クイズ終了！")
        play_sound("fanfare.wav")
        st.write(f"あなたのスコアは {game.score}/{game.total_questions} 点！")

        if game.score == game.total_questions:
            comment = "🌟 パーフェクト！世界マスター！"
            image_path = game.result_images["perfect"]
        elif game.score >= 4:
            comment = "👍 よくできました！あと少しで満点！"
            image_path = game.result_images["good"]
        elif game.score >= 2:
            comment = "🙂 まずまず！次はもっと高得点を目指そう！"
            image_path = game.result_images["average"]
        else:
            comment = "💡 まだまだこれから！世界をもっと知ろう！"
            image_path = game.result_images["low"]

        st.image(image_path, width=400)
        st.write(comment)

        if st.button("🔁 もう一度遊ぶ"):
            st.session_state.game = QuizGame(df)
            st.experimental_rerun()
