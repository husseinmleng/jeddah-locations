import streamlit as st

def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="School Facilities Map Analyzer",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def setup_custom_css():
    """Add custom CSS to the Streamlit app"""
    st.markdown("""
    <style>
        .main .block-container {padding-top: 2rem;}
        .css-18e3th9 {padding-top: 1rem;}
        .css-1d391kg {padding-top: 1rem;}
        h1, h2, h3 {margin-top: 0.5rem;}
        .stSelectbox label, .stMultiSelect label {font-size: 16px; font-weight: bold;}
        .sidebar .sidebar-content {background-color: #f8f9fa;}
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 12px;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
        }
        .metric-title {font-size: 14px; color: #555;}
        .metric-value {font-size: 24px; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

def display_welcome_message():
    """Display welcome message when no file is uploaded"""
    st.markdown("""
    # Welcome to the School Facilities Map Analyzer

    This application helps you visualize and analyze school locations.

    ## How it Works:

    1. **Use the Cascading Filters** in the sidebar:
        - **Zone-based files**: First, select one or more **Zones (الزون)**, then filter by **Neighborhoods** within those zones.
        - **Office-based files**: First, select one or more **Education Offices**, then filter by **Neighborhoods**.
    2. The map will display schools with customizable markers (color by Zone, Neighborhood, Level, Gender, or Type).
    3. You can toggle **Neighborhood Coverage** circles and switch between different map views (Satellite, Light, Dark).
    4. **Select individual schools** to calculate distances between them.

    ## Getting Started:

    1. Upload a CSV or Excel file (.csv, .xls, .xlsx) with your school data.
    2. The file should include:
       - Coordinate columns: `خط العرض` (latitude), `خط الطول` (longitude)
       - For zone-based filtering: `الزون` and `العنوان` (neighborhood/address)
       - For office-based filtering: `مكتب التعليم` and `الحي` (neighborhood)
    """)

def get_color_options():
    """Return color options for the markers"""
    return {
        'zone': 'الزون (Zone)',
        'neighborhood': 'الحي (Neighborhood)',
        'level': 'School Level',
        'gender': 'Gender',
        'type': 'School Type'
    }