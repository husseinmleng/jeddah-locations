from math import sin, cos, sqrt, atan2, radians, pi, fabs

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
    avg_lat = radians((lat1 + lat2) / 2)  # Use average latitude for calculation
    lon_distance = fabs(lon1 - lon2) * 111.0 * cos(avg_lat)

    # Manhattan distance is the sum of the absolute differences
    return lat_distance + lon_distance

def calculate_optimal_location(df, distance_method='manhattan'):
    """
    Calculate the optimal location and distance statistics for a group of schools.

    For Manhattan distance, we use the median center.
    For Haversine distance, we use the mean center.
    """
    if df.empty:
        return None

    if distance_method == 'manhattan':
        center_lat = df['latitude'].median()
        center_lng = df['longitude'].median()
    else:
        center_lat = df['latitude'].mean()
        center_lng = df['longitude'].mean()

    max_distance = 0
    for idx, row in df.iterrows():
        dist = calculate_distance(
            center_lat, center_lng,
            row['latitude'], row['longitude'],
            method=distance_method
        )
        if dist > max_distance:
            max_distance = dist

    return {
        'center_lat': center_lat,
        'center_lng': center_lng,
        'max_distance': max_distance,
    }

def calculate_robust_centroid(df, distance_method='manhattan', outlier_percentile=95, exclude_outliers=True):
    """
    Calculate a robust centroid for a group of schools, handling outliers.

    This function:
    1. Calculates an initial centroid using median (robust to outliers)
    2. Identifies outliers based on distance from initial centroid
    3. Optionally recalculates centroid excluding outliers

    Parameters:
    - df: DataFrame with latitude and longitude columns
    - distance_method: 'manhattan' or 'haversine'
    - outlier_percentile: Schools beyond this percentile distance are considered outliers
    - exclude_outliers: If True, recalculate centroid without outliers. If False, use all schools.

    Returns:
    - Dictionary with centroid location, statistics, and outlier info
    """
    if df.empty:
        return None

    # Always use median for initial centroid (most robust)
    initial_lat = df['latitude'].median()
    initial_lng = df['longitude'].median()

    # Calculate distances from initial centroid
    distances = []
    for idx, row in df.iterrows():
        dist = calculate_distance(
            initial_lat, initial_lng,
            row['latitude'], row['longitude'],
            method=distance_method
        )
        distances.append((idx, dist))

    # Find outlier threshold
    distance_values = [d[1] for d in distances]
    import numpy as np
    outlier_threshold = np.percentile(distance_values, outlier_percentile)

    # Separate inliers and outliers
    inlier_indices = [idx for idx, dist in distances if dist <= outlier_threshold]
    outlier_indices = [idx for idx, dist in distances if dist > outlier_threshold]

    # Recalculate centroid based on exclude_outliers setting
    if exclude_outliers and len(inlier_indices) > 0:
        # Use only inliers for centroid calculation
        inlier_df = df.loc[inlier_indices]
        center_lat = inlier_df['latitude'].median()
        center_lng = inlier_df['longitude'].median()
    else:
        # Use all schools (including outliers) for centroid
        center_lat = initial_lat
        center_lng = initial_lng
        if not exclude_outliers:
            # If we're including outliers, mark them all as inliers
            inlier_indices = list(df.index)
            outlier_indices = []

    # Calculate statistics
    all_distances = []
    max_distance = 0
    for idx, row in df.iterrows():
        dist = calculate_distance(
            center_lat, center_lng,
            row['latitude'], row['longitude'],
            method=distance_method
        )
        all_distances.append(dist)
        if dist > max_distance:
            max_distance = dist

    return {
        'center_lat': center_lat,
        'center_lng': center_lng,
        'max_distance': max_distance,
        'avg_distance': np.mean(all_distances),
        'median_distance': np.median(all_distances),
        'outlier_threshold': outlier_threshold,
        'outlier_indices': outlier_indices,
        'inlier_indices': inlier_indices,
        'distances': all_distances,
        'exclude_outliers': exclude_outliers
    }