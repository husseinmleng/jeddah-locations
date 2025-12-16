import pandas as pd
import re
import streamlit as st

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

def load_and_process_data(file):
    """Load and process CSV or Excel data"""
    try:
        # Detect file type based on filename
        file_name = file.name.lower()
        if file_name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file_name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            st.error("Unsupported file format. Please upload a CSV or Excel file.")
            return None

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
            df[new_name] = df[col].astype(str)
            df[new_name] = df[new_name].str.replace('"', '').str.strip()
            df[new_name] = df[new_name].str.replace(',', '.')
            df[new_name] = pd.to_numeric(df[new_name], errors='coerce')

        # Drop rows with missing coordinates
        df_clean = df.dropna(subset=['latitude', 'longitude'])

        # Filter out any invalid coordinates (too extreme or zero)
        df_clean = df_clean[(df_clean['latitude'] != 0) & (df_clean['longitude'] != 0)]

        # Standardize education office names for filtering
        if 'مكتب التعليم' in df_clean.columns:
            df_clean['standardized_office'] = df_clean['مكتب التعليم'].apply(standardize_office_name)

        # Handle neighborhood column - check for both 'الحي' and 'العنوان'
        if 'الحي' in df_clean.columns:
            df_clean['الحي'] = df_clean['الحي'].fillna('Unknown').astype(str)
        elif 'العنوان' in df_clean.columns:
            # Use address as neighborhood if الحي doesn't exist
            df_clean['الحي'] = df_clean['العنوان'].fillna('Unknown').astype(str)

        # Handle zone column if it exists
        if 'الزون' in df_clean.columns:
            df_clean['الزون'] = df_clean['الزون'].fillna('Unknown').astype(str)

        return df_clean

    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None