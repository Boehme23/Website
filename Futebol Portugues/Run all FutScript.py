import subprocess
import sys
import time
import git
from datetime import datetime
import os


def safety_commit(repo_path, message_prefix="Pre-run backup"):
    try:
        # Initialize the repo object
        repo = git.Repo(repo_path)

        # Check if there are any changes (modified or untracked)
        if repo.is_dirty(untracked_files=True):
            print("Changes detected. Committing before running...")

            # Stage all changes (git add .)
            repo.git.add(A=True)

            # Create a timestamped commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"{message_prefix} - {timestamp}"

            # Commit (git commit -m "...")
            new_commit = repo.index.commit(commit_message)
            print(f"Success! Committed as: {new_commit.hexsha[:7]}")
            return new_commit
        else:
            print("No changes detected. Proceeding...")
            return None

    except Exception as e:
        print(f"Failed to commit: {e}")
        # Decide if you want to stop the script if backup fails
        raise

repo_directory = os.getcwd()  # Or the path to your project
safety_commit(repo_directory)

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