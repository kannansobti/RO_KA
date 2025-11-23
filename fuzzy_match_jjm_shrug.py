#!/usr/bin/env python3
"""Fuzzy matching for JJM villages to SHRUG using multiple techniques."""

import pandas as pd
from rapidfuzz import fuzz, process
import re
from collections import defaultdict

# Load data
print("Loading data...")
unmatched = pd.read_csv('jjm_lgd_to_shrid_unmatched.csv')
manual = pd.read_csv('jjm_manual_name_district_shrid_mapping.csv')
shrug = pd.read_csv('shrid_loc_names.csv')

print(f"Unmatched JJM villages: {len(unmatched)}")
print(f"Manual mappings: {len(manual)}")
print(f"Total SHRUG records: {len(shrug)}")

# Filter SHRUG to Karnataka only
shrug_ka = shrug[shrug['state_name'].str.lower() == 'karnataka'].copy()
print(f"Karnataka SHRUG records: {len(shrug_ka)}")

# Normalize district names for matching
def normalize_name(name):
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    # Remove common suffixes/variations
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)  # Remove parenthetical
    name = re.sub(r'[^a-z\s]', '', name)  # Keep only letters and spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Create district name mapping between JJM and SHRUG
jjm_districts = unmatched['jjm_district'].str.lower().unique()
shrug_districts = shrug_ka['district_name'].str.lower().unique()

print("\nJJM Districts:", sorted(jjm_districts))
print("\nSHRUG Districts:", sorted(shrug_districts))

# Manual district mapping
district_map = {
    'bengaluru rural': 'bangalore rural',
    'bengaluru urban': 'bangalore',
    'ballari': 'bellary',
    'belagavi': 'belgaum',
    'chamarajanagar': 'chamrajanagar',
    'chikkaballapura': 'chikkaballapura',
    'chitradurga': 'chitradurga',
    'dakshina kannada': 'dakshina kannada',
    'davangere': 'davanagere',
    'dharwad': 'dharwad',
    'gadag': 'gadag',
    'hassan': 'hassan',
    'haveri': 'haveri',
    'kalaburagi': 'gulbarga',
    'kodagu': 'kodagu',
    'kolar': 'kolar',
    'koppal': 'koppal',
    'mandya': 'mandya',
    'mysuru': 'mysore',
    'raichur': 'raichur',
    'ramanagara': 'ramanagara',
    'shivamogga': 'shimoga',
    'tumakuru': 'tumkur',
    'udupi': 'udupi',
    'uttara kannada': 'uttara kannada',
    'vijayapura': 'bijapur',
    'yadgir': 'yadgir',
    'bidar': 'bidar',
    'bagalkote': 'bagalkot',
    'chikkamagaluru': 'chikmagalur',
}

# Remove already manually matched village IDs
manual_ids = set(manual['jjm_village_id'].astype(str))
unmatched_remaining = unmatched[~unmatched['jjm_village_id'].astype(str).isin(manual_ids)].copy()
print(f"\nUnmatched after removing manual: {len(unmatched_remaining)}")

# Build SHRUG lookup by district
shrug_by_district = defaultdict(list)
for _, row in shrug_ka.iterrows():
    dist = row['district_name'].lower() if pd.notna(row['district_name']) else ''
    village = row['village_name'] if pd.notna(row['village_name']) else ''
    place = row['place_name'] if pd.notna(row['place_name']) else ''
    shrug_by_district[dist].append({
        'shrid2': row['shrid2'],
        'district_name': row['district_name'],
        'subdistrict_name': row['subdistrict_name'],
        'village_name': village,
        'place_name': place,
        'normalized_village': normalize_name(village),
        'normalized_place': normalize_name(place)
    })

def get_shrug_district(jjm_district):
    """Map JJM district name to SHRUG district name."""
    jjm_lower = jjm_district.lower()
    return district_map.get(jjm_lower, jjm_lower)

def fuzzy_match_village(jjm_village, jjm_district, lgd_village, threshold=80):
    """Find best fuzzy match for a village in the SHRUG data."""
    shrug_dist = get_shrug_district(jjm_district)
    candidates = shrug_by_district.get(shrug_dist, [])

    if not candidates:
        return None

    jjm_norm = normalize_name(jjm_village)
    lgd_norm = normalize_name(lgd_village)

    best_match = None
    best_score = 0

    for cand in candidates:
        # Try matching against both village_name and place_name
        for name_field in ['normalized_village', 'normalized_place']:
            cand_name = cand[name_field]
            if not cand_name:
                continue

            # Try both JJM and LGD village names
            for query in [jjm_norm, lgd_norm]:
                if not query:
                    continue

                # Multiple fuzzy matching strategies
                scores = [
                    fuzz.ratio(query, cand_name),
                    fuzz.partial_ratio(query, cand_name),
                    fuzz.token_sort_ratio(query, cand_name),
                    fuzz.token_set_ratio(query, cand_name)
                ]
                score = max(scores)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = {
                        'shrid2': cand['shrid2'],
                        'district_name': cand['district_name'],
                        'subdistrict_name': cand['subdistrict_name'],
                        'village_name': cand['village_name'],
                        'place_name': cand['place_name'],
                        'match_score': score,
                        'matched_on': name_field.replace('normalized_', '')
                    }

    return best_match

# Perform fuzzy matching
print("\nPerforming fuzzy matching...")
fuzzy_matches = []
no_matches = []

for idx, row in unmatched_remaining.iterrows():
    jjm_village = row['jjm_village']
    jjm_district = row['jjm_district']
    lgd_village = row['lgd_village']

    match = fuzzy_match_village(jjm_village, jjm_district, lgd_village, threshold=75)

    if match:
        fuzzy_matches.append({
            'jjm_village_id': row['jjm_village_id'],
            'jjm_village': jjm_village,
            'jjm_district': jjm_district,
            'jjm_block': row['jjm_block'],
            'jjm_panchayat_id': row['jjm_panchayat_id'],
            'jjm_panchayat': row['jjm_panchayat'],
            'lgd_village_id': row['lgd_village_id'],
            'lgd_village': lgd_village,
            'shrid2': match['shrid2'],
            'shrug_district': match['district_name'],
            'shrug_subdistrict': match['subdistrict_name'],
            'shrug_village': match['village_name'],
            'shrug_place': match['place_name'],
            'match_score': match['match_score'],
            'matched_on': match['matched_on'],
            'match_method': 'fuzzy'
        })
    else:
        no_matches.append({
            'jjm_village_id': row['jjm_village_id'],
            'jjm_village': jjm_village,
            'jjm_district': jjm_district,
            'jjm_block': row['jjm_block'],
            'jjm_panchayat_id': row['jjm_panchayat_id'],
            'jjm_panchayat': row['jjm_panchayat'],
            'lgd_village_id': row['lgd_village_id'],
            'lgd_village': lgd_village
        })

print(f"Fuzzy matches found: {len(fuzzy_matches)}")
print(f"Still unmatched: {len(no_matches)}")

# Save results
if fuzzy_matches:
    fuzzy_df = pd.DataFrame(fuzzy_matches)
    fuzzy_df.to_csv('jjm_fuzzy_matches.csv', index=False)
    print(f"\nSaved fuzzy matches to jjm_fuzzy_matches.csv")

    # Show score distribution
    print("\nMatch score distribution:")
    print(fuzzy_df['match_score'].describe())

if no_matches:
    nomatch_df = pd.DataFrame(no_matches)
    nomatch_df.to_csv('jjm_still_unmatched.csv', index=False)
    print(f"Saved remaining unmatched to jjm_still_unmatched.csv")

# Combine all matches: manual + fuzzy
print("\n--- Combining all matches ---")
manual_formatted = manual[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                           'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                           'shrid2', 'district_name', 'subdistrict_name', 'village_name', 'place_name']].copy()
manual_formatted['match_method'] = 'manual'
manual_formatted.columns = ['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                            'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                            'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                            'shrug_place', 'match_method']

if fuzzy_matches:
    fuzzy_df_simple = fuzzy_df[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                                'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                                'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                                'shrug_place', 'match_method']].copy()
    combined = pd.concat([manual_formatted, fuzzy_df_simple], ignore_index=True)
else:
    combined = manual_formatted

combined.to_csv('jjm_combined_matches.csv', index=False)
print(f"Total combined matches: {len(combined)}")
print(f"  - Manual: {len(manual)}")
print(f"  - Fuzzy: {len(fuzzy_matches)}")

# Summary
print("\n=== SUMMARY ===")
print(f"Original unmatched: {len(unmatched)}")
print(f"Manual matches: {len(manual)}")
print(f"Fuzzy matches: {len(fuzzy_matches)}")
print(f"Total matched: {len(manual) + len(fuzzy_matches)}")
print(f"Still unmatched: {len(no_matches)}")
