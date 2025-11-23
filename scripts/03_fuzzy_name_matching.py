#!/usr/bin/env python3
"""
Phase 3: Fuzzy Name-Based Matching

Matches unmatched JJM villages to SHRUG using fuzzy string matching
with Kannada transliteration normalization.

Input:
    - jjm_lgd_to_shrid_unmatched.csv (from Phase 2)
    - shrid_loc_names.csv (SHRUG location data)
    - jjm_manual_name_district_shrid_mapping.csv (optional manual mappings)

Output:
    - jjm_shrug_matches_strict.csv (strict fuzzy matches)
    - jjm_kannada_norm_matches.csv (Kannada normalized matches)
    - jjm_shrug_all_matches.csv (combined fuzzy matches)
    - jjm_still_unmatched_final.csv (remaining unmatched)
"""

import pandas as pd
import re
from collections import defaultdict
import argparse

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: rapidfuzz not installed. Run: pip install rapidfuzz")
    exit(1)


# District name mapping (JJM -> SHRUG)
DISTRICT_MAP = {
    'bengaluru rural': 'bangalore rural',
    'bengaluru urban': 'bangalore',
    'ballari': 'bellary',
    'belagavi': 'belgaum',
    'chamarajanagara': 'chamarajanagar',
    'davangere': 'davanagere',
    'kalaburagi': 'gulbarga',
    'mysuru': 'mysore',
    'shivamogga': 'shimoga',
    'tumakuru': 'tumkur',
    'vijayapura': 'bijapur',
    'bagalkote': 'bagalkot',
    'chikkamagaluru': 'chikmagalur',
    'vijayanagar': 'bellary',  # New district carved from Bellary
}


def normalize_name(name: str) -> str:
    """Basic normalization of village names."""
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)  # Remove parenthetical
    name = re.sub(r'[^a-z\s]', '', name)  # Keep only letters and spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def kannada_normalize(name: str) -> str:
    """Apply Kannada transliteration normalizations."""
    if not name:
        return name

    # Common suffix/spelling variations
    replacements = [
        (r'hally$', 'halli'),
        (r'haly$', 'halli'),
        (r'hali$', 'halli'),
        (r'pura$', 'pura'),
        (r'pur$', 'pura'),
        (r'puram$', 'pura'),
        (r'keri$', 'kere'),
        (r'geri$', 'gere'),
        # Double consonants
        (r'kk', 'k'), (r'pp', 'p'), (r'tt', 't'),
        (r'dd', 'd'), (r'nn', 'n'), (r'mm', 'm'), (r'll', 'l'),
        # Double vowels
        (r'aa', 'a'), (r'ee', 'i'), (r'ii', 'i'),
        (r'oo', 'u'), (r'uu', 'u'),
    ]

    for pattern, repl in replacements:
        name = re.sub(pattern, repl, name)

    return name


def get_shrug_district(jjm_district: str) -> str:
    """Map JJM district name to SHRUG district name."""
    return DISTRICT_MAP.get(jjm_district.lower(), jjm_district.lower())


def build_shrug_lookup(shrug_df: pd.DataFrame) -> dict:
    """Build lookup dictionary of SHRUG villages by district."""
    lookup = defaultdict(list)

    for _, row in shrug_df.iterrows():
        dist = row['district_name'].lower() if pd.notna(row['district_name']) else ''
        village = row['village_name'] if pd.notna(row['village_name']) else ''
        place = row['place_name'] if pd.notna(row['place_name']) else ''

        norm_village = normalize_name(village)
        norm_place = normalize_name(place)

        lookup[dist].append({
            'shrid2': row['shrid2'],
            'district_name': row['district_name'],
            'subdistrict_name': row['subdistrict_name'],
            'village_name': village,
            'place_name': place,
            'norm_village': norm_village,
            'norm_place': norm_place,
            'kann_village': kannada_normalize(norm_village),
            'kann_place': kannada_normalize(norm_place),
        })

    return lookup


def strict_fuzzy_match(jjm_village: str, jjm_district: str, lgd_village: str,
                       shrug_lookup: dict, threshold: int = 85) -> dict:
    """
    Strict fuzzy matching using only fuzz.ratio (no partial matching).

    Args:
        jjm_village: JJM village name
        jjm_district: JJM district name
        lgd_village: LGD village name
        shrug_lookup: SHRUG lookup dictionary
        threshold: Minimum match score (default 85)

    Returns:
        Best match dict or None
    """
    shrug_dist = get_shrug_district(jjm_district)
    candidates = shrug_lookup.get(shrug_dist, [])

    if not candidates:
        return None

    jjm_norm = normalize_name(jjm_village)
    lgd_norm = normalize_name(lgd_village)

    best_match = None
    best_score = 0

    for cand in candidates:
        for name_field in ['norm_village', 'norm_place']:
            cand_name = cand[name_field]
            if not cand_name:
                continue

            for query in [jjm_norm, lgd_norm]:
                if not query:
                    continue

                # Only use fuzz.ratio for strict full-string matching
                score = fuzz.ratio(query, cand_name)

                # Length ratio check to prevent short names matching in longer names
                len_ratio = min(len(query), len(cand_name)) / max(len(query), len(cand_name))
                if len_ratio < 0.7:
                    continue

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = {
                        'shrid2': cand['shrid2'],
                        'district_name': cand['district_name'],
                        'subdistrict_name': cand['subdistrict_name'],
                        'village_name': cand['village_name'],
                        'place_name': cand['place_name'],
                        'match_score': score,
                    }

    return best_match


def kannada_normalized_match(jjm_village: str, jjm_district: str, lgd_village: str,
                              shrug_lookup: dict, threshold: int = 85) -> dict:
    """
    Match using Kannada-normalized names.
    """
    shrug_dist = get_shrug_district(jjm_district)
    candidates = shrug_lookup.get(shrug_dist, [])

    if not candidates:
        return None

    jjm_norm = normalize_name(jjm_village)
    lgd_norm = normalize_name(lgd_village)
    jjm_kann = kannada_normalize(jjm_norm)
    lgd_kann = kannada_normalize(lgd_norm)

    best_match = None
    best_score = 0

    for cand in candidates:
        for query_norm, query_kann in [(jjm_norm, jjm_kann), (lgd_norm, lgd_kann)]:
            if not query_norm:
                continue

            for name_type in ['village', 'place']:
                cand_norm = cand[f'norm_{name_type}']
                cand_kann = cand[f'kann_{name_type}']
                if not cand_norm:
                    continue

                # Try both normalized and kannada-normalized
                scores = [
                    fuzz.ratio(query_norm, cand_norm),
                    fuzz.ratio(query_kann, cand_kann) if query_kann and cand_kann else 0,
                ]

                score = max(scores)

                # Length ratio check
                len_ratio = min(len(query_norm), len(cand_norm)) / max(len(query_norm), len(cand_norm))
                if len_ratio < 0.7:
                    continue

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = {
                        'shrid2': cand['shrid2'],
                        'district_name': cand['district_name'],
                        'subdistrict_name': cand['subdistrict_name'],
                        'village_name': cand['village_name'],
                        'place_name': cand['place_name'],
                        'match_score': score,
                    }

    return best_match


def main():
    parser = argparse.ArgumentParser(description='Fuzzy name-based matching for unmatched villages')
    parser.add_argument('--unmatched-file', default='jjm_lgd_to_shrid_unmatched.csv',
                        help='Unmatched villages from Phase 2')
    parser.add_argument('--shrug-file', default='shrid_loc_names.csv',
                        help='SHRUG location names CSV file')
    parser.add_argument('--manual-file', default='jjm_manual_name_district_shrid_mapping.csv',
                        help='Manual mappings CSV file (optional)')
    parser.add_argument('--threshold', type=int, default=85,
                        help='Minimum fuzzy match score (default: 85)')
    parser.add_argument('--output-dir', default='.',
                        help='Output directory')
    args = parser.parse_args()

    print("="*60)
    print("Phase 3: Fuzzy Name-Based Matching")
    print("="*60)

    # Load data
    print("\nLoading data...")
    unmatched = pd.read_csv(args.unmatched_file)
    print(f"  Unmatched villages: {len(unmatched)}")

    shrug = pd.read_csv(args.shrug_file)
    shrug_ka = shrug[shrug['state_name'].str.lower() == 'karnataka']
    print(f"  SHRUG Karnataka villages: {len(shrug_ka)}")

    # Load manual mappings if available
    manual_ids = set()
    manual_matches = []
    try:
        manual = pd.read_csv(args.manual_file)
        manual_ids = set(manual['jjm_village_id'].astype(str))
        print(f"  Manual mappings: {len(manual)}")

        # Format manual matches
        for _, row in manual.iterrows():
            manual_matches.append({
                'jjm_village_id': row['jjm_village_id'],
                'jjm_village': row['jjm_village'],
                'jjm_district': row['jjm_district'],
                'jjm_block': row.get('jjm_block', ''),
                'jjm_panchayat_id': row.get('jjm_panchayat_id', ''),
                'jjm_panchayat': row.get('jjm_panchayat', ''),
                'lgd_village_id': row.get('lgd_village_id', ''),
                'lgd_village': row.get('lgd_village', ''),
                'shrid2': row['shrid2'],
                'shrug_district': row.get('district_name', ''),
                'shrug_subdistrict': row.get('subdistrict_name', ''),
                'shrug_village': row.get('village_name', ''),
                'shrug_place': row.get('place_name', ''),
                'match_score': 100,
                'match_method': 'manual'
            })
    except FileNotFoundError:
        print("  No manual mappings file found")

    # Build SHRUG lookup
    print("\nBuilding SHRUG lookup...")
    shrug_lookup = build_shrug_lookup(shrug_ka)

    # Remove already manually matched
    remaining = unmatched[~unmatched['jjm_village_id'].astype(str).isin(manual_ids)]
    print(f"Remaining after manual: {len(remaining)}")

    # Phase 3a: Strict fuzzy matching
    print(f"\nPhase 3a: Strict fuzzy matching (threshold={args.threshold})...")
    strict_matches = []
    still_unmatched = []

    for _, row in remaining.iterrows():
        match = strict_fuzzy_match(
            row['jjm_village'], row['jjm_district'], row['lgd_village'],
            shrug_lookup, args.threshold
        )

        if match:
            strict_matches.append({
                'jjm_village_id': row['jjm_village_id'],
                'jjm_village': row['jjm_village'],
                'jjm_district': row['jjm_district'],
                'jjm_block': row.get('jjm_block', ''),
                'jjm_panchayat_id': row.get('jjm_panchayat_id', ''),
                'jjm_panchayat': row.get('jjm_panchayat', ''),
                'lgd_village_id': row.get('lgd_village_id', ''),
                'lgd_village': row['lgd_village'],
                'shrid2': match['shrid2'],
                'shrug_district': match['district_name'],
                'shrug_subdistrict': match['subdistrict_name'],
                'shrug_village': match['village_name'],
                'shrug_place': match['place_name'],
                'match_score': match['match_score'],
                'match_method': 'strict_fuzzy'
            })
        else:
            still_unmatched.append(row.to_dict())

    print(f"  Strict matches: {len(strict_matches)}")
    print(f"  Still unmatched: {len(still_unmatched)}")

    # Phase 3b: Kannada normalized matching
    print(f"\nPhase 3b: Kannada normalized matching...")
    kann_matches = []
    final_unmatched = []

    for row in still_unmatched:
        match = kannada_normalized_match(
            row['jjm_village'], row['jjm_district'], row['lgd_village'],
            shrug_lookup, args.threshold
        )

        if match:
            kann_matches.append({
                'jjm_village_id': row['jjm_village_id'],
                'jjm_village': row['jjm_village'],
                'jjm_district': row['jjm_district'],
                'jjm_block': row.get('jjm_block', ''),
                'jjm_panchayat_id': row.get('jjm_panchayat_id', ''),
                'jjm_panchayat': row.get('jjm_panchayat', ''),
                'lgd_village_id': row.get('lgd_village_id', ''),
                'lgd_village': row['lgd_village'],
                'shrid2': match['shrid2'],
                'shrug_district': match['district_name'],
                'shrug_subdistrict': match['subdistrict_name'],
                'shrug_village': match['village_name'],
                'shrug_place': match['place_name'],
                'match_score': match['match_score'],
                'match_method': 'kannada_normalized'
            })
        else:
            final_unmatched.append(row)

    print(f"  Kannada normalized matches: {len(kann_matches)}")
    print(f"  Final unmatched: {len(final_unmatched)}")

    # Combine all matches
    all_matches = manual_matches + strict_matches + kann_matches

    # Save results
    output_dir = args.output_dir

    if all_matches:
        all_df = pd.DataFrame(all_matches)

        # Reorder columns for easy comparison
        col_order = [
            'match_score', 'match_method',
            'jjm_village', 'lgd_village', 'shrug_village', 'shrug_place',
            'jjm_district', 'shrug_district',
            'jjm_block', 'shrug_subdistrict',
            'jjm_panchayat',
            'jjm_village_id', 'lgd_village_id', 'jjm_panchayat_id', 'shrid2'
        ]
        col_order = [c for c in col_order if c in all_df.columns]
        all_df = all_df[col_order]

        all_df.to_csv(f'{output_dir}/jjm_shrug_all_matches.csv', index=False)
        print(f"\nSaved all matches to: {output_dir}/jjm_shrug_all_matches.csv")

    if final_unmatched:
        pd.DataFrame(final_unmatched).to_csv(f'{output_dir}/jjm_still_unmatched_final.csv', index=False)
        print(f"Saved unmatched to: {output_dir}/jjm_still_unmatched_final.csv")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Manual matches: {len(manual_matches)}")
    print(f"Strict fuzzy matches: {len(strict_matches)}")
    print(f"Kannada normalized matches: {len(kann_matches)}")
    print(f"Total matched: {len(all_matches)}")
    print(f"Still unmatched: {len(final_unmatched)}")


if __name__ == '__main__':
    main()
