import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from data_processing import load_and_process_data
from map_utils import create_map
from analysis import generate_distance_matrix, calculate_schools_to_office_distances, extract_distance_statistics
from ui_utils import (
    get_csv_download_link, display_office_statistics, plot_office_distances,
    plot_distance_histogram, create_sample_data
)
from app_config import setup_page_config, setup_custom_css, display_welcome_message, get_color_options

def main():
    """Main Streamlit application"""
    # Setup page configuration
    setup_page_config()
    setup_custom_css()

    st.title("School Facilities Map Analyzer")

    # Upload file
    uploaded_file = st.sidebar.file_uploader("Upload CSV file with school data", type=["csv"])

    if uploaded_file is not None:
        # Process the data
        with st.spinner("Processing data..."):
            df = load_and_process_data(uploaded_file)
            run_analysis(df)
    else:
        # Display welcome message and sample data
        display_welcome_message()
        st.subheader("Example Data Format")
        st.dataframe(create_sample_data())

def run_analysis(df):
    """Run analysis if data is loaded successfully"""
    if df is None or len(df) == 0:
        st.error("No valid data found. Please check your CSV file.")
        return

    # Display success message
    st.sidebar.success(f"Loaded {len(df)} schools with valid coordinates")

    # Distance method selection
    distance_method = st.sidebar.radio(
        "Distance calculation method",
        options=["manhattan", "haversine"],
        index=0,
        help="Manhattan: city block distance, better for urban areas. Haversine: 'as the crow flies' distance."
    )

    # Setup sidebar components
    selected_offices, filtered_df = setup_sidebar_filters(df)
    color_by = setup_color_options()
    show_optimal_offices = st.sidebar.checkbox("Show optimal office locations", value=True)
    selected_schools = select_individual_schools(filtered_df)

    # Create map
    m, office_locations = create_map(
        df=filtered_df,
        education_offices=selected_offices,
        selected_schools=selected_schools,
        show_optimal_offices=show_optimal_offices,
        color_by=color_by,
        distance_method=distance_method
    )

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Map", "Analysis", "Data"])

    with tab1:
        display_map_tab(m)

    with tab2:
        display_analysis_tab(filtered_df, office_locations, selected_schools, distance_method)

    with tab3:
        display_data_tab(filtered_df, office_locations, show_optimal_offices)

def setup_sidebar_filters(df):
    """Setup sidebar filters for education offices"""
    # Data overview
    st.sidebar.header("Data Overview")
    st.sidebar.write(f"Total schools: {len(df)}")

    # Filter by education offices
    selected_offices = []
    if 'standardized_office' in df.columns:
        offices = df['standardized_office'].unique()
        st.sidebar.write(f"Education offices: {len(offices)}")

        st.sidebar.header("Filter Options")
        selected_offices = st.sidebar.multiselect(
            "Select Education Offices",
            options=sorted(offices),
            default=None
        )
    else:
        st.sidebar.warning("Education office column not found in data")

    # Filter data if education offices are selected
    if selected_offices and len(selected_offices) > 0:
        filtered_df = df[df['standardized_office'].isin(selected_offices)]
    else:
        filtered_df = df

    return selected_offices, filtered_df

def setup_color_options():
    """Setup color options for markers"""
    color_options = get_color_options()
    return st.sidebar.selectbox(
        "Color markers by",
        options=list(color_options.keys()),
        format_func=lambda x: color_options[x],
        index=0
    )

def select_individual_schools(filtered_df):
    """Select individual schools for analysis"""
    st.sidebar.header("Select Schools for Distance Analysis")

    if 'اسم المدرسة' in filtered_df.columns:
        school_options = {idx: name for idx, name in zip(filtered_df.index, filtered_df['اسم المدرسة'])}
    else:
        school_options = {idx: f"School #{idx}" for idx in filtered_df.index}

    return st.sidebar.multiselect(
        "Select schools for distance analysis",
        options=list(school_options.keys()),
        format_func=lambda x: school_options[x]
    )

def display_map_tab(m):
    """Display the map tab content"""
    st.header("Interactive Map")
    if m is not None:
        folium_static(m, width=1000, height=600)

        st.markdown("""
        **Map Navigation:**
        - Use the mouse wheel or +/- buttons to zoom in/out
        - Click and drag to move around the map
        - Click on markers to view school details
        - Use the Layer Control (top right) to toggle different layers
        - Use measurement tools (top right) to measure distances on the map
        - Use drawing tools (top left) to draw shapes on the map
        """)
    else:
        st.warning("No map to display. Please check your data and selections.")

def display_analysis_tab(filtered_df, office_locations, selected_schools, distance_method):
    """Display the analysis tab content"""
    st.header("Analysis Results")

    # Display the distance method being used
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"
    st.info(f"Using {method_name} distance for calculations. {get_distance_method_explanation(distance_method)}")

    # Office location analysis
    if office_locations and len(office_locations) > 0:
        st.subheader("Optimal Office Locations")

        # Display office statistics
        office_df = display_office_statistics(office_locations)
        st.dataframe(office_df)

        # Download link for office locations
        st.markdown(get_csv_download_link(office_df, "optimal_office_locations.csv",
                                          "Download Optimal Office Locations"), unsafe_allow_html=True)

        # Plot average distances by office
        fig = plot_office_distances(office_df)
        if fig:
            st.pyplot(fig)

    # Distance matrix analysis
    if selected_schools and len(selected_schools) >= 2:
        st.subheader("Distance Matrix Between Selected Schools")

        # Generate and display distance matrix
        distance_df = generate_distance_matrix(filtered_df, selected_schools, distance_method)
        if distance_df is not None:
            # Format distances for display
            formatted_df = distance_df.applymap(lambda x: f"{x:.2f}" if x > 0 else "-")
            st.dataframe(formatted_df)

            # Download link for distance matrix
            st.markdown(get_csv_download_link(distance_df, "distance_matrix.csv",
                                              f"Download {method_name} Distance Matrix"), unsafe_allow_html=True)

            # Display distance statistics
            display_distance_statistics(distance_df)

def get_distance_method_explanation(distance_method):
    """Return an explanation for the chosen distance method"""
    if distance_method == "manhattan":
        return "Manhattan distance represents city block distance, which is often more realistic for urban travel."
    else:
        return "Haversine distance represents direct 'as the crow flies' distance between points."

def display_distance_statistics(distance_df):
    """Display statistics about distances between schools"""
    st.subheader("Distance Statistics")

    # Extract statistics
    stats = extract_distance_statistics(distance_df)
    if not stats:
        return

    method_name = "Manhattan" if stats['distance_method'] == "manhattan" else "Haversine"

    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(f"Min {method_name} Distance (km)", f"{stats['min_distance']:.2f}")
    with col2:
        st.metric(f"Max {method_name} Distance (km)", f"{stats['max_distance']:.2f}")
    with col3:
        st.metric(f"Avg {method_name} Distance (km)", f"{stats['avg_distance']:.2f}")
    with col4:
        st.metric(f"Total {method_name} Distance (km)", f"{stats['total_distance']:.2f}")

    # Plot histogram
    fig = plot_distance_histogram(stats['distances'], method_name)
    st.pyplot(fig)

def display_data_tab(filtered_df, office_locations, show_optimal_offices):
    """Display the data tab content"""
    st.header("Data Table")

    if len(filtered_df) == 0:
        st.warning("No data to display.")
        return

    # Add distance to optimal office if available
    if show_optimal_offices and 'standardized_office' in filtered_df.columns and office_locations:
        display_data_with_distances(filtered_df, office_locations)
    else:
        # Display the dataframe without distance calculations
        st.dataframe(filtered_df)
        st.markdown(get_csv_download_link(filtered_df, "filtered_schools.csv", "Download Filtered Data"),
                    unsafe_allow_html=True)

def display_data_with_distances(filtered_df, office_locations):
    """Display data with distances to optimal office locations"""
    # Calculate distances from each school to their optimal office location
    enhanced_df = calculate_schools_to_office_distances(filtered_df, office_locations)

    # Get distance method (safely)
    # First, get the method from the first office location
    first_office = next(iter(office_locations.values()))
    distance_method = first_office.get('distance_method', 'manhattan')
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"

    # Display info about distance method
    st.info(f"Distances calculated using {method_name} method")

    # Remove distance_method column before displaying if it exists
    if 'distance_method' in enhanced_df.columns:
        enhanced_df = enhanced_df.drop(columns=['distance_method'])

    # Sort by distance to office
    sort_by_distance = st.checkbox("Sort by distance to optimal office")
    if sort_by_distance:
        enhanced_df = enhanced_df.sort_values(by='Distance to Office (km)', ascending=False)

    # Display the enhanced dataframe
    st.dataframe(enhanced_df)

    # Download link for enhanced data
    st.markdown(get_csv_download_link(enhanced_df, "schools_with_distances.csv",
                                      f"Download Full Data with {method_name} Distances"), unsafe_allow_html=True)

    # Show schools farthest from optimal office
    st.subheader("Schools Farthest from Optimal Office")
    farthest_df = enhanced_df.sort_values(by='Distance to Office (km)', ascending=False).head(10)
    display_columns = ['اسم المدرسة', 'standardized_office', 'Distance to Office (km)']

    # Add optional columns if they exist
    optional_columns = ['المرحلة', 'الجنس', 'الحي']
    for col in optional_columns:
        if col in farthest_df.columns:
            display_columns.append(col)

    st.dataframe(farthest_df[display_columns])

    # Show schools closest to optimal office
    st.subheader("Schools Closest to Optimal Office")
    closest_df = enhanced_df.dropna(subset=['Distance to Office (km)'])
    closest_df = closest_df.sort_values(by='Distance to Office (km)', ascending=True).head(10)
    st.dataframe(closest_df[display_columns])

if __name__ == "__main__":
    main()