# JJM to SHRUG Village Mapping: Complete Process Documentation

## Project Objective

Map Jal Jeevan Mission (JJM) villages in Karnataka to SHRUG (Socioeconomic High-resolution Rural-Urban Geographic) identifiers to enable research and analysis linking water infrastructure data with socioeconomic indicators.

---

## Stage 1: JJM Data Extraction

### 1.1 Data Source

**Source URL:** https://ejalshakti.gov.in/JJM/JJMReports/lgd_mapping/rpt_LGDMappedStatus_d.aspx

Downloaded LGD mapping reports for all 31 Karnataka districts manually from the JJM portal.

### 1.2 Raw Data Processing

**Input:** HTML tables from each district (31 files)

**Process:**
1. Converted HTML tables to CSV format for each district
2. Standardized column names across all files
3. Combined all district files into single dataset

**Output:** `jjm_lgd_mapping_karnataka.csv`

### 1.3 Output Schema

| Column | Description |
|--------|-------------|
| state | Karnataka |
| jjm_district | District name from JJM |
| jjm_block | Block/Taluk name |
| jjm_panchayat_id | JJM Panchayat ID |
| jjm_panchayat | Panchayat name |
| jjm_village_id | JJM Village ID (IMIS ID) |
| jjm_village | Village name from JJM |
| lgd_village_id | LGD Village Code |
| lgd_village | Village name from LGD |
| district_from_header | District from file header |
| source_file | Source file name |

### 1.4 Validation

| Check | Result |
|-------|--------|
| Districts validated against KA-list.xls | 31/31 ✓ |
| Total villages | 26,678 |
| Missing LGD Village IDs | 0 |
| Match rate | 100% |

### 1.5 Relationship Analysis (JJM ↔ LGD)

| Relationship | Count | Notes |
|--------------|-------|-------|
| JJM → multiple LGD | 0 | True 1:1 from JJM side ✓ |
| LGD → multiple JJM | 33 | Duplicates in JJM data |

**Conclusion:** Each JJM village maps to exactly one LGD code. However, 33 LGD codes have multiple JJM entries (mostly case variations of same village, 6 are actual conflicts).

---

## Stage 2: SHRUG Data Preparation

### 2.1 Data Source

**Dataset:** SHRUG (Socioeconomic High-resolution Rural-Urban Geographic)
**File:** `shrid_loc_names.csv`

| Scope | Records |
|-------|---------|
| All India | 596,389 |
| Karnataka | 27,556 |

### 2.2 SHRUG Schema

| Column | Description |
|--------|-------------|
| shrid2 | Unique SHRUG identifier |
| state_name | State name |
| district_name | District name |
| subdistrict_name | Subdistrict/Taluk name |
| town_name | Town name (if applicable) |
| village_name | Village name |
| place_name | Place name |

---

## Stage 3: Direct LGD-SHRUG Matching

### 3.1 Method

Exact match on `lgd_village_id` between JJM data and SHRUG data.

### 3.2 Results

| Metric | Count | Percentage |
|--------|-------|------------|
| Matched | 26,137 | 97.97% |
| Unmatched | 541 | 2.03% |

### 3.3 Quality Issues Identified

**JJM Side: 33 Duplicate LGD Mappings**

| Type | Count | Description |
|------|-------|-------------|
| Exact duplicates | 27 | Same village name (case difference), same district/block, different JJM IDs |
| Different villages | 6 | Different villages mapped to same LGD code |

**Specific Conflicts (Different Villages → Same LGD):**

| LGD Code | Village 1 | Village 2 | District |
|----------|-----------|-----------|----------|
| 617801 | Kolagadalu | AIVATHOKLU | Kodagu |
| 617877 | Agalli | BASAVANARE | Kodagu |
| 617980 | KUDIGE | BYADAGOTTA | Kodagu |
| 617981 | KUDUMANGALORE | DODDATHUR | Kodagu |
| 618061 | BADAGARAKERI | BIRUNANI | Kodagu |
| 606201 | Lakkenahalli | LAKKENAHALLY | Chitradurga |

### 3.4 Relationship Analysis (JJM ↔ SHRUG via LGD)

| Relationship | Count | Notes |
|--------------|-------|-------|
| JJM → multiple SHRUG | 0 | True 1:1 from JJM side ✓ |
| SHRUG → multiple JJM | 32 | Inherited from LGD duplicates |
| LGD → multiple SHRUG | 0 | True 1:1 LGD to SHRUG ✓ |

**Conclusion:** The 32 cases of SHRUG→multiple JJM are a direct result of the 33 LGD duplicates from Stage 1. The LGD-SHRUG relationship is clean 1:1.

### 3.5 Output Files

- `jjm_to_shrug_direct_mapping.csv` - All JJM villages with SHRUG IDs where available
- `jjm_lgd_to_shrid_unmatched.csv` - 541 villages without direct match

---

## Stage 4: Name-Based Matching for Unmatched Villages

### 4.1 Matching Strategy

For the 541 unmatched villages, applied multi-stage name matching:

```
541 Unmatched Villages
        │
        ▼
┌───────────────────────────────┐
│  Manual Mappings (User)       │───► 39 matched
└───────────────────────────────┘
        │
        ▼ 502 remaining
┌───────────────────────────────┐
│  Strict Fuzzy Matching        │───► 204 matched
└───────────────────────────────┘
        │
        ▼ 298 remaining
┌───────────────────────────────┐
│  Kannada Transliteration      │───► 18 matched
└───────────────────────────────┘
        │
        ▼
    280 Unmatched (Final)
```

### 4.2 Manual Mappings

**Source:** User-provided corrections for known mismatches
**Count:** 39 villages
**File:** `jjm_manual_name_district_shrid_mapping.csv`

### 4.3 Strict Fuzzy Matching

**Method:** RapidFuzz string matching with constraints

**Algorithm:**
- Function: `fuzz.ratio()` only (full string similarity)
- No partial/substring matching to avoid false positives
- Minimum score threshold: 85%
- Length ratio constraint: ≥70% (prevents short names matching inside longer names)
- District-constrained matching

**Text Normalization:**
1. Convert to lowercase
2. Remove parenthetical suffixes: (D), (CT), (OG), (Part)
3. Remove special characters
4. Normalize whitespace

**District Name Mapping (JJM → SHRUG):**

| JJM District | SHRUG District |
|--------------|----------------|
| Bengaluru Rural | Bangalore Rural |
| Bengaluru Urban | Bangalore |
| Ballari | Bellary |
| Belagavi | Belgaum |
| Chamarajanagara | Chamarajanagar |
| Davangere | Davanagere |
| Kalaburagi | Gulbarga |
| Mysuru | Mysore |
| Shivamogga | Shimoga |
| Tumakuru | Tumkur |
| Vijayapura | Bijapur |
| Bagalkote | Bagalkot |
| Chikkamagaluru | Chikmagalur |
| Vijayanagar | Bellary (new district carved from Bellary) |

**Results:**
| Score Range | Count |
|-------------|-------|
| 100 (exact) | 129 |
| 95-99 | 9 |
| 90-94 | 53 |
| 85-89 | 52 |
| **Total** | **204** |

**File:** `jjm_shrug_matches_strict.csv`

### 4.4 Kannada Transliteration Normalization

**Method:** Apply common Kannada transliteration variations before fuzzy matching

**Normalization Rules:**

| Pattern | Normalized To | Example |
|---------|---------------|---------|
| hally, haly, hali | halli | Gowdenahally → Gowdenahalli |
| pur, puram | pura | Tippapur → Tippapura |
| keri | kere | - |
| geri | gere | - |
| kk, pp, tt, dd, nn, mm, ll | k, p, t, d, n, m, l | - |
| aa, ee, ii, oo, uu | a, i, i, u, u | - |

**Results:** 18 additional matches
**File:** `jjm_kannada_norm_matches.csv`

### 4.5 Quality Verification

**All fuzzy matches (strict + normalized) were manually reviewed and verified.**

### 4.6 Relationship Analysis (Fuzzy Matches)

| Relationship | Count | Notes |
|--------------|-------|-------|
| JJM → multiple SHRUG | 0 | True 1:1 from JJM side ✓ |
| SHRUG → multiple JJM | 8 | Some SHRUG villages matched to multiple JJM entries |

**Note:** The 8 cases of SHRUG→multiple JJM in fuzzy matching are due to similar village names in the unmatched set mapping to the same SHRUG village.

---

## Stage 5: Final Results

### 5.1 Complete Matching Summary

```
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

### 5.2 Matching Comparison

| Metric | Direct Only | + Name Matching |
|--------|-------------|-----------------|
| Matched | 26,137 (97.97%) | 26,398 (98.95%) |
| Unmatched | 541 | 280 |

---

## Process Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    JJM TO SHRUG VILLAGE MATCHING PIPELINE                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: DATA EXTRACTION                                                    │
│                                                                              │
│    ejalshakti.gov.in ──► HTML Tables (31 districts) ──► CSV Conversion       │
│                                     │                                        │
│                                     ▼                                        │
│                      jjm_lgd_mapping_karnataka.csv                           │
│                           26,678 villages                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: DIRECT LGD MATCHING                                                │
│                                                                              │
│    JJM Data ◄────── Match on lgd_village_id ──────► SHRUG Data               │
│    26,678                                            27,556 (KA)             │
│                              │                                               │
│              ┌───────────────┴───────────────┐                               │
│              ▼                               ▼                               │
│        ┌──────────┐                   ┌──────────┐                           │
│        │ MATCHED  │                   │UNMATCHED │                           │
│        │  26,137  │                   │   541    │                           │
│        │ (97.97%) │                   │ (2.03%)  │                           │
│        └──────────┘                   └────┬─────┘                           │
└──────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: NAME-BASED MATCHING                                                │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │  3a. Manual Mappings                                                │   │
│    │      User corrections ──────────────────────────► 39 matched        │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼ 502 remaining                          │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │  3b. Strict Fuzzy Matching                                          │   │
│    │      fuzz.ratio ≥ 85%, length ratio ≥ 70% ──────► 204 matched       │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼ 298 remaining                          │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │  3c. Kannada Transliteration Normalization                          │   │
│    │      hally→halli, pur→pura, etc. ───────────────► 18 matched        │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│                          ┌──────────────────┐                                │
│                          │ FINAL UNMATCHED  │                                │
│                          │      280         │                                │
│                          │    (1.05%)       │                                │
│                          └──────────────────┘                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Output Files Reference

### Primary Output Files

| File | Description | Records |
|------|-------------|---------|
| `jjm_lgd_mapping_karnataka.csv` | Combined JJM-LGD data for Karnataka | 26,678 |
| `jjm_to_shrug_direct_mapping.csv` | Direct LGD→SHRUG matches | 26,678 |
| `jjm_shrug_all_matches.csv` | All name-based matches combined | 261 |
| `jjm_still_unmatched_final.csv` | Villages requiring manual review | 280 |

### Intermediate Files

| File | Description |
|------|-------------|
| `jjm_lgd_to_shrid_unmatched.csv` | Villages without direct LGD match (input to Stage 3) |
| `jjm_manual_name_district_shrid_mapping.csv` | User-provided manual mappings |
| `jjm_shrug_matches_strict.csv` | Strict fuzzy matches |
| `jjm_kannada_norm_matches.csv` | Kannada normalization matches |

### Scripts

| Script | Purpose |
|--------|---------|
| `strict_fuzzy_match.py` | Strict fuzzy matching with length constraints |
| `normalized_fuzzy_match.py` | Kannada transliteration normalization |
| `rearrange_columns.py` | Column ordering for easy comparison |

---

## Data Quality Notes

1. **LGD Duplicates:** 33 JJM entries map to duplicate LGD codes (27 case variations, 6 actual conflicts)
2. **District Name Changes:** Several districts renamed between SHRUG (2011 census based) and JJM (current)
3. **New Districts:** Vijayanagar carved from Bellary in 2020, mapped to Bellary in SHRUG
4. **Transliteration Variance:** Kannada village names have multiple valid English spellings
5. **Manual Verification:** All fuzzy matches were manually reviewed and verified for accuracy

---

## Relationship Summary (All Stages)

| Stage | Relationship | Count | Status |
|-------|--------------|-------|--------|
| 1. JJM-LGD | JJM → multiple LGD | 0 | ✓ Clean |
| 1. JJM-LGD | LGD → multiple JJM | 33 | ⚠️ Duplicates |
| 2. Direct Match | JJM → multiple SHRUG | 0 | ✓ Clean |
| 2. Direct Match | SHRUG → multiple JJM | 32 | ⚠️ From LGD dups |
| 2. Direct Match | LGD → multiple SHRUG | 0 | ✓ Clean |
| 3. Fuzzy Match | JJM → multiple SHRUG | 0 | ✓ Clean |
| 3. Fuzzy Match | SHRUG → multiple JJM | 8 | ⚠️ Similar names |

**Key Finding:** From JJM perspective, all mappings are 1:1. The reverse relationships (SHRUG→JJM) have duplicates due to data quality issues in the source JJM data.

---

## Recommendations for Remaining 280 Unmatched

1. **Manual Review:** Villages in `jjm_still_unmatched_final.csv` require manual verification
2. **Possible Causes:**
   - New villages not in SHRUG (2011 census based)
   - Significant name changes
   - Administrative reorganization
   - Data entry errors in source systems

---

*Document Version: 1.0*
*Last Updated: November 2024*
