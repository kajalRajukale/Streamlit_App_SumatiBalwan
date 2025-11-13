import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️")
st.title("Weather Dashboard")

st.write("Enter one or more city names (comma separated, e.g., Paris, New York, Pune):")
city_input = st.text_input("Cities", "Pune")

# Helper: map Open-Meteo weather codes → emoji
def weather_icon(code):
    mapping = {
        0: "☀️",
        1: "🌤️",
        2: "⛅",
        3: "☁️",
        45: "🌫️",
        48: "🌫️",
        51: "🌦️",
        53: "🌧️",
        55: "🌧️",
        61: "🌦️",
        63: "🌧️",
        65: "🌧️",
        71: "❄️",
        73: "❄️",
        75: "❄️",
        80: "🌦️",
        81: "🌧️",
        82: "⛈️",
        95: "⛈️",
        99: "🌩️",
    }
    return mapping.get(code, "🌍")

if city_input:
    cities = [c.strip() for c in city_input.split(",") if c.strip()]
    map_points = []

    for city in cities:
        # --- Geocoding ---
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_res = requests.get(geo_url).json()

        if "results" not in geo_res or len(geo_res["results"]) == 0:
            st.warning(f"❌ Could not find '{city}'.")
            continue

        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]
        name = geo_res["results"][0]["name"]
        country = geo_res["results"][0].get("country", "")

        # --- Current weather ---
        current_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        current = requests.get(current_url).json().get("current_weather", {})

        emoji = weather_icon(current.get("weathercode", 0))

        # --- 2-week forecast ---
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
            f"&forecast_days=14&timezone=auto"
        )
        forecast = requests.get(forecast_url).json().get("daily", {})

        # --- Display city info ---
        st.subheader(f"📍 {name}, {country} {emoji}")
        if current:
            st.metric("Current Temperature (°C)", current.get("temperature", "N/A"))
            st.metric("Wind Speed (km/h)", current.get("windspeed", "N/A"))

        if forecast:
            df = pd.DataFrame(forecast)
            df["icon"] = df["weathercode"].apply(weather_icon)

            st.markdown("### 🌤️ 14-Day Forecast")
            for i, row in df.iterrows():
                st.write(
                    f"**{row['time']}** — {row['icon']}  | 🌡️ {row['temperature_2m_min']}–{row['temperature_2m_max']} °C | ☔ {row['precipitation_sum']} mm"
                )

        # --- Map marker ---
        map_points.append({
            "city": name,
            "lat": lat,
            "lon": lon,
            "emoji": emoji
        })

    # --- 🌎 Map ---
    if map_points:
        avg_lat = sum([p["lat"] for p in map_points]) / len(map_points)
        avg_lon = sum([p["lon"] for p in map_points]) / len(map_points)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2)

        for p in map_points:
            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=folium.DivIcon(
                    html=f"""<div style="font-size:32px;">{p['emoji']} {p['city']}</div>"""
                )
            ).add_to(m)

        st.write("### 🗺️ City Locations with Weather")
        st_folium(m, width=700, height=500)
