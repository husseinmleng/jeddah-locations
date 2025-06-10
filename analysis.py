import pandas as pd
import numpy as np
from geo_utils import calculate_distance

def generate_distance_matrix(df, selected_schools=None, distance_method='manhattan'):
    """
    Generate a distance matrix between selected schools using specified distance method

    Parameters:
    df - DataFrame with school data
    selected_schools - List of indices of selected schools
    distance_method - Method to calculate distances ('haversine' or 'manhattan')

    Returns:
    DataFrame with distance matrix
    """
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
                    row2['latitude'], row2['longitude'],
                    method=distance_method
                )
            distance_matrix[i, j] = distance

    # Create DataFrame from matrix with school names
    school_names = [row.get('اسم المدرسة', f"School #{idx}") for idx, row in school_df.iterrows()]
    distance_df = pd.DataFrame(distance_matrix, index=school_names, columns=school_names)

    # Add metadata for tracking
    distance_df.attrs['distance_method'] = distance_method

    return distance_df

def extract_distance_statistics(distance_df):
    """Extract statistics from a distance matrix"""
    # Extract the upper triangle of the distance matrix (excluding diagonal)
    distances = []
    for i in range(len(distance_df)):
        for j in range(i+1, len(distance_df)):
            distances.append(distance_df.iloc[i, j])

    if not distances:
        return None

    # Get distance method from DataFrame if available
    distance_method = distance_df.attrs.get('distance_method', 'Unknown')

    return {
        'min_distance': min(distances),
        'max_distance': max(distances),
        'avg_distance': sum(distances)/len(distances),
        'total_distance': sum(distances),
        'distances': distances,  # For histogram
        'distance_method': distance_method
    }