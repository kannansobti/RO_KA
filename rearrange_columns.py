#!/usr/bin/env python3
"""Rearrange columns for easy comparison."""

import pandas as pd

# Load the final matches
df = pd.read_csv('jjm_all_matches_final.csv')

# Rearrange columns for easy comparison
# Group: Village names together, then districts, then IDs, then match info
new_order = [
    # Match quality first
    'match_score',
    'match_method',
    # Village names side by side for comparison
    'jjm_village',
    'lgd_village',
    'shrug_village',
    'shrug_place',
    # Districts side by side
    'jjm_district',
    'shrug_district',
    # Block/subdistrict
    'jjm_block',
    'shrug_subdistrict',
    # Panchayat info
    'jjm_panchayat',
    # IDs
    'jjm_village_id',
    'lgd_village_id',
    'jjm_panchayat_id',
    'shrid2',
]

df_reordered = df[new_order]

# Save reordered file
df_reordered.to_csv('jjm_all_matches_final.csv', index=False)
print("Reordered jjm_all_matches_final.csv")

# Also reorder the review file
review = pd.read_csv('jjm_matches_for_review.csv')
review_reordered = review[new_order]
review_reordered.to_csv('jjm_matches_for_review.csv', index=False)
print("Reordered jjm_matches_for_review.csv")

print("\nNew column order:")
print("  1. match_score, match_method (quality info)")
print("  2. jjm_village, lgd_village, shrug_village, shrug_place (names to compare)")
print("  3. jjm_district, shrug_district (districts to compare)")
print("  4. jjm_block, shrug_subdistrict (sub-regions)")
print("  5. jjm_panchayat (panchayat)")
print("  6. IDs (jjm_village_id, lgd_village_id, jjm_panchayat_id, shrid2)")

print("\nSample rows:")
print(df_reordered[['match_score', 'jjm_village', 'lgd_village', 'shrug_village', 'shrug_place']].head(10).to_string())
