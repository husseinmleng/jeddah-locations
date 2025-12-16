import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from data_processing import load_and_process_data
from map_utils import create_map
from analysis import (
    generate_distance_matrix, extract_distance_statistics,
    generate_centroid_distance_table, extract_centroid_statistics
)
from ui_utils import (
    get_csv_download_link, plot_distance_histogram, create_sample_data
)
from app_config import setup_page_config, setup_custom_css, display_welcome_message, get_color_options

def main():
    """Main Streamlit application"""
    setup_page_config()
    setup_custom_css()

    st.title("School Facilities Map Analyzer")

    uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file with school data", type=["csv", "xls", "xlsx"])

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
    show_coverage = st.sidebar.checkbox(
        "Show Neighborhood Coverage Areas",
        value=False,
        help="Display coverage circles around neighborhoods (can be visually busy)"
    )

    # Add checkbox for zone centroid distances (only if zone column exists)
    show_centroid_distances = False
    if 'الزون' in filtered_df.columns:
        show_centroid_distances = st.sidebar.checkbox(
            "Show Zone Centroid Distances",
            value=False,
            help="Display distance lines from all schools to their zone centroids"
        )

    # Pass the final filtered df to the school selector
    selected_schools = select_individual_schools(filtered_df)

    # Create map using the final filtered data
    m, zone_centroids = create_map(
        df=filtered_df,
        selected_schools=selected_schools,
        color_by=color_by,
        distance_method=distance_method,
        show_coverage_areas=show_coverage,
        show_centroid_distances=show_centroid_distances
    )

    tab1, tab2, tab3 = st.tabs(["Map", "Analysis", "Data"])

    with tab1:
        display_map_tab(m)
    with tab2:
        display_analysis_tab(filtered_df, selected_schools, distance_method, zone_centroids)
    with tab3:
        display_data_tab(filtered_df)

def setup_sidebar_filters(df):
    """
    Setup cascading sidebar filters.
    If 'الزون' exists: Zone -> Neighborhood
    Otherwise: Education Office -> Neighborhood
    Returns the final, filtered DataFrame.
    """
    st.sidebar.header("Data Overview")
    st.sidebar.write(f"Total schools: {len(df)}")
    st.sidebar.header("Filter Options")

    # Check which filtering mode to use
    has_zones = 'الزون' in df.columns
    has_offices = 'standardized_office' in df.columns

    if has_zones:
        # --- Zone-based filtering ---
        zones = sorted(df['الزون'].unique())
        selected_zones = st.sidebar.multiselect(
            "Step 1: Select Zones",
            options=zones,
            help="Select one or more zones (G1, G2, G3, G4, G5)"
        )

        if selected_zones:
            # Filter by selected zones
            zone_filtered_df = df[df['الزون'].isin(selected_zones)]

            # Get neighborhoods available in selected zones
            if 'الحي' in zone_filtered_df.columns:
                available_neighborhoods = sorted(zone_filtered_df['الحي'].unique())

                selected_neighborhoods = st.sidebar.multiselect(
                    "Step 2: Select Neighborhoods",
                    options=available_neighborhoods,
                    help="Select neighborhoods within the selected zones"
                )

                if selected_neighborhoods:
                    final_df = zone_filtered_df[zone_filtered_df['الحي'].isin(selected_neighborhoods)]
                else:
                    final_df = zone_filtered_df
            else:
                final_df = zone_filtered_df
        else:
            final_df = df

    elif has_offices:
        # --- Office-based filtering (original logic) ---
        offices = sorted(df['standardized_office'].unique())
        selected_offices = st.sidebar.multiselect(
            "Step 1: Select Education Offices",
            options=offices
        )

        if selected_offices:
            office_filtered_df = df[df['standardized_office'].isin(selected_offices)]

            if 'الحي' in office_filtered_df.columns:
                available_neighborhoods = sorted(office_filtered_df['الحي'].unique())

                selected_neighborhoods = st.sidebar.multiselect(
                    "Step 2: Select Neighborhoods",
                    options=available_neighborhoods
                )

                if selected_neighborhoods:
                    final_df = office_filtered_df[office_filtered_df['الحي'].isin(selected_neighborhoods)]
                else:
                    final_df = office_filtered_df
            else:
                final_df = office_filtered_df
        else:
            final_df = df
    else:
        st.sidebar.warning("No filtering columns found (Zone or Education Office).")
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

def display_analysis_tab(filtered_df, selected_schools, distance_method, zone_centroids):
    st.header("Analysis Results")
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"
    st.info(f"Using {method_name} distance for calculations.")

    # Display Zone Centroid Analysis if available
    if zone_centroids and 'الزون' in filtered_df.columns:
        st.subheader("Zone Centroid Analysis")

        # Display statistics per zone
        centroid_stats = extract_centroid_statistics(zone_centroids)
        if centroid_stats:
            st.write("**Summary Statistics by Zone:**")

            # Create a summary table
            summary_data = []
            for zone in sorted(centroid_stats.keys()):
                stats = centroid_stats[zone]
                summary_data.append({
                    'Zone': zone,
                    'Total Schools': stats['total_schools'],
                    'Outliers': stats['outliers'],
                    'Avg Distance (km)': f"{stats['avg_distance']:.2f}",
                    'Median Distance (km)': f"{stats['median_distance']:.2f}",
                    'Max Distance (km)': f"{stats['max_distance']:.2f}"
                })

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)

        # Display detailed distance table
        st.write("**Distance from Each School to Zone Centroid:**")
        centroid_distance_df = generate_centroid_distance_table(filtered_df, zone_centroids, distance_method)
        if centroid_distance_df is not None:
            st.dataframe(centroid_distance_df, use_container_width=True)
            st.markdown(
                get_csv_download_link(
                    centroid_distance_df,
                    "centroid_distances.csv",
                    "Download Centroid Distance Table"
                ),
                unsafe_allow_html=True
            )

        st.markdown("---")

    # Display school-to-school distance analysis
    st.subheader("Distance Matrix Between Selected Schools")
    if not selected_schools or len(selected_schools) < 2:
        st.warning("Please select 2 or more schools from the sidebar to perform a distance analysis.")
        return

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