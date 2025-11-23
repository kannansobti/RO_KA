#!/usr/bin/env python3
"""
Phase 2: Direct LGD-SHRUG Matching

Matches JJM villages to SHRUG using LGD village codes.

Input:
    - jjm_lgd_mapping_karnataka.csv (from Phase 1)
    - shrid_loc_names.csv (SHRUG location data)

Output:
    - jjm_to_shrug_direct_mapping.csv (all villages with SHRUG matches where available)
    - jjm_lgd_to_shrid_unmatched.csv (villages without direct match)
"""

import pandas as pd
import argparse
from pathlib import Path


def load_jjm_data(filepath: str) -> pd.DataFrame:
    """Load JJM-LGD mapping data."""
    print(f"Loading JJM data from {filepath}...")
    df = pd.read_csv(filepath)
    print(f"  Records: {len(df)}")
    print(f"  Unique villages: {df['jjm_village_id'].nunique()}")
    return df


def load_shrug_data(filepath: str, state_filter: str = 'karnataka') -> pd.DataFrame:
    """Load SHRUG location data."""
    print(f"\nLoading SHRUG data from {filepath}...")
    df = pd.read_csv(filepath)
    print(f"  Total records: {len(df)}")

    # Filter to state
    if state_filter:
        df = df[df['state_name'].str.lower() == state_filter.lower()]
        print(f"  {state_filter.title()} records: {len(df)}")

    return df


def extract_lgd_from_shrid(shrid: str) -> str:
    """
    Extract LGD village code from SHRID.
    SHRID format: 11-29-XXX-XXXXX-XXXXXX
    Last 6 digits are LGD village code.
    """
    if pd.isna(shrid):
        return None
    parts = str(shrid).split('-')
    if len(parts) >= 5:
        return parts[-1]
    return None


def perform_direct_match(jjm_df: pd.DataFrame, shrug_df: pd.DataFrame) -> tuple:
    """
    Match JJM villages to SHRUG using LGD codes.

    Returns:
        Tuple of (matched_df, unmatched_df)
    """
    print("\nPerforming direct LGD matching...")

    # Extract LGD code from SHRID
    shrug_df = shrug_df.copy()
    shrug_df['shrug_lgd_code'] = shrug_df['shrid2'].apply(extract_lgd_from_shrid)

    # Convert LGD codes to string for matching
    jjm_df = jjm_df.copy()
    jjm_df['lgd_village_id_str'] = jjm_df['lgd_village_id'].astype(str).str.strip()
    shrug_df['shrug_lgd_code'] = shrug_df['shrug_lgd_code'].astype(str).str.strip()

    # Merge on LGD code
    merged = jjm_df.merge(
        shrug_df[['shrid2', 'shrug_lgd_code', 'village_name', 'district_name', 'subdistrict_name']],
        left_on='lgd_village_id_str',
        right_on='shrug_lgd_code',
        how='left'
    )

    # Rename SHRUG columns
    merged = merged.rename(columns={
        'shrid2': 'shrug_shrid2',
        'village_name': 'shrug_village_name',
        'district_name': 'shrug_district',
        'subdistrict_name': 'shrug_subdistrict'
    })

    # Split into matched and unmatched
    matched = merged[merged['shrug_shrid2'].notna()]
    unmatched = merged[merged['shrug_shrid2'].isna()]

    print(f"  Matched: {len(matched)} ({len(matched)/len(merged)*100:.2f}%)")
    print(f"  Unmatched: {len(unmatched)} ({len(unmatched)/len(merged)*100:.2f}%)")

    return merged, unmatched


def analyze_relationships(df: pd.DataFrame) -> dict:
    """Analyze many-to-many relationships in the mapping."""
    results = {}

    # JJM to SHRUG (should be 1:1)
    if 'jjm_village_id' in df.columns and 'shrug_shrid2' in df.columns:
        matched = df[df['shrug_shrid2'].notna()]
        jjm_to_shrug = matched.groupby('jjm_village_id')['shrug_shrid2'].nunique()
        results['jjm_to_multiple_shrug'] = (jjm_to_shrug > 1).sum()

        # SHRUG to JJM
        shrug_to_jjm = matched.groupby('shrug_shrid2')['jjm_village_id'].nunique()
        results['shrug_to_multiple_jjm'] = (shrug_to_jjm > 1).sum()

    # LGD to SHRUG
    if 'lgd_village_id' in df.columns and 'shrug_shrid2' in df.columns:
        matched = df[df['shrug_shrid2'].notna()]
        lgd_to_shrug = matched.groupby('lgd_village_id')['shrug_shrid2'].nunique()
        results['lgd_to_multiple_shrug'] = (lgd_to_shrug > 1).sum()

    return results


def main():
    parser = argparse.ArgumentParser(description='Match JJM villages to SHRUG via LGD codes')
    parser.add_argument('--jjm-file', default='jjm_lgd_mapping_karnataka.csv',
                        help='JJM-LGD mapping CSV file')
    parser.add_argument('--shrug-file', default='shrid_loc_names.csv',
                        help='SHRUG location names CSV file')
    parser.add_argument('--output-matched', default='jjm_to_shrug_direct_mapping.csv',
                        help='Output file for all records with matches')
    parser.add_argument('--output-unmatched', default='jjm_lgd_to_shrid_unmatched.csv',
                        help='Output file for unmatched records')
    args = parser.parse_args()

    print("="*60)
    print("Phase 2: Direct LGD-SHRUG Matching")
    print("="*60)

    # Load data
    jjm_df = load_jjm_data(args.jjm_file)
    shrug_df = load_shrug_data(args.shrug_file)

    # Perform matching
    matched_df, unmatched_df = perform_direct_match(jjm_df, shrug_df)

    # Analyze relationships
    print("\nRelationship Analysis:")
    relationships = analyze_relationships(matched_df)
    for key, value in relationships.items():
        status = "✓ Clean" if value == 0 else f"⚠️ {value} cases"
        print(f"  {key}: {status}")

    # Save results
    print(f"\nSaving matched records to: {args.output_matched}")
    matched_df.to_csv(args.output_matched, index=False)

    print(f"Saving unmatched records to: {args.output_unmatched}")
    unmatched_df.to_csv(args.output_unmatched, index=False)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total JJM villages: {len(jjm_df)}")
    print(f"Matched to SHRUG: {len(matched_df[matched_df['shrug_shrid2'].notna()])}")
    print(f"Unmatched: {len(unmatched_df)}")

    return matched_df, unmatched_df


if __name__ == '__main__':
    main()
