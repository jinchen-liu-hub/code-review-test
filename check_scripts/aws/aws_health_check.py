import sys
import re
import json
import botocore

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from loguru import logger
from libs.query_resource_api import get_account_region_dict
from libs.common import get_secret
from libs.aws import AwsApi


def check_health_alerts():
    # check health status
    # 1. AWS Health has a single global endpoint: https://health.us-east-1.amazonaws.com
    # 2. cn region has no health service (http://docs.aws.amazon.com/health/latest/ug/awshealth-ug.pdf)
    accounts = get_account_region_dict()
    aws_cn_secret = json.loads(get_secret('aws48'))
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'Health',
        'category': '需要关注的事件',
        'logic': '检查出EC2或RDS是否发生了自动调度的事件。',
        'results': []
    }
    for account_info in accounts.keys():
        account_id = account_info.split('_')[2]
        for region in set(accounts[account_info]):
            try:
                if re.match(r"cn-.+", region):
                    aws_key, aws_secret = list(aws_cn_secret.items())[0]
                    client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account_id, is_global=False)
                    region = 'cn-northwest-1'
                else:
                    client = AwsApi(account=account_id)
                    region = 'us-east-1'
                events = client.describe_events(region)
                for i in events["events"]:
                    affected = []
                    res_entities = client.describe_affected_entities(region, i.get('arn', ''))
                    for instance in res_entities["entities"]:
                        affected.append(instance["entityValue"])
                    event_type = i.get('eventTypeCode', 'null').replace('_', ' ')
                    event_StartTime = i.get("startTime", "null")
                    check_data = f"{event_type}, {account_id}, affected: {affected}, startTime: {event_StartTime}"
                    json_data["results"].append(check_data)
            except botocore.exceptions.ClientError as e:
                logger.error(f"Health service not available for: {account_id},{e}")
                continue
            except Exception as e:
                logger.error("Error when checking health alerts for account {account}: {msg}".format(
                    account=account_id, msg=str(e)
                ))
                continue
    return json_data


def run():
    check_health_res = check_health_alerts()
    json_str = json.dumps(check_health_res)
    return json_str


if __name__ == "__main__":
    print(check_health_alerts())
