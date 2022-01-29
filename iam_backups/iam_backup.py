from flask import Flask, jsonify, request
from google.cloud import logging
from google.cloud.logging.resource import Resource
import os
import google.auth
import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from werkzeug.exceptions import BadRequest
from slackclient import SlackClient
import sys
import json
import datetime
import tenacity
from datetime import datetime as date

app = Flask(__name__)

credentials, project = google.auth.default(
  scopes=['https://www.googleapis.com/auth/cloud-platform'])
service = googleapiclient.discovery.build(
  'iam', 'v1', credentials=credentials)
channel_name, project_id, service_name, region = str(), str(), str(), str()
slack_client, cloud_run_resource = None, None
logger = logging.Client().logger('Cloud-Run-Log')
account_email = dict()


def set_token(token):
  global slack_client
  slack_client = SlackClient(token)


def list_channels():
  channels_call = slack_client.api_call('channels.list')
  if channels_call['ok']:
    return channels_call['channels']
  return None


def log_to_stackdriver(message, log_level):
  logger.log_struct(
    message,
    resource=cloud_run_resource,
    severity=log_level
  )


def send_message(channel_id, message):
  log_to_stackdriver(
    {
      'message': 'Making slack api call.',
      'functionName': 'send_message'
    },
    'INFO'
  )
  slack_client.api_call(
    'chat.postMessage',
    channel=channel_id,
    blocks=[{
      'type': 'section',
      'text': {
        'type': 'mrkdwn',
        'text': message
      }
    }]
  )


def send_msg_to_slack(message):
  log_to_stackdriver(
    {
      'message': 'Sending message to slack.',
      'functionName': 'send_msg_to_slack'  
    },
    'INFO'
  )
  channels = list_channels()
  if channels:
    for channel in channels:
      if channel['name'] == channel_name:
        send_message(channel['id'], message)


def get_key_date(key_datetime):
  log_to_stackdriver(
    {
      'message': 'Getting key creation date.',
      'functionName': 'get_key_date'  
    },
    'INFO'
  )
  strip_date = key_datetime.split('T')
  key_date = datetime.datetime.strptime(
  strip_date[0], '%Y-%m-%d')
  key_date = datetime.datetime.strftime(
    key_date, '%d-%m-%Y'
  )
  return key_date


def calculate_key_days(key_date):
  log_to_stackdriver(
    {
      'message': 'Calculating days since key is created.',
      'functionName': 'calculate_key_days'  
    },
    'INFO'
  )
  current_time = date.utcnow().strftime('%d-%m-%Y')
  date_format = '%d-%m-%Y'
  current_time = date.strptime(str(current_time), date_format)
  key_date = date.strptime(key_date, date_format)
  delta= current_time - key_date
  return delta.days


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
def list_service_acc(project_id, data):
  check_service_account = False
  log_to_stackdriver(
    {
      'message': 'Listing service accounts.',
      'functionName': 'list_service_acc'
    },
    'INFO'
  )
  api_request = service.projects().serviceAccounts().list(name=project_id)
  response = api_request.execute()
  for name in data.get('exclude'):
    for service_account in response.get('accounts', []):
      if service_account.get('displayName') == name \
      or service_account.get('email') == name:
        check_service_account = True
        break
    if check_service_account:
      check_service_account = False
      continue
    send_msg_to_slack(
      'Requested service account does not exist. \n `Service Account Name: '
      + name + '`'
    )


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
def check_account_keys(project_id, account_email):
  log_to_stackdriver(
    {
      'message': 'Ckecking service account keys expiration.',
      'serviceAccEmail': account_email,
      'functionName': 'check_account_keys'  
    },
    'INFO'
  )
  for email, threshold in account_email.items():
    name = project_id + '/serviceAccounts/' + email
    request = service.projects().serviceAccounts().keys().list(name=name)
    response = request.execute()
    for keys in response.get('keys', []):
      if keys.get('keyType') == 'USER_MANAGED':
        key_date = get_key_date(keys.get('validAfterTime'))
        key_days = calculate_key_days(key_date)
        if int(threshold) <= key_days:
          send_msg_to_slack(
            'Key Expired. Please generate new key. \n `Service Account: '
            + email + '` \n `Key ID: ' + keys.get('name') + '`'
          )			


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
def get_account_emails(project_id, req_service_accounts):
  log_to_stackdriver(
    {
      'message': 'Getting service account emails from GCP.',
      'functionName': 'get_account_emails'  
    },
    'INFO'
  )
  project_name = project_id
  request = service.projects().serviceAccounts().list(name=project_name)
  response = request.execute()
  key_found = False
  email_found = False
  for key, value in req_service_accounts.items():
    for service_account in response.get('accounts', []):
      if service_account.get('displayName') == key or \
      service_account.get('email') == key:
        account_email[service_account.get('email')] = value
        if value == 'None':
          account_email[service_account.get('email')] = 90
        key_found = True
        break
    if key_found:
      key_found = False
      continue
    send_msg_to_slack(
      'Requested service account does not exist. \n `Service Account Name: '
      + key + '`'
    )
  for service_account in response.get('accounts', []):
    for key, value in account_email.items():
      if service_account.get('displayName') == key or \
      service_account.get('email') == key:
        email_found= True
        break
    if email_found:
      email_found = False
      continue
    account_email[service_account.get('email')] = 90
  check_account_keys(project_id, account_email)


def catch_error(error_type, err, instance):
  exc_type, exc_obj, exc_tb = sys.exc_info()
  if error_type == 'BadRequest':
    return jsonify({"error": str(err)}), 400
  log_to_stackdriver(
    {
      'message': str(err),
      'codeLineNo': str(exc_tb.tb_lineno)
    },
    'ERROR'
  )
  if error_type == 'Exception':
    send_msg_to_slack('Error: ' + str(err))
    return jsonify({
      "error": str(err),
      "codeLineNo": str(exc_tb.tb_lineno)
    }), 417
  else:
    return jsonify({
      "error": str(err),
      "codeLineNo": str(exc_tb.tb_lineno)
    }), 404


def set_metadata(req_channel_name, req_project_id, req_service_name,
                 req_region, req_slack_token):
  global channel_name, project_id, service_name, region
  
  service_name = req_service_name
  region = req_region
  channel_name = req_channel_name
  if req_project_id is None:
    return True, jsonify({"error": 'Please provide projectID'}), 403
  elif service_name is None:
    return True, jsonify({"error": 'Please provide serviceName'}), 403
  elif region is None:
    return True, jsonify({"error": 'Please provide region'}), 403
  elif channel_name is None:
    return True, jsonify({"error": 'Please provide slackChannelName'}),
    403
  elif req_slack_token is None:
    return True, jsonify({"error": 'Please provide slackToken'}), 403
  else:
    project_id = 'projects/' + req_project_id
    set_token(req_slack_token)
    global cloud_run_resource
    cloud_run_resource = Resource(
      type='cloud_run_revision',
      labels={
        'project_id': project_id,
        'service_name': service_name,
        'region': region
      }
    )
    return False, str(), 0


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
@app.route('/', methods=['POST'])
def check_service_account():
  try:
    data = request.get_json(force=True)
    error, message, err_code = set_metadata(
      data.get('slackChannelName'), data.get('projectID'),
      data.get('serviceName'), data.get('region'), data.get('slackToken')
    )
    if error:
      return message, err_code
    list_service_acc(project_id, data)
    get_account_emails(
      project_id,
      data.get('threshold')
    )		
    return jsonify({"info": "Processes successfully initiated."}), 200
  except BadRequest as err:
    error, err_code = catch_error('BadRequest', err, str())
    return error, err_code	
#   except Exception as err:
#     error, err_code = catch_error('Exception', err, str())
#     return error, err_code


if __name__ == '__main__':
  app.run(host='0.0.0.0')
