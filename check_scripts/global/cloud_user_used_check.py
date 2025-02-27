import requests
import traceback
import json
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

prometheus_federation_url = 'http://10.13.149.77:60090'


def check_access_key_used():
    uri = '/api/v1/query'
    query = 'clouduser_access_key_last_used_ts < (time() - 15552000)'
    headers = {
        'Accept': 'application/json'
    }
    params = {
        'query': query
    }

    request_uri = f'{prometheus_federation_url}{uri}'
    try:
        res = requests.get(request_uri, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            logger.error(res.text)
            raise Exception('Get prometheus query_range error')
        access_key_info = {
            'template': 'template_2.html',
            'cloud_product': 'clouduser',
            'rows': []}
        for r in res.json()['data']['result']:
            account = r['metric'].get('account', 'None')
            instance_name = r['metric'].get('instance_name', 'None')
            username = r['metric'].get('username', 'None')
            akid = r['metric'].get('akid', 'None')
            value = int(r['value'][-1])
            access_key_info['rows'].append({
                'instance_name': instance_name,
                'account_id': account,
                'username': username,
                'akid': akid,
                'last_used': datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            })
        return access_key_info
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f'{e},tb:{tb}')


def check_console_used():
    uri = '/api/v1/query'
    query = 'clouduser_password_last_used_ts < (time() - 15552000)'
    headers = {
        'Accept': 'application/json'
    }
    params = {
        'query': query
    }

    request_uri = f'{prometheus_federation_url}{uri}'
    try:
        res = requests.get(request_uri, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            logger.error(res.text)
            raise Exception('Get prometheus query_range error')
        console_info = {
            'template': 'template_2.html',
            'cloud_product': 'clouduser',
            'rows': []}
        for r in res.json()['data']['result']:
            account = r['metric'].get('account', 'None')
            instance_name = r['metric'].get('instance_name', 'None')
            username = r['metric'].get('username', 'None')
            value = int(r['value'][-1])
            if value == 0:
                continue
            console_info['rows'].append({
                'instance_name': instance_name,
                'account_id': account,
                'username': username,
                'last_used': datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            })
        return console_info
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f'{e},tb:{tb}')


def run():
    json_data = [
        check_access_key_used(),
        check_console_used()
    ]
    json_str = json.dumps(json_data)
    return json_str


if __name__ == '__main__':
    print(run())
