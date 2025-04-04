import streamlit as st
import folium
import pickle
import requests
import polyline
from streamlit_folium import folium_static

# Load trained ML model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# Google Maps API Key (Replace with your key)
GOOGLE_MAPS_API_KEY = "AIzaSyD5ELJ03IEUL98JtLBnSN_IKMOHfxOB9Jw"

# Convert place name to latitude and longitude
def get_lat_lng(place_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data['status'] == 'OK':
        loc = data['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    else:
        return None, None

# Get driving directions (polyline route)
def get_directions(start, end):
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&mode=driving&key={GOOGLE_MAPS_API_KEY}"
    res = requests.get(url)
    data = res.json()
    if data['status'] == 'OK':
        steps_polyline = data['routes'][0]['overview_polyline']['points']
        return polyline.decode(steps_polyline)
    else:
        return None

# UI
st.set_page_config(page_title="AI-Powered Smart Car Assistant", layout="wide")
st.title("🚗 AI-Powered Smart Car Assistant")
st.write("Get **optimal driving routes** and estimated time with AI + Google Maps.")

# Inputs
start_place = st.text_input("📍 Enter Start Location", "Gachibowli, Hyderabad")
end_place = st.text_input("📍 Enter Destination", "Chennai Central")

if st.button("🔍 Find Optimal Route"):
    start_lat, start_lng = get_lat_lng(start_place)
    end_lat, end_lng = get_lat_lng(end_place)

    if None in (start_lat, start_lng, end_lat, end_lng):
        st.error("❌ Couldn't fetch location coordinates. Check the place names.")
    else:
        # Feature engineering
        distance_km = ((start_lat - end_lat) ** 2 + (start_lng - end_lng) ** 2) ** 0.5 * 111  # rough estimate
        steps = 10  # Static or calculated if directions API provides it

        # Predict duration (minutes)
        predicted_time = model.predict([[distance_km, steps]])[0]
        total_minutes = int(predicted_time)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        time_str = f"{hours} hr {minutes} min" if hours > 0 else f"{minutes} min"

        # Show prediction
        st.success(f"⏱️ Predicted Travel Time (with traffic): **{time_str}**")

        # Get realistic driving route
        route_coords = get_directions(start_place, end_place)

        if route_coords:
            # Map setup
            route_map = folium.Map(location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2], zoom_start=7)

            folium.Marker([start_lat, start_lng], popup=f"Start: {start_place}", icon=folium.Icon(color="blue")).add_to(route_map)
            folium.Marker([end_lat, end_lng], popup=f"End: {end_place}", icon=folium.Icon(color="red")).add_to(route_map)
            folium.PolyLine(locations=route_coords, color="green", weight=5).add_to(route_map)

            st.subheader("🗺️ Route Map")
            folium_static(route_map)
        else:
            st.warning("⚠️ Couldn't retrieve route from Google Directions API.")
