import streamlit as st
import folium
import pickle
import requests
import polyline
from datetime import datetime, timedelta
from streamlit_folium import folium_static

# Load ML model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# Google Maps API Key
GOOGLE_MAPS_API_KEY = "AIzaSyD5ELJ03IEUL98JtLBnSN_IKMOHfxOB9Jw"

# Get coordinates for a place
def get_lat_lng(place_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data['status'] == 'OK':
        loc = data['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    else:
        return None, None

# Get directions (all alternate routes)
def get_directions(start, end):
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&mode=driving&alternatives=true&departure_time=now&key={GOOGLE_MAPS_API_KEY}"
    res = requests.get(url)
    data = res.json()
    if data['status'] == 'OK':
        routes = data['routes']
        results = []
        for route in routes:
            poly = polyline.decode(route['overview_polyline']['points'])
            duration_sec = route['legs'][0]['duration_in_traffic']['value']
            results.append({'polyline': poly, 'duration_sec': duration_sec})
        return results
    else:
        return None

# Streamlit UI
st.set_page_config(page_title="AI Smart Car Assistant", layout="wide")
st.title("🚗 AI-Powered Smart Car Assistant")
st.markdown("Suggests **optimal driving routes** using AI + Google Maps.\n")

start_place = st.text_input("📍 Enter Start Location", "Bengaluru Palace")
end_place = st.text_input("📍 Enter Destination", "Chennai Central")

if st.button("🔍 Find Routes"):
    start_lat, start_lng = get_lat_lng(start_place)
    end_lat, end_lng = get_lat_lng(end_place)

    if None in (start_lat, start_lng, end_lat, end_lng):
        st.error("❌ Unable to get coordinates. Please check location names.")
    else:
        # Predict with your ML model
        distance_km = ((start_lat - end_lat)**2 + (start_lng - end_lng)**2)**0.5 * 111
        steps = 10  # Approximate
        predicted_time = model.predict([[distance_km, steps]])[0]
        total_minutes = int(predicted_time)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        time_str = f"{hours} hr {minutes} min" if hours else f"{minutes} min"

        st.subheader("🧠 Trained Model Prediction")
        st.success(f"📊 Estimated Travel Time: **{time_str}**")

        # Directions from Google
        routes = get_directions(start_place, end_place)

        if routes:
            st.subheader("🛣️ Live Route Suggestions from Google")
            route_map = folium.Map(location=[(start_lat + end_lat)/2, (start_lng + end_lng)/2], zoom_start=7)

            folium.Marker([start_lat, start_lng], popup=f"Start: {start_place}", icon=folium.Icon(color="blue")).add_to(route_map)
            folium.Marker([end_lat, end_lng], popup=f"End: {end_place}", icon=folium.Icon(color="red")).add_to(route_map)

            now = datetime.now()

            for i, route in enumerate(routes):
                color = ["green", "orange", "purple"][i % 3]
                folium.PolyLine(locations=route['polyline'], color=color, weight=5, popup=f"Route {i+1}").add_to(route_map)
            
                total_minutes = int(route['duration_sec'] // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                duration_str = f"{hours} hr {minutes} min" if hours else f"{minutes} min"
            
                eta = now + timedelta(seconds=route['duration_sec'])
                eta_str = eta.strftime("%I:%M %p")

                st.markdown(f"### 🛤️ Route {i+1}")
                st.info(f"⏱️ **Live Traffic Duration**: {duration_str}")


            st.subheader("🗺️ Map View with Real Routes")
            folium_static(route_map)
        else:
            st.warning("⚠️ Couldn't fetch routes from Google Directions API.")
