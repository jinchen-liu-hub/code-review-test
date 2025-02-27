import os
import time
import boto3
import logging
import calendar
import requests
import pandas as pd
from ruamel.yaml import YAML
from botocore.client import Config

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
CONF_PATH = os.path.join(BASE_PATH, 'conf')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def sync_account_role_token(account_id, role, key, secret, duration_seconds=3600, cn_flag=False):
    # assume role info params is different in cn region
    if not cn_flag:
        client = boto3.client(
            'sts',
            aws_access_key_id=key,
            aws_secret_access_key=secret
        )

        response = client.assume_role(
            RoleArn='arn:aws:iam::' + str(account_id) + ':role/' + role,
            RoleSessionName='{account_id}_{role}'.format(account_id=account_id, role=role),
            DurationSeconds=duration_seconds
        )
    else:
        client = boto3.client(
            'sts',
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            endpoint_url='https://sts.cn-north-1.amazonaws.com.cn',
            region_name='cn-north-1'
        )

        response = client.assume_role(
            RoleArn='arn:aws-cn:iam::' + str(account_id) + ':role/' + role,
            RoleSessionName='{account_id}_{role}'.format(account_id=account_id, role=role),
            DurationSeconds=duration_seconds
        )

    role_info = dict()
    role_info['key'] = response['Credentials']['AccessKeyId']
    role_info['secret'] = response['Credentials']['SecretAccessKey']
    role_info['token'] = response['Credentials']['SessionToken']
    role_info['expiration'] = calendar.timegm(response['Credentials']['Expiration'].utctimetuple())
    return role_info


def create_boto3_client(account_id, role, key, secret, duration_seconds=3600, cn_flag=False,
                        service_type="kinesis",
                        region_name="ap-southeast-1",
                        timeout=60):
    role_info = sync_account_role_token(account_id, role, key, secret, duration_seconds=duration_seconds,
                                        cn_flag=cn_flag)
    boto3_client, expiration = create_boto3_client_using_token(
        role_info,
        service_type=service_type,
        region_name=region_name,
        timeout=timeout)
    return boto3_client, expiration


def create_boto3_client_using_token(role_info, service_type="kinesis", region_name="ap-southeast-1",
                                    timeout=60, max_pool_connections=50):
    """
    Create a specified boto3 client using role_info, the role info is a dict which is mostly returned by
    calling sync_account_role_token() defined above
    :param role_info: A dict containing assumed role info (key, secret, token and expiration)
    :param service_type: AWS supported service type.
    :param region_name: AWS region name
    :param timeout: AWS boto3 timeout in seconds, default 60
    :param max_pool_connections: max_pool_connections here can avoid pool size warnings in multi-threads situations
    :return: boto3 client and update_time which will be used to judge whether the auth will expire
    """
    # config = Config(connect_timeout=timeout, read_timeout=timeout)
    config = Config(connect_timeout=timeout, read_timeout=timeout, max_pool_connections=max_pool_connections)
    boto3_client = boto3.client(
        service_type,
        region_name=region_name,
        aws_access_key_id=role_info['key'],
        aws_secret_access_key=role_info['secret'],
        aws_session_token=role_info['token'],
        config=config
    )
    return boto3_client, role_info['expiration']


def get_config_path(file_name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def get_aws_credential():
    import configparser

    logger.info(message="LOADING CONFIG: Reading credential configurations...")
    accounts = []
    config = configparser.ConfigParser()
    # config = ConfigParser.SafeConfigParser({'enable', 'true'})
    config.read(get_config_path('aws.conf'))
    for credential_name in config.sections():
        cloud = config.get(credential_name, "cloud")
        key = config.get(credential_name, "key").strip()
        secret = config.get(credential_name, "secret").strip()
        account_name = config.get(credential_name, "account_name").strip()
        account_id = config.get(credential_name, "account_id").strip()
        payer = config.get(credential_name, "payer").strip()
        regions = config.get(credential_name, "regions").strip().strip(',').replace(' ', '').split(',')
        try:
            is_enable = config.get(credential_name, 'enable')
        except:
            is_enable = "true"

        if is_enable == "false":
            logger.info(message="LOADING CONFIG: The acount {id} {c} is disabled".format(id=account_id, c=account_name))
            continue
        account = {}
        account['credential_name'] = credential_name
        account['accesskey'] = key
        account['secret'] = secret
        account['account_name'] = account_name
        account['account_id'] = account_id
        account["regions"] = regions
        account["payer"] = payer
        if not cloud:
            cloud = "aws-global"
        account['cloud'] = cloud
        accounts.append(account)
        logger.info(message="LOADING CONFIG: Found credentials " + credential_name)
    return accounts


def send_message_to_duty(topic, service, tags, message, status=1, check_time=0):
    import requests
    import json

    if check_time == 0:
        check_time = int(time.time())

    data = {
        'category': topic,
        'service': service,
        'tags': tags,
        'status': status,
        'message': message,
        'checktime': check_time,
        'space_uuid': 'd10bbc58-4e62-6100-0dfe-17325633ec4a',
        'token': '6D21965CE8F29C860A6C17594AB6A58A'
    }

    url = 'http://duty.funplus.io/Event/index'
    res = requests.post(url, data=data)
    if res.status_code != 200:
        logger.error(f"Send event to duty failed({topic} {service} {tags}),due to return {res.status_code}")
        return False

    ret = json.loads(res.text)
    if ret['status'] == 1:
        logger.info(f"Send event to duty: {topic} {service} {tags} {message}")
        return True
    else:
        logger.error(f"Send event to duty failed({topic} {service} {tags}), due to return {ret['message']}")
        return False


def call_duty(html_content, service, tags):
    # constants for duty api
    DUTY_API = "http://duty.funplus.io/Event/index"
    DUTY_SPACE_UUID = "d10bbc58-4e62-6100-0dfe-17325633ec4a"
    DUTY_TOKEN = "87446290F1D46770036A144BD976AE10"
    DUTY_CATEGORY = "AWS"
    DUTY_DEFAULT_STATUS = 2  # 2 stands for critical
    data = {
        "space_uuid": DUTY_SPACE_UUID,
        "token": DUTY_TOKEN,
        "category": DUTY_CATEGORY,
        "status": DUTY_DEFAULT_STATUS,
        "service": service,
        "tags": tags,
        "checktime": time.time(),
        "message": html_content
    }
    try:
        requests.post(DUTY_API, data=data)
        logger.info("Call duty succeed!")
    except Exception as e:
        logger.error(f"Failed to call duty api: {str(e)}")


def json2html(json_data):
    html_head = """<html>
        <head>
        <style>
        table#base_table {width: 1000px; border-collapse: collapse; font-size: 13px; margin: 0; font-family: Arial, sans-serif; table-layout: fixed;}
        table#base_table th, table#base_table td {border: 1px solid #e6e6e6;; padding: 8px; text-align: center;}
        table#base_table th {background-color: #4CAF50; color: white;}
        table#base_table tr:nth-child(even) {background-color: #f2f2f2;}
        table#base_table tr:hover {background-color: #ddd;}
        </style>
        </head><body>
        """
    html_tail = "</body></html>"
    columns = json_data['headers']
    rows = []
    for row in json_data['rows']:
        # 列表中多个值增加换行
        for key, value in row.items():
            if isinstance(value, list):
                row[key] = '<br>'.join(value)
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns)
    html_content = df.to_html(index=False, escape=False, border=0, table_id='base_table')
    full_html = html_head + html_content + html_tail
    return full_html


def load_config(file_name: str):
    '''
    params: file_name
    return: config content with dict
    '''
    config_file = os.path.join(CONF_PATH, file_name)
    try:
        with open(config_file, 'r', encoding='utf-8') as cf:
            yaml = YAML(typ='rt')
            return yaml.load(cf.read())
    except Exception as e:
        logger.error('read config file [%s] error: %s' % (config_file, e))
        return {}


def get_secret(secret_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name='us-west-2'
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return secret
    except Exception as e:
        raise ('get secret error:', e)


def convert_bytes(size_in_bytes):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_in_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"
