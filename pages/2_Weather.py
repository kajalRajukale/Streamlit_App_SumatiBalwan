# pages/2_Weather.py
import streamlit as st
import requests
import geocoder

# ------------------------------
# ☀️ WEATHER PAGE - Auto + Search weather info
# ------------------------------

st.set_page_config(page_title="Weather", page_icon="☀️", layout="centered")

st.title("☀️ Live Weather Info")
st.markdown("Get current weather for your city 🌍")

# --------- OpenWeatherMap Setup ---------
# You can get a free API key from: https://openweathermap.org/api
API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace or leave blank for demo
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# --------- Auto-detect user's city ---------
st.subheader("📍 Auto-detected Location")
try:
    g = geocoder.ip('me')
    city = g.city or "Pune"  # fallback demo city
    st.write(f"Detected city: **{city}**")
except Exception:
    city = "Pune"
    st.write("Could not detect location, showing Pune 🌆")

# --------- Function to fetch weather ---------
def get_weather(city_name):
    if not API_KEY:
        # Mock demo (for no API)
        return {
            "city": city_name,
            "temp": 29,
            "desc": "Clear Sky (Demo)",
        }
    try:
        params = {"q": city_name, "appid": API_KEY, "units": "metric"}
        res = requests.get(BASE_URL, params=params)
        data = res.json()
        if data.get("cod") != 200:
            return None
        return {
            "city": data["name"],
            "temp": data["main"]["temp"],
            "desc": data["weather"][0]["description"].title(),
        }
    except Exception:
        return None

# --------- Display auto location weather ---------
weather_data = get_weather(city)
if weather_data:
    st.metric("🌡️ Temperature", f"{weather_data['temp']} °C")
    st.write(f"🌤️ Condition: **{weather_data['desc']}**")
else:
    st.error("Could not fetch weather data.")

st.divider()

# --------- Search for another city ---------
st.subheader("🔍 Search another city")
user_city = st.text_input("Enter city name", placeholder="e.g., Mumbai")
if st.button("Search Weather"):
    user_weather = get_weather(user_city)
    if user_weather:
        st.success(f"**Weather in {user_weather['city']}**")
        st.metric("Temperature", f"{user_weather['temp']} °C")
        st.write(f"Condition: **{user_weather['desc']}**")
    else:
        st.error("City not found. Try again!")
