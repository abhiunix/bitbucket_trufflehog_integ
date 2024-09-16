import os
import subprocess
import argparse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up argument parser
parser = argparse.ArgumentParser(description='Run TruffleHog on all repositories in a specified directory and send results to Slack.')
parser.add_argument('all_repos_dir', type=str, help='Path to the all_repos directory')

# Parse the arguments
args = parser.parse_args()

# Convert the provided path to an absolute path
all_repos_dir = os.path.abspath(args.all_repos_dir)

# Check if the provided path is valid
if not os.path.isdir(all_repos_dir):
    print(f"Error: The directory {all_repos_dir} does not exist.")
    exit(1)

# Initialize Slack client
slack_token = os.getenv('slack_bot_token')  # Slack bot token from environment variables
client = WebClient(token=slack_token)
slack_channel = os.getenv('slack_channel')  # Slack channel ID from environment variables

# Function to send a file to Slack
def send_to_slack(filepath, foldername):
    try:
        result = client.files_upload(
            channels=slack_channel,
            file=filepath,
            title=f"TruffleHog results for {foldername}",
            initial_comment=f"Here are the TruffleHog results for {foldername}."
        )
        print(f"File {filepath} sent to Slack channel {slack_channel}")
    except SlackApiError as e:
        print(f"Error sending file to Slack: {e.response['error']}")

# Function to send an alert if no results were found
def send_empty_file_alert(foldername):
    try:
        result = client.chat_postMessage(
            channel=slack_channel,
            text=f"No results found for {foldername}."
        )
        print(f"Alert sent for empty results in {foldername}")
    except SlackApiError as e:
        print(f"Error sending alert to Slack: {e.response['error']}")

# Function to send the final completion message
def send_completion_message():
    try:
        result = client.chat_postMessage(
            channel=slack_channel,
            text="Secret Scan completed with the TruffleHog."
        )
        print("Completion message sent to Slack.")
    except SlackApiError as e:
        print(f"Error sending completion message to Slack: {e.response['error']}")

# Send summary to Slack
def send_summary_to_slack(total_repos, new_repos, updated_repos):
    try:
        summary_text = f"""
        Total existing repos: {total_repos}
        New repos found: {len(new_repos)}
        These repos got updated in last check:\n
        {', '.join(updated_repos)}
        TruffleHog results for updated and new repos are:
        """
        client.chat_postMessage(channel=slack_channel, text=summary_text)
    except SlackApiError as e:
        print(f"Error sending summary to Slack: {e.response['error']}")

# Change the working directory to "all_repos"
os.chdir(all_repos_dir)

# Loop through each folder in the "all_repos" directory
for foldername in os.listdir(all_repos_dir):
    folder_path = os.path.join(all_repos_dir, foldername)
    
    # Check if it is a directory
    if os.path.isdir(folder_path):
        print(f"Processing folder: {foldername}")
        
        # Command to run trufflehog and save the result to <foldername>_th_results.txt
        result_file = f"{foldername}_th_results.txt"
        trufflehog_command = ["trufflehog", "filesystem", folder_path, "--only-verified"]
        
        # Open the result file and run trufflehog command
        with open(result_file, 'w') as outfile:
            subprocess.run(trufflehog_command, stdout=outfile)
        
        print(f"Results saved to {result_file}")
        
        # Check if the result file is empty
        if os.path.getsize(result_file) == 0:
            print(f"No results found for {foldername}.")
            send_empty_file_alert(foldername)  # Send alert if the file is empty
        else:
            send_to_slack(result_file, foldername)  # Send the result file if it contains data

# Send the completion message after processing all repositories
send_completion_message()


#Usage:
#python3 th_collect_all_at_one_place.py /path/to/all/repos
#python3 th_collect_all_at_one_place.py /Users/abhijeetsingh/Downloads/scripts/bitbucketRepoScanner/all_reposes/all_repos