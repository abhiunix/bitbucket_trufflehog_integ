This repository contains scripts and tools for automating scanning org's bitbucket for keys and secrets using trufflehog. 

## Directory Structure

- `.env`: Environment variables configuration file.
- `all_repos/`: Directory containing multiple repositories.

## Environment Variables

The `.env` file contains the following environment variables:

- `BITBUCKET_APP_PASSWORD`: The application password for Bitbucket.
- `BITBUCKET_USERNAME`: The username for Bitbucket.
- `BITBUCKET_WORKSPACE`: The workspace name in Bitbucket.
- `slack_token`: The token for Slack API.
- `channel_id`: The ID of the Slack channel.
- `slack_bot_token`: The bot token for Slack.
- `slack_channel`: The name of the Slack channel.

Example `.env` file:

```properties
BITBUCKET_APP_PASSWORD=xyz
BITBUCKET_USERNAME=xyz
BITBUCKET_WORKSPACE=xyz
slack_token=xyz
channel_id=xyz
slack_bot_token=xyz
slack_channel=#channel_name
```


## Scripts

### bitbucketrepoCloner.py

This script is used to clone Bitbucket repositories. It retrieves the list of repositories from the Bitbucket API and clones them into the `all_repos/` directory.

### send_to_slack.py

This script sends notifications to a Slack channel. It can be used to notify team members about the status of various tasks.

### th_collect_all_at_one_place.py

You can use this script collects stand alone data from all repos and consolidates it into a single location.