import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="City Weather Dashboard 🌦️", page_icon="☀️", layout="centered")
st.title("🌍 City Weather Dashboard (Open-Meteo API)")

# --- City Input ---
city = st.text_input("Enter City Name", value="Pune")

if st.button("Show Weather"):
    # --- Step 1: Get coordinates using Open-Meteo Geocoding API ---
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo_res = requests.get(geo_url).json()

    if "results" not in geo_res or len(geo_res["results"]) == 0:
        st.error("❌ City not found. Please try another name.")
    else:
        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]
        city_name = geo_res["results"][0]["name"]
        country = geo_res["results"][0].get("country", "")

        st.success(f"📍 Location found: {city_name}, {country} (Lat: {lat}, Lon: {lon})")

        # --- Step 2: Get weather forecast using Open-Meteo Forecast API ---
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,wind_speed_10m,weathercode"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration"
            f"&timezone=auto&forecast_days=14"
        )

        weather_res = requests.get(url).json()

        # --- Current Weather ---
        current = weather_res.get("current", {})
        st.subheader("🌦️ Current Weather")
        st.metric("Temperature (°C)", current.get("temperature_2m"))
        st.metric("Wind Speed (km/h)", current.get("wind_speed_10m"))

        # Optional: weather description
        weather_codes = {
            0: "☀️ Clear sky",
            1: "🌤️ Mainly clear",
            2: "⛅ Partly cloudy",
            3: "☁️ Overcast",
            45: "🌫️ Fog",
            48: "🌫️ Depositing rime fog",
            51: "🌦️ Light drizzle",
            61: "🌧️ Light rain",
            71: "❄️ Snow fall",
            95: "⛈️ Thunderstorm",
        }
        code = current.get("weathercode", 0)
        st.write("Condition:", weather_codes.get(code, "Unknown"))

        # --- 2-Week Forecast ---
        st.subheader("📅 2-Week Forecast")

        daily = weather_res.get("daily", {})
        df = pd.DataFrame({
            "Date": daily["time"],
            "Max Temp (°C)": daily["temperature_2m_max"],
            "Min Temp (°C)": daily["temperature_2m_min"],
            "Rain (mm)": daily["precipitation_sum"],
            "Sunshine (s)": daily["sunshine_duration"]
        })

        st.dataframe(df.style.format({"Sunshine (s)": "{:.0f}"}))

        # --- Charts ---
        st.line_chart(df.set_index("Date")[["Max Temp (°C)", "Min Temp (°C)"]])
        st.bar_chart(df.set_index("Date")[["Rain (mm)"]])

st.info("Data from [Open-Meteo API](https://open-meteo.com) — Free & No API key required.")
