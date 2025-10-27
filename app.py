# app.py -- 頑強版 CSV ローダ付きの完全版
import streamlit as st
import pandas as pd
import random
import base64
import os
import io
import csv

# ==============================
# 📊 頑強な CSV 読み込み関数
# ==============================
def load_country_data(csv_path="country_quiz.csv", expected_cols=5):
    """
    いろんな壊れ方を自動修正して DataFrame を返す。
    - 行全体が "a,b,c" のようにダブルクォートでくくられている
    - 普通の CSV（カンマ区切り）
    - 一部行で列数が違う → 余分なカンマは末尾の列に結合して調整
    """
    if not os.path.exists(csv_path):
        st.error(f"CSVが見つかりません: {csv_path}")
        st.stop()

    # まず生のテキストを読む
    with open(csv_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # try: pandas の通常読み込み（最初のトライ）
    try:
        df_try = pd.read_csv(io.StringIO(text), encoding="utf-8", engine="python")
        # 正常に5列と認識されればそのまま返す
        if len(df_try.columns) == expected_cols:
            df_try.columns = ["国名", "人口", "画像URL", "首都", "通貨"]
            return df_try
    except Exception:
        pass  # 次の方法へ

    # 次: csv.reader を使って行ごとにパースして整形する（堅牢）
    rows = []
    with io.StringIO(text) as s:
        # use csv.reader to respect quoting. delimiter=',' and quotechar='"'
        reader = csv.reader(s, delimiter=',', quotechar='"')
        for raw_row in reader:
            # raw_row is a list. Common problematic patterns:
            # - raw_row == ['国名,人口,画像URL,首都,通貨']  (1 element containing commas)
            # - raw_row == ['国名','人口','...'] (good)
            if len(raw_row) == 1 and ',' in raw_row[0]:
                # split the single string by comma
                parts = raw_row[0].split(',')
            else:
                parts = raw_row

            # strip whitespace from parts
            parts = [p.strip() for p in parts]

            # adjust length:
            if len(parts) < expected_cols:
                # pad missing columns with empty strings
                parts = parts + [""] * (expected_cols - len(parts))
            elif len(parts) > expected_cols:
                # too many fields: join extras into the last column
                # join from (expected_cols-1) onward into last field
                first = parts[: expected_cols - 1]
                last = ",".join(parts[expected_cols - 1 :])
                parts = first + [last]

            rows.append(parts)

    # 最低でもヘッダー行があるか確認
    if len(rows) == 0:
        st.error("CSVが空です。")
        st.stop()

    # if header row looks like data header (contains '国名' etc), remove quotes already handled
    header = rows[0]
    # If header row contains '国名' or '人口' etc in any cell, treat as header; else create header row
    if any("国名" in str(h) or "人口" in str(h) for h in header):
        data_rows = rows[1:]
    else:
        # no header present -> assume rows are all data
        data_rows = rows

    # Build DataFrame
    df = pd.DataFrame(data_rows, columns=["国名", "人口", "画像URL", "首都", "通貨"])

    # Try to coerce population to numeric if possible
    try:
        df["人口"] = df["人口"].astype(str).str.replace(",", "").str.replace("、", "").str.strip()
        # if numeric strings, convert
        df["人口_num"] = pd.to_numeric(df["人口"], errors="coerce")
        # keep original as string too
    except Exception:
        pass

    return df

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
# 🎵 音声再生
# ==============================
def play_sound(sound_file):
    if os.path.exists(sound_file):
        with open(sound_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f"<audio autoplay><source src='data:audio/wav;base64,{b64}' type='audio/wav'></audio>", unsafe_allow_html=True)

# ==============================
# 🎯 Quiz クラス定義
# ==============================
# ==============================
# 🎯 ゲーム設定
# ==============================
class QuizGame:
    def __init__(self, df):
        self.df = df
        self.score = 0
        self.total_questions = 5
        self.current_question = 0
        self.category = None  # ← 選択ジャンルを保持

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

    def set_category(self, category):
        """ジャンルを設定"""
        self.category = category

    def get_question(self):
        """ジャンルに応じた問題を生成"""
        question_data = self.df.sample(1).iloc[0]
        country = question_data["国名"]

        if self.category == "population":
            question_text = f"🌍 {country}の人口は次のうちどれ？"
            correct = str(question_data["人口"])
            options = list(self.df["人口"].dropna().astype(str).sample(3))
        elif self.category == "currency":
            question_text = f"💰 {country}の通貨は次のうちどれ？"
            correct = question_data["通貨"]
            options = list(self.df["通貨"].dropna().sample(3))
        elif self.category == "capital":
            question_text = f"🏙️ {country}の首都は次のうちどれ？"
            correct = question_data["首都"]
            options = list(self.df["首都"].dropna().sample(3))
        else:
            question_text = f"{country}についてのクイズです！"
            correct = None
            options = []

        if correct not in options:
            options.append(correct)
        random.shuffle(options)

        return {
            "text": question_text,
            "correct": correct,
            "options": options,
            "image": question_data["画像URL"]
        }


class QuizGame:
    def __init__(self, df):
        self.df = df
        self.current_question = 0
        self.score = 0
        self.total_questions = 10
        self.category = None  # 'population', 'currency', 'capital' など
        self.result_images = {
            "perfect": "images/result_perfect.png",
            "good": "images/result_good.png",
            "average": "images/result_average.png",
            "low": "images/result_low.png",
        }

    def set_category(self, category):
        self.category = category

    def get_question(self):
    question = self.df.sample(1).iloc[0]
    country_name = question["国名"]

    if self.category == "capital":
        text = f"{country_name} の首都は次のうちどれ？"
        correct_answer = question["首都"]
        choices = list(self.df["首都"].dropna().sample(3))
    elif self.category == "currency":
        text = f"{country_name} の通貨は次のうちどれ？"
        correct_answer = question["通貨"]
        choices = list(self.df["通貨"].dropna().sample(3))
    else:
        text = f"{country_name} の人口は次のうちどれ？"
        correct_answer = str(question["人口"])
        choices = list(self.df["人口"].dropna().astype(str).sample(3))

    if correct_answer not in choices:
        choices.append(correct_answer)
    random.shuffle(choices)

    return {
        "country": country_name,  # ← これを追加！
        "text": text,
        "choices": choices,
        "correct": correct_answer,
        "image": question["画像URL"]
    }


        # 重複を防いでシャッフル
        options = list(set(options))
        random.shuffle(options)

        return {
            "text": question_text,
            "correct": correct,
            "options": options,
            "image": question_data["画像URL"],
        }



# ==============================
# 🚀 Streamlit 本体
# ==============================
st.set_page_config(page_title="地理クイズ", page_icon="🌍", layout="centered")

# load data
df = load_country_data("country_quiz.csv")

# show debug info (only when needed) -- comment out later
# st.write(f"データ行数: {len(df)} / 列: {list(df.columns)}")  # ← デバッグ表示をオフにする

# init session
if "game" not in st.session_state:
    st.session_state.game = QuizGame(df)

genre_labels = {"capital": "首都クイズ", "currency": "通貨クイズ", "population": "人口クイズ"}
genre_colors = {"capital": "#180B4A", "currency": "#024E1B", "population": "#f1c542"}

st.title("🌍 地理クイズ！")
genre = st.radio("ジャンルを選んでね", ["capital", "currency", "population"], format_func=lambda x: genre_labels[x])

st.markdown(
    f"<div style='background-color:{genre_colors[genre]};padding:10px;border-radius:10px;'>"
    f"<h3 style='text-align:center;color:white;'>{genre_labels[genre]}</h3></div>",
    unsafe_allow_html=True
)
# 選んだジャンルをクラスにセット
st.session_state.game.set_category(genre)

# 問題生成（←ここを修正）
question = st.session_state.game.get_question()

game = st.session_state.game
game.set_category(genre)
question = game.get_question()

st.subheader(f"第 {game.current_question + 1} 問")
st.write(f"🌏 この国はどこ？ → **{question['country']}**")

# 画像表示（ローカルパスまたはURL）
image_url = question["image"]
if isinstance(image_url, str) and image_url.strip() != "":
    # ローカルにファイルがあればそれを表示、なければ URL 表示（Streamlit が URL を処理）
    if os.path.exists(image_url):
        st.image(image_url, width=300)
    else:
        try:
            st.image(image_url, width=300)
        except Exception:
            st.image("images/no_image.png", width=300)
else:
    st.image("images/no_image.png", width=300)

answer = st.radio("答えを選んでください：", question["choices"])

# セッション状態の初期化
if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False
if "last_answer_correct" not in st.session_state:
    st.session_state.last_answer_correct = None

# 回答ボタン
if st.button("回答！"):
    st.session_state.show_feedback = True
    st.session_state.last_answer_correct = (answer == question["correct"])

    # 正解・不正解判定
    if st.session_state.last_answer_correct:
        play_sound("correct.wav")
        game.score += 1
    else:
        play_sound("wrong.wav")

# 回答後の表示処理
if "answered" not in st.session_state:
    st.session_state.answered = False

if not st.session_state.answered:
    if st.button("回答！"):
        st.session_state.answered = True
        st.session_state.last_answer_correct = (answer == question["correct"])

if st.session_state.answered:
    if st.session_state.last_answer_correct:
        st.success("✅ 正解！")
        play_sound("correct.wav")
        st.markdown("""
            <style>
            @keyframes fadeInOut {
                0% {opacity: 0; transform: scale(0.5);}
                30% {opacity: 1; transform: scale(1.1);}
                70% {opacity: 1; transform: scale(1.0);}
                100% {opacity: 0; transform: scale(0.5);}
            }
            .stamp {animation: fadeInOut 1.5s ease-in-out; text-align:center;}
            </style>
            <div class="stamp">
                <img src="images/correct_stamp.png" width="200">
            </div>
        """, unsafe_allow_html=True)
        game.score += 1
    else:
        st.error(f"❌ 不正解！正解は「{question['correct']}」です。")
        play_sound("wrong.wav")
        st.markdown("""
            <style>
            @keyframes fadeInOut {
                0% {opacity: 0; transform: scale(0.5);}
                30% {opacity: 1; transform: scale(1.1);}
                70% {opacity: 1; transform: scale(1.0);}
                100% {opacity: 0; transform: scale(0.5);}
            }
            .stamp {animation: fadeInOut 1.5s ease-in-out; text-align:center;}
            </style>
            <div class="stamp">
                <img src="images/wrong_stamp.png" width="200">
            </div>
        """, unsafe_allow_html=True)

    # 「次の問題へ」ボタンを出す
    if st.button("➡️ 次の問題へ"):
        game.current_question += 1
        st.session_state.answered = False

        if game.current_question >= game.total_questions:
            play_sound("fanfare.wav")
            st.subheader("🎉 クイズ終了！")
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

            if st.button("🔁 もう一度遊ぶ"):
                st.session_state.game = QuizGame(df)
                st.session_state.answered = False
                st.session_state.last_answer_correct = None
                st.experimental_rerun()
        else:
            st.experimental_rerun()



    game.current_question += 1

    # クイズ終了時
    if game.current_question >= game.total_questions:
        st.subheader("🎉 クイズ終了！")
        play_sound("fanfare.wav")
        st.write(f"あなたのスコアは {game.score}/{game.total_questions} 点！")
    else:
        st.experimental_rerun()




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

        try:
            st.image(image_path, width=400)
        except Exception:
            pass
        st.write(comment)

        if st.button("🔁 もう一度遊ぶ"):
            st.session_state.game = QuizGame(df)
            st.rerun()
