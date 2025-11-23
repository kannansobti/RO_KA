# JJM to SHRUG Village Mapping: Process Documentation

## Overview

This document describes the process of mapping Jal Jeevan Mission (JJM) villages in Karnataka to SHRUG (Socioeconomic High-resolution Rural-Urban Geographic) identifiers for research and analysis purposes.

## Data Sources

| Dataset | Description | Records |
|---------|-------------|---------|
| JJM Karnataka | Village-level water scheme data | 26,678 villages |
| LGD (Local Government Directory) | Official village-GP mapping | Linked to JJM |
| SHRUG | Socioeconomic village database | 596,389 (India), 27,556 (Karnataka) |

## Process Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    JJM TO SHRUG VILLAGE MATCHING PIPELINE                   │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────────┐
                            │  JJM Karnataka   │
                            │  26,678 villages │
                            └────────┬─────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │  STAGE 1: LGD-SHRUG Direct     │
                    │  Match on lgd_village_id       │
                    └────────────────┬───────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌───────────────────┐             ┌───────────────────┐
        │     MATCHED       │             │    UNMATCHED      │
        │  26,137 villages  │             │   541 villages    │
        │     (97.97%)      │             │     (2.03%)       │
        └───────────────────┘             └─────────┬─────────┘
                                                    │
                                                    ▼
                                   ┌────────────────────────────────┐
                                   │  STAGE 2: Manual Mappings      │
                                   │  User-provided corrections     │
                                   └────────────────┬───────────────┘
                                                    │
                                   ┌────────────────┴────────────────┐
                                   │                                 │
                                   ▼                                 ▼
                       ┌───────────────────┐             ┌───────────────────┐
                       │  MANUAL MATCHED   │             │    REMAINING      │
                       │   39 villages     │             │  502 villages     │
                       └───────────────────┘             └─────────┬─────────┘
                                                                   │
                                                                   ▼
                                                  ┌────────────────────────────────┐
                                                  │  STAGE 3: Strict Fuzzy Match   │
                                                  │  fuzz.ratio ≥ 85%              │
                                                  │  Length ratio ≥ 70%            │
                                                  └────────────────┬───────────────┘
                                                                   │
                                                  ┌────────────────┴────────────────┐
                                                  │                                 │
                                                  ▼                                 ▼
                                      ┌───────────────────┐             ┌───────────────────┐
                                      │   FUZZY MATCHED   │             │    REMAINING      │
                                      │  204 villages     │             │  298 villages     │
                                      └───────────────────┘             └─────────┬─────────┘
                                                                                  │
                                                                                  ▼
                                                                 ┌────────────────────────────────┐
                                                                 │  STAGE 4: Kannada Normalized   │
                                                                 │  hally→halli, puram→pura, etc. │
                                                                 └────────────────┬───────────────┘
                                                                                  │
                                                                 ┌────────────────┴────────────────┐
                                                                 │                                 │
                                                                 ▼                                 ▼
                                                     ┌───────────────────┐             ┌───────────────────┐
                                                     │ NORMALIZED MATCH  │             │  FINAL UNMATCHED  │
                                                     │   18 villages     │             │   280 villages    │
                                                     └───────────────────┘             └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                              FINAL SUMMARY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Total JJM Villages:        26,678                                          │
│  ─────────────────────────────────────────────────────────────────────────  │
│  LGD Direct Match:          26,137  (97.97%)                                │
│  Manual Mappings:               39  ( 0.15%)                                │
│  Strict Fuzzy Match:           204  ( 0.76%)                                │
│  Kannada Normalized:            18  ( 0.07%)                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  TOTAL MATCHED:             26,398  (98.95%)                                │
│  UNMATCHED:                    280  ( 1.05%)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Stage Descriptions

### Stage 1: LGD-SHRUG Direct Matching

**Method:** Exact match on `lgd_village_id` between JJM data and SHRUG data.

**Input:**
- JJM Karnataka villages with LGD codes: 26,678
- SHRUG Karnataka villages: 27,556

**Output:**
- Matched: 26,137 (97.97%)
- Unmatched: 541 (2.03%)

**Files:**
- `jjm_to_shrug_direct_mapping.csv` - All JJM villages with SHRUG matches where available
- `jjm_lgd_to_shrid_unmatched.csv` - 541 villages without direct LGD match

---

### Stage 2: Manual Mappings

**Method:** User-provided manual corrections for known mismatches.

**Input:** 541 unmatched villages

**Output:**
- Manually matched: 39
- Remaining: 502

**Files:**
- `jjm_manual_name_district_shrid_mapping.csv` - Manual mappings

---

### Stage 3: Strict Fuzzy Matching

**Method:** RapidFuzz string matching with strict constraints:
- Uses only `fuzz.ratio()` (full string similarity)
- No partial matching to avoid substring matches
- Minimum score threshold: 85%
- Length ratio check: strings must be within 70% length of each other
- District-constrained: only matches within same district

**Normalization applied:**
- Convert to lowercase
- Remove parenthetical suffixes like (D), (CT), (OG)
- Remove special characters
- Normalize whitespace

**District Mapping:** (JJM → SHRUG)
| JJM District | SHRUG District |
|--------------|----------------|
| Bengaluru Rural | Bangalore Rural |
| Bengaluru Urban | Bangalore |
| Ballari | Bellary |
| Belagavi | Belgaum |
| Kalaburagi | Gulbarga |
| Mysuru | Mysore |
| Vijayapura | Bijapur |
| Vijayanagar | Bellary (new district) |

**Input:** 502 remaining unmatched

**Output:**
- Matched: 204
- Remaining: 298

**Score Distribution:**
| Score Range | Count |
|-------------|-------|
| 100 (exact) | 129 |
| 95-99 | 9 |
| 90-94 | 53 |
| 85-89 | 52 |

**Files:**
- `jjm_shrug_matches_strict.csv` - Strict fuzzy matches + manual
- `jjm_unmatched_strict.csv` - Remaining unmatched

---

### Stage 4: Kannada Transliteration Normalization

**Method:** Apply common Kannada transliteration variations before fuzzy matching.

**Normalizations applied:**
| Pattern | Normalized To |
|---------|---------------|
| hally, haly, hali | halli |
| pur, puram | pura |
| keri | kere |
| geri | gere |
| Double consonants (kk, pp, tt) | Single (k, p, t) |
| Double vowels (aa, ee, oo) | Single (a, i, u) |

**Input:** 298 remaining unmatched

**Output:**
- Matched: 18
- Remaining: 280

**Files:**
- `jjm_kannada_norm_matches.csv` - Normalized matches
- `jjm_still_unmatched_final.csv` - Final unmatched

---

## Final Output Files

| File | Description | Records |
|------|-------------|---------|
| `jjm_shrug_all_matches.csv` | All matched villages (manual + fuzzy + normalized) | 261 |
| `jjm_to_shrug_direct_mapping.csv` | Direct LGD matches | 26,678 |
| `jjm_still_unmatched_final.csv` | Villages requiring manual review | 280 |

## Quality Assurance Notes

1. **Strict matching preferred:** Only `fuzz.ratio()` used to avoid false positives from partial/substring matches
2. **Length constraint:** Prevents short names matching inside longer names
3. **District constraint:** All matches restricted to same district to avoid cross-district false matches
4. **Manual review:** 280 remaining villages (1.05%) require manual verification

## Scripts

| Script | Purpose |
|--------|---------|
| `strict_fuzzy_match.py` | Strict fuzzy matching with length constraints |
| `normalized_fuzzy_match.py` | Kannada transliteration normalization |
| `rearrange_columns.py` | Column ordering for easy comparison |

---

*Document generated: November 2024*
