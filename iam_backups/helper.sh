set -e

createIAMRole() {
 
  if [[ -z $roleName ]]; then
    roleName="defaultRole"
    echo "roleName ($roleName)"
  fi
  if [[ -z $title ]]; then
    title="Cloud Run Role"
    echo "title ($title)"
  fi
  if [[ -z $description ]]; then
    description="Cloud Run Role for user to create applications."
    echo "description ($description)"
  fi
  if [[ -z $iamMember ]]; then
    echo "Please provide iamMember email."
    exit 1
  fi
  if [[ -z $iamPermission ]]; then
    echo "Please provide iamPermission with comma seprated values."
    exit 
  fi

  gcloud iam roles create $roleName --project $projectName \
  --title $title --description $roleDescription \
  --permissions $iamPermission \
  --stage ALPHA

  if [[ $? -ne 0 ]]; then
    echo "Error while creating Cloud Run Role."
    exit 1
  fi

  gcloud projects add-iam-policy-binding $projectName --member user:$iamMember \
  --role projects/$projectName/roles/$roleName

  if [[ $? -ne 0 ]]; then
    echo "Error while binding Cloud Run Role with IAM user."
    exit 1
  fi
}

createAppServiceAccount() {

  if [[ -z $serviceAccName ]]; then
    serviceAccName="ApplicationServiceAccount"
    echo "serviceAccName ($serviceAccName)"
  fi
  if [[ -z $roleID ]]; then
    echo "Please provide roleID."
    exit 1
  fi
  gcloud iam service-accounts create $serviceAccName --display-name $serviceAccName

  if [[ $? -ne 0 ]]; then
    echo "Error while cretaing Service Account."
    exit 1
  fi

  gcloud projects add-iam-policy-binding $projectName \
  --member "serviceAccount:"$serviceAccName"@"$projectName".iam.gserviceaccount.com"\
  --role "$roleID"

  gcloud projects add-iam-policy-binding $projectName \
  --member "serviceAccount:"$serviceAccName"@"$projectName".iam.gserviceaccount.com"\
  --role roles/logging.logWriter

  gcloud projects add-iam-policy-binding $projectName \
  --member "serviceAccount:"$serviceAccName"@"$projectName".iam.gserviceaccount.com"\
  --role roles/logging.viewer

  gcloud projects add-iam-policy-binding $projectName \
  --member "serviceAccount:"$serviceAccName"@"$projectName".iam.gserviceaccount.com"\
  --role roles/source.reader

  if [[ $? -ne 0 ]]; then
    echo "Error while assigning roles to Service Account."
    exit 1
  fi

}

createCloudRunService() {

  if [[ -z $serviceName ]]; then
    serviceName="default-app"
    echo "serviceName ($serviceName)"
  fi
  if [[ -z $imageName ]]; then
    echo "Please provide imageName hosted on GCR."
    exit 1
  fi
  if [[ -z $regionName ]]; then
    regionName="us-central1"
    echo "regionName ($regionName)"
  fi
  if [[ -z $serviceAccount ]]; then
    echo "serviceAccount is required."
    exit 1
  fi
  if [[ -z $authentication ]]; then
    authentication="--no-allow-unauthenticated"
    echo "authentication ($authentication)"
  fi
  if [[ $authentication == 'yes' ]]; 
  then
    authentication="--no-allow-unauthenticated"
  else
    authentication="--allow-unauthenticated"
  fi
  
  if [[ -z $port ]]; then
    port="5000"
    echo "port ($port)"
  fi
  if [[ -z $scriptRepoName ]]; then
    echo "scriptRepoName not provided"
    exit 1
  fi
  if [[ -z $branch ]]; then
    branch="master" 
    echo "branch ($branch)"
  fi
  if [[ -z $fileName ]]; then 
    echo "please provide fileName relative to scriptRepoName"
    exit 1
  fi
  
  echo "Creating cloud run service ($serviceName)..."
  gcloud alpha run deploy $serviceName --image $imageName --region $regionName \
  --service-account $serviceAccount $authentication --platform managed --port $port \
  --update-env-vars scriptRepoName=$scriptRepoName,fileName=$fileName,branch=$branch
}

createScheduler() {
  
  if [[ -z $schedulerName ]]; then 
    schedulerName="defaultschedular"
    echo "schedulerName ($schedulerName)"
  fi
  if [[ -z $scheduleFrequency ]]; then
    scheduleFrequency="* * * * *"
    echo "scheduleFrequency ($scheduleFrequency)"
  fi
  if [[ -z $httpURI ]]; then
    echo "httpURI is required."
    exit 1
  fi 
  if [[ -z $serviceAccountEmail ]]; then
    echo "serviceAccountEmail is required."
    exit 1
  fi 
  if [[ -z $messageBody ]]; then
    exit 1
  else
    echo "messageBody ($messageBody)"
  fi

  gcloud scheduler jobs create http $schedulerName --schedule="$scheduleFrequency" --uri=$httpURI \
  --oidc-service-account-email=$serviceAccountEmail \
  --message-body-from-file=$messageBody \
  --oidc-token-audience=$httpURI
}

projectName=$(gcloud config list --format 'value(core.project)')

if [[ $1 == createCloudRunService ]]; then
  createCloudRunService

elif [[ $1 == createScheduler ]]; then
  createScheduler

elif [[ $1 == createIAMRole ]]; then
  createIAMRole

elif [[ $1 == createAppServiceAccount ]]; then
  createAppServiceAccount

elif [[ -z $1 ]]; then
  echo "No bash argument given."
  exit 1

else
  echo "Unexpected value ($1) given."
fi
