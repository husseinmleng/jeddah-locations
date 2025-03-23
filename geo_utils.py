from math import sin, cos, sqrt, atan2, radians, cos, pi, fabs

def calculate_distance(lat1, lon1, lat2, lon2, method='haversine'):
    """
    Calculate distance between two points using specified method

    Parameters:
    lat1, lon1 - Coordinates of first point
    lat2, lon2 - Coordinates of second point
    method - 'haversine' (as crow flies) or 'manhattan' (city block)

    Returns:
    Distance in kilometers
    """
    if method == 'manhattan':
        return calculate_manhattan_distance(lat1, lon1, lat2, lon2)
    else:
        return calculate_haversine_distance(lat1, lon1, lat2, lon2)

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
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

def calculate_manhattan_distance(lat1, lon1, lat2, lon2):
    """
    Calculate Manhattan (city block) distance between two geographic points
    This is the sum of the absolute differences of their Cartesian coordinates
    """
    # Convert latitude difference to kilometers (111 km per degree is approximate)
    lat_distance = fabs(lat1 - lat2) * 111.0

    # Convert longitude difference to kilometers (varies with latitude)
    # At the equator, 1 degree of longitude is about 111 km
    # This decreases as you move toward the poles by a factor of cos(latitude)
    avg_lat = radians((lat1 + lat2) / 2)  # Use average latitude for calculation
    lon_distance = fabs(lon1 - lon2) * 111.0 * cos(avg_lat)

    # Manhattan distance is the sum of the absolute differences
    return lat_distance + lon_distance

def calculate_optimal_location(df, distance_method='manhattan'):
    """
    Calculate the optimal location using specified distance method

    For Manhattan distance, we use the median center instead of mean center
    as it minimizes the sum of Manhattan distances
    """
    if distance_method == 'manhattan':
        # For Manhattan distance, median center is optimal
        center_lat = df['latitude'].median()
        center_lng = df['longitude'].median()
    else:
        # For Haversine distance, use mean center
        center_lat = df['latitude'].mean()
        center_lng = df['longitude'].mean()

    # Find closest and farthest schools
    min_distance = float('inf')
    max_distance = 0
    closest_school = None
    farthest_school = None
    closest_school_idx = None
    closest_school_coords = None
    farthest_school_idx = None
    farthest_school_coords = None

    for idx, row in df.iterrows():
        dist = calculate_distance(
            center_lat, center_lng,
            row['latitude'], row['longitude'],
            method=distance_method
        )

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
        dist = calculate_distance(
            center_lat, center_lng,
            row['latitude'], row['longitude'],
            method=distance_method
        )
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
        'farthest_school_coords': farthest_school_coords,
        'distance_method': distance_method
    }