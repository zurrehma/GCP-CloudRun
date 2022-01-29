## Usage
Use the helper script to create cloud run and cloud scheduler jobs.  

## Pre-Requisites
Setup `gcloud` and set the project to use.
```
gcloud auth login
gcloud config set project <project-id>
```
Enable the following APIs for the project, which are needed to create a cloud run application, build a container, publish a container into the Google Container registry and to work with the cloud scheduler:
```
gcloud services enable container.googleapis.com containerregistry.googleapis.com \  
run.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com

```
    
## 1. Cloud Run
[Cloud Run] is a fully managed compute platform that automatically scales your stateless containers.  
#### Deployment Permissions
A user needs the following permissions to create a new Cloud Run service:  

* **`run.services.create`**
* **`run.services.update`**  
* **`iam.serviceAccounts.actAs`**    
* **`run.revisions.get`**
* **`run.revisions.list`**
* **`run.services.update`**
* **`monitoring.timeSeries.list`**
* **`serviceusage.operations.get`**
* **`serviceusage.operations.list`**
* **`serviceusage.quotas.get`**
* **`serviceusage.services.get`**
* **`serviceusage.services.list`**
* **`serviceusage.services.use`**  
* **`resourcemanager.projects.get`** 
* **`resourcemanager.projects.list`** 
* **`storage.objects.create`** 
* **`storage.objects.delete`** 
* **`storage.objects.get`** 
* **`storage.objects.getIamPolicy`** 
* **`storage.objects.list`** 
* **`storage.objects.setIamPolicy`** 
* **`storage.objects.update`** 
* **`loudbuild.builds.create`**
* **`cloudbuild.builds.get`**
* **`cloudbuild.builds.list`**
* **`cloudbuild.builds.update`**
* **`remotebuildexecution.blobs.get`**
* **`resourcemanager.projects.get`**
* **`resourcemanager.projects.list`**

Cloud run role can be created with necessary permissions either by [GCP console] or from helper script.  
A cloud run role can be created with necessary permissions from helper script by executing below command:    
```
roleName=<role-name> title=<title> roleDescription=<role-description> \
iamMember=<iamMember-email> iamPermission=<iam-permission> bash helper.sh createIAMRole
```
**`roleName`** is the name of IAM role.    
**`title`** is the title for IAM role.  
**`roleDescription`** is the description of IAM role.  
**`iamMember`** is the email with which this role will be binded.  
**`iamPermission`** is the comma seprated permissions.  
#### Application Authentication with GCP services (IAM and Logging) 
If application is created from Dockerfile. It is necessary to authenticate the application.    
In order to communicate with application dependent libraries, user needs the following permissions.   

* **`iam.serviceAccountKeys.list`**
* **`iam.serviceAccounts.list`**

A cloud run role can be created with necessary permissions from helper script by executing below command:    
```
roleName=<role-name> title=<title> roleDescription=<role-description> \
iamMember=<iamMember-email> iamPermission=<iam-permission> bash helper.sh createIAMRole
```
**`roleName`** is the name of IAM role.    
**`title`** is the title for IAM role.  
**`roleDescription`** is the description of IAM role.  
**`iamMember`** is the email with which this role will be binded.  
**`iamPermission`** is the comma seprated permissions.  
Following roles are necessary to be attached with service account:   

* **`<roleName>`**   
* **`Logs Writer`**  
* **`Logs Viewer`**  
* **`Source Repository Reader`**  

**`<roleName>`** is the name of IAM role created above which contain service account permissions.  

You can create [service account] with the help of GCP console and then grant [IAM roles] to service account or create a service account from helper script.  
For the creation of service account along with predefined roles from helper script, use:    
```
serviceAccName=<service-account-name> roleID=<role-id> bash helper.sh createAppServiceAccount
```
**`<roleID>`** is the ID of IAM role created above which contain service account permissions. It must be in the form of **`projects/{project_id}/roles/{roleName}`**
#### Cloud Run Application Deployment

In order to the create cloud run application, use below command:   
```
serviceName=<application-name> imageName=<image-name> regionName=<region-name> \
serviceAccount=<service-account> authentication=<authentication> port=<port> \
scriptRepoName=<script-repo-name> fileName=<file-name> branch=<branch-name> \
bash helper.sh createCloudRunService
```
**`serviceName`** is the name of application.  
**`imageName`** is the docker image image hosted on GCR. If image is not created yet, it can be created by executing the following command in a directory where Dockerfile is present.
```
 gcloud builds submit --tag gcr.io/<project-id>/<image-name>
```
**`regionName`** is the region where cloud run application will be hosted.  
**`serviceAccount`** is the email used by the applications to make authorized API calls.  
**`authentication`** Use **`authentication=yes`** to enable and **`authentication=no`** to disable. Application by default will accept authenticated requests only.   
**`port`** is the port number on which application is running. Default is set to 5000.  
**`scriptRepoName`** is the name of repository where python file resides.    
**`fileName`** is the path to python file relative to **`scriptRepoName`**.  
**`branch`** is the branch name, default is set to **`master`**.  

## 2. Cloud Scheduler
[Cloud Scheduler] is a fully managed enterprise-grade cron job scheduler.   
#### Cloud Scheduler Permissions
A user needs the following permissions to create a new Cloud scheduler job:  

* **`appengine.applications.get`**
* **`cloudscheduler.jobs.fullView`**
* **`cloudscheduler.jobs.run`**
* **`resourcemanager.projects.get`**
* **`resourcemanager.projects.list`**
* **`serviceusage.services.get`**
* **`serviceusage.services.list`**
* **`cloudscheduler.jobs.create`**
* **`cloudscheduler.jobs.delete`**
* **`cloudscheduler.jobs.enable`**
* **`cloudscheduler.jobs.fullView`**
* **`cloudscheduler.jobs.get`**
* **`cloudscheduler.jobs.list`**
* **`cloudscheduler.jobs.pause`**
* **`cloudscheduler.jobs.update`**
* **`cloudscheduler.locations.get`**
* **`cloudscheduler.locations.list`**

Cloud schedular role can be created with necessary permissions either by [GCP console] or from helper script.   
A cloud schedular role can be created with necessary permissions from helper script by executing below command:    
```
roleName=<role-name> title=<title> roleDescription=<role-description> \
iamMember=<iamMember-email> iamPermission=<iam-permission>  bash helper.sh createIAMRole
```
**`roleName`** is the name of IAM role.    
**`title`** is the title for IAM role.  
**`roleDescription`** is the description of IAM role.  
**`iamMember`** is the email with which this role will be binded.  
**`iamPermission`** is the comma seprated permissions.  
#### Authenticating Cloud Scheduler with Cloud Run
As cloud run application end point is private,we need to authenticate cloud scheduler with cloud run. For this please visit https://cloud.google.com/run/docs/triggering/using-scheduler#create-service-account   
#### Cloud Schedular Job Creation  
  
In order to create cloud scheduler job, use below command  
```
schedulerName=<scheduler-name> scheduleFrequency=<schedule-frequency> \ 
httpURI=<http-uri> serviceAccountEmail=<service-account> messageBody=<message-body> \
bash helper.sh createScheduler
```
**`schedulerName`** is the name of scheduler job.   
**`scheduleFrequency`** The schedule can be either of the following types:  

 * Crontab: http://en.wikipedia.org/wiki/Cron#Overview
 * English-like schedule: https://cloud.google.com/scheduler/docs/quickstart#defining_the_job_schedule  

**`httpURI`** is the full URI path that the request will be sent to. This string must begin with either http:// or https://.   
**`serviceAccount`** is the email used by the applications to make authorized API calls.  
**`messageBody`** is the path to file containing the data payload to be included as the body of the HTTP request. **`body.json`** file contains the data payload document structure.  
## 3. Data Payload Document
**`body.json`** file contains the JSON document which will be sent to Cloud Run application end-point through Cloud Scheduler job.  
The file contains the following fields:  

**`projectID`** is the ID of the GCP project.  
**`serviceName`** is the name of the Cloud Run application.  
**`region`** is the GCP region.  
**`slackToken`** is the token which will be used by Cloud Run application for authentication with slack, in order to send notifications to slack channel.  
**`slackChannelName`** is the name of the slack channel.  
**`exclude`** is the list of service accounts excluded while checking service accounts.  
**`threshold`** is the key value pair. key is service account name or email and value is days to check if any of the service account key is rotated or not in given days.  

#### Slack Token  
In order to authenticate Cloud Run application with slack, we need OAuth 2.0. It is a protocol that lets your app request authorization to private details in a user's Slack account without getting their password. It's also the vehicle by which Slack apps are installed on a team.    
You'll need to register your app before getting started. A registered app is assigned a unique Client ID and Client Secret which will be used in the OAuth flow. The Client Secret should not be shared.  
1: For registration of app visit https://api.slack.com/apps  
   
   * Click on **`Create New App`** button.  
   * Provide **`App Name`**.  
   * Select Development Slack Workspace.  
   * Click **`Create App`**.  

2: After the creation of the slack app, **`Basic Information`** page will be displayed.  
3: Click on **`OAuth & Permissions`** tab.  
4: In **`Scopes`** section on **`OAuth & Permissions`** page, add following scopes to **`Bot Token Scopes`**.  

   * **`channels:history`**
   * **`channels:manage`**
   * **`channels:read`**
   * **`chat:write`**

5: Click on **`Install App to Workspace`**.  
6: Copy **`Bot User OAuth Access Token`**.  
7: Token generated by this process will be provided in **`body.json`**.  
#### Integration of Slack App with Slack Channel
Slack App needs to be integrated with Slack channel. For this:  

* Select channel from your workspace.  
* Click on **`Conversation setting`** icon in the top right corner.  
* Click on **`View channel details`**.  
* Select **`APP`**.  
* Finally add your app.  

[console]: https://cloud.google.com/appengine/docs/standard/go/access-control#user_account
[GCP console]: https://cloud.google.com/iam/docs/creating-custom-roles
[Cloud Scheduler]: https://cloud.google.com/scheduler/
[Cloud Run]: https://cloud.google.com/run 
[service account]: https://cloud.google.com/iam/docs/creating-managing-service-accounts
[IAM roles]: https://cloud.google.com/iam/docs/granting-roles-to-service-accounts