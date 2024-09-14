# Github Notification Bot

This bot is designed to notify lark users when a (PR/issue/CI)-related github event occurs (e.g. when a PR is requested to be reviewed, an issue is assigned to somebody, etc.).

### Features

- Handles GitHub webhook events
- Sends notifications to Lark
- IP verification for GitHub webhooks
- Configurable user mapping
- Optional event logging


## Quick Start 

Start bot backend for flavius team:
1. Create a `flavius_user_list` file containing github user login names and lark user ids (example below)

   ```text
   TatianaJin xxxxxxxx
   SomeGithubUser yyyyyyyy
   ```
3. Start the bot backend by `docker compose -p github_bot -f docker-compose.flask.yml up -d`

## Use bot backend for other teams

For more detailed guide on how to create a customized bot for your own team, see https://u2htb344y9.sg.larksuite.com/wiki/VVcIwqdF5iAqbjkFr8fl7z86gme

### Simple Guide
1. Clone the repository
2. Create a user list file
3. Set up a Lark bot and obtain the bot URI
4. Obtain a publicly-accessible port on the host for running the bot backend
5. Change the `command` section to use your own port, lark URI, and user file.
6. Configure the github webhook to push specific events (PR/issue/workflow run) to the bot backend
