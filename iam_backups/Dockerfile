# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.7-slim

# Copy local code to the container image.
WORKDIR /app
COPY ./requirements.txt ./start.sh ./

# Install production dependencies.
RUN apt-get update && \
  apt-get install -y gnupg2 curl git && \
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-sdk -y && \
  pip3 install -r requirements.txt

ENTRYPOINT [ "bash" ]
CMD [ "start.sh" ]
