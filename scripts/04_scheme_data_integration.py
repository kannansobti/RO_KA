#!/usr/bin/env python3
"""
Phase 4: Scheme Data Integration

Creates final village-to-SHRID mapping and integrates with scheme data.

Input:
    - jjm_to_shrug_direct_mapping.csv (from Phase 2)
    - jjm_shrug_all_matches.csv (from Phase 3)
    - Karnataka Scheme Details.xlsx (optional, for integration)

Output:
    - villageid_to_shrid_mapping.csv (final mapping file)
    - scheme_villages_without_shrid.csv (unmatched villages in scheme data)
"""

import pandas as pd
import argparse
from pathlib import Path


def create_unified_mapping(direct_file: str, fuzzy_file: str) -> pd.DataFrame:
    """
    Create unified village ID to SHRID mapping.

    Args:
        direct_file: Direct LGD-SHRUG matches
        fuzzy_file: Fuzzy name-based matches

    Returns:
        Unified mapping DataFrame
    """
    print("Creating unified mapping...")

    # Load direct matches
    direct = pd.read_csv(direct_file)
    direct_map = direct[['jjm_village_id', 'shrug_shrid2', 'jjm_village',
                         'lgd_village_id', 'jjm_district']].dropna(subset=['shrug_shrid2'])
    direct_map = direct_map.rename(columns={'shrug_shrid2': 'shrid2'})
    direct_map['match_source'] = 'lgd_direct'
    print(f"  Direct matches: {len(direct_map)}")

    # Load fuzzy matches
    try:
        fuzzy = pd.read_csv(fuzzy_file)
        fuzzy_map = fuzzy[['jjm_village_id', 'shrid2', 'jjm_village',
                           'lgd_village_id', 'jjm_district', 'match_method']].copy()
        fuzzy_map = fuzzy_map.rename(columns={'match_method': 'match_source'})
        print(f"  Fuzzy matches: {len(fuzzy_map)}")
    except FileNotFoundError:
        fuzzy_map = pd.DataFrame()
        print("  No fuzzy matches file found")

    # Combine (exclude fuzzy matches for villages already in direct)
    if len(fuzzy_map) > 0:
        direct_ids = set(direct_map['jjm_village_id'])
        fuzzy_new = fuzzy_map[~fuzzy_map['jjm_village_id'].isin(direct_ids)]
        print(f"  New from fuzzy (not in direct): {len(fuzzy_new)}")
        unified = pd.concat([direct_map, fuzzy_new], ignore_index=True)
    else:
        unified = direct_map

    # Rename for clarity
    unified = unified.rename(columns={
        'jjm_village_id': 'villageid',
        'jjm_village': 'village_name',
        'jjm_district': 'district'
    })

    print(f"  Total unified mappings: {len(unified)}")

    return unified


def integrate_with_scheme(mapping: pd.DataFrame, scheme_file: str) -> tuple:
    """
    Integrate mapping with scheme data and analyze coverage.

    Args:
        mapping: Village to SHRID mapping
        scheme_file: Path to scheme data Excel file

    Returns:
        Tuple of (coverage_stats, unmatched_villages)
    """
    print(f"\nLoading scheme data from {scheme_file}...")
    scheme = pd.read_excel(scheme_file)
    print(f"  Total scheme records: {len(scheme)}")

    # Filter to valid villages (villageid > 0)
    valid_scheme = scheme[scheme['villageid'] > 0]
    print(f"  Valid village records: {len(valid_scheme)}")

    # Get unique villages
    scheme_villages = valid_scheme[['villageid', 'villagename']].drop_duplicates()
    print(f"  Unique villages in scheme: {len(scheme_villages)}")

    # Check coverage
    mapping_ids = set(mapping['villageid'])
    scheme_ids = set(scheme_villages['villageid'])

    matched = scheme_ids & mapping_ids
    unmatched = scheme_ids - mapping_ids

    coverage_stats = {
        'total_scheme_records': len(scheme),
        'valid_village_records': len(valid_scheme),
        'unique_villages': len(scheme_villages),
        'villages_with_shrid': len(matched),
        'villages_without_shrid': len(unmatched),
        'coverage_pct': len(matched) / len(scheme_villages) * 100 if len(scheme_villages) > 0 else 0
    }

    # Get unmatched village details
    unmatched_df = scheme_villages[scheme_villages['villageid'].isin(unmatched)]

    return coverage_stats, unmatched_df


def analyze_relationships(mapping: pd.DataFrame) -> dict:
    """Analyze many-to-many relationships in the mapping."""
    results = {}

    # Village to SHRID (should be 1:1)
    village_to_shrid = mapping.groupby('villageid')['shrid2'].nunique()
    results['village_to_multiple_shrid'] = (village_to_shrid > 1).sum()

    # SHRID to Village (can have duplicates)
    shrid_to_village = mapping.groupby('shrid2')['villageid'].nunique()
    results['shrid_to_multiple_village'] = (shrid_to_village > 1).sum()

    return results


def main():
    parser = argparse.ArgumentParser(description='Create unified mapping and integrate with scheme data')
    parser.add_argument('--direct-file', default='jjm_to_shrug_direct_mapping.csv',
                        help='Direct LGD-SHRUG matches from Phase 2')
    parser.add_argument('--fuzzy-file', default='jjm_shrug_all_matches.csv',
                        help='Fuzzy matches from Phase 3')
    parser.add_argument('--scheme-file', default=None,
                        help='Scheme data Excel file (optional)')
    parser.add_argument('--output-mapping', default='villageid_to_shrid_mapping.csv',
                        help='Output mapping file')
    parser.add_argument('--output-unmatched', default='scheme_villages_without_shrid.csv',
                        help='Output file for unmatched scheme villages')
    args = parser.parse_args()

    print("="*60)
    print("Phase 4: Scheme Data Integration")
    print("="*60)

    # Create unified mapping
    mapping = create_unified_mapping(args.direct_file, args.fuzzy_file)

    # Analyze relationships
    print("\nRelationship Analysis:")
    relationships = analyze_relationships(mapping)
    for key, value in relationships.items():
        status = "✓ Clean" if value == 0 else f"⚠️ {value} cases"
        print(f"  {key}: {status}")

    # Save mapping
    mapping.to_csv(args.output_mapping, index=False)
    print(f"\nSaved mapping to: {args.output_mapping}")

    # Integrate with scheme data if provided
    if args.scheme_file and Path(args.scheme_file).exists():
        print("\n" + "-"*60)
        coverage, unmatched = integrate_with_scheme(mapping, args.scheme_file)

        print("\nScheme Data Coverage:")
        for key, value in coverage.items():
            if key == 'coverage_pct':
                print(f"  {key}: {value:.2f}%")
            else:
                print(f"  {key}: {value:,}")

        # Save unmatched
        unmatched.to_csv(args.output_unmatched, index=False)
        print(f"\nSaved unmatched villages to: {args.output_unmatched}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total village mappings: {len(mapping)}")

    by_source = mapping['match_source'].value_counts()
    for source, count in by_source.items():
        print(f"  {source}: {count}")


if __name__ == '__main__':
    main()
