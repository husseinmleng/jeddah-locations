import pandas as pd
import numpy as np
import streamlit as st
import folium
from folium.plugins import MarkerCluster, MeasureControl, Draw
from streamlit_folium import folium_static
import re
from itertools import combinations
from folium.features import DivIcon
from math import sin, cos, sqrt, atan2, radians
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="School Facilities Map Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve UI appearance
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

# Function to calculate distance between two points using Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on earth (specified in decimal degrees)"""
    # Approximate radius of earth in km
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    # Differences
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance  # in kilometers
def standardize_office_name(name):
    """Standardize education office names by removing gender suffixes and normalizing prefixes"""
    if pd.isna(name):
        return "Unknown"

    # Convert to string
    name = str(name)

    # Remove gender suffixes like "- بنين" or "- بنات"
    name = re.sub(r'-\s*بنين$', '', name)
    name = re.sub(r'-\s*بنات$', '', name)
    name = name.replace('بال', 'ال')
    name = name.replace('التعليم', 'تعليم')
    name = name.replace('بر','ر')
    name = name.replace('بأ','أ')
    name = name.replace('بخ','خ')

# Remove any trailing whitespace
    name = name.strip()

    return name

# Function to calculate optimal office location (mean center) and find closest/farthest schools
def calculate_optimal_location(df):
    """Calculate the optimal location (mean center) and find closest/farthest schools"""
    # Simple approach: calculate mean center
    center_lat = df['latitude'].mean()
    center_lng = df['longitude'].mean()

    # Find closest and farthest schools
    min_distance = float('inf')
    max_distance = 0
    closest_school = None
    farthest_school = None

    for idx, row in df.iterrows():
        dist = calculate_distance(center_lat, center_lng, row['latitude'], row['longitude'])

        if dist < min_distance:
            min_distance = dist
            closest_school = row.get('اسم المدرسة', f"School #{idx}")
            closest_school_idx = idx
            closest_school_coords = (row['latitude'], row['longitude'])

        if dist > max_distance:
            max_distance = dist
            farthest_school = row.get('اسم المدرسة', f"School #{idx}")
            farthest_school_idx = idx
            farthest_school_coords = (row['latitude'], row['longitude'])

    # Calculate statistics for all schools
    total_distance = 0
    for _, row in df.iterrows():
        dist = calculate_distance(center_lat, center_lng, row['latitude'], row['longitude'])
        total_distance += dist

    average_distance = total_distance / len(df) if len(df) > 0 else 0

    return {
        'center_lat': center_lat,
        'center_lng': center_lng,
        'total_distance': total_distance,
        'average_distance': average_distance,
        'min_distance': min_distance,
        'max_distance': max_distance,
        'closest_school': closest_school,
        'closest_school_idx': closest_school_idx,
        'closest_school_coords': closest_school_coords,
        'farthest_school': farthest_school,
        'farthest_school_idx': farthest_school_idx,
        'farthest_school_coords': farthest_school_coords
    }

# Function to convert data frame to CSV download link
def get_csv_download_link(df, filename="data.csv", text="Download CSV"):
    """Generate a download link for a dataframe as CSV"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Function to generate distance matrix between schools
def generate_distance_matrix(df, selected_schools=None):
    """Generate a distance matrix between selected schools"""
    if selected_schools is None or len(selected_schools) < 2:
        return None

    # Filter dataframe to only include selected schools
    school_df = df.loc[selected_schools]

    # Create empty distance matrix
    n = len(school_df)
    distance_matrix = np.zeros((n, n))

    # Calculate distances
    for i, (idx1, row1) in enumerate(school_df.iterrows()):
        for j, (idx2, row2) in enumerate(school_df.iterrows()):
            if i == j:
                distance = 0
            else:
                distance = calculate_distance(
                    row1['latitude'], row1['longitude'],
                    row2['latitude'], row2['longitude']
                )
            distance_matrix[i, j] = distance

    # Create DataFrame from matrix with school names
    school_names = [row.get('اسم المدرسة', f"School #{idx}") for idx, row in school_df.iterrows()]
    distance_df = pd.DataFrame(distance_matrix, index=school_names, columns=school_names)

    return distance_df

# Function to load and process data
def load_and_process_data(file):
    """Load and process CSV data"""
    try:
        df = pd.read_csv(file)

        # Find coordinate columns
        lat_col = None
        lng_col = None
        for col in df.columns:
            col_lower = col.lower()
            # For Arabic text that might include "خط العرض" (latitude) or "خط الطول" (longitude)
            if 'lat' in col_lower or 'خط العرض' in col:
                lat_col = col
            elif 'lon' in col_lower or 'lng' in col_lower or 'خط الطول' in col:
                lng_col = col

        if not lat_col or not lng_col:
            st.warning("Could not automatically identify latitude and longitude columns. Please select them manually.")
            all_cols = list(df.columns)
            lat_col = st.selectbox("Select latitude column", all_cols)
            lng_col = st.selectbox("Select longitude column", all_cols)

        # Clean coordinate data
        for col, new_name in [(lat_col, 'latitude'), (lng_col, 'longitude')]:
            # Convert to string first to handle any unexpected formats
            df[new_name] = df[col].astype(str)

            # Clean any quotes or extra characters
            df[new_name] = df[new_name].str.replace('"', '').str.strip()

            # Handle comma as decimal separator if needed
            df[new_name] = df[new_name].str.replace(',', '.')

            # Convert to float, coercing errors to NaN
            df[new_name] = pd.to_numeric(df[new_name], errors='coerce')

        # Drop rows with missing coordinates
        df_clean = df.dropna(subset=['latitude', 'longitude'])

        # Filter out any invalid coordinates (too extreme or zero)
        df_clean = df_clean[(df_clean['latitude'] != 0) & (df_clean['longitude'] != 0)]

        # Standardize education office names
        if 'مكتب التعليم' in df_clean.columns:
            df_clean['standardized_office'] = df_clean['مكتب التعليم'].apply(standardize_office_name)

        return df_clean

    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

# Function to create the map
def create_map(df, education_offices=None, selected_schools=None, show_optimal_offices=True, color_by='office'):
    """
    Create a Folium map with schools and optimal office locations

    Parameters:
    df - DataFrame with school data
    education_offices - List of selected education offices to filter by
    selected_schools - List of indices of selected schools
    show_optimal_offices - Whether to show optimal office locations
    color_by - How to color the markers ('office', 'level', 'gender', 'type')
    """
    # Check if we have data
    if df is None or len(df) == 0:
        st.warning("No data available to display on map.")
        return None, None

    # Filter by education offices if specified
    if education_offices and len(education_offices) > 0:
        df_filtered = df[df['standardized_office'].isin(education_offices)]
        if len(df_filtered) == 0:
            st.warning("No schools match the selected education offices.")
            return None, None
    else:
        df_filtered = df

    # Calculate center of all filtered data points
    center_lat = df_filtered['latitude'].mean()
    center_lng = df_filtered['longitude'].mean()

    # Create the map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=10, control_scale=True)

    # Add tile layers
    folium.TileLayer('cartodbpositron', name='Light Map').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='Dark Map').add_to(m)
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    folium.TileLayer('Stamen Terrain', name='Terrain Map').add_to(m)

    # Add measurement control
    measure_control = MeasureControl(
        position='topright',
        primary_length_unit='kilometers',
        secondary_length_unit='miles',
        primary_area_unit='square kilometers',
        secondary_area_unit='acres'
    )
    m.add_child(measure_control)

    # Add drawing tools
    draw = Draw(
        position='topleft',
        draw_options={
            'polyline': True,
            'polygon': True,
            'circle': True,
            'marker': False,
            'circlemarker': False,
            'rectangle': True,
        },
        edit_options={
            'featureGroup': None
        }
    )
    m.add_child(draw)

    # Create a feature group for all schools
    all_schools = folium.FeatureGroup(name="All Schools").add_to(m)

    # Create a marker cluster for all schools
    all_schools_cluster = MarkerCluster(name="Clustered Schools").add_to(all_schools)

    # Create a feature group for the education office centers
    office_centers = folium.FeatureGroup(name="Optimal Office Locations").add_to(m)

    # Create a feature group for selected schools and distance lines
    selected_group = folium.FeatureGroup(name="Selected Schools").add_to(m)

    # Create a feature group for distance lines
    distance_lines = folium.FeatureGroup(name="Distance Lines").add_to(m)

    # Dictionary to keep track of schools by education office
    office_schools = {}

    # Color dictionary for education offices
    office_colors = {}
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred',
              'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'lightblue', 'lightgreen']
    for i, office in enumerate(df_filtered['standardized_office'].unique()):
        office_colors[office] = colors[i % len(colors)]

    # Color dictionary for school levels
    level_colors = {
        'رياض الأطفال': 'blue',
        'المرحلة الإبتدائية': 'green',
        'المرحلة المتوسطة': 'orange',
        'المرحلة الثانوية': 'red',
        'التعليم المستمر': 'purple',
        'معهد': 'darkred',
        'تربية خاصة': 'darkpurple'
    }

    # Gender colors
    gender_colors = {
        'بنين': 'blue',
        'بنات': 'red'
    }

    # Type colors
    type_colors = {
        'تعليم عام': 'blue',
        'تحفيظ قران': 'green',
        'تعليم كبيرات': 'purple',
        'معهد': 'red',
        'تربية خاصة': 'orange'
    }

    # Add markers for each school
    for idx, row in df_filtered.iterrows():
        # Get education office
        office = row.get('standardized_office', 'Unknown')

        # Add to office schools dictionary
        if office not in office_schools:
            office_schools[office] = []
        office_schools[office].append(idx)

        # Prepare popup content with all available information
        popup_html = f"<b>{row.get('اسم المدرسة', f'School {idx}')}</b><br>"

        # Add all information except coordinates
        for col in row.index:
            if col not in ['latitude', 'longitude', 'standardized_office']:
                popup_html += f"{col}: {row[col]}<br>"

        # Create icon color based on coloring method
        if color_by == 'office':
            color = office_colors.get(office, 'blue')
        elif color_by == 'level' and 'المرحلة' in row:
            color = level_colors.get(row['المرحلة'], 'blue')
        elif color_by == 'gender' and 'الجنس' in row:
            color = gender_colors.get(row['الجنس'], 'blue')
        elif color_by == 'type' and 'نوع التعليم' in row:
            color = type_colors.get(row['نوع التعليم'], 'blue')
        else:
            color = 'blue'

        # Check if this school is among the selected schools
        is_selected = selected_schools is not None and idx in selected_schools

        # Create marker
        if is_selected:
            # Use a different icon for selected schools
            icon = folium.Icon(color='green', icon='star', prefix='fa')
            marker = folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row.get('اسم المدرسة', f'School {idx}'),
                icon=icon
            )
            marker.add_to(selected_group)
        else:
            marker = folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row.get('اسم المدرسة', f'School {idx}'),
                icon=folium.Icon(color=color)
            )
            marker.add_to(all_schools_cluster)

    # Calculate and add optimal office locations for each education office

    # Calculate and add optimal office locations for each education office
    office_locations = {}

    if show_optimal_offices and len(office_schools) > 0:
        for office, school_indices in office_schools.items():
            # Skip if not in selected education offices (if any are selected)
            if education_offices and office not in education_offices:
                continue

            # Get schools for this office
            office_df = df_filtered.loc[school_indices]

            if len(office_df) > 0:
                # Calculate optimal location
                result = calculate_optimal_location(office_df)
                opt_lat = result['center_lat']
                opt_lng = result['center_lng']
                total_dist = result['total_distance']
                avg_dist = result['average_distance']
                max_dist = result['max_distance']
                farthest_school = result['farthest_school']

                # VALIDATION: Cap maximum radius to a reasonable value
                # Typically, educational offices serve areas within 100-150km
                # Use 95th percentile of distances instead of max to avoid outliers
                distances = []
                for _, row in office_df.iterrows():
                    dist = calculate_distance(
                        opt_lat, opt_lng,
                        row['latitude'], row['longitude']
                    )
                    distances.append(dist)

                # Sort distances and get the 95th percentile
                distances.sort()
                if len(distances) >= 20:  # If we have enough data points
                    radius_95 = distances[int(len(distances) * 0.95)]
                else:
                    # For smaller datasets, use a more conservative approach
                    radius_95 = distances[int(len(distances) * 0.8)] if len(distances) > 1 else max_dist

                # Cap maximum radius to 150km regardless
                display_radius = min(radius_95, 150)

                # Store the location for later use (keeping original max_dist for reference)
                office_locations[office] = {
                    'latitude': opt_lat,
                    'longitude': opt_lng,
                    'total_distance': total_dist,
                    'average_distance': avg_dist,
                    'max_distance': max_dist,
                    'display_radius': display_radius,  # Add the capped display radius
                    'farthest_school': farthest_school,
                    'school_count': len(office_df)
                }

                # Add marker for the optimal office location
                folium.Marker(
                    location=[opt_lat, opt_lng],
                    popup=folium.Popup(f"""<b>Optimal location for {office}</b><br>
                             Total schools: {len(office_df)}<br>
                             Total distance to all schools: {total_dist:.2f} km<br>
                             Average distance to schools: {avg_dist:.2f} km<br>
                             Coverage radius: {display_radius:.2f} km<br>
                             Maximum school distance: {max_dist:.2f} km<br>
                             Farthest school: {farthest_school}""",max_width=300),
                    tooltip=f"Optimal location: {office}",
                    icon=folium.Icon(color='black', icon='building', prefix='fa')
                ).add_to(office_centers)

                # Add circle to represent coverage area with the properly capped radius
                folium.Circle(
                    location=[opt_lat, opt_lng],
                    radius=display_radius * 1000,  # Convert km to meters
                    color=office_colors.get(office, 'black'),
                    fill=True,
                    fill_opacity=0.1,
                    tooltip=f"Coverage area for {office} (radius: {display_radius:.2f} km)"
                ).add_to(office_centers)


    # If schools are selected, draw lines between them and calculate distances
    if selected_schools and len(selected_schools) >= 2:
        selected_df = df_filtered.loc[selected_schools]

        # Draw lines between all pairs of selected schools
        for idx1, idx2 in combinations(selected_schools, 2):
            school1 = df_filtered.loc[idx1]
            school2 = df_filtered.loc[idx2]

            distance = calculate_distance(
                school1['latitude'], school1['longitude'],
                school2['latitude'], school2['longitude']
            )

            # Create a line between the schools
            line = folium.PolyLine(
                locations=[
                    [school1['latitude'], school1['longitude']],
                    [school2['latitude'], school2['longitude']]
                ],
                color='red',
                weight=3,
                opacity=0.7,
                tooltip=f"Distance: {distance:.2f} km"
            )
            line.add_to(distance_lines)

            # Add distance label at the middle of the line
            mid_point = [
                (school1['latitude'] + school2['latitude']) / 2,
                (school1['longitude'] + school2['longitude']) / 2
            ]

            folium.map.Marker(
                mid_point,
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18),
                    html=f'<div style="background-color: white; padding: 2px 5px; border-radius: 3px; font-size: 12px; font-weight: bold;">{distance:.2f} km</div>'
                )
            ).add_to(distance_lines)

    # If a single school is selected and we have office locations, show distance to optimal office
    if selected_schools and len(selected_schools) == 1 and office_locations:
        school = df_filtered.loc[selected_schools[0]]
        office = school.get('standardized_office', 'Unknown')

        if office in office_locations:
            office_location = office_locations[office]

            # Calculate distance
            distance = calculate_distance(
                school['latitude'], school['longitude'],
                office_location['latitude'], office_location['longitude']
            )

            # Create a line between the school and the office
            line = folium.PolyLine(
                locations=[
                    [school['latitude'], school['longitude']],
                    [office_location['latitude'], office_location['longitude']]
                ],
                color='blue',
                weight=3,
                opacity=0.7,
                tooltip=f"Distance to optimal office: {distance:.2f} km"
            )
            line.add_to(distance_lines)

            # Add distance label
            mid_point = [
                (school['latitude'] + office_location['latitude']) / 2,
                (school['longitude'] + office_location['longitude']) / 2
            ]

            folium.map.Marker(
                mid_point,
                icon=DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18),
                    html=f'<div style="background-color: white; padding: 2px 5px; border-radius: 3px; font-size: 12px; font-weight: bold;">{distance:.2f} km</div>'
                )
            ).add_to(distance_lines)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    return m, office_locations

# Function to calculate distances from each school to their optimal office location
def calculate_schools_to_office_distances(df, office_locations):
    """Calculate distances from each school to their optimal office location"""
    if not office_locations or 'standardized_office' not in df.columns:
        return df

    # Create a copy of the dataframe
    result_df = df.copy()

    # Add column for distance to optimal office
    result_df['distance_to_office'] = None

    # Calculate distance for each school
    for idx, row in result_df.iterrows():
        office = row['standardized_office']
        if office in office_locations:
            office_loc = office_locations[office]
            distance = calculate_distance(
                row['latitude'], row['longitude'],
                office_loc['latitude'], office_loc['longitude']
            )
            result_df.at[idx, 'distance_to_office'] = distance

    return result_df

# Main Streamlit app
def main():
    st.title("School Facilities Map Analyzer")

    # Upload file
    uploaded_file = st.sidebar.file_uploader("Upload CSV file with school data", type=["csv"])

    if uploaded_file is not None:
        # Process the data
        with st.spinner("Processing data..."):
            df = load_and_process_data(uploaded_file)

            if df is not None and len(df) > 0:
                st.sidebar.success(f"Loaded {len(df)} schools with valid coordinates")

                # Data overview
                st.sidebar.header("Data Overview")
                st.sidebar.write(f"Total schools: {len(df)}")

                if 'standardized_office' in df.columns:
                    offices = df['standardized_office'].unique()
                    st.sidebar.write(f"Education offices: {len(offices)}")

                    # Filter by education offices
                    st.sidebar.header("Filter Options")
                    selected_offices = st.sidebar.multiselect(
                        "Select Education Offices",
                        options=sorted(offices),
                        default=None
                    )
                else:
                    selected_offices = []
                    st.sidebar.warning("Education office column not found in data")

                # Color by options
                color_options = {
                    'office': 'Education Office',
                    'level': 'School Level',
                    'gender': 'Gender',
                    'type': 'School Type'
                }
                color_by = st.sidebar.selectbox(
                    "Color markers by",
                    options=list(color_options.keys()),
                    format_func=lambda x: color_options[x],
                    index=0
                )

                # Show optimal office locations
                show_optimal_offices = st.sidebar.checkbox("Show optimal office locations", value=True)

                # Filter data if education offices are selected
                if selected_offices and len(selected_offices) > 0:
                    filtered_df = df[df['standardized_office'].isin(selected_offices)]
                else:
                    filtered_df = df

                # Select schools for distance calculation
                st.sidebar.header("Select Schools for Distance Analysis")

                # Choose selection method
                selection_method = st.sidebar.radio(
                    "School selection method",
                    options=["Individual schools", "All schools in office"],
                    index=1
                )

                if selection_method == "Individual schools":
                    # Show dropdown to select individual schools
                    if 'اسم المدرسة' in filtered_df.columns:
                        school_options = {idx: name for idx, name in zip(filtered_df.index, filtered_df['اسم المدرسة'])}
                    else:
                        school_options = {idx: f"School #{idx}" for idx in filtered_df.index}

                    selected_schools = st.sidebar.multiselect(
                        "Select schools for distance analysis",
                        options=list(school_options.keys()),
                        format_func=lambda x: school_options[x]
                    )
                else:
                    # Select all schools in one education office
                    if len(selected_offices) == 1:
                        office_df = filtered_df[filtered_df['standardized_office'] == selected_offices[0]]
                        selected_schools = list(office_df.index)
                        st.sidebar.info(f"Selected all {len(selected_schools)} schools in {selected_offices[0]}")
                    elif len(selected_offices) > 1:
                        select_office = st.sidebar.selectbox(
                            "Select an education office for analysis",
                            options=selected_offices
                        )
                        office_df = filtered_df[filtered_df['standardized_office'] == select_office]
                        selected_schools = list(office_df.index)
                        st.sidebar.info(f"Selected all {len(selected_schools)} schools in {select_office}")
                    else:
                        st.sidebar.warning("Please select at least one education office")
                        selected_schools = []

                # Create map
                m, office_locations = create_map(
                    df=filtered_df,
                    education_offices=selected_offices,
                    selected_schools=selected_schools,
                    show_optimal_offices=show_optimal_offices,
                    color_by=color_by
                )

                # Layout with tabs
                tab1, tab2, tab3 = st.tabs(["Map", "Analysis", "Data"])

                with tab1:
                    # Display the map
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

                with tab2:
                    st.header("Analysis Results")

                    # Office location analysis
                    if office_locations and len(office_locations) > 0:
                        st.subheader("Optimal Office Locations")

                        # Create a dataframe from office_locations
                        office_df = pd.DataFrame.from_dict(office_locations, orient='index')
                        office_df.index.name = 'Education Office'
                        office_df = office_df.reset_index()

                        # Reorder and rename columns
                        office_df = office_df[[
                            'Education Office', 'school_count', 'latitude', 'longitude',
                            'total_distance', 'average_distance', 'max_distance', 'farthest_school'
                        ]]
                        office_df.columns = [
                            'Education Office', 'Number of Schools', 'Latitude', 'Longitude',
                            'Total Distance (km)', 'Average Distance (km)', 'Maximum Distance (km)', 'Farthest School'
                        ]

                        # Round distance values
                        for col in ['Total Distance (km)', 'Average Distance (km)', 'Maximum Distance (km)']:
                            office_df[col] = office_df[col].round(2)

                        # Display the dataframe
                        st.dataframe(office_df)

                        # Download link for office locations
                        st.markdown(get_csv_download_link(office_df, "optimal_office_locations.csv", "Download Optimal Office Locations"), unsafe_allow_html=True)

                        # Display a bar chart comparing average distances by office
                        if len(office_df) > 1:
                            st.subheader("Average Distance to Schools by Education Office")
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.bar(office_df['Education Office'], office_df['Average Distance (km)'], color='skyblue')
                            ax.set_xlabel('Education Office')
                            ax.set_ylabel('Average Distance (km)')
                            ax.set_title('Average Distance from Optimal Office Location to Schools')
                            plt.xticks(rotation=45, ha='right')
                            plt.tight_layout()
                            st.pyplot(fig)

                    # Distance matrix analysis
                    if selected_schools and len(selected_schools) >= 2:
                        st.subheader("Distance Matrix Between Selected Schools")

                        # Generate and display distance matrix
                        distance_df = generate_distance_matrix(filtered_df, selected_schools)
                        if distance_df is not None:
                            # Format distances to 2 decimal places
                            formatted_df = distance_df.applymap(lambda x: f"{x:.2f}" if x > 0 else "-")
                            st.dataframe(formatted_df)

                            # Download link for distance matrix
                            st.markdown(get_csv_download_link(distance_df, "distance_matrix.csv", "Download Distance Matrix"), unsafe_allow_html=True)

                            # Calculate and display statistics
                            st.subheader("Distance Statistics")

                            # Extract the upper triangle of the distance matrix (excluding diagonal)
                            distances = []
                            for i in range(len(distance_df)):
                                for j in range(i+1, len(distance_df)):
                                    distances.append(distance_df.iloc[i, j])

                            if distances:
                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.metric("Min Distance (km)", f"{min(distances):.2f}")
                                with col2:
                                    st.metric("Max Distance (km)", f"{max(distances):.2f}")

                                with col3:
                                    st.metric("Avg Distance (km)", f"{sum(distances)/len(distances):.2f}")

                                with col4:
                                    st.metric("Total Distance (km)", f"{sum(distances):.2f}")

                                # Create a histogram of distances
                                fig, ax = plt.subplots(figsize=(10, 6))
                                ax.hist(distances, bins=20, color='skyblue', edgecolor='black')
                                ax.set_xlabel('Distance (km)')
                                ax.set_ylabel('Frequency')
                                ax.set_title('Distribution of Distances Between Schools')
                                st.pyplot(fig)

                with tab3:
                    st.header("Data Table")

                    # Display dataframe
                    if len(filtered_df) > 0:
                        # Add distance to optimal office if available
                        if show_optimal_offices and 'standardized_office' in filtered_df.columns and office_locations:
                            # Calculate distances from each school to their optimal office location
                            enhanced_df = filtered_df.copy()
                            enhanced_df['Distance to Office (km)'] = None

                            for idx, row in enhanced_df.iterrows():
                                office = row['standardized_office']
                                if office in office_locations:
                                    office_loc = office_locations[office]
                                    distance = calculate_distance(
                                        row['latitude'], row['longitude'],
                                        office_loc['latitude'], office_loc['longitude']
                                    )
                                    enhanced_df.at[idx, 'Distance to Office (km)'] = round(distance, 2)

                            # Sort by distance to office
                            sort_by_distance = st.checkbox("Sort by distance to optimal office")
                            if sort_by_distance:
                                enhanced_df = enhanced_df.sort_values(by='Distance to Office (km)', ascending=False)

                            # Display the enhanced dataframe
                            st.dataframe(enhanced_df)

                            # Download link for enhanced data
                            st.markdown(get_csv_download_link(enhanced_df, "schools_with_distances.csv", "Download Full Data with Distances"), unsafe_allow_html=True)

                            # Show schools farthest from optimal office
                            st.subheader("Schools Farthest from Optimal Office")
                            farthest_df = enhanced_df.sort_values(by='Distance to Office (km)', ascending=False).head(10)
                            st.dataframe(farthest_df[['اسم المدرسة', 'standardized_office', 'Distance to Office (km)', 'المرحلة', 'الجنس', 'الحي']])

                            # Show schools closest to optimal office
                            st.subheader("Schools Closest to Optimal Office")
                            closest_df = enhanced_df.dropna(subset=['Distance to Office (km)']).sort_values(by='Distance to Office (km)', ascending=True).head(10)
                            st.dataframe(closest_df[['اسم المدرسة', 'standardized_office', 'Distance to Office (km)', 'المرحلة', 'الجنس', 'الحي']])
                        else:
                            # Display the dataframe without distance calculations
                            st.dataframe(filtered_df)

                            # Download link for data
                            st.markdown(get_csv_download_link(filtered_df, "filtered_schools.csv", "Download Filtered Data"), unsafe_allow_html=True)
    else:
        # Display instructions when no file is uploaded
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

        # Show a sample format
        st.subheader("Example Data Format")
        sample_data = pd.DataFrame({
            '#': [1, 2, 3],
            'اسم المدرسة': ['مدرسة 1', 'مدرسة 2', 'مدرسة 3'],
            'المرحلة': ['ابتدائية', 'متوسط', 'ثانوي'],
            'مكتب التعليم': ['مكتب 1', 'مكتب 2 - بنين', 'مكتب 1'],
            'الجنس': ['بنين', 'بنين', 'بنات'],
            'خط العرض': [21.50, 21.55, 21.60],
            'خط الطول': [39.20, 39.25, 39.30]
        })
        st.dataframe(sample_data)

if __name__ == "__main__":
    main()