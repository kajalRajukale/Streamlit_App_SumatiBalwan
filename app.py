# Home.py
import streamlit as st

# ------------------------------
# 🏠 HOME PAGE - Main navigation hub
# ------------------------------

st.set_page_config(page_title="AI Mini App - Quiz & Weather", page_icon="🌤️", layout="centered")

st.title("🌟 Welcome to AI Mini App")
st.markdown("### Choose a page from the sidebar or click below 👇")

# Add buttons for quick navigation
col1, col2 = st.columns(2)
with col1:
    if st.button("🧠 Go to Quiz"):
        st.switch_page("pages/1_Quiz.py")

with col2:
    if st.button("☀️ Go to Weather"):
        st.switch_page("pages/2_Weather.py")

st.divider()
st.markdown(
    """
    **✨ Tips**
    - Use the sidebar to switch between pages.
    - Try the fun quiz and check weather for your city!
    """
)
