#!/usr/bin/env python3
"""
JJM to SHRUG Mapping Pipeline - Run All Phases

This script runs all phases of the JJM to SHRUG village mapping pipeline.

Usage:
    python run_all_phases.py --input-dir "JJM ID to LGD" --shrug-file shrid_loc_names.csv

Requirements:
    pip install pandas rapidfuzz openpyxl
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_phase(script_name: str, args: list) -> bool:
    """Run a phase script with arguments."""
    cmd = [sys.executable, script_name] + args
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent))
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Run all phases of JJM-SHRUG mapping')
    parser.add_argument('--input-dir', default='../JJM ID to LGD',
                        help='Directory with JJM district files')
    parser.add_argument('--shrug-file', default='../shrid_loc_names.csv',
                        help='SHRUG location names file')
    parser.add_argument('--manual-file', default='../jjm_manual_name_district_shrid_mapping.csv',
                        help='Manual mappings file')
    parser.add_argument('--scheme-file', default=None,
                        help='Scheme data file (optional)')
    parser.add_argument('--output-dir', default='..',
                        help='Output directory')
    parser.add_argument('--skip-phase1', action='store_true',
                        help='Skip Phase 1 (use existing jjm_lgd_mapping_karnataka.csv)')
    args = parser.parse_args()

    output_dir = args.output_dir
    success = True

    # Phase 1: Combine JJM-LGD data
    if not args.skip_phase1:
        success = run_phase('01_combine_jjm_lgd_data.py', [
            '--input-dir', args.input_dir,
            '--output', f'{output_dir}/jjm_lgd_mapping_karnataka.csv'
        ])
        if not success:
            print("\n❌ Phase 1 failed!")
            return 1

    # Phase 2: Direct LGD-SHRUG matching
    success = run_phase('02_direct_lgd_shrug_match.py', [
        '--jjm-file', f'{output_dir}/jjm_lgd_mapping_karnataka.csv',
        '--shrug-file', args.shrug_file,
        '--output-matched', f'{output_dir}/jjm_to_shrug_direct_mapping.csv',
        '--output-unmatched', f'{output_dir}/jjm_lgd_to_shrid_unmatched.csv'
    ])
    if not success:
        print("\n❌ Phase 2 failed!")
        return 1

    # Phase 3: Fuzzy name matching
    phase3_args = [
        '--unmatched-file', f'{output_dir}/jjm_lgd_to_shrid_unmatched.csv',
        '--shrug-file', args.shrug_file,
        '--output-dir', output_dir
    ]
    if Path(args.manual_file).exists():
        phase3_args.extend(['--manual-file', args.manual_file])

    success = run_phase('03_fuzzy_name_matching.py', phase3_args)
    if not success:
        print("\n❌ Phase 3 failed!")
        return 1

    # Phase 4: Scheme data integration
    phase4_args = [
        '--direct-file', f'{output_dir}/jjm_to_shrug_direct_mapping.csv',
        '--fuzzy-file', f'{output_dir}/jjm_shrug_all_matches.csv',
        '--output-mapping', f'{output_dir}/villageid_to_shrid_mapping.csv',
        '--output-unmatched', f'{output_dir}/scheme_villages_without_shrid.csv'
    ]
    if args.scheme_file and Path(args.scheme_file).exists():
        phase4_args.extend(['--scheme-file', args.scheme_file])

    success = run_phase('04_scheme_data_integration.py', phase4_args)
    if not success:
        print("\n❌ Phase 4 failed!")
        return 1

    print("\n" + "="*60)
    print("✓ ALL PHASES COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\nOutput files in: {output_dir}")
    print("  - jjm_lgd_mapping_karnataka.csv")
    print("  - jjm_to_shrug_direct_mapping.csv")
    print("  - jjm_shrug_all_matches.csv")
    print("  - villageid_to_shrid_mapping.csv")
    print("  - jjm_still_unmatched_final.csv")

    return 0


if __name__ == '__main__':
    sys.exit(main())
