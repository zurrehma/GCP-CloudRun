set -e

cloneRepo() {
  gcloud source repos clone $scriptRepoName
  cd $scriptRepoName
  git checkout $branch
  python3 $fileName
}

cloneRepo