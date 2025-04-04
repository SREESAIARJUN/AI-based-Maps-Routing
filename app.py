import streamlit as st
import folium
import pickle
import pandas as pd
import requests
from streamlit_folium import folium_static

# Load trained model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# Google Maps Geocoding API Key
GOOGLE_MAPS_API_KEY = "AIzaSyD5ELJ03IEUL98JtLBnSN_IKMOHfxOB9Jw"

# Geocoding: Convert address to latitude and longitude
def get_lat_lng(place_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data['status'] == 'OK':
        loc = data['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    else:
        return None, None

# Streamlit UI
st.title("🚗 AI-Powered Smart Car Assistant")
st.subheader("Smart route suggestions with AI + Google Maps 🧠🗺️")

# Input locations
start_place = st.text_input("Enter Start Location", value="Bangalore")
end_place = st.text_input("Enter Destination", value="Chennai")

if st.button("Find Optimal Route"):
    # Convert place names to lat/lng
    start_lat, start_lng = get_lat_lng(start_place)
    end_lat, end_lng = get_lat_lng(end_place)

    if None in (start_lat, start_lng, end_lat, end_lng):
        st.error("❌ Failed to get coordinates. Please check the location names.")
    else:
        # Feature engineering
        distance_km = ((start_lat - end_lat) ** 2 + (start_lng - end_lng) ** 2) ** 0.5 * 111
        steps = 10  # Estimate or placeholder for number of turns
        
        predicted_time = model.predict([[distance_km, steps]])[0]
        total_minutes = int(predicted_time)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        time_str = f"{hours} hr {minutes} min" if hours > 0 else f"{minutes} min"
        st.success(f"⏱️ Predicted Travel Time (With Traffic): {time_str}")


        # Visualize route
        route_map = folium.Map(location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2], zoom_start=7)
        folium.Marker([start_lat, start_lng], popup=f"Start: {start_place}", icon=folium.Icon(color="blue")).add_to(route_map)
        folium.Marker([end_lat, end_lng], popup=f"End: {end_place}", icon=folium.Icon(color="red")).add_to(route_map)
        folium.PolyLine([(start_lat, start_lng), (end_lat, end_lng)], color="green", weight=4).add_to(route_map)

        folium_static(route_map)
