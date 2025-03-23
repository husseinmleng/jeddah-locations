import base64
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def get_csv_download_link(df, filename="data.csv", text="Download CSV"):
    """Generate a download link for a dataframe as CSV"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def display_office_statistics(office_locations):
    """Display office location statistics in a dataframe"""
    if not office_locations or len(office_locations) == 0:
        return None

    # Create a dataframe from office_locations
    office_df = pd.DataFrame.from_dict(office_locations, orient='index')
    office_df.index.name = 'Education Office'
    office_df = office_df.reset_index()

    # Get distance method
    distance_method = office_df['distance_method'].iloc[0] if 'distance_method' in office_df.columns else 'Unknown'
    method_name = "Manhattan" if distance_method == "manhattan" else "Haversine"

    # Reorder and rename columns
    columns = [
        'Education Office', 'school_count', 'latitude', 'longitude',
        'total_distance', 'average_distance', 'max_distance', 'farthest_school'
    ]

    if 'distance_method' in office_df.columns:
        columns.append('distance_method')

    office_df = office_df[columns]

    # Rename columns
    column_names = [
        'Education Office', 'Number of Schools', 'Latitude', 'Longitude',
        f'Total {method_name} Distance (km)', f'Average {method_name} Distance (km)',
        f'Maximum {method_name} Distance (km)', 'Farthest School'
    ]

    if 'distance_method' in office_df.columns:
        column_names.append('Distance Method')

    office_df.columns = column_names

    # Round distance values
    for col in [col for col in column_names if "Distance (km)" in col]:
        office_df[col] = office_df[col].round(2)

    return office_df

def plot_office_distances(office_df):
    """Plot a bar chart of average distances by education office"""
    if len(office_df) <= 1:
        return None

    # Find the average distance column (works regardless of which method was used)
    avg_col = next((col for col in office_df.columns if "Average" in col and "Distance" in col), None)
    if not avg_col:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(office_df['Education Office'], office_df[avg_col], color='skyblue')
    ax.set_xlabel('Education Office')
    ax.set_ylabel(avg_col)
    ax.set_title(f'{avg_col} from Optimal Office Location to Schools')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig

def plot_distance_histogram(distances, method_name="Manhattan"):
    """Plot a histogram of distances"""
    if not distances:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(distances, bins=20, color='skyblue', edgecolor='black')
    ax.set_xlabel(f'{method_name} Distance (km)')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Distribution of {method_name} Distances Between Schools')

    return fig

def create_sample_data():
    """Create sample data for display when no file is uploaded"""
    return pd.DataFrame({
        '#': [1, 2, 3],
        'اسم المدرسة': ['مدرسة 1', 'مدرسة 2', 'مدرسة 3'],
        'المرحلة': ['ابتدائية', 'متوسط', 'ثانوي'],
        'مكتب التعليم': ['مكتب 1', 'مكتب 2 - بنين', 'مكتب 1'],
        'الجنس': ['بنين', 'بنين', 'بنات'],
        'خط العرض': [21.50, 21.55, 21.60],
        'خط الطول': [39.20, 39.25, 39.30]
    })