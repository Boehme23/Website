import subprocess
import sys
import time

# List of scripts to run in order
scripts = [
    "GetFutData.py",
    "GetGamesResult.py",
    "NextRound.py",
    'Merger.py',
    'MergeProximosJogos.py',
    'CheckNames.py',
    'FutMLTest.py'

]


def run_script(script_name):
    print(f"==========================================")
    print(f"🚀 STARTING: {script_name}")
    print(f"==========================================\n")

    start_time = time.time()

    try:
        # This runs the script and waits for it to finish.
        # 'check=True' will raise an error if the script fails (crashes).
        result = subprocess.run([sys.executable, script_name], check=True)

        elapsed = time.time() - start_time
        print(f"\n✅ SUCCESS: {script_name} finished in {elapsed:.2f} seconds.")
        return True

    except subprocess.CalledProcessError:
        print(f"\n❌ ERROR: {script_name} failed/crashed.")
        return False
    except FileNotFoundError:
        print(f"\n❌ ERROR: Could not find the file '{script_name}'.")
        return False


# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    print("Starting automated sequence...\n")

    for script in scripts:
        success = run_script(script)
        if not success:
            print("\n⛔ Sequence stopped due to an error.")
            break

        # Optional: Add a small pause between scripts
        time.sleep(1)

    if success:
        print("\n==========================================")
        print("🎉 ALL SCRIPTS FINISHED SUCCESSFULLY")
        print("==========================================")