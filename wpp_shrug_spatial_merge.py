#!/usr/bin/env python3
"""
WPP to SHRUG Spatial Merge

Matches WPP water purification plants to SHRUG villages using lat/long coordinates.
Requires a SHRUG village-level GPKG file with village boundaries.

Usage:
    python wpp_shrug_spatial_merge.py --shrug-gpkg /path/to/shrug_villages.gpkg

Requirements:
    pip install geopandas pandas shapely rtree
"""

import argparse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
from pathlib import Path
import re


def parse_coordinate(value: str) -> float:
    """
    Parse various coordinate formats to decimal degrees.

    Handles formats like:
    - 12°43'46.6"N or 76°05'49.4"E (DMS with symbols)
    - x-13.2153°, y-76.045° (decimal with prefix)
    - N-12.41.48, E-76.09.51 (dot-separated DMS)
    - n-13 14 49, e-76 09 19 (space-separated DMS)
    - n-12'40'48, e-75'52'37 (quote-separated DMS)
    - n -13° 1' 7", E-75°59'0" (mixed format)
    - 13053'19"N (run-together DMS)
    - 15.02.04 (dot-separated DMS without direction)
    - 15.7873289- (decimal with trailing dash)
    - 15 23 48 (space-separated DMS)
    - Lat:16.552743, Long: 76.086175 (labeled format)
    - 16.438925 76.250074 (lat+long in one field)

    Returns decimal degrees or None if parsing fails.
    """
    if pd.isna(value):
        return None

    value = str(value).strip()
    if not value:
        return None

    # Remove common prefixes/suffixes
    value = value.replace('Lat:', '').replace('Long:', '')
    value = value.replace('lat:', '').replace('long:', '')
    value = re.sub(r'^[nNeEsSwW]\s*[-=]?\s*', '', value)  # N-, E-, n =, etc.
    value = re.sub(r'^[xXyY]\s*[-=]\s*', '', value)  # x-, y-
    value = value.rstrip('-,')  # trailing dash or comma
    value = value.strip()

    # Check for direction indicators (to determine sign)
    is_south_or_west = bool(re.search(r'[sSwW]$', value) or re.search(r'^[sSwW]', value))
    value = re.sub(r'[nNeEsSwW]$', '', value)  # Remove trailing direction
    value = re.sub(r'^[nNeEsSwW]\s*', '', value)  # Remove leading direction
    value = value.strip()

    # If it contains both lat and long (space-separated decimals), take first
    if re.match(r'^[\d.]+\s+[\d.]+$', value):
        value = value.split()[0]

    # Try direct decimal conversion first
    try:
        result = float(value)
        if 0 < abs(result) < 180:
            return -result if is_south_or_west else result
    except ValueError:
        pass

    # Normalize various degree/minute/second symbols
    value = value.replace('º', '°').replace('*', '°').replace('o', '°')
    value = value.replace("''", '"').replace("'", "'")
    value = value.replace('"', '"').replace('"', '"')

    # Pattern 1: Standard DMS - 12°43'46.6" or 12° 43' 46.6"
    dms_pattern = r"(\d+)\s*°\s*(\d+)\s*['\u2019]\s*([\d.]+)\s*[\"\u201d]?"
    match = re.search(dms_pattern, value)
    if match:
        d, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
        result = d + m/60 + s/3600
        return -result if is_south_or_west else result

    # Pattern 2: Run-together DMS - 13053'19" (degrees run into minutes)
    # If first number is >360, likely degrees+minutes run together
    runon_pattern = r"(\d{3,})['\"'](\d+)['\"\u2019\u201d]?"
    match = re.search(runon_pattern, value)
    if match:
        dm_str = match.group(1)
        s = float(match.group(2))
        # Split: first 2-3 digits are degrees, rest are minutes
        if len(dm_str) >= 4:
            d = float(dm_str[:2])
            m = float(dm_str[2:])
        else:
            d = float(dm_str[:1])
            m = float(dm_str[1:])
        result = d + m/60 + s/3600
        if 0 < result < 180:
            return -result if is_south_or_west else result

    # Pattern 3: Dot-separated - 15.02.04 or 12.41.48
    dot_pattern = r"^(\d{1,3})\.(\d{1,2})\.(\d{1,2})$"
    match = re.match(dot_pattern, value)
    if match:
        d, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
        result = d + m/60 + s/3600
        if 0 < result < 180:
            return -result if is_south_or_west else result

    # Pattern 4: Space-separated - 13 14 49 or 15 23 48
    space_pattern = r"^(\d{1,3})\s+(\d{1,2})\s+(\d{1,2}(?:\.\d+)?)$"
    match = re.match(space_pattern, value)
    if match:
        d, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
        result = d + m/60 + s/3600
        if 0 < result < 180:
            return -result if is_south_or_west else result

    # Pattern 5: Quote-separated - 12'40'48 or 13' 11' 08.85
    quote_pattern = r"(\d{1,3})['\"]\s*(\d{1,2})['\"]\s*([\d.]+)"
    match = re.search(quote_pattern, value)
    if match:
        d, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
        result = d + m/60 + s/3600
        if 0 < result < 180:
            return -result if is_south_or_west else result

    # Pattern 6: Degree-minute only - 14°02' or 13°56'
    dm_pattern = r"(\d+)\s*°\s*(\d+(?:\.\d+)?)\s*['\u2019]?"
    match = re.search(dm_pattern, value)
    if match:
        d, m = float(match.group(1)), float(match.group(2))
        result = d + m/60
        if 0 < result < 180:
            return -result if is_south_or_west else result

    # Pattern 7: Extract any decimal number as last resort
    decimal_match = re.search(r'(\d+\.?\d*)', value)
    if decimal_match:
        result = float(decimal_match.group(1))
        if 0 < result < 180:
            return -result if is_south_or_west else result

    return None


def clean_coordinates(wpp: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and parse all coordinate columns in WPP data.
    Creates new columns: lat_parsed, lon_parsed
    """
    print("\nCleaning coordinates...")

    # Parse latitude
    wpp['lat_parsed'] = wpp['latitude'].apply(parse_coordinate)
    lat_clean_parsed = wpp['latitude_clean'].apply(parse_coordinate)
    # Use latitude_clean if latitude parsing failed
    wpp['lat_parsed'] = wpp['lat_parsed'].fillna(lat_clean_parsed)

    # Parse longitude
    wpp['lon_parsed'] = wpp['longitude'].apply(parse_coordinate)
    lon_clean_parsed = wpp['longitude_clean'].apply(parse_coordinate)
    # Use longitude_clean if longitude parsing failed
    wpp['lon_parsed'] = wpp['lon_parsed'].fillna(lon_clean_parsed)

    # Stats
    lat_success = wpp['lat_parsed'].notna().sum()
    lon_success = wpp['lon_parsed'].notna().sum()
    print(f"  Latitude parsed: {lat_success}/{len(wpp)} ({lat_success/len(wpp)*100:.1f}%)")
    print(f"  Longitude parsed: {lon_success}/{len(wpp)} ({lon_success/len(wpp)*100:.1f}%)")

    return wpp


def load_wpp_data(filepath: str) -> gpd.GeoDataFrame:
    """Load WPP data and create GeoDataFrame from coordinates."""
    print("Loading WPP data...")

    # Load CSV (skip description row)
    wpp = pd.read_csv(filepath, skiprows=[1], encoding='latin-1', low_memory=False)
    print(f"  Total WPP records: {len(wpp)}")

    # Clean and parse coordinates
    wpp = clean_coordinates(wpp)

    # Use parsed coordinates
    wpp['lat'] = wpp['lat_parsed']
    wpp['lon'] = wpp['lon_parsed']

    # Filter to valid Karnataka coordinates (roughly 11-19 lat, 74-79 long)
    valid_mask = (
        (wpp['lat'] >= 11) & (wpp['lat'] <= 19) &
        (wpp['lon'] >= 74) & (wpp['lon'] <= 79)
    )
    wpp_valid = wpp[valid_mask].copy()
    print(f"  Records with valid Karnataka coordinates: {len(wpp_valid)}")
    print(f"  Records with invalid/missing coordinates: {len(wpp) - len(wpp_valid)}")

    # Create geometry
    geometry = [Point(lon, lat) for lon, lat in zip(wpp_valid['lon'], wpp_valid['lat'])]
    wpp_gdf = gpd.GeoDataFrame(wpp_valid, geometry=geometry, crs="EPSG:4326")

    return wpp_gdf, wpp[~valid_mask]


def load_shrug_villages(gpkg_path: str, state_filter: str = 'karnataka') -> gpd.GeoDataFrame:
    """Load SHRUG village boundaries from GPKG file."""
    print(f"\nLoading SHRUG villages from {gpkg_path}...")

    shrug = gpd.read_file(gpkg_path)
    print(f"  Total SHRUG villages: {len(shrug)}")

    # Filter to Karnataka if state column exists
    state_cols = [c for c in shrug.columns if 'state' in c.lower()]
    if state_cols and state_filter:
        state_col = state_cols[0]
        shrug = shrug[shrug[state_col].str.lower() == state_filter.lower()]
        print(f"  Karnataka villages: {len(shrug)}")

    # Ensure CRS matches
    if shrug.crs != "EPSG:4326":
        shrug = shrug.to_crs("EPSG:4326")

    return shrug


def spatial_join_with_nearest(wpp_gdf: gpd.GeoDataFrame,
                               shrug_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Perform spatial join with nearest village selection for points in multiple villages.

    Strategy:
    1. First do point-in-polygon join
    2. For points matching multiple villages, select the closest (by centroid distance)
    3. For points matching no villages, find nearest village
    """
    print("\nPerforming spatial join...")

    # Step 1: Point-in-polygon join
    joined = gpd.sjoin(wpp_gdf, shrug_gdf, how='left', predicate='within')

    # Count matches per WPP point
    wpp_gdf['_idx'] = range(len(wpp_gdf))
    match_counts = joined.groupby(joined.index).size()

    multi_match = match_counts[match_counts > 1]
    no_match = wpp_gdf.index[~wpp_gdf.index.isin(joined.index)]
    single_match = match_counts[match_counts == 1]

    print(f"  Single village match: {len(single_match)}")
    print(f"  Multiple village match: {len(multi_match)}")
    print(f"  No village match: {len(no_match)}")

    # Step 2: Handle multiple matches - select closest village by centroid
    if len(multi_match) > 0:
        print("\nResolving multiple matches (selecting closest village)...")

        # Calculate centroids for distance comparison
        shrug_gdf['centroid'] = shrug_gdf.geometry.centroid

        for idx in multi_match.index:
            point = wpp_gdf.loc[idx, 'geometry']
            matches = joined[joined.index == idx]

            # Calculate distance to each village centroid
            min_dist = float('inf')
            best_match_idx = None

            for _, match_row in matches.iterrows():
                village_idx = match_row['index_right']
                centroid = shrug_gdf.loc[village_idx, 'centroid']
                dist = point.distance(centroid)

                if dist < min_dist:
                    min_dist = dist
                    best_match_idx = match_row.name

            # Keep only the closest match
            drop_indices = matches.index[matches.index != best_match_idx]
            joined = joined.drop(drop_indices)

    # Step 3: Handle no matches - find nearest village
    if len(no_match) > 0:
        print(f"\nFinding nearest villages for {len(no_match)} unmatched points...")

        from shapely.ops import nearest_points

        # Create union of all village boundaries for nearest search
        shrug_union = shrug_gdf.unary_union

        nearest_matches = []
        for idx in no_match:
            point = wpp_gdf.loc[idx, 'geometry']

            # Find nearest point on any village boundary
            nearest_geom = nearest_points(point, shrug_union)[1]

            # Find which village contains this nearest point
            for shrug_idx, row in shrug_gdf.iterrows():
                if row.geometry.contains(nearest_geom) or row.geometry.touches(nearest_geom):
                    # Create match record
                    match_record = wpp_gdf.loc[idx].copy()
                    for col in shrug_gdf.columns:
                        if col != 'geometry' and col != 'centroid':
                            match_record[col] = row[col]
                    match_record['index_right'] = shrug_idx
                    match_record['_nearest_match'] = True
                    nearest_matches.append(match_record)
                    break

        if nearest_matches:
            nearest_df = pd.DataFrame(nearest_matches)
            joined = pd.concat([joined, nearest_df], ignore_index=True)

    return joined


def analyze_results(merged: gpd.GeoDataFrame, shrug_id_col: str = 'shrid2'):
    """Analyze merge results for many-to-many relationships."""
    print("\n" + "="*60)
    print("MERGE ANALYSIS")
    print("="*60)

    total = len(merged)
    with_shrid = merged[shrug_id_col].notna().sum()
    without_shrid = merged[shrug_id_col].isna().sum()

    print(f"\nTotal WPP records processed: {total}")
    print(f"Matched to SHRUG: {with_shrid} ({with_shrid/total*100:.2f}%)")
    print(f"Unmatched: {without_shrid} ({without_shrid/total*100:.2f}%)")

    # Check many-to-many relationships
    print("\nRelationship Analysis:")

    # WPP to SHRUG (should be 1:1 or 1:0)
    wpp_to_shrug = merged.groupby('_idx')[shrug_id_col].nunique()
    multi_shrug = wpp_to_shrug[wpp_to_shrug > 1]
    print(f"  WPP points with multiple SHRUG: {len(multi_shrug)}")

    # SHRUG to WPP (can be 1:many - multiple WPPs in one village)
    if shrug_id_col in merged.columns:
        shrug_to_wpp = merged[merged[shrug_id_col].notna()].groupby(shrug_id_col)['_idx'].nunique()
        multi_wpp = shrug_to_wpp[shrug_to_wpp > 1]
        print(f"  SHRUG villages with multiple WPP: {len(multi_wpp)}")
        print(f"  Max WPP per village: {shrug_to_wpp.max()}")


def main():
    parser = argparse.ArgumentParser(description='Merge WPP data with SHRUG villages spatially')
    parser.add_argument('--shrug-gpkg', required=True, help='Path to SHRUG village GPKG file')
    parser.add_argument('--wpp-csv', default='WPP details_clean_full(Data1).csv',
                        help='Path to WPP CSV file')
    parser.add_argument('--output', default='wpp_shrug_spatial_merged.csv',
                        help='Output CSV file path')
    parser.add_argument('--shrid-col', default='shrid2',
                        help='SHRUG ID column name in GPKG')
    args = parser.parse_args()

    # Load data
    wpp_gdf, wpp_invalid = load_wpp_data(args.wpp_csv)
    shrug_gdf = load_shrug_villages(args.shrug_gpkg)

    # Perform spatial join
    merged = spatial_join_with_nearest(wpp_gdf, shrug_gdf)

    # Analyze results
    analyze_results(merged, args.shrid_col)

    # Save results
    print(f"\nSaving results to {args.output}...")

    # Drop geometry columns for CSV output
    output_df = merged.drop(columns=['geometry', 'centroid'], errors='ignore')
    output_df.to_csv(args.output, index=False)

    # Save invalid coordinates separately
    invalid_output = args.output.replace('.csv', '_invalid_coords.csv')
    wpp_invalid.to_csv(invalid_output, index=False)
    print(f"Saved invalid coordinates to {invalid_output}")

    print("\nDone!")

    return merged


if __name__ == '__main__':
    main()
