import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️")
st.title("Weather Dashboard")

st.write("Enter one or more city names (comma separated, e.g., Paris, New York, Pune):")
city_input = st.text_input("Cities", "Pune")

# Helper: weather code → emoji
def weather_icon(code):
    mapping = {
        0: "☀️ Clear",
        1: "🌤️ Mostly clear",
        2: "⛅ Partly cloudy",
        3: "☁️ Cloudy",
        45: "🌫️ Fog",
        48: "🌫️ Fog",
        51: "🌦️ Drizzle",
        53: "🌧️ Drizzle",
        55: "🌧️ Heavy drizzle",
        61: "🌦️ Light rain",
        63: "🌧️ Rain",
        65: "🌧️ Heavy rain",
        71: "❄️ Snow",
        73: "❄️ Moderate snow",
        75: "❄️ Heavy snow",
        80: "🌦️ Showers",
        81: "🌧️ Rain showers",
        82: "⛈️ Thunderstorm",
        95: "⛈️ Thunderstorm",
        99: "🌩️ Hail storm",
    }
    return mapping.get(code, "🌍 Unknown")

if city_input:
    cities = [c.strip() for c in city_input.split(",") if c.strip()]
    map_points = []

    for city in cities:
        # Geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_res = requests.get(geo_url).json()

        if "results" not in geo_res or len(geo_res["results"]) == 0:
            st.warning(f"❌ Could not find '{city}'.")
            continue

        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]
        name = geo_res["results"][0]["name"]
        country = geo_res["results"][0].get("country", "")

        # Current weather
        current_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        current = requests.get(current_url).json().get("current_weather", {})

        # Forecast (14 days)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
            f"&forecast_days=14&timezone=auto"
        )
        forecast = requests.get(forecast_url).json().get("daily", {})

        # --- Show data ---
        st.subheader(f"📍 {name}, {country}")
        if current:
            st.metric("Current Temperature (°C)", current.get("temperature", "N/A"))
            st.metric("Wind Speed (km/h)", current.get("windspeed", "N/A"))

        if forecast:
            df = pd.DataFrame(forecast)
            df["icon"] = df["weathercode"].apply(weather_icon)

            st.markdown("### 🌤️ 14-Day Forecast")
            for i, row in df.iterrows():
                st.write(
                    f"**{row['time']}** — {row['icon']} | 🌡️ {row['temperature_2m_min']}–{row['temperature_2m_max']} °C | ☔ {row['precipitation_sum']} mm"
                )

        map_points.append({"city": name, "lat": lat, "lon": lon})

    # --- 🌎 Create map like Google Maps ---
    if map_points:
        avg_lat = sum([p["lat"] for p in map_points]) / len(map_points)
        avg_lon = sum([p["lon"] for p in map_points]) / len(map_points)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2)

        for p in map_points:
            folium.Marker(
                location=[p["lat"], p["lon"]],
                popup=f"<b>{p['city']}</b>",
                icon=folium.Icon(color="blue", icon="cloud"),
            ).add_to(m)

        st.write("### 🗺️ City Locations on Map")
        st_folium(m, width=700, height=500)
