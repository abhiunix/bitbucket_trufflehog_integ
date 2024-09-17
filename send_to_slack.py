#!/usr/bin/env python3
import os
import argparse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Slack client
slack_token = os.getenv('slack_bot_token')  # Slack bot token from environment variables
client = WebClient(token=slack_token)
slack_channel = os.getenv('slack_channel')  # Slack channel ID from environment variables

# Function to send a file to Slack
def send_file_to_slack(filepath: str, repo_name: str):
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

# Function to send a message to Slack
def send_message_to_slack(message: str):
    try:
        response = client.chat_postMessage(
            channel=slack_channel,
            text=message
        )
        print("Message sent to Slack successfully.")
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Send a file or message to Slack.')
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands: send_file or send_message')

    # Sub-parser for sending files
    parser_file = subparsers.add_parser('send_file', help='Send a file to Slack.')
    parser_file.add_argument('file_path', type=str, help='Path to the file to send')
    parser_file.add_argument('repo_name', type=str, help='Repository name')

    # Sub-parser for sending messages
    parser_message = subparsers.add_parser('send_message', help='Send a message to Slack.')
    parser_message.add_argument('message', type=str, help='Message to send')

    # Parse the arguments
    args = parser.parse_args()

    if args.command == 'send_file':
        file_path = os.path.abspath(args.file_path)
        # Check if the provided file exists
        if not os.path.isfile(file_path):
            print(f"Error: The file {file_path} does not exist.")
            exit(1)
        send_file_to_slack(file_path, args.repo_name)
    elif args.command == 'send_message':
        send_message_to_slack(args.message)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
