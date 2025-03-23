import folium
from folium.plugins import MarkerCluster, MeasureControl, Draw
from folium.features import DivIcon
from itertools import combinations
from geo_utils import calculate_distance, calculate_optimal_location

def create_map(df, education_offices=None, selected_schools=None, show_optimal_offices=True,
               color_by='office', distance_method='manhattan'):
    """
    Create a Folium map with schools and optimal office locations

    Parameters:
    df - DataFrame with school data
    education_offices - List of selected education offices to filter by
    selected_schools - List of indices of selected schools
    show_optimal_offices - Whether to show optimal office locations
    color_by - How to color the markers ('office', 'level', 'gender', 'type')
    distance_method - Method to calculate distances ('haversine' or 'manhattan')
    """
    # Check if we have data
    if df is None or len(df) == 0:
        return None, None

    # Filter by education offices if specified
    if education_offices and len(education_offices) > 0:
        df_filtered = df[df['standardized_office'].isin(education_offices)]
        if len(df_filtered) == 0:
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

    # Create feature groups
    all_schools = folium.FeatureGroup(name="All Schools").add_to(m)
    all_schools_cluster = MarkerCluster(name="Clustered Schools").add_to(all_schools)
    office_centers = folium.FeatureGroup(name="Optimal Office Locations").add_to(m)
    selected_group = folium.FeatureGroup(name="Selected Schools").add_to(m)
    distance_lines = folium.FeatureGroup(name="Distance Lines").add_to(m)

    # Dictionary to keep track of schools by education office
    office_schools = {}

    # Color dictionaries
    office_colors = _get_office_colors(df_filtered)
    level_colors = _get_level_colors()
    gender_colors = _get_gender_colors()
    type_colors = _get_type_colors()

    # Add markers for each school
    for idx, row in df_filtered.iterrows():
        # Get education office
        office = row.get('standardized_office', 'Unknown')

        # Add to office schools dictionary
        if office not in office_schools:
            office_schools[office] = []
        office_schools[office].append(idx)

        # Create popup and marker
        popup_html = _create_popup_html(row, idx)
        color = _get_marker_color(row, color_by, office, office_colors, level_colors, gender_colors, type_colors)

        # Check if this school is among the selected schools
        is_selected = selected_schools is not None and idx in selected_schools

        # Create marker
        _add_school_marker(row, idx, popup_html, color, is_selected, selected_group, all_schools_cluster)

    # Calculate and add optimal office locations
    office_locations = {}
    if show_optimal_offices and len(office_schools) > 0:
        for office, school_indices in office_schools.items():
            if education_offices and office not in education_offices:
                continue

            # Get schools for this office
            office_df = df_filtered.loc[school_indices]

            if len(office_df) > 0:
                # Process and add office location
                office_locations = _process_office_location(
                    office, office_df, office_locations, office_centers, office_colors, distance_method
                )

    # Handle selected schools
    if selected_schools:
        if len(selected_schools) >= 2:
            _add_distance_lines_between_schools(df_filtered, selected_schools, distance_lines, distance_method)
        elif len(selected_schools) == 1 and office_locations:
            _add_distance_to_office(df_filtered, selected_schools[0], office_locations, distance_lines, distance_method)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    return m, office_locations

def _get_office_colors(df):
    """Generate colors for education offices"""
    office_colors = {}
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred',
              'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'lightblue', 'lightgreen']
    for i, office in enumerate(df['standardized_office'].unique()):
        office_colors[office] = colors[i % len(colors)]
    return office_colors

def _get_level_colors():
    """Get color mapping for school levels"""
    return {
        'رياض الأطفال': 'blue',
        'المرحلة الإبتدائية': 'green',
        'المرحلة المتوسطة': 'orange',
        'المرحلة الثانوية': 'red',
        'التعليم المستمر': 'purple',
        'معهد': 'darkred',
        'تربية خاصة': 'darkpurple'
    }

def _get_gender_colors():
    """Get color mapping for gender"""
    return {
        'بنين': 'blue',
        'بنات': 'red'
    }

def _get_type_colors():
    """Get color mapping for school types"""
    return {
        'تعليم عام': 'blue',
        'تحفيظ قران': 'green',
        'تعليم كبيرات': 'purple',
        'معهد': 'red',
        'تربية خاصة': 'orange'
    }

def _create_popup_html(row, idx):
    """Create HTML content for marker popup"""
    popup_html = f"<b>{row.get('اسم المدرسة', f'School {idx}')}</b><br>"

    # Add all information except coordinates
    for col in row.index:
        if col not in ['latitude', 'longitude', 'standardized_office']:
            popup_html += f"{col}: {row[col]}<br>"

    return popup_html

def _get_marker_color(row, color_by, office, office_colors, level_colors, gender_colors, type_colors):
    """Determine marker color based on coloring method"""
    if color_by == 'office':
        return office_colors.get(office, 'blue')
    elif color_by == 'level' and 'المرحلة' in row:
        return level_colors.get(row['المرحلة'], 'blue')
    elif color_by == 'gender' and 'الجنس' in row:
        return gender_colors.get(row['الجنس'], 'blue')
    elif color_by == 'type' and 'نوع التعليم' in row:
        return type_colors.get(row['نوع التعليم'], 'blue')
    else:
        return 'blue'

def _add_school_marker(row, idx, popup_html, color, is_selected, selected_group, all_schools_cluster):
    """Add a school marker to the map"""
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

def _process_office_location(office, office_df, office_locations, office_centers, office_colors, distance_method):
    """Calculate and add optimal office location using specified distance method"""
    # Calculate optimal location
    result = calculate_optimal_location(office_df, distance_method=distance_method)
    opt_lat = result['center_lat']
    opt_lng = result['center_lng']
    total_dist = result['total_distance']
    avg_dist = result['average_distance']
    max_dist = result['max_distance']
    farthest_school = result['farthest_school']

    # Calculate display radius (capped to avoid outliers)
    display_radius = _calculate_display_radius(office_df, opt_lat, opt_lng, max_dist, distance_method)

    # Store the location
    office_locations[office] = {
        'latitude': opt_lat,
        'longitude': opt_lng,
        'total_distance': total_dist,
        'average_distance': avg_dist,
        'max_distance': max_dist,
        'display_radius': display_radius,
        'farthest_school': farthest_school,
        'school_count': len(office_df),
        'distance_method': distance_method
    }

    # Add marker for the optimal office location
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"
    _add_office_marker(
        office, opt_lat, opt_lng, len(office_df),
        total_dist, avg_dist, display_radius, max_dist,
        farthest_school, office_centers, method_name
    )

    # Add circle to represent coverage area
    folium.Circle(
        location=[opt_lat, opt_lng],
        radius=display_radius * 1000,  # Convert km to meters
        color=office_colors.get(office, 'black'),
        fill=True,
        fill_opacity=0.1,
        tooltip=f"Coverage area for {office} (radius: {display_radius:.2f} km)"
    ).add_to(office_centers)

    return office_locations

def _calculate_display_radius(office_df, opt_lat, opt_lng, max_dist, distance_method):
    """Calculate a reasonable display radius for the office coverage using specified distance method"""
    distances = []
    for _, row in office_df.iterrows():
        dist = calculate_distance(
            opt_lat, opt_lng,
            row['latitude'], row['longitude'],
            method=distance_method
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
    return min(radius_95, 150)

def _add_office_marker(office, lat, lng, school_count, total_dist, avg_dist,
                       display_radius, max_dist, farthest_school, feature_group, method_name):
    """Add a marker for an optimal office location"""
    popup_content = f"""<b>Optimal location for {office}</b><br>
                     <b>Method:</b> {method_name} distance<br>
                     Total schools: {school_count}<br>
                     Total distance to all schools: {total_dist:.2f} km<br>
                     Average distance to schools: {avg_dist:.2f} km<br>
                     Coverage radius: {display_radius:.2f} km<br>
                     Maximum school distance: {max_dist:.2f} km<br>
                     Farthest school: {farthest_school}"""

    folium.Marker(
        location=[lat, lng],
        popup=folium.Popup(popup_content, max_width=300),
        tooltip=f"Optimal location: {office} ({method_name})",
        icon=folium.Icon(color='black', icon='building', prefix='fa')
    ).add_to(feature_group)

def _add_distance_lines_between_schools(df, selected_schools, feature_group, distance_method):
    """Add lines between all pairs of selected schools"""
    for idx1, idx2 in combinations(selected_schools, 2):
        school1 = df.loc[idx1]
        school2 = df.loc[idx2]

        distance = calculate_distance(
            school1['latitude'], school1['longitude'],
            school2['latitude'], school2['longitude'],
            method=distance_method
        )

        method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"

        # Create a line between the schools
        line = folium.PolyLine(
            locations=[
                [school1['latitude'], school1['longitude']],
                [school2['latitude'], school2['longitude']]
            ],
            color='red',
            weight=3,
            opacity=0.7,
            tooltip=f"{method_name} Distance: {distance:.2f} km"
        )
        line.add_to(feature_group)

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
                html=f'<div style="background-color: white; padding: 2px 5px; border-radius: 3px; font-size: 12px; font-weight: bold;">{distance:.2f} km ({method_name})</div>'
            )
        ).add_to(feature_group)

def _add_distance_to_office(df, school_idx, office_locations, feature_group, distance_method):
    """Add a line between a school and its optimal office location"""
    school = df.loc[school_idx]
    office = school.get('standardized_office', 'Unknown')

    if office in office_locations:
        office_location = office_locations[office]

        # Calculate distance
        distance = calculate_distance(
            school['latitude'], school['longitude'],
            office_location['latitude'], office_location['longitude'],
            method=distance_method
        )

        method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"

        # Create a line between the school and the office
        line = folium.PolyLine(
            locations=[
                [school['latitude'], school['longitude']],
                [office_location['latitude'], office_location['longitude']]
            ],
            color='blue',
            weight=3,
            opacity=0.7,
            tooltip=f"{method_name} Distance to optimal office: {distance:.2f} km"
        )
        line.add_to(feature_group)

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
                html=f'<div style="background-color: white; padding: 2px 5px; border-radius: 3px; font-size: 12px; font-weight: bold;">{distance:.2f} km ({method_name})</div>'
            )
        ).add_to(feature_group)