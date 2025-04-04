import streamlit as st
import folium
import pickle
import pandas as pd
from streamlit_folium import folium_static

# Load trained model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# Streamlit UI
st.title("🚗 AI-Powered Smart Car Assistant")
st.subheader("Find the fastest driving route with real-time traffic insights!")

# Input fields
start_lat = st.number_input("Start Latitude", value=12.9716)
start_lng = st.number_input("Start Longitude", value=77.5946)
end_lat = st.number_input("Destination Latitude", value=13.0827)
end_lng = st.number_input("Destination Longitude", value=80.2707)

if st.button("Find Optimal Route"):
    # Predict duration
    distance_km = ((start_lat - end_lat)**2 + (start_lng - end_lng)**2)**0.5 * 111  # Approximate distance
    steps = 10  # Placeholder for step count
    predicted_time = model.predict([[distance_km, steps]])[0]

    st.success(f"🚀 Predicted Travel Time (With Traffic): {predicted_time:.2f} minutes")

    # Display route on map
    route_map = folium.Map(location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2], zoom_start=7)
    folium.Marker([start_lat, start_lng], popup="Start", icon=folium.Icon(color="blue")).add_to(route_map)
    folium.Marker([end_lat, end_lng], popup="Destination", icon=folium.Icon(color="red")).add_to(route_map)
    folium.PolyLine([(start_lat, start_lng), (end_lat, end_lng)], color="green", weight=4).add_to(route_map)
    
    folium_static(route_map)
