# OCP Infra Slack Bot

This is a Slack bot built to help users interact with AWS and OpenStack cloud resources through simple commands. The bot can create OpenShift clusters in AWS and virtual machines in OpenStack etc etc. It can connect to JIRA and Jenkins to perform some tasks.It also provides helpful information when mentioned or through direct messages.

## Features

- **Infrastructure commands**: Handles the infrastructure create tasks with different cloud providers : AWS, AZURE, GCP etc.
- **JIRA & other tool commands**: Handle JIRA commands and other jenkins/ci job trigger commands.
- **Help Command**: The bot responds with a list of available commands when mentioned with the word `help`.
- **Other commands**: Commands to display important team links, trigger a tool/job etc.
- **Message Handling**: The bot can respond to messages and mentions, providing helpful information or performing actions based on user input.
- **Common slack SDK python module** : we are building a common slack backend python module which is opensource and can be installable and reusable . Planning to push to pypi public python registry available to all.
- **API interface using above module** : we are also building an api wrapper around the SDK . This can be deployed an independet app and provides same integrations that we are using in slackbot . This will be helpful to have same functionality with other apps such as google chat etc.

## Technologies

- **Slack Bolt for Python**: Framework for building Slack apps.
- **AWS SDK (Boto3)**: Interact with AWS services like EC2 and ROSA.
- **OpenStack SDK**: Interact with OpenStack resources.
- **Python 3.x**: The language used for development.

## Requirements

- Python 3.12 
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
It's recommended to use a virtual environment to manage dependencies:

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

**create-aws-cluster <cluster_name>**
Creates an AWS OpenShift cluster using the provided cluster_name.


**create-aws-vm**
Creates an AWS EC2 instance.

Sample usage:
```
create-aws-vm --os_name=linux --instance_type=t2.micro --key_pair=new
create-aws-vm --os_name=linux --instance_type=t2.micro --key_pair=existing
```

**list-aws-vms**
Lists AWS EC2 instances

Sample usage:
```

list-aws-vms --state=pending,running,shutting-down,terminated,stopping,stopped
list-aws-vms --type=t3.micro,t2.micro
list-aws-vms --type=t3.micro,t2.micro --state=pending,stopped
list-aws-vms --instance-ids=i-123456,i-987654

```
Note 1:
The list of parameters that can be passed using the --type subcommand is extremely large. 
See [https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_instances.html](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_instances.html) for the complete list.
Search for t2.micro


**create-openstack-vm <name> <image> <flavor> <network>**
Creates an OpenStack VM with the specified name, os type, flavor, network and key name.

Sample usage:
```
create-openstack-vm --name=PAYMENTGATEWAY1 --os_name=fedora --flavor=ci.cpu.small --network=provider_net_ocp_dev --key_name=sustaining-bot-key
```


**list-openstack-vms <status>**
Lists OpenStack VMs.

Sample usage:
```
list-openstack-vms -status=ACTIVE
list-openstack-vms -status=ERROR
```

**hello**
Greets the user with a friendly message.

**help**
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
1. There is a dev slack bot namely : ocp-sustaining-bot is already created . Please get those credentials along with other cloud credentials of the slack bot.
2. There is a testing slack workspace created : slackbot-template.slack.com . Please get your user/mail added to this by the admin.
3. Make sure you add your local .env file with all secrets to the repo root.
4. Once you have your code changes ready then run the code locally using `python slack_main.py` 
5. Then from the slackbot template workspace run your command by mention or direct message to test.

## Draft requirements 

Please refer to the below google docs 
https://docs.google.com/document/d/1D_efhIfCjikWhoY43WqJOOe25DEKsWeXIbmEpqkFJfo/edit?tab=t.0
I will have those tasks added under our sustaining jira project soon.

## Backend Deployment

1. A build pipeline called "Create Docker Image for Slackbot" will create the docker image and push it to the registry `quay.io/ocp_sustaining_engineering/slack_backend` which is also open source.
2. It runs as a docker container inside `project-tools` VM in our openstack cluster. 
   
3. **Troubleshooting tips** :
   Get the key of that server from admin to login . Then use below or similar commands to explore.

   **Docker container commands** : 
    To check if container is running or killed :
     `docker ps -a`
     
   **Docker run command** : 

    `docker run -d --name slack_backend --env-file /root/sec/.env --restart unless-stopped quay.io/ocp_sustaining_engineering/slack_backend:1.0.1`

   **To trace logs** :

   `docker logs -f slack_backend`

   **Increase the log**:
   
   update root/sec/.env and set LOG_LEVEL=DEBUG . Then stop the container and restart it with above mentioned run command.
