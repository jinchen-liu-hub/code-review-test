import sys
import os
import re
import json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.query_resource_api import get_account_region_dict
from libs.common import create_boto3_client
from loguru import logger

# aws info from env(passed in by jenkins)
AWS_ROLE = "cloud"
# AWS_KEY_GLOBAL = os.getenv("AWS_KEY_GLOBAL", "")
# AWS_SECRET_GLOBAL = os.getenv("AWS_SECRET_GLOBAL", "")
AWS_KEY_GLOBAL = "AKIAT4DJIW4D233RTEO5"
AWS_SECRET_GLOBAL = "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"

AWS_ROLE_CN = "cloud"
# AWS_KEY_CN = os.getenv("AWS_KEY_CN", "")
# AWS_SECRET_CN = os.getenv("AWS_SECRET_CN", "")
AWS_KEY_CN = "AKIATA27Y6NASGSRGPBS"
AWS_SECRET_CN = "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"


def check_rds_tags():
    no_monitor_ins = {}
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'RDS',
        'category': 'no monitor rds',
        'logic': '检查出标签prometheus:monitor为false的RDS实例。',
        'results': []
    }
    try:
        #get the boto3 client
        accounts = get_account_region_dict()
        for account_info in accounts.keys():
            account = account_info.split('_')[0]
            account_name = account_info.split('_')[1]
            account_id = account_info.split('_')[2]

            for region in set(accounts[account_info]):
                cn_flag, aws_key, aws_secret, aws_role = [True, AWS_KEY_CN, AWS_SECRET_CN, AWS_ROLE_CN] \
                     if re.match(r"cn-.+", region) else [False, AWS_KEY_GLOBAL, AWS_SECRET_GLOBAL, AWS_ROLE]
                # 跳过cn
                if "cn-" in region:
                    continue
                client, _ = create_boto3_client(account_id, aws_role, aws_key, aws_secret, cn_flag=cn_flag,
                                                                 service_type="rds", region_name=region)
                #get rds tags info
                response = client.describe_db_instances()
                if response['DBInstances']:
                    for rds in response['DBInstances']:
                        DBInstanceArn = rds['DBInstanceArn']
                        DBInstanceIdentifier = rds['DBInstanceIdentifier']
                        tags = client.list_tags_for_resource(ResourceName=DBInstanceArn)
                        tags_ = {}
                        for tag in tags.get('TagList',None):
                            Key = tag.get('Key',None)
                            Value = tag.get('Value',None)
                            tags_[Key] = Value
                            
                        if not tags['TagList'] or tags_.get('prometheus:monitor') == 'false':
                            key = f"{account}_{account_id}_{account_name}_{region}"
                            if key not in no_monitor_ins:
                                no_monitor_ins[key] = []
                            no_monitor_ins[key].append(DBInstanceIdentifier)
                            
        if no_monitor_ins:
            for key, rds in no_monitor_ins.items():
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
    print(run())
