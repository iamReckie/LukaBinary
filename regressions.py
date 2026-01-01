#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import difflib

def main():
    # 1. Environment Variables
    home = os.environ.get('HOME')
    project_name = os.environ.get('PROJECT_NAME')
    regression_path = os.environ.get('REGRESSION_PATH')
    results_path = os.environ.get('REGRESSION_RESULTS_PATH')

    # Validate Environment Variables
    if not all([home, project_name, regression_path, results_path]):
        print("Error: Required environment variables are not set.")
        if not home: print("  HOME is missing")
        if not project_name: print("  PROJECT_NAME is missing")
        if not regression_path: print("  REGRESSION_PATH is missing")
        if not results_path: print("  REGRESSION_RESULTS_PATH is missing")
        sys.exit(1)

    # 2. Binary Path
    binary_path = os.path.join(home, project_name, "Release", "Luka")
    if not os.path.exists(binary_path):
        # Fallback to Debug if Release doesn't exist (Optional, but helpful)
        debug_path = os.path.join(home, project_name, "Debug", "Luka")
        if os.path.exists(debug_path):
            print(f"Warning: Release binary not found at {binary_path}. Using Debug binary at {debug_path}")
            binary_path = debug_path
        else:
            print(f"Error: Binary not found at {binary_path}")
            sys.exit(1)

    # Create Results Directory
    if not os.path.exists(results_path):
        os.makedirs(results_path)

    # Output Files
    result_txt_path = os.path.join(results_path, "test_result.txt")
    diff_log_path = os.path.join(results_path, "test_diffs.log")

    print(f"Starting Regression Test...")
    print(f"Binary: {binary_path}")
    print(f"Source: {regression_path}")
    print(f"Results: {results_path}")

    with open(result_txt_path, 'w') as res_file, open(diff_log_path, 'w') as diff_file:
        # 3. Iterate Directories (1 to N)
        try:
            # Filter only numeric directories and sort them numerically
            dirs = sorted([d for d in os.listdir(regression_path) if d.isdigit()], key=int)
        except FileNotFoundError:
            print(f"Error: REGRESSION_PATH {regression_path} does not exist.")
            sys.exit(1)

        if not dirs:
            print("No numbered directories found in REGRESSION_PATH.")
            return

        for d in dirs:
            src_dir = os.path.join(regression_path, d)
            dest_dir = os.path.join(results_path, d)

            # 4. Copy Directory
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(src_dir, dest_dir)

            print(f"[{d}] Running...", end='', flush=True)

            # 5. Run Binary
            try:
                # Run binary in the destination directory
                subprocess.run([binary_path], cwd=dest_dir, check=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                print(" ERROR (Crash)")
                res_file.write(f"{d}: FAIL (Crash)\n")
                continue
            except Exception as e:
                print(f" ERROR ({e})")
                res_file.write(f"{d}: ERROR ({e})\n")
                continue

            # 6. Compare output.log and regression/*
            files_to_check = []
            if os.path.exists(os.path.join(src_dir, "output.log")):
                files_to_check.append("output.log")
            
            src_reg_dir = os.path.join(src_dir, "regression")
            if os.path.exists(src_reg_dir) and os.path.isdir(src_reg_dir):
                for f in sorted(os.listdir(src_reg_dir)):
                    files_to_check.append(os.path.join("regression", f))

            if not files_to_check:
                print(" SKIP (No Ref Logs)")
                res_file.write(f"{d}: SKIP (No reference logs found)\n")
                continue

            all_diffs = []
            missing_files = []

            for rel_path in files_to_check:
                src_f = os.path.join(src_dir, rel_path)
                dest_f = os.path.join(dest_dir, rel_path)

                if not os.path.exists(dest_f):
                    missing_files.append(rel_path)
                    continue

                with open(src_f, 'r') as f1, open(dest_f, 'r') as f2:
                    lines_ref = f1.readlines()
                    lines_new = f2.readlines()
                
                diff = list(difflib.unified_diff(lines_ref, lines_new, 
                                               fromfile=f"Reference/{d}/{rel_path}", 
                                               tofile=f"Result/{d}/{rel_path}",
                                               lineterm=''))
                all_diffs.extend(diff)

            if not missing_files and not all_diffs:
                print(" PASS")
                res_file.write(f"{d}: PASS\n")
            else:
                print(" FAIL", end="")
                if missing_files: print(f" (Missing: {', '.join(missing_files)})", end="")
                if all_diffs: print(" (Diff)", end="")
                print("")
                
                res_file.write(f"{d}: FAIL\n")
                diff_file.write(f"========================================\n")
                diff_file.write(f"FAIL: Case {d}\n")
                diff_file.write(f"========================================\n")
                if missing_files:
                    diff_file.write(f"Missing files: {', '.join(missing_files)}\n\n")
                if all_diffs:
                    diff_file.writelines(all_diffs)
                diff_file.write("\n\n")

    print(f"\nRegression Test Completed.")
    print(f"Results: {result_txt_path}")
    print(f"Diffs:   {diff_log_path}")

if __name__ == "__main__":
    main()
