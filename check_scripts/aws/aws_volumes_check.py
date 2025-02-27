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


def check_volumes_status():
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EBS',
        'category': '未使用EBS',
        'logic': '检查出没有与EC2实例关联的EBS。',
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
                    # get available volumeids
                    response = client.describe_volumes(region)
                    volumeids = []
                    if response.get("Volumes", "") and account_id not in exclude_account:
                        for volume in response.get("Volumes", ""):
                            volumeids.append(volume['VolumeId'])
                        if volumeids:
                            check_data = f"{account_info}, {region}, {volumeids}"
                            json_data["results"].append(check_data)
                except Exception as e:
                    logger.error(f"Failed account: {account_id}, {str(e)}")

    except Exception as e:
        logger.error(f"Failed to get volumes info: {str(e)}")
    finally:
        return json_data


def run():
    check_res = check_volumes_status()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    print(check_volumes_status())
