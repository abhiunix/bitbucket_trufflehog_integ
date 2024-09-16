import os
import argparse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up argument parser
parser = argparse.ArgumentParser(description='Send a file to Slack.')
parser.add_argument('file_path', type=str, help='Path to the file to send')
parser.add_argument('repo_name', type=str, help='Repository name')

# Parse the arguments
args = parser.parse_args()

# Convert the provided path to an absolute path
file_path = os.path.abspath(args.file_path)

# Check if the provided file exists
if not os.path.isfile(file_path):
    print(f"Error: The file {file_path} does not exist.")
    exit(1)

# Initialize Slack client
slack_token = os.getenv('slack_bot_token')  # Slack bot token from environment variables
client = WebClient(token=slack_token)
slack_channel = os.getenv('slack_channel')  # Slack channel ID from environment variables

# Function to send a file to Slack
def send_to_slack(filepath, repo_name):
    try:
        result = client.files_upload(
            channels=slack_channel,
            file=filepath,
            title=f"TruffleHog results for {repo_name}",
            initial_comment=f"Here are the TruffleHog results for {repo_name}."
        )
        print(f"File {filepath} sent to Slack channel {slack_channel}")
    except SlackApiError as e:
        print(f"Error sending file to Slack: {e.response['error']}")

# Send the file to Slack
send_to_slack(file_path, args.repo_name)
