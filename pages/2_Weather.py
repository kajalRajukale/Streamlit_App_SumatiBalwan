# pages/2_Weather.py
import streamlit as st
import requests
import pandas as pd
import time
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from gtts import gTTS
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --------------------------
# Page config
# --------------------------
st.set_page_config(page_title="Weather Dashboard — Maps, Voice, Hourly & 7-day", layout="wide")
st.title("🌦️ Weather Dashboard — Maps, Voice, Hourly & Weekly Forecasts")

# --------------------------
# Styles / small animated icons via CSS + emoji fallback
# --------------------------
ICON_MAP = {
    # mapping Open-Meteo weathercode groups to simple gif or emoji as fallback
    "clear": "☀️",
    "partly_cloudy": "⛅",
    "cloudy": "☁️",
    "fog": "🌫️",
    "rain": "🌧️",
    "drizzle": "🌦️",
    "snow": "❄️",
    "thunder": "⛈️",
    "unknown": "🌈"
}

def weathercode_to_key(code):
    if code is None:
        return "unknown"
    c = int(code)
    if c == 0:
        return "clear"
    if c in (1,2,3):
        return "partly_cloudy"
    if c in (45,48):
        return "fog"
    if 51 <= c <= 67 or 80 <= c <= 82 or 95 <= c <= 99 or (c >= 80 and c <= 99):
        return "rain"
    if 71 <= c <= 77:
        return "snow"
    if 95 <= c <= 99:
        return "thunder"
    return "cloudy"

# --------------------------
# Helpers: geocode via Open-Meteo then fallback to Nominatim
# --------------------------
def geocode_city(city, tries=2, pause=0.5):
    city = city.strip()
    if not city:
        return None
    # Open-Meteo geocoding
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(city)}&count=1&language=en"
        for _ in range(tries):
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                js = r.json()
                if "results" in js and len(js["results"])>0:
                    res = js["results"][0]
                    return {
                        "name": res.get("name", city),
                        "latitude": res.get("latitude"),
                        "longitude": res.get("longitude"),
                        "country": res.get("country","")
                    }
            time.sleep(pause)
    except Exception:
        pass
    # fallback: geopy Nominatim
    try:
        geolocator = Nominatim(user_agent="weather_dashboard_app")
        for _ in range(tries):
            loc = geolocator.geocode(city, timeout=10)
            if loc:
                country = ""
                if hasattr(loc, "raw") and isinstance(loc.raw, dict):
                    country = loc.raw.get("address", {}).get("country", "")
                return {
                    "name": getattr(loc, "address", city),
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "country": country
                }
            time.sleep(pause)
    except Exception:
        pass
    return None

# --------------------------
# Helpers: Open-Meteo forecast fetch
# --------------------------
def fetch_open_meteo(lat, lon, hours=24, days=7):
    try:
        # hourly (next 48 to be safe) and daily 7
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,weathercode"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
            f"&current_weather=true&forecast_days={days}&timezone=auto"
        )
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            return None
        js = r.json()
        # build pandas structures
        current = js.get("current_weather", {})
        hourly = pd.DataFrame(js.get("hourly", {})) if js.get("hourly") else pd.DataFrame()
        daily = pd.DataFrame(js.get("daily", {})) if js.get("daily") else pd.DataFrame()
        if not hourly.empty and "time" in hourly.columns:
            hourly["time"] = pd.to_datetime(hourly["time"])
        if not daily.empty and "time" in daily.columns:
            daily["time"] = pd.to_datetime(daily["time"]).dt.date
        return {"current": current, "hourly": hourly, "daily": daily}
    except Exception:
        return None

# --------------------------
# Helper: Text to audio (gTTS) returns audio bytes
# --------------------------
def tts_bytes(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None

# --------------------------
# Helper: IP-based auto-location (approximate)
# --------------------------
def ip_geolocate():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=6)
        if r.status_code == 200:
            js = r.json()
            loc = js.get("loc")  # "lat,lon"
            if loc:
                lat, lon = loc.split(",")
                return {"latitude": float(lat), "longitude": float(lon), "city": js.get("city",""), "region": js.get("region",""), "country": js.get("country","")}
    except Exception:
        pass
    return None

# --------------------------
# Sidebar: inputs and controls
# --------------------------
st.sidebar.header("Search & Settings")
city_input = st.sidebar.text_input("Enter city names (comma-separated)", value="Mumbai, Berlin, New York")
max_wait = st.sidebar.slider("Pause between geocoding requests (s)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
enable_voice = st.sidebar.checkbox("Enable voice (gTTS)", value=True)
auto_speak = st.sidebar.checkbox("Auto-speak results after fetch", value=False)
show_hourly = st.sidebar.checkbox("Show hourly (24h) charts", value=True)
show_weekly = st.sidebar.checkbox("Show 7-day forecast", value=True)
use_ip_location = st.sidebar.button("Use my approximate location (IP-based)")

# collect cities
cities = [c.strip() for c in city_input.split(",") if c.strip()]
# allow empty: prompt
if not cities and not use_ip_location:
    st.info("Enter at least one city in the sidebar, or use IP-based location.")
    st.stop()

# If user pressed IP location, geolocate and set city_input to that coordinate
if use_ip_location:
    with st.spinner("Detecting your approximate location via IP..."):
        loc = ip_geolocate()
        if loc:
            st.success(f"Detected approximate location: {loc.get('city','')} {loc.get('region','')} {loc.get('country','')}")
            # override cities with coordinates string (lat,lon)
            cities = [f"{loc['latitude']},{loc['longitude']}"]
        else:
            st.error("Could not detect location via IP. Enter cities manually.")

# Fetch button
if st.sidebar.button("Fetch Weather"):
    st.session_state.pop("results", None)
    st.session_state.pop("failed", None)
    results = []
    failed = []
    with st.spinner("Searching cities and fetching data..."):
        for city in cities:
            # support "lat,lon" direct input
            if "," in city and all(part.strip().replace('.','',1).replace('-','',1).isdigit() for part in city.split(",")[:2]):
                lat = float(city.split(",")[0].strip())
                lon = float(city.split(",")[1].strip())
                place = {"name": f"{lat:.3f},{lon:.3f}", "latitude": lat, "longitude": lon, "country": ""}
            else:
                place = geocode_city(city, pause=max_wait)
            if not place:
                failed.append(city)
                st.warning(f"Could not locate: {city}")
                continue
            # polite pause
            time.sleep(max_wait)
            data = fetch_open_meteo(place["latitude"], place["longitude"], hours=24, days=7)
            if not data:
                failed.append(city)
                st.warning(f"Could not fetch weather for: {city}")
                continue
            # attach place info
            results.append({
                "query": city,
                "place": place,
                "data": data
            })
    st.session_state["results"] = results
    st.session_state["failed"] = failed
    st.experimental_rerun()

# --------------------------
# If we have results, display dashboard
# --------------------------
if "results" in st.session_state and st.session_state["results"]:
    results = st.session_state["results"]
    failed = st.session_state.get("failed", [])

    st.success(f"Loaded weather for {len(results)} place(s).")
    if failed:
        st.warning(f"Failed for: {', '.join(failed)}")

    # Top-level layout: left column for list, right column for map
    left, right = st.columns([1.4, 1])

    # Build a combined map centered on average coords
    try:
        avg_lat = sum([r["place"]["latitude"] for r in results]) / len(results)
        avg_lon = sum([r["place"]["longitude"] for r in results]) / len(results)
    except Exception:
        avg_lat, avg_lon = 0, 0

    # build folium map
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=3, tiles="CartoDB positron")

    # In left column show cards for each city + controls
    with left:
        st.header("📍 City Dashboards")
        for idx, r in enumerate(results):
            p = r["place"]
            d = r["data"]
            cur = d.get("current", {})
            hourly = d.get("hourly", pd.DataFrame())
            daily = d.get("daily", pd.DataFrame())

            # top card (name, basic metrics)
            code = cur.get("weathercode", None)
            icon_key = weathercode_to_key(code)
            icon = ICON_MAP.get(icon_key, ICON_MAP["unknown"])

            st.markdown(f"""
                <div style="background:linear-gradient(120deg, rgba(255,255,255,0.02), rgba(0,0,0,0.03));
                            padding:12px;border-radius:12px;margin-bottom:10px;border-left:6px solid #0ea5a4;">
                    <h3 style="margin:0">{p.get('name')} <small style='opacity:0.7'>{p.get('country','')}</small></h3>
                    <div style="font-size:20px;">{icon} <span style="font-weight:600;margin-left:8px;">{cur.get('temperature','N/A')}°C</span> • Wind {cur.get('windspeed','N/A')} m/s</div>
                    <div style="opacity:0.75;font-size:13px;">Lat: {p['latitude']:.3f} • Lon: {p['longitude']:.3f}</div>
                </div>
            """, unsafe_allow_html=True)

            # metrics in columns
            c1, c2, c3 = st.columns(3)
            c1.metric("🌡️ Temperature (°C)", cur.get("temperature", "N/A"))
            # humidity available only hourly as column "relativehumidity_2m" at same time as current
            humidity = None
            if not hourly.empty and "relativehumidity_2m" in hourly.columns:
                # find hourly row matching current time (closest)
                try:
                    now = pd.to_datetime(cur.get("time"))
                    idx_closest = (hourly["time"] - now).abs().idxmin()
                    humidity = hourly.loc[idx_closest, "relativehumidity_2m"]
                except Exception:
                    humidity = None
            c2.metric("💧 Humidity (%)", humidity if humidity is not None else "N/A")
            c3.metric("💨 Wind (m/s)", cur.get("windspeed", "N/A"))

            # Buttons: speak, show details
            btn_col1, btn_col2 = st.columns([1, 3])
            with btn_col1:
                if enable_voice and st.button(f"🔊 Speak {p.get('name')}", key=f"voice_{idx}"):
                    speak_text = f"Weather in {p.get('name')}. Temperature {cur.get('temperature','unknown')} degrees Celsius. Wind {cur.get('windspeed','unknown')} meters per second."
                    audio_bytes = tts_bytes(speak_text)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.error("Could not generate audio (gTTS failure).")

            with btn_col2:
                with st.expander("📘 Show hourly (24h) and 7-day forecast & charts"):
                    # Hourly table + chart
                    if show_hourly:
                        if hourly is None or hourly.empty:
                            st.info("Hourly data not available.")
                        else:
                            # show next 24 hours from now
                            try:
                                now = pd.Timestamp.now(tz=hourly['time'].dt.tz) if 'time' in hourly.columns else pd.Timestamp.now()
                                next24 = hourly[hourly['time'] >= pd.Timestamp.now(tz=hourly['time'].dt.tz)].head(24) if 'time' in hourly.columns else hourly.head(24)
                            except Exception:
                                next24 = hourly.head(24)
                            if not next24.empty:
                                st.write("Next 24 hours")
                                display_hour = next24[["time", "temperature_2m", "relativehumidity_2m", "windspeed_10m", "weathercode"]].copy() if set(["temperature_2m","relativehumidity_2m","windspeed_10m","weathercode"]).issubset(next24.columns) else next24.head(24)
                                # human-friendly
                                if "time" in display_hour.columns:
                                    display_hour["time"] = display_hour["time"].dt.strftime("%Y-%m-%d %H:%M")
                                st.dataframe(display_hour, use_container_width=True)

                                # chart temperature hourly
                                try:
                                    fig, ax = plt.subplots()
                                    ax.plot(next24["time"], next24["temperature_2m"], marker="o")
                                    ax.set_title(f"Hourly Temp — {p.get('name')}")
                                    ax.set_xlabel("Time")
                                    ax.set_ylabel("°C")
                                    ax.grid(True, alpha=0.3)
                                    st.pyplot(fig)
                                except Exception as e:
                                    st.write("Could not render hourly chart:", e)
                            else:
                                st.info("No upcoming hourly rows available.")

                    # Weekly (7-day)
                    if show_weekly:
                        if daily is None or daily.empty:
                            st.info("Daily forecast not available.")
                        else:
                            st.write("7-day forecast")
                            # create readable dataframe
                            df_daily = daily.copy()
                            # rename columns if present
                            rename_map = {}
                            if "temperature_2m_max" in df_daily.columns: rename_map["temperature_2m_max"]="Max °C"
                            if "temperature_2m_min" in df_daily.columns: rename_map["temperature_2m_min"]="Min °C"
                            if "precipitation_sum" in df_daily.columns: rename_map["precipitation_sum"]="Precip (mm)"
                            if "weathercode" in df_daily.columns: rename_map["weathercode"]="WCode"
                            if "time" in df_daily.columns: rename_map["time"]="Date"
                            disp = df_daily.rename(columns=rename_map)
                            if "Date" in disp.columns:
                                disp["Date"] = pd.to_datetime(disp["Date"]).dt.date
                            st.dataframe(disp, use_container_width=True)

                            # weekly chart
                            try:
                                fig2, ax2 = plt.subplots()
                                if "Max °C" in disp.columns and "Min °C" in disp.columns:
                                    ax2.plot(disp["Date"], disp["Max °C"], marker="o", label="Max °C")
                                    ax2.plot(disp["Date"], disp["Min °C"], marker="o", label="Min °C")
                                elif "temperature_2m_max" in daily.columns:
                                    ax2.plot(df_daily["time"], df_daily["temperature_2m_max"], marker="o", label="Max °C")
                                ax2.set_title(f"7-day Temps — {p.get('name')}")
                                ax2.set_xlabel("Date")
                                ax2.set_ylabel("°C")
                                ax2.legend()
                                ax2.grid(True, alpha=0.3)
                                st.pyplot(fig2)
                            except Exception as e:
                                st.write("Could not render weekly chart:", e)

            # add marker to map for this place
            try:
                popup = folium.Popup(f"<b>{p.get('name')}</b><br>Temp: {cur.get('temperature','N/A')}°C<br>Wind: {cur.get('windspeed','N/A')} m/s", max_width=250)
                folium.Marker([p["latitude"], p["longitude"]], popup=popup, tooltip=p.get("name")).add_to(fmap)
            except Exception:
                pass

            st.markdown("---")

    # in right column, show map and summary visuals
    with right:
        st.header("🗺️ Map & Comparison")
        st_folium(fmap, width=700, height=520)

        # comparison charts: temperature bar across places
        try:
            comp_df = pd.DataFrame([{
                "City": r["place"]["name"],
                "Temperature": r["data"]["current"].get("temperature", None),
                "Wind": r["data"]["current"].get("windspeed", None)
            } for r in results])
            st.subheader("🌡️ Temperature comparison")
            fig3, ax3 = plt.subplots(figsize=(6,3))
            ax3.bar(comp_df["City"], comp_df["Temperature"])
            ax3.set_ylabel("°C")
            ax3.grid(axis="y", alpha=0.3)
            st.pyplot(fig3)

            st.subheader("💨 Wind comparison")
            fig4, ax4 = plt.subplots(figsize=(6,3))
            ax4.bar(comp_df["City"], comp_df["Wind"])
            ax4.set_ylabel("m/s")
            ax4.grid(axis="y", alpha=0.3)
            st.pyplot(fig4)
        except Exception:
            st.info("Comparison charts not available.")

    # optionally auto-speak all
    if enable_voice and auto_speak:
        try:
            speak_all = " . ".join([f"{r['place']['name']}: {r['data']['current'].get('temperature','unknown')} degree C, wind {r['data']['current'].get('windspeed','unknown')} meters per second" for r in results])
            audio = tts_bytes(speak_all)
            if audio:
                st.audio(audio, format="audio/mp3")
        except Exception:
            st.error("Auto-speak failed.")

# If fetch was attempted but nothing succeeded
elif "failed" in st.session_state and st.session_state["failed"]:
    failed_list = st.session_state["failed"]
    if not st.session_state.get("results"):
        st.error("⚠️ Could not fetch weather for any of the entered cities. Please check spelling or add country (e.g., 'Berlin, Germany').")
        st.write("Failed cities:", ", ".join(failed_list))

# Footer help
st.markdown("---")
st.caption("Notes: This app uses Open-Meteo (no API key). IP-based location is approximate. Audio uses gTTS — small delay while generating speech.")
