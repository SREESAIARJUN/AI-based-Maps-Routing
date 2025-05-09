import streamlit as st
import folium
import pickle
import requests
import polyline
import os
import time
from datetime import datetime, timedelta
from streamlit_folium import folium_static

# Page configuration with improved styling
st.set_page_config(
    page_title="AI Smart Car Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #424242;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .route-card {
        background-color: #f1f8e9;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #7cb342;
    }
    .info-text {
        color: #424242;
        font-size: 1rem;
    }
    .highlight {
        font-weight: bold;
        color: #1E88E5;
    }
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .success-message {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Function to load ML model with error handling
@st.cache_resource
def load_model():
    try:
        with open("model.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        st.error("Model file not found. Please ensure 'model.pkl' exists in the application directory.")
        return None
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

# Google Maps API Key - Securely handled
def get_api_key():
    # In production, use st.secrets or environment variables
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "AIzaSyD5ELJ03IEUL98JtLBnSN_IKMOHfxOB9Jw")
    return api_key

# Get coordinates for a place with improved error handling
def get_lat_lng(place_name):
    if not place_name:
        return None, None
    
    try:
        api_key = get_api_key()
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        if data['status'] == 'OK':
            loc = data['results'][0]['geometry']['location']
            return loc['lat'], loc['lng']
        else:
            st.error(f"Geocoding error: {data['status']}. Please check the location name.")
            return None, None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {str(e)}")
        return None, None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None, None

# Get directions with improved error handling
def get_directions(start, end):
    try:
        api_key = get_api_key()
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&mode=driving&alternatives=true&departure_time=now&key={api_key}"
        
        with st.spinner("Fetching routes from Google Maps..."):
            res = requests.get(url, timeout=15)
            res.raise_for_status()
        
        data = res.json()
        if data['status'] == 'OK':
            routes = data['routes']
            results = []
            for route in routes:
                poly = polyline.decode(route['overview_polyline']['points'])
                duration_sec = route['legs'][0]['duration_in_traffic']['value'] if 'duration_in_traffic' in route['legs'][0] else route['legs'][0]['duration']['value']
                distance_m = route['legs'][0]['distance']['value']
                
                # Extract additional useful information
                steps = len(route['legs'][0]['steps'])
                summary = route['summary']
                
                results.append({
                    'polyline': poly, 
                    'duration_sec': duration_sec,
                    'distance_m': distance_m,
                    'steps': steps,
                    'summary': summary
                })
            return results
        else:
            st.error(f"Directions API error: {data['status']}. Please check your inputs.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error while fetching directions: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

# Format duration nicely
def format_duration(seconds):
    total_minutes = int(seconds // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours} hr {minutes} min" if hours else f"{minutes} min"

# Main application
def main():
    # Load model
    model = load_model()
    if model is None:
        st.stop()
    
    # Application header
    st.markdown('<div class="main-header">🚗 AI-Powered Smart Car Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Suggests optimal driving routes using AI + Google Maps</div>', unsafe_allow_html=True)
    
    # Create two columns for input
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        start_place = st.text_input("📍 Enter Start Location", "Bengaluru Palace")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        end_place = st.text_input("📍 Enter Destination", "Chennai Central")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Search button
    if st.button("🔍 Find Optimal Routes"):
        if not start_place or not end_place:
            st.error("Please enter both start and destination locations.")
            st.stop()
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Get coordinates
        status_text.text("Getting location coordinates...")
        progress_bar.progress(10)
        start_lat, start_lng = get_lat_lng(start_place)
        progress_bar.progress(20)
        end_lat, end_lng = get_lat_lng(end_place)
        progress_bar.progress(30)
        
        if None in (start_lat, start_lng, end_lat, end_lng):
            st.error("❌ Unable to get coordinates. Please check location names.")
            st.stop()
        
        # Step 2: ML prediction
        status_text.text("Making AI predictions...")
        progress_bar.progress(40)
        
        try:
            # Calculate straight-line distance in km
            distance_km = ((start_lat - end_lat)**2 + (start_lng - end_lng)**2)**0.5 * 111
            steps = 10  # Approximate
            predicted_time = model.predict([[distance_km, steps]])[0]
            total_minutes = int(predicted_time)
            time_str = format_duration(total_minutes * 60)
            
            progress_bar.progress(60)
            
            # Step 3: Get Google directions
            status_text.text("Fetching live traffic data...")
            routes = get_directions(start_place, end_place)
            progress_bar.progress(80)
            
            if not routes:
                st.warning("⚠️ Couldn't fetch routes from Google Directions API.")
                st.stop()
            
            # Step 4: Display results
            status_text.text("Preparing results...")
            progress_bar.progress(100)
            time.sleep(0.5)  # Small delay for UX
            status_text.empty()
            progress_bar.empty()
            
            # Display AI prediction
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🧠 AI Model Prediction")
            st.markdown(f"<div class='success-message'>📊 Estimated Travel Time: <span class='highlight'>{time_str}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Display routes
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🛣️ Live Route Suggestions")
            
            # Create map
            route_map = folium.Map(location=[(start_lat + end_lat)/2, (start_lng + end_lng)/2], zoom_start=7)
            
            # Add markers
            folium.Marker(
                [start_lat, start_lng], 
                popup=f"Start: {start_place}", 
                tooltip=start_place,
                icon=folium.Icon(color="blue", icon="play", prefix="fa")
            ).add_to(route_map)
            
            folium.Marker(
                [end_lat, end_lng], 
                popup=f"End: {end_place}", 
                tooltip=end_place,
                icon=folium.Icon(color="red", icon="stop", prefix="fa")
            ).add_to(route_map)
            
            # Current time
            now = datetime.now()
            
            # Route colors
            route_colors = ["green", "orange", "purple", "blue", "red"]
            
            # Display routes
            for i, route in enumerate(routes):
                color = route_colors[i % len(route_colors)]
                
                # Add route to map
                folium.PolyLine(
                    locations=route['polyline'], 
                    color=color, 
                    weight=5, 
                    popup=f"Route {i+1}: {route['summary']}"
                ).add_to(route_map)
                
                # Format duration
                duration_str = format_duration(route['duration_sec'])
                
                # Calculate ETA
                eta = now + timedelta(seconds=route['duration_sec'])
                eta_str = eta.strftime("%I:%M %p")
                
                # Calculate distance in km
                distance_km = route['distance_m'] / 1000
                
                # Display route information
                st.markdown(f'<div class="route-card">', unsafe_allow_html=True)
                st.markdown(f"#### 🛤️ Route {i+1}: {route['summary']}")
                
                # Create columns for route details
                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1:
                    st.markdown(f"⏱️ **Duration**: {duration_str}")
                with r_col2:
                    st.markdown(f"🕒 **ETA**: {eta_str}")
                with r_col3:
                    st.markdown(f"📏 **Distance**: {distance_km:.1f} km")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Display map
            st.subheader("🗺️ Interactive Map")
            folium_static(route_map)
            st.markdown("</div>", unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"An error occurred during processing: {str(e)}")
    
    # Add footer with information
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>AI Smart Car Assistant uses machine learning and Google Maps API to provide route suggestions.</p>
        <p>© 2023 AI Smart Car Assistant</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
