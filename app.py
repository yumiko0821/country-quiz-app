import streamlit as st
import pandas as pd
import random
import base64

# ==============================
# 🔧 CSVファイルの自動修正＆読み込み
# ==============================
@st.cache_data
def load_clean_csv(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        # ダブルクォートで囲まれていたら除去
        cleaned_lines = [line.strip().strip('"') for line in lines]
        clean_path = "country_quiz_cleaned.csv"
        with open(clean_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(cleaned_lines))
        df = pd.read_csv(clean_path)
        return df
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        return pd.DataFrame()

# ==============================
# 🔊 音声をbase64で読み込み
# ==============================
def load_sound(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:audio/wav;base64,{b64}"

correct_sound = load_sound("correct.wav")
wrong_sound = load_sound("wrong.wav")
fanfare_sound = load_sound("fanfare.wav")

# ==============================
# 🎨 カラーとラベル設定
# ==============================
GENRE_LABELS = {
    'capital': '首都クイズ',
    'currency': '通貨クイズ',
    'population': '人口クイズ'
}

GENRE_COLORS = {
    'capital': '#ccf2ff',
    'currency': '#d9fcd9',
    'population': '#fff2cc'
}

# ==============================
# 📊 画像設定
# ==============================
FEEDBACK_IMAGES = {
    'correct': 'images/correct_stamp.png',
    'wrong': 'images/wrong_stamp.png'
}

RESULT_IMAGES = {
    'perfect': 'images/j428_7_1.png',
    'good': 'images/j428_6_1.png',
    'average': 'images/j428_6_2.png',
    'low': 'images/j428_7_2.png'
}

# ==============================
# 📘 アプリ本体
# ==============================
st.title("🌍 世界の国クイズ")

password = st.text_input("パスワードを入力してください（例：demo1030）", type="password")
if password != "demo1030":
    st.stop()

# データ読み込み
df = load_clean_csv("country_quiz.csv")

if df.empty:
    st.error("データが読み込めませんでした。")
    st.stop()

# ==============================
# 🎮 クイズ設定
# ==============================
genre = st.selectbox("クイズのジャンルを選んでください：", list(GENRE_LABELS.keys()), format_func=lambda x: GENRE_LABELS[x])

st.markdown(
    f"<div style='background-color:{GENRE_COLORS[genre]}; padding:10px; border-radius:10px;'>"
    f"現在のモード：<b>{GENRE_LABELS[genre]}</b></div>",
    unsafe_allow_html=True
)

if "questions" not in st.session_state:
    st.session_state.questions = random.sample(df.to_dict(orient="records"), 5)
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.finished = False

index = st.session_state.index
score = st.session_state.score
questions = st.session_state.questions

if not st.session_state.finished:
    q = questions[index]
    country_name = q["国名"]
    image_url = q["画像URL"]

    if genre == "capital":
        correct_answer = q["首都"]
        choices = [correct_answer] + random.sample(df["首都"].dropna().tolist(), 3)
    elif genre == "currency":
        correct_answer = q["通貨"]
        choices = [correct_answer] + random.sample(df["通貨"].dropna().tolist(), 3)
    else:  # population
        correct_answer = str(q["人口"])
        choices = [correct_answer] + random.sample(df["人口"].astype(str).dropna().tolist(), 3)

    random.shuffle(choices)

    st.image(image_url, caption=f"{country_name}", width=300)
    st.subheader(f"Q{index+1}. {country_name} の {GENRE_LABELS[genre]} は？")

    answer = st.radio("選択肢を選んでください：", choices, key=f"q_{index}")

    if st.button("回答する"):
        if answer == correct_answer:
            st.session_state.score += 1
            st.success("⭕ 正解！")
            st.image(FEEDBACK_IMAGES["correct"], width=200)
            st.markdown(f"<audio autoplay><source src='{correct_sound}' type='audio/wav'></audio>", unsafe_allow_html=True)
        else:
            st.error(f"❌ 不正解！ 正解は「{correct_answer}」です。")
            st.image(FEEDBACK_IMAGES["wrong"], width=200)
            st.markdown(f"<audio autoplay><source src='{wrong_sound}' type='audio/wav'></audio>", unsafe_allow_html=True)

        st.session_state.index += 1

        if st.session_state.index >= 5:
            st.session_state.finished = True
        st.experimental_rerun()

else:
    # 結果表示
    st.balloons()
    st.markdown(f"<audio autoplay><source src='{fanfare_sound}' type='audio/wav'></audio>", unsafe_allow_html=True)
    st.subheader(f"🎉 あなたの得点は {score} / 5 点！")

    if score >= 5:
        comment = "🌟 パーフェクト！世界マスター！"
        image_path = RESULT_IMAGES['perfect']
    elif score >= 3:
        comment = "👍 よくできました！あと少しで満点！"
        image_path = RESULT_IMAGES['good']
    elif score >= 2:
        comment = "🙂 まずまず！次はもっと高得点を目指そう！"
        image_path = RESULT_IMAGES['average']
    else:
        comment = "💡 まだまだこれから！世界をもっと知ろう！"
        image_path = RESULT_IMAGES['low']

    st.image(image_path, width=350)
    st.write(comment)

    if st.button("もう一度遊ぶ"):
        for key in ["questions", "index", "score", "finished"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()
