# JJM to SHRUG Village Mapping Scripts

Scripts for mapping Jal Jeevan Mission (JJM) villages to SHRUG identifiers.

## Requirements

```bash
pip install pandas rapidfuzz openpyxl
```

## Quick Start

Run all phases:
```bash
python run_all_phases.py --skip-phase1
```

Or run individual phases:
```bash
python 02_direct_lgd_shrug_match.py
python 03_fuzzy_name_matching.py
python 04_scheme_data_integration.py
```

## Pipeline Overview

```
Phase 1                Phase 2                Phase 3                Phase 4
─────────────────────────────────────────────────────────────────────────────
JJM District    ───►   Direct LGD      ───►   Fuzzy Name     ───►   Final
Files                  Matching               Matching              Mapping

(31 .xls files)        (97.97%)               (+1.0%)               (98.95%)
                       26,137 matched         261 matched           26,398 total
                       541 unmatched          280 unmatched
```

## Scripts

### 01_combine_jjm_lgd_data.py
Combines individual district HTML/Excel files into single CSV.

```bash
python 01_combine_jjm_lgd_data.py \
    --input-dir "../JJM ID to LGD" \
    --output "../jjm_lgd_mapping_karnataka.csv"
```

### 02_direct_lgd_shrug_match.py
Matches JJM villages to SHRUG using LGD village codes.

```bash
python 02_direct_lgd_shrug_match.py \
    --jjm-file "../jjm_lgd_mapping_karnataka.csv" \
    --shrug-file "../shrid_loc_names.csv" \
    --output-matched "../jjm_to_shrug_direct_mapping.csv" \
    --output-unmatched "../jjm_lgd_to_shrid_unmatched.csv"
```

### 03_fuzzy_name_matching.py
Fuzzy name-based matching for unmatched villages.

```bash
python 03_fuzzy_name_matching.py \
    --unmatched-file "../jjm_lgd_to_shrid_unmatched.csv" \
    --shrug-file "../shrid_loc_names.csv" \
    --manual-file "../jjm_manual_name_district_shrid_mapping.csv" \
    --threshold 85 \
    --output-dir ".."
```

### 04_scheme_data_integration.py
Creates final mapping and integrates with scheme data.

```bash
python 04_scheme_data_integration.py \
    --direct-file "../jjm_to_shrug_direct_mapping.csv" \
    --fuzzy-file "../jjm_shrug_all_matches.csv" \
    --scheme-file "../Karnataka Scheme Details (30-09-2025).xlsx" \
    --output-mapping "../villageid_to_shrid_mapping.csv"
```

## Output Files

| File | Description |
|------|-------------|
| `jjm_lgd_mapping_karnataka.csv` | Combined JJM-LGD data (26,678 villages) |
| `jjm_to_shrug_direct_mapping.csv` | Direct LGD→SHRUG matches |
| `jjm_shrug_all_matches.csv` | All fuzzy matches (261 villages) |
| `villageid_to_shrid_mapping.csv` | Final village→SHRID mapping (26,398) |
| `jjm_still_unmatched_final.csv` | Unmatched villages (280) |

## Matching Methods

### Direct Matching (Phase 2)
- Extracts LGD code from SHRID (last 6 digits)
- Exact match on LGD village ID
- 97.97% match rate

### Fuzzy Matching (Phase 3)
- Uses `rapidfuzz.fuzz.ratio()` for strict full-string matching
- Minimum threshold: 85%
- Length ratio constraint: ≥70%
- District-constrained

### Kannada Normalization
Handles transliteration variations:
- `hally` → `halli`
- `pur/puram` → `pura`
- Double consonants (kk, pp) → single (k, p)

## District Name Mapping

| JJM District | SHRUG District |
|--------------|----------------|
| Bengaluru Rural | Bangalore Rural |
| Bengaluru Urban | Bangalore |
| Ballari | Bellary |
| Belagavi | Belgaum |
| Kalaburagi | Gulbarga |
| Mysuru | Mysore |
| Vijayapura | Bijapur |
| Vijayanagar | Bellary |
