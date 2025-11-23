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


def load_wpp_data(filepath: str) -> gpd.GeoDataFrame:
    """Load WPP data and create GeoDataFrame from coordinates."""
    print("Loading WPP data...")

    # Load CSV (skip description row)
    wpp = pd.read_csv(filepath, skiprows=[1], encoding='latin-1', low_memory=False)
    print(f"  Total WPP records: {len(wpp)}")

    # Convert coordinates to numeric
    wpp['lat'] = pd.to_numeric(wpp['latitude_clean'], errors='coerce')
    wpp['lon'] = pd.to_numeric(wpp['longitude_clean'], errors='coerce')

    # Filter to valid Karnataka coordinates (roughly 11-19 lat, 74-79 long)
    valid_mask = (
        (wpp['lat'] >= 11) & (wpp['lat'] <= 19) &
        (wpp['lon'] >= 74) & (wpp['lon'] <= 79)
    )
    wpp_valid = wpp[valid_mask].copy()
    print(f"  Records with valid coordinates: {len(wpp_valid)}")
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
