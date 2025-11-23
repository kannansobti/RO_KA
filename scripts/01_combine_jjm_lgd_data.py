#!/usr/bin/env python3
"""
Phase 1: Combine JJM-LGD District Data

Combines individual district HTML/Excel files downloaded from JJM portal into
a single standardized CSV file.

Input: Individual district files from JJM portal (HTML tables saved as .xls)
Output: jjm_lgd_mapping_karnataka.csv

Source: https://ejalshakti.gov.in/JJM/JJMReports/lgd_mapping/rpt_LGDMappedStatus_d.aspx
"""

import pandas as pd
import os
import re
from pathlib import Path
import argparse


def read_jjm_district_file(filepath: str) -> pd.DataFrame:
    """
    Read a JJM district file (HTML table saved as .xls).

    Args:
        filepath: Path to the district file

    Returns:
        DataFrame with standardized columns
    """
    # Try reading as HTML first (most JJM files are HTML disguised as .xls)
    try:
        tables = pd.read_html(filepath)
        if tables:
            df = tables[0]
        else:
            raise ValueError("No tables found")
    except:
        # Fall back to Excel
        try:
            df = pd.read_excel(filepath)
        except:
            # Try CSV
            df = pd.read_csv(filepath)

    return df


def standardize_columns(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """
    Standardize column names across different district file formats.

    Args:
        df: Raw DataFrame from district file
        source_file: Source filename for reference

    Returns:
        DataFrame with standardized columns
    """
    # Common column name mappings
    column_mappings = {
        'panchayat id': 'jjm_panchayat_id',
        'panchayatid': 'jjm_panchayat_id',
        'panchayat name': 'jjm_panchayat',
        'panchayatname': 'jjm_panchayat',
        'village id': 'jjm_village_id',
        'villageid': 'jjm_village_id',
        'imis village id': 'jjm_village_id',
        'village name': 'jjm_village',
        'villagename': 'jjm_village',
        'imis village name': 'jjm_village',
        'lgd village code': 'lgd_village_id',
        'lgd code': 'lgd_village_id',
        'lgdvillagecode': 'lgd_village_id',
        'lgd village name': 'lgd_village',
        'lgdvillagename': 'lgd_village',
        'block': 'jjm_block',
        'block name': 'jjm_block',
        'blockname': 'jjm_block',
        'district': 'jjm_district',
        'district name': 'jjm_district',
        'districtname': 'jjm_district',
    }

    # Normalize column names
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Apply mappings
    rename_dict = {}
    for old_name, new_name in column_mappings.items():
        if old_name in df.columns:
            rename_dict[old_name] = new_name

    df = df.rename(columns=rename_dict)

    # Add source file reference
    df['source_file'] = source_file

    return df


def extract_district_from_filename(filename: str) -> str:
    """Extract district name from filename."""
    # Remove extension and common prefixes/suffixes
    name = Path(filename).stem
    name = re.sub(r'[_\-\d]+', ' ', name)
    name = name.strip().upper()
    return name


def combine_district_files(input_dir: str) -> pd.DataFrame:
    """
    Combine all district files from a directory.

    Args:
        input_dir: Directory containing district files

    Returns:
        Combined DataFrame with all districts
    """
    all_data = []

    # Find all potential data files
    extensions = ['.xls', '.xlsx', '.csv', '.html']
    files = []
    for ext in extensions:
        files.extend(Path(input_dir).glob(f'*{ext}'))

    print(f"Found {len(files)} files to process")

    for filepath in sorted(files):
        print(f"  Processing: {filepath.name}")

        try:
            df = read_jjm_district_file(str(filepath))
            df = standardize_columns(df, filepath.name)

            # Extract district from filename if not in data
            if 'jjm_district' not in df.columns or df['jjm_district'].isna().all():
                df['district_from_header'] = extract_district_from_filename(filepath.name)
            else:
                df['district_from_header'] = df['jjm_district'].iloc[0] if len(df) > 0 else ''

            all_data.append(df)
            print(f"    -> {len(df)} records")

        except Exception as e:
            print(f"    -> ERROR: {str(e)}")

    if not all_data:
        raise ValueError("No data files could be processed")

    # Combine all dataframes
    combined = pd.concat(all_data, ignore_index=True)

    return combined


def validate_data(df: pd.DataFrame) -> dict:
    """
    Validate the combined data.

    Returns:
        Dictionary with validation results
    """
    results = {
        'total_records': len(df),
        'unique_villages': df['jjm_village_id'].nunique() if 'jjm_village_id' in df.columns else 0,
        'unique_districts': df['jjm_district'].nunique() if 'jjm_district' in df.columns else 0,
        'missing_lgd_ids': df['lgd_village_id'].isna().sum() if 'lgd_village_id' in df.columns else len(df),
        'duplicate_jjm_ids': df['jjm_village_id'].duplicated().sum() if 'jjm_village_id' in df.columns else 0,
    }

    # Check for LGD duplicates (multiple JJM -> same LGD)
    if 'lgd_village_id' in df.columns and 'jjm_village_id' in df.columns:
        lgd_counts = df.groupby('lgd_village_id')['jjm_village_id'].nunique()
        results['lgd_with_multiple_jjm'] = (lgd_counts > 1).sum()

    return results


def main():
    parser = argparse.ArgumentParser(description='Combine JJM-LGD district data files')
    parser.add_argument('--input-dir', default='JJM ID to LGD',
                        help='Directory containing district files')
    parser.add_argument('--output', default='jjm_lgd_mapping_karnataka.csv',
                        help='Output CSV file path')
    args = parser.parse_args()

    print("="*60)
    print("Phase 1: Combine JJM-LGD District Data")
    print("="*60)

    # Combine files
    print(f"\nReading files from: {args.input_dir}")
    combined = combine_district_files(args.input_dir)

    # Add state column
    combined['state'] = 'Karnataka'

    # Reorder columns
    preferred_order = [
        'state', 'jjm_district', 'jjm_block', 'jjm_panchayat_id', 'jjm_panchayat',
        'jjm_village_id', 'jjm_village', 'lgd_village_id', 'lgd_village',
        'district_from_header', 'source_file'
    ]
    existing_cols = [c for c in preferred_order if c in combined.columns]
    other_cols = [c for c in combined.columns if c not in preferred_order]
    combined = combined[existing_cols + other_cols]

    # Validate
    print("\nValidation Results:")
    results = validate_data(combined)
    for key, value in results.items():
        print(f"  {key}: {value}")

    # Save
    combined.to_csv(args.output, index=False)
    print(f"\nSaved to: {args.output}")
    print(f"Total records: {len(combined)}")

    return combined


if __name__ == '__main__':
    main()
