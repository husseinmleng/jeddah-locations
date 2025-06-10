import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from data_processing import load_and_process_data
from map_utils import create_map
from analysis import generate_distance_matrix, extract_distance_statistics
from ui_utils import (
    get_csv_download_link, plot_distance_histogram, create_sample_data
)
from app_config import setup_page_config, setup_custom_css, display_welcome_message, get_color_options

def main():
    """Main Streamlit application"""
    setup_page_config()
    setup_custom_css()

    st.title("School Facilities Map Analyzer")

    uploaded_file = st.sidebar.file_uploader("Upload CSV file with school data", type=["csv"])

    if uploaded_file is not None:
        with st.spinner("Processing data..."):
            df = load_and_process_data(uploaded_file)
            run_analysis(df)
    else:
        display_welcome_message()
        st.subheader("Example Data Format")
        st.dataframe(create_sample_data())

def run_analysis(df):
    """Run analysis if data is loaded successfully"""
    if df is None or len(df) == 0:
        st.error("No valid data found. Please check your CSV file.")
        return

    st.sidebar.success(f"Loaded {len(df)} schools with valid coordinates")

    distance_method = st.sidebar.radio(
        "Distance calculation method",
        options=["manhattan", "haversine"],
        index=0,
        help="Manhattan: city block distance. Haversine: 'as the crow flies' distance."
    )

    # The new filter function returns the final, doubly-filtered dataframe
    filtered_df = setup_sidebar_filters(df)
    
    color_by = setup_color_options()
    show_coverage = st.sidebar.checkbox("Show Neighborhood Coverage", value=True)
    
    # Pass the final filtered df to the school selector
    selected_schools = select_individual_schools(filtered_df)

    # Create map using the final filtered data
    m, _ = create_map(
        df=filtered_df,
        selected_schools=selected_schools,
        color_by=color_by,
        distance_method=distance_method,
        show_coverage_areas=show_coverage
    )

    tab1, tab2, tab3 = st.tabs(["Map", "Analysis", "Data"])

    with tab1:
        display_map_tab(m)
    with tab2:
        display_analysis_tab(filtered_df, selected_schools, distance_method)
    with tab3:
        display_data_tab(filtered_df)

def setup_sidebar_filters(df):
    """
    Setup cascading sidebar filters for Offices and then Neighborhoods.
    Returns the final, filtered DataFrame.
    """
    st.sidebar.header("Data Overview")
    st.sidebar.write(f"Total schools: {len(df)}")
    st.sidebar.header("Filter Options")

    # --- Filter Level 1: Education Office ---
    selected_offices = []
    if 'standardized_office' in df.columns:
        offices = sorted(df['standardized_office'].unique())
        selected_offices = st.sidebar.multiselect(
            "Step 1: Select Education Offices",
            options=offices
        )
    else:
        st.sidebar.warning("Education Office ('مكتب التعليم') column not found.")
        return df # Return original df if no office column

    # --- Filter Level 2: Neighborhood (dependent on Office) ---
    if selected_offices:
        # Create a dataframe filtered ONLY by the selected offices
        office_filtered_df = df[df['standardized_office'].isin(selected_offices)]
        
        # Find which neighborhoods are available within that office selection
        available_neighborhoods = sorted(office_filtered_df['الحي'].unique())
        
        selected_neighborhoods = st.sidebar.multiselect(
            "Step 2: Select Neighborhoods",
            options=available_neighborhoods
        )

        # Determine the final dataframe to return
        if selected_neighborhoods:
            # If user has selected specific neighborhoods, filter further
            final_df = office_filtered_df[office_filtered_df['الحي'].isin(selected_neighborhoods)]
        else:
            # If user has selected offices but no neighborhoods, show all from the offices
            final_df = office_filtered_df
    else:
        # If no offices are selected, show everything
        final_df = df

    return final_df

def setup_color_options():
    """Setup color options for markers"""
    color_options = get_color_options()
    return st.sidebar.selectbox(
        "Color markers by",
        options=list(color_options.keys()),
        format_func=lambda x: color_options[x],
        index=0 # Default to 'neighborhood'
    )

def select_individual_schools(filtered_df):
    """Select individual schools for analysis"""
    st.sidebar.header("Select Schools for Distance Analysis")
    if 'اسم المدرسة' in filtered_df.columns:
        # Ensure the options are from the filtered_df to prevent errors
        school_options = {idx: name for idx, name in zip(filtered_df.index, filtered_df['اسم المدرسة'])}
    else:
        school_options = {idx: f"School #{idx}" for idx in filtered_df.index}

    return st.sidebar.multiselect(
        "Select schools for distance analysis",
        options=list(school_options.keys()),
        format_func=lambda x: school_options.get(x, x) # Use .get for safety
    )

def display_map_tab(m):
    st.header("Interactive Map")
    if m is not None:
        folium_static(m, width=1000, height=600)
        st.markdown("""
        **Map Navigation:**
        - Use the mouse wheel or +/- buttons to zoom in/out
        - Click and drag to move around the map
        - Click on markers to view school details
        - Use the Layer Control (top right) to toggle different layers
        """)
    else:
        st.warning("No map to display. Please check your data and selections.")

def display_analysis_tab(filtered_df, selected_schools, distance_method):
    st.header("Analysis Results")
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"
    st.info(f"Using {method_name} distance for calculations.")

    if not selected_schools or len(selected_schools) < 2:
        st.warning("Please select 2 or more schools from the sidebar to perform a distance analysis.")
        return

    st.subheader("Distance Matrix Between Selected Schools")
    distance_df = generate_distance_matrix(filtered_df, selected_schools, distance_method)
    if distance_df is not None:
        formatted_df = distance_df.applymap(lambda x: f"{x:.2f}" if x > 0 else "-")
        st.dataframe(formatted_df)
        st.markdown(get_csv_download_link(distance_df, "distance_matrix.csv", f"Download {method_name} Distance Matrix"), unsafe_allow_html=True)
        display_distance_statistics(distance_df)

def display_distance_statistics(distance_df):
    st.subheader("Distance Statistics")
    stats = extract_distance_statistics(distance_df)
    if not stats: return
    method_name = "Manhattan" if stats['distance_method'] == "manhattan" else "Haversine"
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric(f"Min {method_name} Distance (km)", f"{stats['min_distance']:.2f}")
    with col2: st.metric(f"Max {method_name} Distance (km)", f"{stats['max_distance']:.2f}")
    with col3: st.metric(f"Avg {method_name} Distance (km)", f"{stats['avg_distance']:.2f}")
    with col4: st.metric(f"Total {method_name} Distance (km)", f"{stats['total_distance']:.2f}")
    fig = plot_distance_histogram(stats['distances'], method_name)
    st.pyplot(fig)

def display_data_tab(filtered_df):
    st.header("Data Table")
    if len(filtered_df) == 0:
        st.warning("No data to display.")
        return
    st.dataframe(filtered_df)
    st.markdown(get_csv_download_link(filtered_df, "filtered_schools.csv", "Download Filtered Data"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()