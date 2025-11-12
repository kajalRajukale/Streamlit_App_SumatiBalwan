# pages/1_Quiz.py
import streamlit as st

# ------------------------------
# 🧠 QUIZ PAGE - 3 question mini quiz
# ------------------------------

st.set_page_config(page_title="Quiz", page_icon="🧠", layout="centered")
st.title("🧠 Fun Knowledge Quiz")
st.markdown("Answer the 3 questions below and test yourself!")

# Define quiz data
quiz = [
    {
        "question": "1️⃣ What is the capital of France?",
        "options": ["Paris", "London", "Berlin", "Rome"],
        "answer": "Paris"
    },
    {
        "question": "2️⃣ Who developed Python?",
        "options": ["Guido van Rossum", "Elon Musk", "Linus Torvalds", "Mark Zuckerberg"],
        "answer": "Guido van Rossum"
    },
    {
        "question": "3️⃣ What is 5 * 3 + 2?",
        "options": ["17", "18", "15", "20"],
        "answer": "17"
    }
]

# Store user answers
user_answers = []

for q in quiz:
    ans = st.radio(q["question"], q["options"], index=None)
    user_answers.append(ans)

if st.button("✅ Submit"):
    score = 0
    for idx, q in enumerate(quiz):
        if user_answers[idx] == q["answer"]:
            score += 1

    st.success(f"🎉 You scored {score} / {len(quiz)}")
    
    if score == 3:
        st.balloons()
        st.markdown("**Excellent! 🌟 You're a genius!**")
    elif score == 2:
        st.markdown("**Nice work 👍 Keep learning!**")
    else:
        st.markdown("**Keep practicing 🤓 You'll get there!**")
