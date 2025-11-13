# weather_app.py
import streamlit as st
import requests
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pyttsx3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Weather Explorer (Improved)", layout="wide")
st.title("🌦️ Weather Explorer — reliable city search + 7-day forecast")

# ------------------------
# Helper: geocode with fallback
# ------------------------
def geocode_city(city, tries=2, pause=0.6):
    """
    Try Open-Meteo geocoding first. If not found, fall back to Nominatim.
    Returns dict with {name, latitude, longitude, country} or None.
    """
    city = city.strip()
    if not city:
        return None

    # 1) Try Open-Meteo geocoding
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(city)}&count=1&language=en"
        for attempt in range(tries):
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                js = r.json()
                if "results" in js and len(js["results"]) > 0:
                    res = js["results"][0]
                    return {
                        "name": res.get("name", city),
                        "latitude": res.get("latitude"),
                        "longitude": res.get("longitude"),
                        "country": res.get("country", "")
                    }
            time.sleep(pause)
    except Exception:
        # fail silently and move to fallback
        pass

    # 2) Fallback: Nominatim (geopy)
    try:
        geolocator = Nominatim(user_agent="weather_explorer_app")
        for attempt in range(tries):
            location = geolocator.geocode(city, timeout=10)
            if location:
                # Nominatim doesn't always provide country in a single field; we use 'address' if exists
                country = None
                if hasattr(location, "raw") and isinstance(location.raw, dict):
                    country = location.raw.get("address", {}).get("country", "")
                return {
                    "name": getattr(location, "address", city),
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "country": country or ""
                }
            time.sleep(pause)
    except Exception:
        pass

    # Not found
    return None

# ------------------------
# Helper: fetch weather from Open-Meteo
# ------------------------
def fetch_weather_for_point(lat, lon):
    """
    Returns dict: current temp, windspeed, weathercode, daily DataFrame (7 days)
    or None on failure.
    """
    try:
        # Current weather + 7-day daily forecast
        # Use forecast_days=7 (today + next 6)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
            f"&forecast_days=7&timezone=auto"
        )
        r = requests.get(forecast_url, timeout=10)
        if r.status_code != 200:
            return None
        js = r.json()

        current = js.get("current_weather", {})
        daily = js.get("daily", {})

        # Build DataFrame for daily
        df = pd.DataFrame(daily) if daily else pd.DataFrame()
        # Ensure time column present
        if not df.empty and "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
        return {
            "current": current,
            "daily": df
        }
    except Exception:
        return None

# ------------------------
# UI: inputs
# ------------------------
st.sidebar.header("Search cities")
city_input = st.sidebar.text_input("Enter city names (comma-separated)", "Mumbai, Berlin, New York")
max_wait = st.sidebar.slider("Pause between geocoding requests (seconds)", min_value=0.3, max_value=2.0, value=0.6, step=0.1)
do_speak = st.sidebar.checkbox("Enable Speak Buttons (pyttsx3)", value=False)
do_auto_speak = st.sidebar.checkbox("Auto-speak all on fetch (may block UI)", value=False)

cities = [c.strip() for c in city_input.split(",") if c.strip()]
if len(cities) == 0:
    st.info("Enter at least one city in the sidebar to start.")
    st.stop()

if st.sidebar.button("Fetch Weather"):
    st.session_state["results"] = None
    failed = []
    results = []
    with st.spinner("Finding cities and fetching weather..."):
        for city in cities:
            st.write(f"Searching '{city}' ...")
            place = geocode_city(city, pause=max_wait)
            if not place:
                failed.append(city)
                st.warning(f"❌ Could not locate '{city}' — try a different spelling or add country (e.g., 'Berlin, Germany').")
                continue

            lat = place["latitude"]
            lon = place["longitude"]
            # small pause to be polite
            time.sleep(max_wait)

            weather = fetch_weather_for_point(lat, lon)
            if not weather:
                failed.append(city)
                st.warning(f"⚠️ Weather fetch failed for '{city}' (lat:{lat}, lon:{lon}).")
                continue

            # Compose readable results
            cur = weather["current"]
            daily_df = weather["daily"]
            # Current values - Open-Meteo current_weather keys: temperature, windspeed, weathercode
            cur_temp = cur.get("temperature", "N/A")
            cur_wind = cur.get("windspeed", "N/A")
            cur_code = cur.get("weathercode", None)

            results.append({
                "query": city,
                "name": place.get("name", city),
                "country": place.get("country", ""),
                "latitude": lat,
                "longitude": lon,
                "temperature": cur_temp,
                "windspeed": cur_wind,
                "weathercode": cur_code,
                "daily": daily_df
            })

    st.session_state["results"] = results
    st.session_state["failed"] = failed

# ------------------------
# If results exist show them
# ------------------------
if "results" in st.session_state and st.session_state["results"]:
    results = st.session_state["results"]
    failed = st.session_state.get("failed", [])

    st.success(f"Loaded weather for {len(results)} cities.")
    if failed:
        st.warning(f"Failed to fetch for: {', '.join(failed)}")

    # Display cards for each city
    st.subheader("City Weather")
    for i, r in enumerate(results):
        # color mapping (dark friendly)
        def card_color_from_desc(code):
            # Map some weathercode groups to colors
            # Open-Meteo weathercode reference: 0 clear, 1-3 partial/cloudy, 45/48 fog, 51-67 drizzle/rain, 71-77 snow, 80-99 thunder
            if code is None:
                return "#374151"  # fallback dark gray
            if code == 0:
                return "#F59E0B"  # sunny amber
            if code in (1,2,3):
                return "#93C5FD"  # light blue (partly-cloudy)
            if code in (45,48):
                return "#6B7280"  # foggy gray
            if 51 <= code <= 67 or 80 <= code <= 82 or 95 <= code <= 99:
                return "#1E3A8A"  # rainy/dark blue
            if 71 <= code <= 77:
                return "#60A5FA"  # snowy light blue
            return "#374151"

        bg = card_color_from_desc(r.get("weathercode"))

        # Header and two columns for temp & wind
        st.markdown(
            f"""
            <div style="
                background-color:{bg};
                color: white;
                padding:14px;
                border-radius:10px;
                box-shadow:0 6px 18px rgba(0,0,0,0.35);
                margin-bottom:10px;
            ">
                <h3 style="margin:0">🌆 {r['name']} <small style="opacity:0.8"> {r.get('country','')}</small></h3>
                <div style="opacity:0.95">Lat: {round(r['latitude'],3)} • Lon: {round(r['longitude'],3)}</div>
            </div>
            """, unsafe_allow_html=True
        )

        col1, col2 = st.columns([1,1])
        with col1:
            st.metric(label="🌡️ Temperature (°C)", value=r["temperature"])
        with col2:
            st.metric(label="💨 Wind Speed (km/h)", value=r["windspeed"])

        # Buttons: speak & show details
        btn_col1, btn_col2 = st.columns([1,3])
        with btn_col1:
            if do_speak and st.button(f"🔊 Speak {r['name']}"):
                try:
                    engine = pyttsx3.init()
                    text = f"Weather in {r['name']}. Temperature {r['temperature']} degrees Celsius. Wind {r['windspeed']} kilometers per hour."
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    st.error(f"Voice error: {e}")
        with btn_col2:
            with st.expander("📘 Show 7-day forecast & chart"):
                daily = r["daily"]
                if daily is None or daily.empty:
                    st.info("No daily forecast data available.")
                else:
                    # show table
                    df_display = daily.copy()
                    # if Open-Meteo returns temperature_2m_max/min columns rename if different
                    # show readable table with dates and min/max temps and precipitation
                    show_cols = []
                    if "time" in df_display.columns:
                        show_cols.append("time")
                    for c in ["temperature_2m_min", "temperature_2m_max", "precipitation_sum", "weathercode"]:
                        if c in df_display.columns:
                            show_cols.append(c)
                    if show_cols:
                        st.dataframe(df_display[show_cols].rename(columns={
                            "time":"Date",
                            "temperature_2m_min":"Min °C",
                            "temperature_2m_max":"Max °C",
                            "precipitation_sum":"Precip (mm)",
                            "weathercode":"WCode"
                        }).assign(Date=lambda d: pd.to_datetime(d["Date"]).dt.date), use_container_width=True)
                    # chart
                    try:
                        fig, ax = plt.subplots()
                        if "temperature_2m_max" in df_display.columns and "time" in df_display.columns:
                            ax.plot(pd.to_datetime(df_display["time"]), df_display["temperature_2m_max"], marker="o", label="Max °C")
                        if "temperature_2m_min" in df_display.columns and "time" in df_display.columns:
                            ax.plot(pd.to_datetime(df_display["time"]), df_display["temperature_2m_min"], marker="o", label="Min °C")
                        ax.set_title(f"7-day temp for {r['name']}")
                        ax.set_xlabel("Date")
                        ax.set_ylabel("°C")
                        ax.grid(True, alpha=0.3)
                        ax.legend()
                        st.pyplot(fig)
                    except Exception as e:
                        st.write("Could not render chart:", e)

        st.markdown("---")

    # Map of all cities
    st.subheader("🗺️ Map of cities")
    # center map at mean coords if available
    avg_lat = sum([x["latitude"] for x in results]) / len(results)
    avg_lon = sum([x["longitude"] for x in results]) / len(results)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2, tiles="CartoDB positron")
    for r in results:
        popup_html = f"<b>{r['name']}</b><br>🌡️ {r['temperature']} °C<br>💨 {r['windspeed']} km/h"
        folium.Marker(location=[r["latitude"], r["longitude"]], popup=popup_html, tooltip=r["name"]).add_to(m)
    st_folium(m, width=900, height=500)

    # Optionally auto speak all (if user enabled)
    if do_auto_speak:
        try:
            engine = pyttsx3.init()
            for r in results:
                text = f"{r['name']}: {r['temperature']} degrees Celsius, wind {r['windspeed']} kilometers per hour."
                engine.say(text)
            engine.runAndWait()
        except Exception as e:
            st.error(f"Auto-speak error: {e}")

# If we have failures but no results yet (user pressed fetch but nothing succeeded)
elif "failed" in st.session_state and st.session_state["failed"]:
    failed_list = st.session_state["failed"]
    if "results" not in st.session_state or not st.session_state["results"]:
        st.error("⚠️ Could not fetch weather for any of the entered cities. Please check spelling or add country (e.g., 'Berlin, Germany').")
        st.write("Failed cities:", ", ".join(failed_list))
