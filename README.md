# OCP Infra Slack Bot

This is a Slack bot built to help users interact with AWS and OpenStack cloud resources through simple commands. The bot can create OpenShift clusters in AWS and virtual machines in OpenStack etc etc. It can connect to JIRA and Jenkins to perform some tasks.It also provides helpful information when mentioned or through direct messages.

## Features

- **Create AWS OpenShift Clusters**: Easily create an OpenShift cluster in AWS using the `create-aws-cluster` command.
- **Create OpenStack Virtual Machines**: Create a VM on OpenStack using the `create-openstack-vm` command.
- **Help Command**: The bot responds with a list of available commands when mentioned with the word `help`.
- **Message Handling**: The bot can respond to messages and mentions, providing helpful information or performing actions based on user input.

## Technologies

- **Slack Bolt for Python**: Framework for building Slack apps.
- **AWS SDK (Boto3)**: Interact with AWS services like EC2 and ROSA.
- **OpenStack SDK**: Interact with OpenStack resources.
- **Python 3.x**: The language used for development.

## Requirements

- Python 3.8 or higher
- Slack App with `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
- AWS account with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- OpenStack credentials (`OS_AUTH_URL`, `OS_PROJECT_NAME`, `OS_INTERFACE`, `OS_ID_API_VERSION`,`OS_REGION_NAME`,`OS_APP_CRED_ID`,`OS_APP_CRED_SECRET`,`OS_AUTH_TYPE`)
- AZURE
- GCP
- JIRA
- JENKINS

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/openshift-sustaining/ocp-sustaining-bot.git
cd ocp-sustaining-bot

```

### 2. Create a Virtual Environment
It’s recommended to use a virtual environment to manage dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
```
### 3. Install Dependencies

```bash
pip install -r requirements.txt
```
### 4. Configure Environment Variables
Create a .env file in the root directory and add your Slack and cloud credentials you received from admin:

```bash
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_DEFAULT_REGION=us-west-2

OS_AUTH_URL=https://your-openstack-auth-url
OS_PROJECT_NAME=your-openstack-project-name
.
.
.
```

### 5. Run the Bot

```bash
python slack_main.py
```
## Slack Commands

**/create-aws-cluster <cluster_name>**
Creates an AWS OpenShift cluster using the provided cluster_name.

**/create-openstack-vm <name> <image> <flavor> <network>**
Creates an OpenStack VM with the specified name, image, flavor, and network.

**/hello**
Greets the user with a friendly message.

**/help**
Lists the available commands and how to use them.

## Event Handling

The bot responds to the following events:

Direct Messages: Responds to DMs with helpful information.
Mentions: If the bot is mentioned in a message, it can respond with a message or trigger an action.


## Contributions

Skills required for contributsions are the basic python coding , cloud providers SDK  , jira and jekins integration knowledge . Even if you dont have it we can learn and do it.

Feel free to fork the repository and submit pull requests. Contributions are welcome! 

1. Fork this repository
2. Create a new branch (git checkout -b feature-branch)
3. Do the changes and make sure you lint and format the code using ruff tool.
    - Install Ruff : `pip install ruff`
    - Check code quality : `ruff format --check .`
    - Format the code : `ruff format . --respect-gitignore`
4. Commit your changes (git commit -am 'Add new feature')
5. Push to the branch (git push origin feature-branch)
6. Create a new Pull Request

## Testing
1. There is a slack bot namely : ocp-sustaining-bot is already created and whose credentials will be shared with you along with other cloud credentials.
2. There is a testing slack workspace created : slackbot-template.slack.com . Please get added your user/mail to this by admin.
3. Make sure you add your local .env file with all secrets to the repo root.
4. Once you have your code changes ready the run the code locally using `python slack_main.py` 
5. Then from the slackbot template workspace run your command by mention or direct message to test.

## Draft requirements 

Please refer to the below google docs 
https://docs.google.com/document/d/1D_efhIfCjikWhoY43WqJOOe25DEKsWeXIbmEpqkFJfo/edit?tab=t.0
I will have those tasks added under our sustaining jira project soon.

## TBD 
1. unit tests to be added
2. We need to raise a slack addon enablement service now ticket (https://redhat.service-now.com/help?id=sc_cat_item&sys_id=35bfc06313b82a00dce03ff18144b0d2 ) for this bot to be added to our workspace.
3. Once we are ready with basic commands we can deploy this to our server / or any redhat platform where we run production workloads.  Then ppl can start using this on redhat workspace. 
4. We need to limit this bot our user group which is not done yet.
5. We need to create a build ,test , deploy pipeline to prod for automating new change deployment. Will use github actions.
