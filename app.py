import streamlit as st
import tensorflow as tf
import joblib
import googlemaps
import folium
from streamlit_folium import folium_static
import numpy as np
from datetime import datetime, timedelta
from haversine import haversine
import os
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Page configuration
st.set_page_config(
    page_title="Smart Car Assistant - India",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Google Maps client
gmaps = googlemaps.Client(key='AIzaSyD5ELJ03IEUL98JtLBnSN_IKMOHfxOB9Jw')

# Load model and scaler
@st.cache_resource
def load_models():
    model = tf.keras.models.load_model('results/smart_car_assistant_model.h5')
    scaler = joblib.load('results/scaler.pkl')
    return model, scaler

# Load historical data
@st.cache_data
def load_historical_data():
    return pd.read_csv('results/raw_route_data.csv')

# City information
CITIES = {
    "New Delhi": {"center": [28.6139, 77.2090]},
    "Mumbai": {"center": [19.0760, 72.8777]},
    "Bengaluru": {"center": [12.9716, 77.5946]},
    "Hyderabad": {"center": [17.3850, 78.4867]},
    "Chennai": {"center": [13.0827, 80.2707]},
    "Ahmedabad": {"center": [23.0225, 72.5714]}
}

def get_location_coordinates(location_name, city):
    """Get coordinates for a location using Google Maps Geocoding API"""
    try:
        geocode_result = gmaps.geocode(f"{location_name}, {city}, India")
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        return None
    except Exception as e:
        st.error(f"Error getting coordinates: {str(e)}")
        return None

def get_route_details(start_coords, end_coords, departure_time):
    """Get route details from Google Maps API"""
    try:
        directions = gmaps.directions(
            start_coords,
            end_coords,
            mode="driving",
            departure_time=departure_time,
            alternatives=True
        )
        
        if directions:
            routes = []
            for route in directions:
                leg = route['legs'][0]
                
                duration_in_traffic = leg.get('duration_in_traffic', {}).get('value', 0)
                normal_duration = leg['duration']['value']
                traffic_level = duration_in_traffic / normal_duration if duration_in_traffic > 0 else 1
                
                routes.append({
                    'distance': leg['distance']['value'],
                    'duration': leg['duration']['value'],
                    'duration_in_traffic': duration_in_traffic,
                    'traffic_level': traffic_level,
                    'steps': leg['steps'],
                    'polyline': route['overview_polyline']['points'],
                    'start_location': leg['start_location'],
                    'end_location': leg['end_location']
                })
            
            return routes
        return None
    
    except Exception as e:
        st.error(f"Error getting route details: {str(e)}")
        return None

def create_route_map(start_coords, end_coords, routes):
    """Create an interactive map with route alternatives"""
    try:
        center_lat = (start_coords[0] + end_coords[0]) / 2
        center_lng = (start_coords[1] + end_coords[1]) / 2
        
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=12,
            tiles="cartodbpositron"
        )
        
        # Add markers
        folium.Marker(
            start_coords,
            popup="Start",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)
        
        folium.Marker(
            end_coords,
            popup="End",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        # Add routes with different colors
        colors = ['blue', 'purple', 'orange']
        for i, route in enumerate(routes):
            points = googlemaps.convert.decode_polyline(route['polyline'])
            coordinates = [[point['lat'], point['lng']] for point in points]
            
            # Create route info
            duration_mins = route['duration_in_traffic'] / 60
            distance_km = route['distance'] / 1000
            traffic_status = "Heavy" if route['traffic_level'] > 1.3 else \
                           "Moderate" if route['traffic_level'] > 1.1 else "Light"
            
            route_info = f"""
                Route {i+1}:<br>
                Duration: {duration_mins:.1f} mins<br>
                Distance: {distance_km:.1f} km<br>
                Traffic: {traffic_status}
            """
            
            # Add route to map
            folium.PolyLine(
                coordinates,
                weight=4,
                color=colors[i] if i < len(colors) else 'gray',
                popup=route_info,
                tooltip=f"Route {i+1}"
            ).add_to(m)
        
        return m
    
    except Exception as e:
        st.error(f"Error creating map: {str(e)}")
        return None

def predict_route_duration(features, model, scaler):
    """Predict route duration using the trained model"""
    try:
        scaled_features = scaler.transform(features)
        predicted_duration = model.predict(scaled_features)
        return predicted_duration[0][0]
    except Exception as e:
        st.error(f"Error making prediction: {str(e)}")
        return None

def show_traffic_analysis(historical_data, city):
    """Show traffic analysis for the selected city"""
    try:
        city_data = historical_data[historical_data['city'] == city]
        
        # Traffic patterns by time of day
        fig_time = px.line(
            city_data.groupby('time_of_day')['traffic_level'].mean().reset_index(),
            x='time_of_day',
            y='traffic_level',
            title=f'Traffic Patterns in {city} by Time of Day'
        )
        st.plotly_chart(fig_time)
        
        # Average duration by day of week
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        city_data['day_name'] = city_data['day_of_week'].map(lambda x: days[x])
        
        fig_day = px.box(
            city_data,
            x='day_name',
            y='duration',
            title=f'Journey Durations in {city} by Day of Week'
        )
        st.plotly_chart(fig_day)
        
    except Exception as e:
        st.error(f"Error in traffic analysis: {str(e)}")

def main():
    # Load models and data
    model, scaler = load_models()
    historical_data = load_historical_data()
    
    # Sidebar
    st.sidebar.title("🚗 Navigation Options")
    selected_city = st.sidebar.selectbox("Select City", list(CITIES.keys()))
    
    # Main content
    st.title("🚗 AI-Powered Smart Car Assistant - India")
    st.write("Get optimal driving routes with real-time traffic predictions")
    
    # Input form
    col1, col2 = st.columns(2)
    
    with col1:
        start_location = st.text_input("Start Location", "")
        departure_time = st.time_input("Departure Time", datetime.now())
    
    with col2:
        end_location = st.text_input("End Location", "")
        departure_date = st.date_input("Date", datetime.now())
    
    # Combine date and time
    departure_datetime = datetime.combine(departure_date, departure_time)
    
    if departure_datetime < datetime.now():
        st.warning("Please select a future date and time for accurate traffic predictions.")
        departure_datetime = datetime.now() + timedelta(minutes=5)
    
    if st.button("🔍 Find Optimal Routes"):
        with st.spinner("Calculating optimal routes..."):
            # Get coordinates
            start_coords = get_location_coordinates(start_location, selected_city)
            end_coords = get_location_coordinates(end_location, selected_city)
            
            if start_coords and end_coords:
                # Get route details
                routes = get_route_details(start_coords, end_coords, departure_datetime)
                
                if routes:
                    # Create and display map
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("📍 Route Map")
                        m = create_route_map(start_coords, end_coords, routes)
                        if m:
                            folium_static(m)
                    
                    with col2:
                        st.subheader("🛣️ Route Details")
                        
                        for i, route in enumerate(routes):
                            with st.expander(f"Route {i+1}"):
                                # Calculate features for prediction
                                features = np.array([[
                                    start_coords[0],
                                    start_coords[1],
                                    end_coords[0],
                                    end_coords[1],
                                    route['traffic_level'],
                                    departure_datetime.hour,
                                    1 if (departure_datetime.hour >= 8 and departure_datetime.hour <= 11) or \
                                       (departure_datetime.hour >= 17 and departure_datetime.hour <= 20) else 0,
                                    1 if departure_datetime.weekday() >= 5 else 0,
                                    route['distance']/1000,
                                    haversine(start_coords, end_coords),
                                    route['distance']/(haversine(start_coords, end_coords)*1000),
                                    list(CITIES.keys()).index(selected_city),
                                    1 if route['traffic_level'] > 1.3 else 0
                                ]])
                                
                                # Make prediction
                                predicted_duration = predict_route_duration(features, model, scaler)
                                
                                # Display metrics
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.metric(
                                        "Distance",
                                        f"{route['distance']/1000:.1f} km"
                                    )
                                    st.metric(
                                        "Current Duration",
                                        f"{route['duration_in_traffic']/60:.1f} mins"
                                    )
                                
                                with col2:
                                    traffic_status = "Heavy" if route['traffic_level'] > 1.3 else \
                                                   "Moderate" if route['traffic_level'] > 1.1 else "Light"
                                    st.metric(
                                        "Traffic Level",
                                        traffic_status
                                    )
                                    if predicted_duration:
                                        st.metric(
                                            "AI Prediction",
                                            f"{predicted_duration:.1f} mins"
                                        )
                    
                    # Show traffic analysis
                    st.subheader("📊 Traffic Analysis")
                    show_traffic_analysis(historical_data, selected_city)
                
                else:
                    st.error("Could not find any routes between the specified locations.")
            
            else:
                st.error("Could not find coordinates for the specified locations.")

if __name__ == "__main__":
    main()
