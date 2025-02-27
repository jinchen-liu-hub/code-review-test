import sys
import re
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.query_resource_api import get_account_region_dict
from libs.common import get_secret
from libs.aws import AwsApi
from loguru import logger


def check_rds_tags():
    no_tag_ins = {}
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'RDS',
        'category': 'no tags',
        'logic': '检查出没有配置tag的RDS。',
        'results': []
    }
    try:
        aws_cn_secret = json.loads(get_secret('aws48'))
        accounts = get_account_region_dict()
        for account_info in accounts.keys():
            account = account_info.split('_')[0]
            account_name = account_info.split('_')[1]
            account_id = account_info.split('_')[2]

            for region in set(accounts[account_info]):
                try:
                    if re.match(r"cn-.+", region):
                        aws_key, aws_secret = list(aws_cn_secret.items())[0]
                        client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account_id, is_global=False)
                    else:
                        client = AwsApi(account=account_id)

                    # get rds tags info
                    response = client.describe_db_instances(region)
                    if response['DBInstances']:
                        for rds in response['DBInstances']:
                            DBInstanceArn = rds['DBInstanceArn']
                            DBInstanceIdentifier = rds['DBInstanceIdentifier']
                            tags = client.list_tags_for_resource(region, DBInstanceArn)
                            tags_ = {}
                            for tag in tags.get('TagList', None):
                                Key = tag.get('Key', None)
                                Value = tag.get('Value', None)
                                tags_[Key] = Value

                            if not tags['TagList'] or not all(
                                    tags_.get(k) for k in ['bProject', 'bRelease', 'bEnvironment', 'bService']):
                                key = f"{account}_{account_id}_{account_name}_{region}"
                                if key not in no_tag_ins:
                                    no_tag_ins[key] = []
                                no_tag_ins[key].append(DBInstanceIdentifier)
                except Exception as e:
                    logger.error(f"Failed account: {account_id}, {str(e)}")

        if no_tag_ins:
            for key, rds in no_tag_ins.items():
                account = "_".join(key.split('_')[0:2])
                region = key.split('_')[-1]
                check_data = f"{account}, {region}, {rds}"
                json_data["results"].append(check_data)
        return json_data
    except Exception as err:
        logger.info(f"Please check get instance failed: {str(err)}")


def run():
    check_res = check_rds_tags()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    run()
