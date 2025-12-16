import folium
from folium.plugins import MarkerCluster, MeasureControl, Draw
from folium.features import DivIcon
from itertools import combinations
from geo_utils import calculate_distance, calculate_optimal_location, calculate_robust_centroid

def create_map(df, selected_schools=None,
               color_by='neighborhood', distance_method='manhattan',
               show_coverage_areas=True, show_centroid_distances=False):
    """
    Create a Folium map. The received DataFrame is pre-filtered by office.
    This function groups the data by neighborhood for visualization.

    Parameters:
    - show_centroid_distances: If True, show zone centroids and distances to all schools

    Returns:
    - m: Folium map object
    - zone_centroids: Dictionary with zone centroid information
    """
    if df is None or df.empty:
        return None, None

    # Use the passed dataframe directly, as it's already filtered.
    df_filtered = df

    center_lat = df_filtered['latitude'].mean()
    center_lng = df_filtered['longitude'].mean()

    m = folium.Map(location=[center_lat, center_lng], zoom_start=10, control_scale=True)

    # --- Start of New Code ---
    
    # Add Google Satellite as the default layer
    folium.TileLayer(
        tile='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # Add Esri World Imagery as another satellite option
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # --- End of New Code ---


    # Add the other, non-satellite layers
    folium.TileLayer('cartodbpositron', name='Light Map').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='Dark Map').add_to(m)
    
    m.add_child(MeasureControl(position='topright', primary_length_unit='kilometers'))
    m.add_child(Draw(position='topleft'))

    # Feature groups
    all_schools_cluster = MarkerCluster(name="Clustered Schools").add_to(m)
    selected_group_fg = folium.FeatureGroup(name="Selected Schools").add_to(m)
    distance_lines_fg = folium.FeatureGroup(name="Distance Lines").add_to(m)

    if show_coverage_areas:
        coverage_areas_fg = folium.FeatureGroup(name="Neighborhood Coverage").add_to(m)

    # Calculate zone centroids if zone column exists
    zone_centroids = {}
    if 'الزون' in df_filtered.columns:
        centroids_fg = folium.FeatureGroup(name="Zone Centroids").add_to(m)
        centroid_distances_fg = folium.FeatureGroup(name="Centroid Distances").add_to(m)

        for zone in df_filtered['الزون'].unique():
            zone_df = df_filtered[df_filtered['الزون'] == zone]
            centroid_info = calculate_robust_centroid(zone_df, distance_method=distance_method)

            if centroid_info:
                zone_centroids[zone] = centroid_info

                # Add centroid marker
                zone_color = _get_zone_colors(df_filtered).get(zone, 'gray')
                folium.Marker(
                    location=[centroid_info['center_lat'], centroid_info['center_lng']],
                    popup=f"<b>Zone {zone} Centroid</b><br>"
                          f"Avg Distance: {centroid_info['avg_distance']:.2f} km<br>"
                          f"Median Distance: {centroid_info['median_distance']:.2f} km<br>"
                          f"Max Distance: {centroid_info['max_distance']:.2f} km<br>"
                          f"Schools: {len(zone_df)}<br>"
                          f"Outliers: {len(centroid_info['outlier_indices'])}",
                    tooltip=f"Zone {zone} Centroid",
                    icon=folium.Icon(color=zone_color, icon='star', prefix='fa')
                ).add_to(centroids_fg)

                # Add distance lines if requested
                if show_centroid_distances:
                    for idx, row in zone_df.iterrows():
                        dist = calculate_distance(
                            centroid_info['center_lat'], centroid_info['center_lng'],
                            row['latitude'], row['longitude'],
                            method=distance_method
                        )

                        # Use different line style for outliers
                        is_outlier = idx in centroid_info['outlier_indices']
                        line_color = 'red' if is_outlier else zone_color
                        line_weight = 2 if is_outlier else 1
                        line_opacity = 0.6 if is_outlier else 0.3

                        folium.PolyLine(
                            locations=[
                                [centroid_info['center_lat'], centroid_info['center_lng']],
                                [row['latitude'], row['longitude']]
                            ],
                            color=line_color,
                            weight=line_weight,
                            opacity=line_opacity,
                            tooltip=f"{row.get('اسم المدرسة', 'School')}: {dist:.2f} km"
                                    + (" (Outlier)" if is_outlier else "")
                        ).add_to(centroid_distances_fg)

    # Dictionary to group schools by neighborhood
    neighborhood_schools = {}
    if 'الحي' in df_filtered.columns:
        for idx, row in df_filtered.iterrows():
            neighborhood = row.get('الحي', 'Unknown')
            if neighborhood not in neighborhood_schools:
                neighborhood_schools[neighborhood] = []
            neighborhood_schools[neighborhood].append(idx)

    # Color dictionaries
    neighborhood_colors = _get_group_colors(df_filtered, 'الحي')
    zone_colors = _get_zone_colors(df_filtered)
    level_colors = _get_level_colors()
    gender_colors = _get_gender_colors()
    type_colors = _get_type_colors()

    # Add markers for each school
    for idx, row in df_filtered.iterrows():
        neighborhood = row.get('الحي', 'Unknown')
        zone = row.get('الزون', 'Unknown')
        popup_html = _create_popup_html(row, idx)
        color = _get_marker_color(row, color_by, neighborhood, zone, neighborhood_colors, zone_colors, level_colors, gender_colors, type_colors)
        
        is_selected = selected_schools is not None and idx in selected_schools
        _add_school_marker(row, idx, popup_html, color, is_selected, selected_group_fg, all_schools_cluster)

    # Calculate and draw coverage areas if requested
    if show_coverage_areas and neighborhood_schools:
        for neighborhood, school_indices in neighborhood_schools.items():
            neighborhood_df = df_filtered.loc[school_indices]
            result = calculate_optimal_location(neighborhood_df, distance_method=distance_method)
            
            if result:
                folium.Circle(
                    location=[result['center_lat'], result['center_lng']],
                    radius=result['max_distance'] * 1000,
                    color=neighborhood_colors.get(neighborhood, 'black'),
                    weight=2, fill=True, fill_opacity=0.1,
                    tooltip=f"Coverage Area: {neighborhood}"
                ).add_to(coverage_areas_fg)

    # Handle distance lines for selected schools
    if selected_schools and len(selected_schools) >= 2:
        _add_distance_lines_between_schools(df_filtered, selected_schools, distance_lines_fg, distance_method)

    folium.LayerControl(collapsed=False).add_to(m)
    return m, zone_centroids

def _get_group_colors(df, group_column):
    group_colors = {}
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'lightblue', 'lightgreen']
    if group_column in df.columns:
        for i, group in enumerate(df[group_column].unique()):
            group_colors[group] = colors[i % len(colors)]
    return group_colors

def _get_zone_colors(df):
    """Get colors for zones (G1-G5)"""
    zone_colors = {
        'G1': 'blue',
        'G2': 'green',
        'G3': 'red',
        'G4': 'purple',
        'G5': 'orange'
    }
    # If zone column exists, add any additional zones found
    if 'الزون' in df.columns:
        additional_colors = ['darkred', 'lightred', 'darkblue', 'darkgreen', 'cadetblue']
        zones = df['الزون'].unique()
        for i, zone in enumerate(zones):
            if zone not in zone_colors:
                zone_colors[zone] = additional_colors[i % len(additional_colors)]
    return zone_colors

def _get_level_colors():
    return {'رياض الأطفال': 'blue', 'المرحلة الإبتدائية': 'green', 'المرحلة المتوسطة': 'orange', 'المرحلة الثانوية': 'red', 'التعليم المستمر': 'purple', 'معهد': 'darkred', 'تربية خاصة': 'darkpurple'}

def _get_gender_colors(): return {'بنين': 'blue', 'بنات': 'red'}

def _get_type_colors():
    return {'تعليم عام': 'blue', 'تحفيظ قران': 'green', 'تعليم كبيرات': 'purple', 'معهد': 'red', 'تربية خاصة': 'orange'}

def _create_popup_html(row, idx):
    popup_html = f"<b>{row.get('اسم المدرسة', f'School {idx}')}</b><br>"
    for col in row.index:
        if col not in ['latitude', 'longitude', 'standardized_office']:
            popup_html += f"{col}: {row[col]}<br>"
    return popup_html

def _get_marker_color(row, color_by, neighborhood, zone, neighborhood_colors, zone_colors, level_colors, gender_colors, type_colors):
    if color_by == 'zone': return zone_colors.get(zone, 'gray')
    elif color_by == 'neighborhood': return neighborhood_colors.get(neighborhood, 'gray')
    elif color_by == 'level' and 'المرحلة' in row: return level_colors.get(row['المرحلة'], 'blue')
    elif color_by == 'gender':
        # Check both possible gender column names
        gender_col = 'جنس المدرسة' if 'جنس المدرسة' in row else 'الجنس'
        if gender_col in row: return gender_colors.get(row[gender_col], 'blue')
    elif color_by == 'type' and 'نوع التعليم' in row: return type_colors.get(row['نوع التعليم'], 'blue')
    return 'blue'

def _add_school_marker(row, idx, popup_html, color, is_selected, selected_group, all_schools_cluster):
    icon = folium.Icon(color='green', icon='star', prefix='fa') if is_selected else folium.Icon(color=color)
    marker = folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=row.get('اسم المدرسة', f'School {idx}'),
        icon=icon
    )
    if is_selected: marker.add_to(selected_group)
    else: marker.add_to(all_schools_cluster)

def _add_distance_lines_between_schools(df, selected_schools, feature_group, distance_method):
    for idx1, idx2 in combinations(selected_schools, 2):
        school1, school2 = df.loc[idx1], df.loc[idx2]
        distance = calculate_distance(school1['latitude'], school1['longitude'], school2['latitude'], school2['longitude'], method=distance_method)
        
        folium.PolyLine(
            locations=[[school1['latitude'], school1['longitude']], [school2['latitude'], school2['longitude']]],
            color='red', weight=3, opacity=0.7, tooltip=f"Distance: {distance:.2f} km"
        ).add_to(feature_group)
        mid_point = [(school1['latitude'] + school2['latitude']) / 2, (school1['longitude'] + school2['longitude']) / 2]
        folium.map.Marker(
            mid_point,
            icon=DivIcon(
                icon_size=(150, 36), icon_anchor=(75, 18),
                html=f'<div style="background-color: white; padding: 2px 5px; border-radius: 3px; font-size: 12px; font-weight: bold;">{distance:.2f} km</div>'
            )
        ).add_to(feature_group)