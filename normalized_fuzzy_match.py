#!/usr/bin/env python3
"""Fuzzy matching with Kannada transliteration normalization."""

import pandas as pd
from rapidfuzz import fuzz
import re
from collections import defaultdict

# Load data
print("Loading data...")
unmatched = pd.read_csv('jjm_unmatched_strict.csv')
manual = pd.read_csv('jjm_manual_name_district_shrid_mapping.csv')
shrug = pd.read_csv('shrid_loc_names.csv')

print(f"Previously unmatched: {len(unmatched)}")

# Filter SHRUG to Karnataka
shrug_ka = shrug[shrug['state_name'].str.lower() == 'karnataka'].copy()

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
    'vijayanagar': 'bellary',
}

def normalize_name(name):
    """Basic normalization."""
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)  # Remove parenthetical
    name = re.sub(r'[^a-z\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def kannada_normalize(name):
    """Apply Kannada transliteration normalizations."""
    if not name:
        return name

    # Common suffix variations - normalize to one form
    replacements = [
        # halli/hally variations
        (r'hally$', 'halli'),
        (r'haly$', 'halli'),
        (r'hali$', 'halli'),

        # pura/pur variations
        (r'pura$', 'pura'),
        (r'pur$', 'pura'),
        (r'puram$', 'pura'),

        # kere/keri variations
        (r'kere$', 'kere'),
        (r'keri$', 'kere'),

        # geri/gere variations
        (r'geri$', 'gere'),

        # Double consonants
        (r'kk', 'k'),
        (r'pp', 'p'),
        (r'tt', 't'),
        (r'dd', 'd'),
        (r'nn', 'n'),
        (r'mm', 'm'),
        (r'll', 'l'),

        # Double vowels
        (r'aa', 'a'),
        (r'ee', 'i'),
        (r'ii', 'i'),
        (r'oo', 'u'),
        (r'uu', 'u'),
    ]

    for pattern, repl in replacements:
        name = re.sub(pattern, repl, name)

    return name

# Build SHRUG lookup
shrug_by_district = defaultdict(list)
for _, row in shrug_ka.iterrows():
    dist = row['district_name'].lower() if pd.notna(row['district_name']) else ''
    village = row['village_name'] if pd.notna(row['village_name']) else ''
    place = row['place_name'] if pd.notna(row['place_name']) else ''

    norm_village = normalize_name(village)
    norm_place = normalize_name(place)

    shrug_by_district[dist].append({
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

def get_shrug_district(jjm_district):
    return district_map.get(jjm_district.lower(), jjm_district.lower())

def match_with_normalization(jjm_village, jjm_district, lgd_village, threshold=85):
    """Match using Kannada-normalized names."""
    shrug_dist = get_shrug_district(jjm_district)
    candidates = shrug_by_district.get(shrug_dist, [])

    if not candidates:
        return None

    jjm_norm = normalize_name(jjm_village)
    lgd_norm = normalize_name(lgd_village)
    jjm_kann = kannada_normalize(jjm_norm)
    lgd_kann = kannada_normalize(lgd_norm)

    best_match = None
    best_score = 0

    for cand in candidates:
        # Try both normalized and kannada-normalized versions
        for query, query_type in [(jjm_norm, 'jjm'), (lgd_norm, 'lgd'),
                                   (jjm_kann, 'jjm_kann'), (lgd_kann, 'lgd_kann')]:
            if not query:
                continue

            for name_field in ['norm_village', 'norm_place', 'kann_village', 'kann_place']:
                cand_name = cand[name_field]
                if not cand_name:
                    continue

                # Use fuzz.ratio for full string match
                score = fuzz.ratio(query, cand_name)

                # Length ratio check
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
                        'query_type': query_type,
                        'matched_field': name_field
                    }

    return best_match

# Perform matching
print("\nMatching with Kannada transliteration normalization...")
matches = []
no_matches = []

for _, row in unmatched.iterrows():
    jjm_village = row['jjm_village']
    jjm_district = row['jjm_district']
    lgd_village = row['lgd_village']

    match = match_with_normalization(jjm_village, jjm_district, lgd_village, threshold=85)

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
            'match_method': 'kannada_normalized'
        })
    else:
        no_matches.append(row.to_dict())

print(f"New matches with normalization: {len(matches)}")
print(f"Still unmatched: {len(no_matches)}")

# Save new matches
if matches:
    match_df = pd.DataFrame(matches)

    # Reorder columns
    col_order = [
        'match_score', 'match_method',
        'jjm_village', 'lgd_village', 'shrug_village', 'shrug_place',
        'jjm_district', 'shrug_district',
        'jjm_block', 'shrug_subdistrict',
        'jjm_panchayat',
        'jjm_village_id', 'lgd_village_id', 'jjm_panchayat_id', 'shrid2'
    ]
    match_df = match_df[col_order]
    match_df.to_csv('jjm_kannada_norm_matches.csv', index=False)
    print(f"\nSaved to jjm_kannada_norm_matches.csv")

    print("\nNew matches found:")
    print(match_df[['match_score', 'jjm_village', 'lgd_village', 'shrug_village']].to_string())

if no_matches:
    pd.DataFrame(no_matches).to_csv('jjm_still_unmatched_final.csv', index=False)
    print(f"\nSaved {len(no_matches)} unmatched to jjm_still_unmatched_final.csv")

# Combine all matches
print("\n=== Combining all matches ===")
strict = pd.read_csv('jjm_shrug_matches_strict.csv')
print(f"Previous strict matches: {len(strict)}")

if matches:
    all_matches = pd.concat([strict, match_df], ignore_index=True)
else:
    all_matches = strict

all_matches.to_csv('jjm_shrug_all_matches.csv', index=False)
print(f"Total matches: {len(all_matches)}")
print(f"Still unmatched: {len(no_matches)}")
