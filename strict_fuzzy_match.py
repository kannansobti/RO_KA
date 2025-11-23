#!/usr/bin/env python3
"""Strict fuzzy matching - full string matches only, no partial/substring matches."""

import pandas as pd
from rapidfuzz import fuzz
import re
from collections import defaultdict

# Load data
print("Loading data...")
unmatched = pd.read_csv('jjm_lgd_to_shrid_unmatched.csv')
manual = pd.read_csv('jjm_manual_name_district_shrid_mapping.csv')
shrug = pd.read_csv('shrid_loc_names.csv')

print(f"Unmatched JJM villages: {len(unmatched)}")
print(f"Manual mappings: {len(manual)}")

# Filter SHRUG to Karnataka only
shrug_ka = shrug[shrug['state_name'].str.lower() == 'karnataka'].copy()
print(f"Karnataka SHRUG records: {len(shrug_ka)}")

def normalize_name(name):
    """Normalize village name for comparison."""
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)  # Remove parenthetical like (D), (CT)
    name = re.sub(r'[^a-z\s]', '', name)  # Keep only letters and spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# District mapping
district_map = {
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
    'vijayanagar': 'bellary',  # New district from Bellary
}

# Remove already manually matched village IDs
manual_ids = set(manual['jjm_village_id'].astype(str))
unmatched_remaining = unmatched[~unmatched['jjm_village_id'].astype(str).isin(manual_ids)].copy()
print(f"Unmatched after removing manual: {len(unmatched_remaining)}")

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
        'norm_village': normalize_name(village),
        'norm_place': normalize_name(place)
    })

def get_shrug_district(jjm_district):
    return district_map.get(jjm_district.lower(), jjm_district.lower())

def strict_fuzzy_match(jjm_village, jjm_district, lgd_village, threshold=85):
    """
    Strict matching using only fuzz.ratio (full string similarity).
    No partial_ratio or token_set_ratio to avoid substring matches.
    """
    shrug_dist = get_shrug_district(jjm_district)
    candidates = shrug_by_district.get(shrug_dist, [])

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

                # ONLY use fuzz.ratio - requires full string match
                # This avoids "HALLI" matching "SOMEHALLI" etc.
                score = fuzz.ratio(query, cand_name)

                # Additional check: reject if lengths are very different
                # This prevents short names matching inside longer names
                len_ratio = min(len(query), len(cand_name)) / max(len(query), len(cand_name))
                if len_ratio < 0.7:  # Reject if one string is less than 70% length of other
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
                        'matched_field': name_field.replace('norm_', '')
                    }

    return best_match

# Perform strict matching
print("\nPerforming strict fuzzy matching (full string only)...")
matches = []
no_matches = []

for idx, row in unmatched_remaining.iterrows():
    jjm_village = row['jjm_village']
    jjm_district = row['jjm_district']
    lgd_village = row['lgd_village']

    match = strict_fuzzy_match(jjm_village, jjm_district, lgd_village, threshold=85)

    if match:
        matches.append({
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
            'match_method': 'strict_fuzzy'
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

print(f"Strict fuzzy matches: {len(matches)}")
print(f"Unmatched: {len(no_matches)}")

# Prepare manual matches
manual_df = manual[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                    'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                    'shrid2', 'district_name', 'subdistrict_name', 'village_name', 'place_name']].copy()
manual_df['match_score'] = 100
manual_df['match_method'] = 'manual'
manual_df.columns = ['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                     'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                     'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                     'shrug_place', 'match_score', 'match_method']

# Combine manual + strict fuzzy
if matches:
    fuzzy_df = pd.DataFrame(matches)
    combined = pd.concat([manual_df, fuzzy_df], ignore_index=True)
else:
    combined = manual_df

# Reorder columns for easy comparison
col_order = [
    'match_score', 'match_method',
    'jjm_village', 'lgd_village', 'shrug_village', 'shrug_place',
    'jjm_district', 'shrug_district',
    'jjm_block', 'shrug_subdistrict',
    'jjm_panchayat',
    'jjm_village_id', 'lgd_village_id', 'jjm_panchayat_id', 'shrid2'
]
combined = combined[col_order]

# Save results
combined.to_csv('jjm_shrug_matches_strict.csv', index=False)
print(f"\nSaved {len(combined)} matches to jjm_shrug_matches_strict.csv")

if no_matches:
    nomatch_df = pd.DataFrame(no_matches)
    nomatch_df.to_csv('jjm_unmatched_strict.csv', index=False)
    print(f"Saved {len(no_matches)} unmatched to jjm_unmatched_strict.csv")

# Summary
print("\n=== SUMMARY ===")
print(f"Manual matches: {len(manual_df)}")
print(f"Strict fuzzy matches: {len(matches)}")
print(f"Total matched: {len(combined)}")
print(f"Still unmatched: {len(no_matches)}")

print("\n=== Match score distribution ===")
print(f"100: {len(combined[combined['match_score'] == 100])}")
print(f"95-99: {len(combined[(combined['match_score'] >= 95) & (combined['match_score'] < 100)])}")
print(f"90-94: {len(combined[(combined['match_score'] >= 90) & (combined['match_score'] < 95)])}")
print(f"85-89: {len(combined[(combined['match_score'] >= 85) & (combined['match_score'] < 90)])}")

print("\nSample matches:")
print(combined[['match_score', 'jjm_village', 'lgd_village', 'shrug_village']].head(20).to_string())
