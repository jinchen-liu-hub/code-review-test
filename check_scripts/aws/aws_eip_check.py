import sys
import re
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.query_resource_api import get_account_region_dict
from libs.common import get_secret
from libs.aws import AwsApi
from loguru import logger

exclude_account = ['583300917620', '289997590022', '921287511715']


def check_eips_status():
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EIP',
        'category': '未使用EIP',
        'logic': '检查出没有与EC2实例关联的EIP。',
        'results': []
    }

    try:
        aws_cn_secret = json.loads(get_secret('aws48'))
        accounts = get_account_region_dict()
        for account_info in accounts.keys():
            account_id = account_info.split('_')[2]
            for region in set(accounts[account_info]):
                try:
                    if re.match(r"cn-.+", region):
                        aws_key, aws_secret = list(aws_cn_secret.items())[0]
                        client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account_id, is_global=False)
                    else:
                        client = AwsApi(account=account_id)
                    # get available eips
                    response = client.describe_addresses(region)
                    eips = []
                    if response.get("Addresses", "") and account_id not in exclude_account:
                        for eip in response.get("Addresses", ""):
                            if not eip.get('InstanceId', '') and not eip.get('PrivateIpAddress', ''):
                                eips.append(eip['PublicIp'])
                        if eips:
                            check_data = f"{account_info}, {region}, {eips}"
                            json_data["results"].append(check_data)
                except Exception as e:
                    logger.error(f"Failed account: {account_id}, {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get eips info: {str(e)}")
    finally:
        return json_data


def run():
    check_res = check_eips_status()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    print(run())
