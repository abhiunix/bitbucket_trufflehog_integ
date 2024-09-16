import os
import requests
import json
import sqlite3
from datetime import datetime
import pytz
import subprocess
from dotenv import load_dotenv
import shlex

# Load environment variables from .env file
load_dotenv()

BITBUCKET_APP_PASSWORD = os.getenv('BITBUCKET_APP_PASSWORD')
BITBUCKET_USERNAME = os.getenv('BITBUCKET_USERNAME')
BITBUCKET_WORKSPACE = os.getenv('BITBUCKET_WORKSPACE')

# Directory where all repositories will be cloned
REPOS_DIR = 'all_repos'

# Create the directory if it doesn't exist
if not os.path.exists(REPOS_DIR):
    os.makedirs(REPOS_DIR)

# API endpoint to list repositories
REPOS_URL = f'https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}'

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect('repo_tracker.db')
    c = conn.cursor()
    
    # Create or update table to track repo updates with branch name
    c.execute('''
        CREATE TABLE IF NOT EXISTS repo_updates (
            repo_name TEXT PRIMARY KEY,
            branch_name TEXT,
            last_commit_hash TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Save the last commit hash to the DB
def save_commit_hash(repo_name, branch_name, commit_hash):
    conn = sqlite3.connect('repo_tracker.db')
    c = conn.cursor()
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

    # Insert or update the repository info along with the branch name
    c.execute('REPLACE INTO repo_updates (repo_name, branch_name, last_commit_hash, timestamp) VALUES (?, ?, ?, ?)',
              (repo_name, branch_name, commit_hash, timestamp))
    
    conn.commit()
    conn.close()

# Get the last commit hash from the DB
def get_last_commit_hash(repo_name):
    conn = sqlite3.connect('repo_tracker.db')
    c = conn.cursor()
    c.execute('SELECT last_commit_hash FROM repo_updates WHERE repo_name = ?', (repo_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Function to get the repositories list
def get_repositories():
    repos = []
    next_url = REPOS_URL

    while next_url:
        response = requests.get(next_url, auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
        
        if response.status_code != 200:
            print(f"Error: Failed to retrieve repositories, status code {response.status_code}")
            print(response.text)
            return []
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print("Error: Failed to parse JSON response.")
            print(f"Response content: {response.text}")
            return []
        
        repos.extend(data.get('values', []))
        next_url = data.get('next')

    return repos

# Function to clone or update repositories
def clone_or_update_repository(repo_slug, repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name)

    # If the repo already exists locally, pull the latest changes
    if os.path.exists(repo_path):
        last_commit_hash = get_last_commit_hash(repo_name)

        branches_url = f'https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/refs/branches'
        response = requests.get(branches_url, auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
        
        if response.status_code != 200:
            print(f"Error: Failed to retrieve branches for {repo_name}.")
            return False

        branches = response.json().get('values', [])
        if not branches:
            print(f"No branches found for repository '{repo_name}'. Skipping pull.")
            return False

        branch_names = [branch['name'] for branch in branches]
        branch_to_clone = 'master' if 'master' in branch_names else 'main' if 'main' in branch_names else branch_names[0]

        branch_info = next((branch for branch in branches if branch['name'] == branch_to_clone), None)

        if branch_info and 'target' in branch_info:
            latest_commit_hash = branch_info['target'].get('hash')
            if not latest_commit_hash:
                print(f"Error: No commit hash found for branch '{branch_to_clone}' in repository '{repo_name}'.")
                return False
        else:
            print(f"Error: 'target' key missing for branch '{branch_to_clone}' in repository '{repo_name}'.")
            return False

        if last_commit_hash == latest_commit_hash:
            print(f"No updates for repository '{repo_name}'. Skipping pull.")
            return False  # No update

        print(f"Pulling latest updates for repository '{repo_name}'...")
        os.system(f'git -C "{repo_path}" pull')

        # Get the list of modified files
        modified_files = subprocess.check_output(
            ['git', '-C', repo_path, 'diff', '--name-only', f'{last_commit_hash}..HEAD']
        ).decode().splitlines()

        # If there are modified files, run TruffleHog on those files
        if modified_files:
            print(f"Modified files for {repo_name}: {modified_files}")
            for modified_file in modified_files:
                modified_file_path = os.path.join(repo_path, modified_file)
                if os.path.isfile(modified_file_path):
                    run_trufflehog_on_file(modified_file_path, repo_name)
        else:
            print(f"No modified files found for {repo_name}.")

        # Save the branch name along with commit hash in the DB
        save_commit_hash(repo_name, branch_to_clone, latest_commit_hash)
        return True  # Repo updated

    else:
        # Clone the repository if it doesn't exist locally
        clone_repository(repo_slug, repo_name)
        branches_url = f'https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/refs/branches'
        response = requests.get(branches_url, auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))

        if response.status_code != 200:
            print(f"Error: Failed to retrieve branches for {repo_name}.")
            return False

        branches = response.json().get('values', [])
        if not branches:
            print(f"No branches found for repository '{repo_name}'. Skipping clone.")
            return False

        branch_names = [branch['name'] for branch in branches]
        branch_to_clone = 'master' if 'master' in branch_names else 'main' if 'main' in branch_names else branch_names[0]

        branch_info = next((branch for branch in branches if branch['name'] == branch_to_clone), None)
        if branch_info and 'target' in branch_info:
            latest_commit_hash = branch_info['target'].get('hash')

            # Save the branch name and commit hash
            save_commit_hash(repo_name, branch_to_clone, latest_commit_hash)
            return True  # New repo cloned
        else:
            print(f"Error: 'target' key missing for branch '{branch_to_clone}' in repository '{repo_name}'.")
            return False

def run_trufflehog_on_file(file_path, repo_name):
    print(f"Running TruffleHog on file: {file_path}")
    
    # Save the result file in the all_repos folder
    result_file = os.path.join(REPOS_DIR, f"{repo_name}_th_results.txt")
    
    trufflehog_command = ["trufflehog", "filesystem", file_path, "--only-verified"]
    
    # Run the TruffleHog command and save the results in the all_repos folder
    with open(result_file, 'w') as outfile:
        subprocess.run(trufflehog_command, stdout=outfile)
    
    print(f"TruffleHog results saved to {result_file}")
    
    # Call the send_to_slack.py script to send the result to Slack
    print(f"Sending {result_file} to Slack...")
    subprocess.run(['python3', 'send_to_slack.py', result_file, repo_name])

# Save repository info
def save_repo_info(repos):
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

    info = {
        "Total number of repositories found": len(repos),
        "Timestamp in IST": timestamp,
        "Repositories name": [repo['name'] for repo in repos]
    }

    with open('repo_info.json', 'w') as f:
        json.dump(info, f, indent=4)

# Function to clone repositories
def clone_repository(repo_slug, repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name)
    if os.path.exists(repo_path):
        print(f"Directory '{repo_path}' already exists. Skipping clone.")
        return

    # Use the repository slug in the URL to handle special characters
    repo_url = f'https://{BITBUCKET_USERNAME}:{BITBUCKET_APP_PASSWORD}@bitbucket.org/{BITBUCKET_WORKSPACE}/{repo_slug}.git'
    branches_url = f'https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{repo_slug}/refs/branches'
    
    response = requests.get(branches_url, auth=(BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD))
    
    if response.status_code != 200:
        print(f"Error: Failed to retrieve branches for {repo_name}.")
        return
    
    branches = response.json().get('values', [])
    
    if not branches:
        print(f"No branches found for {repo_name}. Skipping clone.")
        return
    
    branch_names = [branch['name'] for branch in branches]

    # Check for 'master' or 'main', otherwise use the first available branch
    branch_to_clone = 'master' if 'master' in branch_names else 'main' if 'main' in branch_names else branch_names[0]

    # Safely escape the branch name to handle any special characters
    escaped_branch_to_clone = shlex.quote(branch_to_clone)

    print(f"Cloning branch '{escaped_branch_to_clone}' of repository '{repo_name}' (slug: '{repo_slug}')...")
    os.system(f'git clone --branch {escaped_branch_to_clone} "{repo_url}" "{repo_path}"')

def main():
    # Initialize the DB
    init_db()

    repos = get_repositories()
    if not repos:
        print("No repositories found or failed to retrieve repositories.")
        return

    save_repo_info(repos)
    updated_repos = []
    for repo in repos:
        repo_slug = repo['slug']
        repo_name = repo['name']
        if clone_or_update_repository(repo_slug, repo_name):
            updated_repos.append(repo_name)

if __name__ == '__main__':
    main()
