import sys
import json

from pathlib import Path
from libs.alicloud import AlicloudApi
from libs.common import load_config, convert_bytes
from loguru import logger

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.common import get_secret

ali_cn_secret = json.loads(get_secret('alicloud_cn'))
ali_cn_key, ali_cn_secret = list(ali_cn_secret.items())[0]

def get_all_data():
    ali_accounts = load_config('alicloud.yaml')
    data = []
    for k, v in ali_accounts.items():
        if v.get('cloud') != 'alicloud-cn':
            continue
        account = v.get('account_id')
        try:
            alicloud_client = AlicloudApi(account=account, access_key_id=ali_cn_key,
                                          access_key_secret=ali_cn_secret)
            response = alicloud_client.describe_cdn_report()
            if response:
                data.extend(response)
        except Exception as e:
            logger.error(e)
    return data


def check_ali_cdn_flow():
    data = get_all_data()
    alert_info = {
        'template': 'template_2.html',
        'cloud_product': 'cdn',
        'rows': []}
    for record in data:
        for domain in record:
            if not record.get(domain):
                continue
            for item in record.get(domain):
                alert_info['rows'].append({
                    'domain': domain,
                    'ip': item.get('ip', ''),
                    'traffic': convert_bytes(item.get('traf', 0)),
                    'requestNum': item.get('acc', 0)
                })
    return alert_info


def run():
    check_res = check_ali_cdn_flow()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == '__main__':
    print(run())
    # print(convert_bytes(12297594050))
