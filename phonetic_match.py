#!/usr/bin/env python3
"""Additional matching using phonetic algorithms and lower thresholds."""

import pandas as pd
from rapidfuzz import fuzz
import re
from collections import defaultdict

# Load data
unmatched = pd.read_csv('jjm_still_unmatched.csv')
shrug = pd.read_csv('shrid_loc_names.csv')
shrug_ka = shrug[shrug['state_name'].str.lower() == 'karnataka'].copy()

print(f"Remaining unmatched: {len(unmatched)}")

# District mapping - note Vijayanagar is new district carved from Bellary
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
    'vijayanagar': 'bellary',  # New district carved from Bellary in 2020
}

def normalize_name(name):
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)
    name = re.sub(r'[^a-z\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def simple_phonetic(name):
    """Simple phonetic normalization for Kannada transliteration variations."""
    if not name:
        return ''
    name = name.lower()
    # Common transliteration variations in Kannada
    replacements = [
        ('kk', 'k'), ('ll', 'l'), ('nn', 'n'), ('mm', 'm'), ('tt', 't'), ('pp', 'p'),
        ('aa', 'a'), ('ee', 'i'), ('oo', 'u'), ('ii', 'i'), ('uu', 'u'),
        ('th', 't'), ('dh', 'd'), ('bh', 'b'), ('ph', 'p'), ('gh', 'g'), ('kh', 'k'),
        ('sh', 's'), ('ch', 'c'),
        ('hundi', 'hundi'), ('hundi', 'hundy'),
        ('pura', 'pura'), ('pur', 'pura'), ('puram', 'pura'),
        ('halli', 'halli'), ('hally', 'halli'), ('hali', 'halli'),
        ('agrahara', 'agrahara'), ('agrahar', 'agrahara'),
    ]
    for old, new in replacements:
        name = name.replace(old, new)
    return name

# Build SHRUG lookup
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
        'norm_place': normalize_name(place),
        'phon_village': simple_phonetic(normalize_name(village)),
        'phon_place': simple_phonetic(normalize_name(place))
    })

def match_village(jjm_village, jjm_district, lgd_village, threshold=65):
    """Match using multiple strategies with lower threshold."""
    shrug_dist = district_map.get(jjm_district.lower(), jjm_district.lower())
    candidates = shrug_by_district.get(shrug_dist, [])

    if not candidates:
        print(f"  No candidates for district: {jjm_district} -> {shrug_dist}")
        return None

    jjm_norm = normalize_name(jjm_village)
    lgd_norm = normalize_name(lgd_village)
    jjm_phon = simple_phonetic(jjm_norm)
    lgd_phon = simple_phonetic(lgd_norm)

    best_match = None
    best_score = 0

    for cand in candidates:
        for query_norm, query_phon in [(jjm_norm, jjm_phon), (lgd_norm, lgd_phon)]:
            if not query_norm:
                continue

            for name_type in ['village', 'place']:
                cand_norm = cand[f'norm_{name_type}']
                cand_phon = cand[f'phon_{name_type}']
                if not cand_norm:
                    continue

                # Standard fuzzy scores
                scores = [
                    fuzz.ratio(query_norm, cand_norm),
                    fuzz.partial_ratio(query_norm, cand_norm),
                    fuzz.token_sort_ratio(query_norm, cand_norm),
                    fuzz.token_set_ratio(query_norm, cand_norm),
                ]

                # Phonetic matching (if phonetic forms match better)
                if query_phon and cand_phon:
                    scores.extend([
                        fuzz.ratio(query_phon, cand_phon),
                        fuzz.partial_ratio(query_phon, cand_phon),
                    ])

                score = max(scores)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = {
                        'shrid2': cand['shrid2'],
                        'district_name': cand['district_name'],
                        'subdistrict_name': cand['subdistrict_name'],
                        'village_name': cand['village_name'],
                        'place_name': cand['place_name'],
                        'match_score': score
                    }

    return best_match

# Try matching remaining
print("\nTrying to match remaining villages with lower threshold...\n")
new_matches = []
still_unmatched = []

for _, row in unmatched.iterrows():
    jjm_village = row['jjm_village']
    jjm_district = row['jjm_district']
    lgd_village = row['lgd_village']

    print(f"Trying: {jjm_village} ({jjm_district})")
    match = match_village(jjm_village, jjm_district, lgd_village, threshold=60)

    if match:
        print(f"  -> MATCHED: {match['village_name']} ({match['match_score']})")
        new_matches.append({
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
            'match_method': 'phonetic_lower_threshold'
        })
    else:
        print(f"  -> NO MATCH")
        still_unmatched.append(row.to_dict())

print(f"\n=== Results ===")
print(f"New matches: {len(new_matches)}")
print(f"Still unmatched: {len(still_unmatched)}")

if new_matches:
    new_df = pd.DataFrame(new_matches)
    new_df.to_csv('jjm_phonetic_matches.csv', index=False)
    print("Saved to jjm_phonetic_matches.csv")

if still_unmatched:
    pd.DataFrame(still_unmatched).to_csv('jjm_final_unmatched.csv', index=False)
    print("Saved to jjm_final_unmatched.csv")

# Combine all matches
print("\n=== Combining all matches ===")
fuzzy = pd.read_csv('jjm_fuzzy_matches.csv')
manual = pd.read_csv('jjm_manual_name_district_shrid_mapping.csv')

# Prepare manual
manual_df = manual[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                    'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                    'shrid2', 'district_name', 'subdistrict_name', 'village_name', 'place_name']].copy()
manual_df['match_score'] = 100
manual_df['match_method'] = 'manual'
manual_df.columns = ['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                     'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                     'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                     'shrug_place', 'match_score', 'match_method']

# Prepare fuzzy
fuzzy_df = fuzzy[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                  'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                  'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                  'shrug_place', 'match_score', 'match_method']].copy()

all_matches = [manual_df, fuzzy_df]

if new_matches:
    phonetic_df = pd.DataFrame(new_matches)[['jjm_village_id', 'jjm_village', 'jjm_district', 'jjm_block',
                                             'jjm_panchayat_id', 'jjm_panchayat', 'lgd_village_id', 'lgd_village',
                                             'shrid2', 'shrug_district', 'shrug_subdistrict', 'shrug_village',
                                             'shrug_place', 'match_score', 'match_method']]
    all_matches.append(phonetic_df)

combined = pd.concat(all_matches, ignore_index=True)
combined.to_csv('jjm_all_matches_combined.csv', index=False)

print(f"\nFinal combined matches: {len(combined)}")
print(f"  - Manual: {len(manual_df)}")
print(f"  - Fuzzy: {len(fuzzy_df)}")
print(f"  - Phonetic: {len(new_matches)}")
print(f"  - Total: {len(combined)}")
print(f"  - Still unmatched: {len(still_unmatched)}")
