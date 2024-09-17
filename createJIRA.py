#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv
from typing import Optional, List
import csv
from typing import Optional

def get_project_key_from_csv(repo_name: str, project_repo_map: dict) -> Optional[str]:
    """
    Retrieve the project key from the project-repo mapping.

    Args:
        repo_name (str): The name of the repository.
        project_repo_map (dict): The mapping of repo names to project keys.

    Returns:
        Optional[str]: The project key if found, else None.
    """
    return project_repo_map.get(repo_name)

# Load environment variables from .env file
load_dotenv()

# JIRA Configuration
JIRA_BASE_URL = os.getenv('JIRA_BASE_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')  # As specified

# Validate environment variables
if not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
    raise EnvironmentError("Missing one or more JIRA environment variables. Please check your .env file.")

def convert_description_to_adf(description_text: str) -> dict:
    """
    Convert a markdown-like description to Atlassian Document Format (ADF).

    Args:
        description_text (str): The description text with possible markdown elements.

    Returns:
        dict: ADF-compliant JSON object for JIRA API.
    """
    lines = description_text.split('\n')
    content = []

    in_code_block = False
    code_block_content = []
    bullet_points = False

    for line in lines:
        stripped_line = line.strip()
        
        # Detect code block start/end
        if stripped_line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_content = []
            else:
                in_code_block = False
                # Add code block to content
                content.append({
                    "type": "codeBlock",
                    "content": [
                        {
                            "type": "text",
                            "text": "\n".join(code_block_content)
                        }
                    ]
                })
            continue

        if in_code_block:
            code_block_content.append(line)
            continue

        # Detect bullet points
        if stripped_line.startswith('- '):
            if not bullet_points:
                bullet_points = True
                content.append({
                    "type": "bulletList",
                    "content": []
                })
            # Add list item
            bullet_text = stripped_line[2:].strip()
            content[-1]['content'].append({
                "type": "listItem",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": bullet_text
                            }
                        ]
                    }
                ]
            })
            continue
        else:
            if bullet_points:
                bullet_points = False

        # Handle bold text (e.g., *Issue Summary:*)
        if stripped_line.startswith('*') and stripped_line.endswith('*'):
            # It's a bold line
            bold_text = stripped_line.strip('*').strip()
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": bold_text,
                        "marks": [{"type": "strong"}]
                    }
                ]
            })
            continue

        # Regular paragraph
        if stripped_line == '':
            # Add a new paragraph for empty lines
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": ""
                    }
                ]
            })
        else:
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": line
                    }
                ]
            })

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }

def get_project_key_from_db(repo_name: str) -> Optional[str]:
    """
    Retrieve the project key from the repo_tracker.db for the given repository name.

    Args:
        repo_name (str): The name of the repository.

    Returns:
        Optional[str]: The project key if found, else None.
    """
    conn = sqlite3.connect('repo_tracker.db')
    c = conn.cursor()
    c.execute('SELECT Project_keys FROM repo_updates WHERE repo_name = ?', (repo_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def create_jira_ticket(summary: str, description: str, repo_name: str, project_repo_map: dict, issuetype: str = "Task", labels: Optional[List[str]] = None) -> Optional[str]:
    project_key = get_project_key_from_csv(repo_name, project_repo_map)

    if not project_key:
        print(f"Error: No project key found for repository '{repo_name}'.")
        return None

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Convert description to ADF
    description_adf = convert_description_to_adf(description)

    # Build the payload with the project key and optional labels
    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": summary,
            "description": description_adf,
            "issuetype": {
                "name": issuetype
            }
        }
    }

    if labels:
        payload["fields"]["labels"] = labels

    try:
        response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload))
        response.raise_for_status()
        issue = response.json()
        issue_key = issue.get('key')
        print(f"JIRA ticket created successfully: {issue_key}")
        return issue_key
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while creating JIRA ticket: {http_err}")
        print(f"Response: {response.text}")
    except Exception as err:
        print(f"An error occurred while creating JIRA ticket: {err}")
    
    return None

def add_comment_to_jira(issue_key: str, comment: str) -> bool:
    """
    Add a comment to an existing JIRA ticket.

    Args:
        issue_key (str): The key of the JIRA ticket (e.g., SECURITY-123).
        comment (str): The comment to add.

    Returns:
        bool: True if the comment was added successfully, False otherwise.
    """
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Convert comment to ADF
    comment_adf = convert_description_to_adf(comment)

    payload = {
        "body": comment_adf
    }

    try:
        response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload))
        response.raise_for_status()
        print(f"Comment added to JIRA ticket {issue_key} successfully.")
        return True
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while adding comment to JIRA ticket: {http_err}")
        print(f"Response: {response.text}")
    except Exception as err:
        print(f"An error occurred while adding comment to JIRA ticket: {err}")
    
    return False

def get_issue_details(issue_key: str) -> Optional[dict]:
    """
    Retrieve details of a JIRA ticket.

    Args:
        issue_key (str): The key of the JIRA ticket (e.g., SECURITY-123).

    Returns:
        Optional[dict]: A dictionary containing issue details if successful, else None.
    """
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        issue = response.json()
        print(f"Retrieved details for JIRA ticket {issue_key}.")
        return issue
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while retrieving JIRA ticket details: {http_err}")
        print(f"Response: {response.text}")
    except Exception as err:
        print(f"An error occurred while retrieving JIRA ticket details: {err}")
    
    return None
