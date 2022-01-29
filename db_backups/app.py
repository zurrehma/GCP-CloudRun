from flask import Flask, jsonify, request
from google.cloud import logging
from google.cloud.logging.resource import Resource
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from werkzeug.exceptions import BadRequest
from datetime import datetime as date
import datetime
import os
import sys
import time
import pytz
import json
import tenacity
from slackclient import SlackClient


app = Flask(__name__)
service = discovery.build('sqladmin', 'v1beta4', cache_discovery=True)
channel_name, project_id, service_name, region = str(), str(), str(), str()
slack_client, cloud_run_resource = None, None
logger = logging.Client().logger('Cloud-Run-Log')

def set_token(token):
  global slack_client
  slack_client = SlackClient(str(token))


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
      "message": "Making slack api call.",
      "functionName": "send_message"
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


def check_diff_time(backup_datetime):
  current_utc = date.utcnow()
  current_time = current_utc.strftime('%d-%m-%Y %H:%M:%S')
  backup_datetime = backup_datetime.strftime('%d-%m-%Y %H:%M:%S')
  date_format = '%d-%m-%Y %H:%M:%S'
  current_time = date.strptime(current_time, date_format)
  backup_datetime = date.strptime(backup_datetime, date_format)
  diff = current_time - backup_datetime
  backup_minutes = (diff.days * 60 * 24) + (diff.seconds // 60)
  return backup_minutes


def compare_threshold(instance, backup_mint, threshold_min):
  log_to_stackdriver(
    {
      "message": "Comparing threshold of instance.",
      "instanceName": str(instance),
      "lastBackupInMin": str(backup_mint),
      "thresholdMinutes": str(threshold_min),
      "functionName": "compare_threshold"  
    },
    'INFO'
  )
  if backup_mint > threshold_min:
    send_msg_to_slack(
      'Backup of instance is not taken \n `Instance Name: '
      + str(instance) + '` \n `Threshold in minutes: ' +
      str(threshold_min) + '` \n `Time since last backup taken in minutes: '
      + str(backup_mint) + '`'
    )


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
def take_backup(instance):
  log_to_stackdriver(
    {
      "message": "Taking backup of instance.",
      "instanceName": str(instance),
      "functionName": "take_backup"
    },
    'INFO'
  )
  insert_response = service.backupRuns().insert(
    project=project_id,
    instance=instance,
    body={}
  ).execute(num_retries=2)
  time.sleep(3)
  for key, value in insert_response.items():
    if key == 'operationType':
      operationType = value
    elif key == 'targetProject':
      targetProject = value
  send_msg_to_slack(
    'SQL instance backup processes initiated for: \n `Instance Name : '
    + str(instance) + '` \n `OperationType: ' + str(operationType) +
    '` \n `Project: ' + str(targetProject) + '`'
  )


def get_backup_time(backup_datetime):
  strip_datetime = backup_datetime.split('T')
  backup_time = strip_datetime[1]
  backup_time = backup_time.split('Z')
  backup_datetime = strip_datetime[0] + ' ' + backup_time[0]
  backup_datetime = datetime.datetime.strptime(backup_datetime.split(".")[0], '%Y-%m-%d  %H:%M:%S')
  return backup_datetime


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
def get_backup(instance, threshold_min, check_only):
  log_to_stackdriver(
    {
      "message": "Getting last backup of instance.",
      "instanceName": str(instance),
      "functionName": "get_backup"
    },
    'INFO'
  )
  backup_list = service.backupRuns().list(
    project=project_id,
    instance=instance, maxResults=1
  ).execute(num_retries=2)
  for key, value in backup_list.items():
    if key == 'items':
      for key1, value1 in value[0].items():
        if (key1 == 'status' and value1 != 'RUNNING'):
          if check_only:
            log_to_stackdriver(
              {
                "message": "Checking backup status.",
                "instanceName": str(instance),
                "backupStatus": str(value1),
                "functionName": "get_backup"
              },
              'INFO'
            )
            if value[0].get('status') != 'SUCCESSFUL':
              send_msg_to_slack(
                'Last backup details: \n `Instance name: '
                + str(instance) + '` \n `Backup id: ' + str(value[0].get('id'))
                + '` \n `Backup Status: ' + str(value[0].get('status')) + '`'
              )
          else:
            backup_datetime = get_backup_time(
              str(value[0].get('endTime'))
            )
            backup_mint = check_diff_time(backup_datetime)
            compare_threshold(instance, int(backup_mint), int(threshold_min))
            time.sleep(1)


def send_msg_to_slack(message):
  log_to_stackdriver(
    {
      "message": "Sending message to slack.",
      "functionName": "send_msg_to_slack"  
    },
    'INFO'
  )
  channels = list_channels()
  if channels:
    for channel in channels:
      if channel['name'] == channel_name:
        send_message(channel['id'], message)


def set_metadata(req_channel_name, req_project_id, req_service_name, 
                 req_region, req_slack_token):
  global channel_name, project_id, service_name, region
  project_id = req_project_id
  service_name = req_service_name
  region = req_region
  channel_name = req_channel_name
  if project_id is None:
    return True, jsonify({"error": str('Please provide projectID')}), 403
  elif service_name is None:
    return True, jsonify({"error": str('Please provide serviceName')}), 403
  elif region is None:
    return True, jsonify({"error": str('Please provide region')}), 403
  elif channel_name is None:
    return True, jsonify({"error": str('Please provide slackChannelName')}), 
    403
  elif req_slack_token is None:
    return True, jsonify({"error": str('Please provide slackToken')}), 403
  else:
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


def catch_error(error_type, err, instance):
  exc_type, exc_obj, exc_tb = sys.exc_info()
  log_to_stackdriver(
    {
      "message": str(err),
      "codeLineNo": str(exc_tb.tb_lineno) 
    },
    'ERROR'
  )
  if error_type == 'HttpError':
    if err.resp.status == 409:
      if err.resp.get('content-type', '').startswith('application/json'):
        reason = 'Operation failed because another backup ' \
          'operation was already in progress for \n `Instance Name:' \
          + str(instance) + '`'
        send_msg_to_slack(reason)
        return jsonify({"error": str(err)}), 409
    elif err.resp.status == 403:
      send_msg_to_slack(
        'Error: Invalid request. please check if the instance `'
        + str(instance) + '` exist or not.'
      )
      return jsonify({"error": str(err)}), 403
    else:
      return jsonify({"error": str(err)}), 404
  elif error_type == 'BadRequest':
    send_msg_to_slack(
      'Invalid request: Please check your document syntex'
    )
    return jsonify({"error": str(err)}), 400
  elif error_type == 'Exception':
    send_msg_to_slack('Error: ' + str(err))
    return jsonify ({"error": str(err)}), 417
  else:
    return jsonify({"error": str(err)}), 404


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
@app.route('/checkBackup', methods=['POST'])
def check_backup():
  try:
    data = request.get_json(force=True)
    error, message, err_code = set_metadata(
      data.get('slackChannelName'), data.get('projectID'),
      data.get('serviceName'), data.get('region'), data.get('slackToken')
    )
    if error:
      return message, err_code
    for instance in data.get('instances'):
      try:
        get_backup(instance, 0, True)
        time.sleep(2)
      except HttpError as err:
        error, err_code = catch_error('HttpError', err, str(instance))
        continue
    return jsonify({"info": "Processes successfully initiated."}), 200
  except BadRequest as err:
    error, err_code = catch_error('BadRequest', err, str())
    return error, err_code
#   except Exception as err:
#     error, err_code = catch_error('Exception', err, str())
#     return error, err_code 


@tenacity.retry(
  wait=tenacity.wait_fixed(5),
  stop=tenacity.stop_after_attempt(3),
  retry=tenacity.retry_if_exception_type(ConnectionResetError) | 
  tenacity.retry_if_exception_type(BrokenPipeError) |
  tenacity.retry_if_exception_type(IOError))
@app.route('/', methods=['POST'])
def parse_json():
  try:
    data = request.get_json(force=True)
    error, message, err_code = set_metadata(
      data.get('slackChannelName'), data.get('projectID'),
      data.get('serviceName'), data.get('region'), data.get('slackToken')
    )
    if error:
      return message, err_code
    for instance, threshold in data.get('threshold').items():
      try:
        get_backup(instance, threshold, False)
        time.sleep(2)
      except HttpError as err:
        error, err_code = catch_error('HttpError', err, str(instance))
        continue
    for instance in data.get('instances'):
      try:
        take_backup(instance)
        time.sleep(2)
      except HttpError as err:
        error, err_code = catch_error('HttpError', err, str(instance))
        continue
    return jsonify({"info": "Processes successfully initiated."}), 200
  except BadRequest as err:
    error, err_code = catch_error('BadRequest', err, str())
    return error, err_code
#   except Exception as err:
#     error, err_code = catch_error('Exception', err, str())
#     return error, err_code   


if __name__ == '__main__':
  app.run(host='0.0.0.0', debug=True)
