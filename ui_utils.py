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
        'اسم المدرسة': ['مدرسة السلام', 'مدرسة النجاح', 'مدرسة الأمل'],
        'المرحلة': ['ابتدائية', 'متوسط', 'ثانوي'],
        'الحي': ['حي الزهور', 'حي النسيم', 'حي الزهور'],
        'الجنس': ['بنين', 'بنين', 'بنات'],
        'خط العرض': [21.50, 21.55, 21.60],
        'خط الطول': [39.20, 39.25, 39.30]
    })