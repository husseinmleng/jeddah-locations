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
    
    This application helps you visualize and analyze school locations to:
    
    1. **Identify optimal locations** for education offices to serve schools
    2. **Calculate distances** between schools and to proposed office locations
    3. **Analyze school distribution** by education office, level, gender, and type
    
    ## Getting Started:
    
    1. Upload a CSV file containing school data using the uploader in the sidebar
    2. The file should include columns for:
       - School names and details
       - Education office names
       - Latitude and longitude coordinates
    
    The app will automatically process the data and provide interactive visualizations and analysis tools.
    """)

def get_color_options():
    """Return color options for the markers"""
    return {
        'office': 'Education Office',
        'level': 'School Level',
        'gender': 'Gender',
        'type': 'School Type'
    }
