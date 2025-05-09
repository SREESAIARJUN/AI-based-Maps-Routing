import streamlit as st
import folium
import pickle
import requests
import polyline
import os
import time
from datetime import datetime, timedelta
from streamlit_folium import folium_static

# Page configuration
st.set_page_config(
    page_title="AI Smart Car Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern dark theme CSS
st.markdown("""
<style>
    /* Base theme - dark mode */
    .stApp {
        background-color: #0f1117;
        color: #e0e0e0;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #e0e0e0 !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Main header */
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        color: #2196F3 !important;
        margin-bottom: 0;
        padding-bottom: 0;
        line-height: 1.2;
    }
    
    /* Subtitle */
    .subtitle {
        font-size: 1rem;
        color: #9e9e9e !important;
        margin-top: 0;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        font-size: 1.5rem;
        color: #e0e0e0 !important;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .section-header svg {
        margin-right: 0.5rem;
    }
    
    /* Input fields */
    .stTextInput > div > div {
        background-color: #1a1f2c !important;
        color: #e0e0e0 !important;
        border-radius: 8px !important;
        border: 1px solid #2d3748 !important;
    }
    
    .stTextInput > label {
        color: #e0e0e0 !important;
        font-weight: 500 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #2196F3 !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        width: 100% !important;
        height: 2.5rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #1976D2 !important;
        box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3) !important;
    }
    
    /* Route cards */
    .route-card {
        background-color: #1a1f2c;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #2196F3;
    }
    
    /* Prediction card */
    .prediction-card {
        background-color: rgba(33, 150, 243, 0.1);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid rgba(33, 150, 243, 0.3);
    }
    
    /* Info text */
    .info-text {
        color: #9e9e9e;
        font-size: 0.9rem;
    }
    
    /* Highlight text */
    .highlight {
        font-weight: 600;
        color: #2196F3;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #2196F3 !important;
    }
    
    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #9e9e9e;
        font-size: 0.8rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #2d3748;
    }
    
    /* Location icon */
    .location-icon {
        color: #f06292;
        margin-right: 0.5rem;
    }
    
    /* Input container */
    .input-container {
        margin-bottom: 1rem;
    }
    
    /* Map container */
    .map-container {
        border-radius: 8px;
        overflow: hidden;
        margin-top: 1rem;
    }
    
    /* Route metrics */
    .route-metrics {
        display: flex;
        justify-content: space-between;
        margin-top: 0.5rem;
    }
    
    .metric {
        display: flex;
        align-items: center;
    }
    
    .metric-icon {
        margin-right: 0.3rem;
        color: #2196F3;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom divider */
    .divider {
        height: 1px;
        background-color: #2d3748;
        margin: 1.5rem 0;
    }
    
    /* Spinner */
    .stSpinner > div > div {
        border-top-color: #2196F3 !important;
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
    
    # Application header with car icon
    st.markdown("""
    <div style="display: flex; align-items: center;">
        <span style="font-size: 2rem; margin-right: 0.5rem;">🚗</span>
        <h1 class="main-header">AI-Powered Smart Car Assistant</h1>
    </div>
    <p class="subtitle">Suggests optimal driving routes using AI + Google Maps</p>
    """, unsafe_allow_html=True)
    
    # Create two columns for input
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        st.markdown('<span class="location-icon">📍</span> Enter Start Location', unsafe_allow_html=True)
        start_place = st.text_input("", "India Gate", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        st.markdown('<span class="location-icon">📍</span> Enter Destination', unsafe_allow_html=True)
        end_place = st.text_input(" ", "Taj Mahal", label_visibility="collapsed")
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
            st.markdown('<div class="section-header">🧠 AI Model Prediction</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="prediction-card">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 0.5rem;">📊</span>
                    <span>Estimated Travel Time: <span class="highlight">{time_str}</span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display routes
            st.markdown('<div class="section-header">🛣️ Live Route Suggestions</div>', unsafe_allow_html=True)
            
            # Create map - KEEPING THE ORIGINAL MAP STYLE
            route_map = folium.Map(
                location=[(start_lat + end_lat)/2, (start_lng + end_lng)/2],
                zoom_start=7
            )
            
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
            
            # Route colors - using bright colors that stand out on the default map
            route_colors = ["#2196F3", "#00BCD4", "#4CAF50", "#FFC107", "#FF5722"]
            
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
                st.markdown(f"""
                <div class="route-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0;">🛤️ Route {i+1}: {route['summary']}</h4>
                        <span class="highlight">{duration_str}</span>
                    </div>
                    <div class="route-metrics">
                        <div class="metric">
                            <span class="metric-icon">🕒</span>
                            <span>ETA: {eta_str}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-icon">📏</span>
                            <span>Distance: {distance_km:.1f} km</span>
                        </div>
                        <div class="metric">
                            <span class="metric-icon">🚦</span>
                            <span>Steps: {route['steps']}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Display map
            st.markdown('<div class="section-header">🗺️ Interactive Map</div>', unsafe_allow_html=True)
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            folium_static(route_map, width=1320)
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"An error occurred during processing: {str(e)}")
    
    # Add footer with information
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="footer">
        <p>AI Smart Car Assistant uses machine learning and Google Maps API to provide route suggestions.</p>
        <p>© 2023 AI Smart Car Assistant</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
