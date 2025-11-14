import streamlit as st
import requests
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt

st.set_page_config(page_title="Weather Dashboard", layout="wide")
st.title("Weather Dashboard")

# -------------------------------
# Helper: Geocode city
# -------------------------------
def geocode_city(city):
    """Geocode using Open-Meteo first, fallback Nominatim."""
    city = city.strip()
    if not city:
        return None

    # 1) Open-Meteo Geocoding
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en"
        r = requests.get(url, timeout=8)
        js = r.json()

        if "results" in js and len(js["results"]) > 0:
            res = js["results"][0]
            return {
                "name": res.get("name", city),
                "latitude": res["latitude"],
                "longitude": res["longitude"],
                "country": res.get("country", "")
            }
    except:
        pass

    # 2) Nominatim fallback
    try:
        geolocator = Nominatim(user_agent="weather_app")
        location = geolocator.geocode(city, timeout=10)
        if location:
            return {
                "name": city,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "country": ""
            }
    except:
        pass

    return None


# -------------------------------
# Helper: Weather Data
# -------------------------------
def fetch_weather(lat, lon):
    """Fetch current + 7-day forecast from Open-Meteo."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&forecast_days=7&timezone=auto"
        )
        r = requests.get(url, timeout=10)
        js = r.json()

        daily_df = pd.DataFrame(js["daily"])
        daily_df["time"] = pd.to_datetime(daily_df["time"])

        return {
            "current": js["current_weather"],
            "daily": daily_df
        }
    except Exception as e:
        return None


# -----------------------------------
# UI – Sidebar
# -----------------------------------
st.sidebar.header("Search City")
city = st.sidebar.text_input("Enter a city name", "Mumbai")

if st.sidebar.button("Get Weather"):
    place = geocode_city(city)
    if not place:
        st.error("City not found!")
        st.stop()

    weather = fetch_weather(place["latitude"], place["longitude"])
    if not weather:
        st.error("Weather not available!")
        st.stop()

    st.session_state["place"] = place
    st.session_state["weather"] = weather


# -----------------------------------
# Show Results
# -----------------------------------
if "place" in st.session_state:
    place = st.session_state["place"]
    weather = st.session_state["weather"]

    st.subheader(f"🌍 {place['name']} ({place['country']})")
    st.write(f"Lat: {place['latitude']} | Lon: {place['longitude']}")

    # Current weather
    st.metric("Temperature (°C)", weather["current"]["temperature"])
    st.metric("Wind Speed (km/h)", weather["current"]["windspeed"])

    st.markdown("---")

    # Table
    df = weather["daily"]
    st.subheader("7-Day Forecast")
    st.dataframe(df, use_container_width=True)

    # Chart
    fig, ax = plt.subplots()
    ax.plot(df["time"], df["temperature_2m_max"], marker="o", label="Max")
    ax.plot(df["time"], df["temperature_2m_min"], marker="o", label="Min")
    ax.set_xlabel("Date")
    ax.set_ylabel("°C")
    ax.set_title("Temperature Forecast")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    st.markdown("---")

    # Map
    st.subheader("📍 Location Map")
    m = folium.Map(
        location=[place["latitude"], place["longitude"]],
        zoom_start=8,
        tiles="CartoDB positron"
    )
    folium.Marker(
        [place["latitude"], place["longitude"]],
        popup=place["name"]
    ).add_to(m)

    st_folium(m, width=800, height=500)
