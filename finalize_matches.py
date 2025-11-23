#!/usr/bin/env python3
"""Finalize matches and create quality review file."""

import pandas as pd

# Load all match files
combined = pd.read_csv('jjm_all_matches_combined.csv')
phonetic = pd.read_csv('jjm_phonetic_matches.csv')

print(f"Total combined matches: {len(combined)}")

# Separate high-confidence and low-confidence matches
high_conf = combined[combined['match_score'] >= 85].copy()
low_conf = combined[combined['match_score'] < 85].copy()

print(f"High confidence (>= 85): {len(high_conf)}")
print(f"Low confidence (< 85): {len(low_conf)}")

# Save review file for low confidence matches
if len(low_conf) > 0:
    low_conf.to_csv('jjm_matches_for_review.csv', index=False)
    print(f"\nSaved {len(low_conf)} low-confidence matches to jjm_matches_for_review.csv for manual review")
    print("\nLow confidence matches:")
    print(low_conf[['jjm_village', 'jjm_district', 'shrug_village', 'match_score', 'match_method']].to_string())

# Save final combined file
combined.to_csv('jjm_all_matches_final.csv', index=False)
print(f"\nSaved all {len(combined)} matches to jjm_all_matches_final.csv")

# Summary by match method
print("\n=== Summary by match method ===")
print(combined.groupby('match_method').agg({
    'jjm_village_id': 'count',
    'match_score': ['mean', 'min', 'max']
}).round(2))

# Match score distribution
print("\n=== Match score distribution ===")
print(f"100: {len(combined[combined['match_score'] == 100])}")
print(f"95-99: {len(combined[(combined['match_score'] >= 95) & (combined['match_score'] < 100)])}")
print(f"90-94: {len(combined[(combined['match_score'] >= 90) & (combined['match_score'] < 95)])}")
print(f"85-89: {len(combined[(combined['match_score'] >= 85) & (combined['match_score'] < 90)])}")
print(f"80-84: {len(combined[(combined['match_score'] >= 80) & (combined['match_score'] < 85)])}")
print(f"75-79: {len(combined[(combined['match_score'] >= 75) & (combined['match_score'] < 80)])}")
print(f"<75: {len(combined[combined['match_score'] < 75])}")
