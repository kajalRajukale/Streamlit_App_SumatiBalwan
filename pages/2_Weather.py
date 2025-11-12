import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Weather Dashboard", page_icon="☀️", layout="centered")
st.title("🌤️ Weather Dashboard")

st.write("Enter one or more city names separated by commas (e.g. `Pune, Mumbai, Delhi`)")

# --- Input multiple cities ---
cities_input = st.text_input("Cities", value="Pune, Mumbai, Delhi")

if st.button("Show Weather"):
    cities = [c.strip() for c in cities_input.split(",") if c.strip()]
    all_weather = []
    map_points = []

    # --- Weather code legend ---
    weather_codes = {
        0: "☀️ Clear sky",
        1: "🌤️ Mainly clear",
        2: "⛅ Partly cloudy",
        3: "☁️ Overcast",
        45: "🌫️ Fog",
        48: "🌫️ Rime fog",
        51: "🌦️ Drizzle",
        61: "🌧️ Light rain",
        71: "❄️ Snow fall",
        95: "⛈️ Thunderstorm",
    }

    for city in cities:
        try:
            # Step 1: Get coordinates
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
            geo_res = requests.get(geo_url).json()

            if "results" not in geo_res or len(geo_res["results"]) == 0:
                st.warning(f"⚠️ City not found: {city}")
                continue

            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            city_name = geo_res["results"][0]["name"]
            country = geo_res["results"][0].get("country", "")

            # Step 2: Get weather
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,wind_speed_10m,weathercode"
                f"&timezone=auto"
            )
            weather_res = requests.get(url).json()
            current = weather_res.get("current", {})

            code = current.get("weathercode", 0)
            condition = weather_codes.get(code, "Unknown")
            emoji = condition.split(" ")[0] if condition != "Unknown" else "❓"

            # Save for table + map
            all_weather.append({
                "City": city_name,
                "Country": country,
                "Temp (°C)": current.get("temperature_2m"),
                "Wind (km/h)": current.get("wind_speed_10m"),
                "Condition": condition
            })

            map_points.append({
                "lat": lat,
                "lon": lon,
                "icon": emoji,
                "label": f"{city_name}: {condition}"
            })

        except Exception as e:
            st.error(f"❌ Error loading {city}: {e}")

    # --- If we have data ---
    if all_weather:
        st.subheader("📊 Summary of Cities")
        st.dataframe(pd.DataFrame(all_weather))

        # --- 🗺️ Map with Icons ---
        st.subheader("🗺️ City Weather Map")

        map_df = pd.DataFrame(map_points)

        icon_layer = pdk.Layer(
            "TextLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_text="icon",
            get_color=[255, 165, 0],
            get_size=32,
            size_scale=1.5,
        )

        label_layer = pdk.Layer(
            "TextLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_text="label",
            get_color=[0, 0, 0],
            get_size=16,
            size_scale=1.0,
            get_alignment_baseline="'bottom'"
        )

        view_state = pdk.ViewState(latitude=20.59, longitude=78.96, zoom=4, pitch=0)
        st.pydeck_chart(pdk.Deck(layers=[icon_layer, label_layer], initial_view_state=view_state))

        # --- Select one city for detailed 2-week forecast ---
        st.subheader("📅 Detailed Forecast (Select a City)")
        selected_city = st.selectbox("Choose a city", [c["City"] for c in all_weather])

        # Find lat/lon again for that city
        for p in map_points:
            if p["label"].startswith(selected_city):
                lat, lon = p["lat"], p["lon"]
                break

        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration"
            f"&timezone=auto&forecast_days=14"
        )
        forecast_res = requests.get(forecast_url).json()

        daily = forecast_res.get("daily", {})
        df = pd.DataFrame({
            "Date": daily["time"],
            "Max Temp (°C)": daily["temperature_2m_max"],
            "Min Temp (°C)": daily["temperature_2m_min"],
            "Rain (mm)": daily["precipitation_sum"],
            "Sunshine (s)": daily["sunshine_duration"]
        })

        st.dataframe(df.style.format({"Sunshine (s)": "{:.0f}"}))
        st.line_chart(df.set_index("Date")[["Max Temp (°C)", "Min Temp (°C)"]])
        st.bar_chart(df.set_index("Date")[["Rain (mm)"]])

st.info("Data from [Open-Meteo API](https://open-meteo.com) — Free & No API key required.")
