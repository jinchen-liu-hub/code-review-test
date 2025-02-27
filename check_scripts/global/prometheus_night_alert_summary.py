import requests
import traceback
import json
import pytz
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

prometheus_federation_url = 'http://10.13.149.77:60090'

utc = pytz.utc


def check_night_alert():
    uri = '/api/v1/query_range'
    query = 'ALERTS{alertstate="firing"}'
    step = 30
    end = datetime.strptime(
        datetime.now(pytz.utc).strftime("%Y-%m-%dT02:05:00.000Z"),
        '%Y-%m-%dT%H:%M:%S.000Z'
    ).timestamp()
    start = datetime.strptime(
        (datetime.now(pytz.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%dT13:55:00.000Z"),
        '%Y-%m-%dT%H:%M:%S.000Z'
    ).timestamp()

    headers = {
        'Accept': 'application/json'
    }
    params = {
        'query': query,
        'start': start,
        'end': end,
        'step': step
    }

    request_uri = f'{prometheus_federation_url}{uri}'
    try:
        res = requests.get(request_uri, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            logger.warning(res.text)
            raise Exception('Get prometheus query_range error')
        # alert_info = {
        #     'alertname|severity|instance': {
        #         'alert_ts': []
        #     }
        # }
        alert_info = {
            'template': 'template_2.html',
            'cloud_product': 'prometheus',
            'rows': []}

        grouped_data = defaultdict(list)
        for r in res.json()['data']['result']:

            if float(r['values'][0][0]) < (start + 300):
                continue

            alertname = r['metric']['alertname']
            severity = r['metric']['severity']
            project = r['metric'].get('project', 'None')
            instance_id = r['metric'].get('instance', 'None')
            instance_name = r['metric'].get('instance_name', 'None')
            if severity in ['warning', 'Warning', 'Error', 'Critical']:
                continue

            value_map = {}
            last_ts = 0
            v_key = 0
            for v in r['values']:
                alert_ts = int(v[0])
                if alert_ts - last_ts > 30:
                    v_key = alert_ts
                last_ts = alert_ts
                if v_key not in value_map:
                    value_map[v_key] = []
                value_map[v_key].append(alert_ts)

            for vm, ts_list in value_map.items():
                grouped_data[(project, alertname, severity, instance_id, instance_name)].append({
                    'start': datetime.fromtimestamp(ts_list[0]).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': datetime.fromtimestamp(ts_list[-1]).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': str(round((ts_list[-1] - ts_list[0]) / 60, 2)) + 'm'
                })

        for (project, alertname, severity, instance_id, instance_name), records in grouped_data.items():
            alert_info['rows'].append({
                'project': project,
                'alert_name': alertname,
                'severity': severity,
                'instance_id': instance_id,
                'instance_name': instance_name,
                'alert_count': len(records),
                'records': records
            })

        return alert_info
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f'{e},tb:{tb}')


def run():
    check_res = check_night_alert()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    run()
