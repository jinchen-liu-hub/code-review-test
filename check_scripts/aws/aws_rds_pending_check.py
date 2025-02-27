import sys
import re
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from loguru import logger
from libs.query_resource_api import get_account_region_rds_dict
from libs.common import get_secret
from libs.aws import AwsApi


def check_pending_actions():
    aws_cn_secret = json.loads(get_secret('aws48'))
    rds_dict = get_account_region_rds_dict()
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'RDS',
        'category': 'Rds维护事件',
        'logic': '检查出RDS是否存在即将维护的事件。',
        'results': []
    }
    for account in rds_dict:
        for region in rds_dict[account]:
            try:
                if re.match(r"cn-.+", region):
                    aws_key, aws_secret = list(aws_cn_secret.items())[0]
                    cn_flag = True
                    client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account, is_global=False)
                else:
                    client = AwsApi(account=account)
                    cn_flag = False
            except Exception as e:
                logger.info("Failed to create boto3 client ({region}/{account}/{role}): {msg}".format(
                    region=region,
                    account=account,
                    role=AWS_ROLE,
                    msg=str(e)
                ))
                continue
            for rds_instance in rds_dict[account][region]:
                try:
                    if cn_flag:
                        arn = "arn:aws-cn:rds:" + region + ":" + account + ":db:" + rds_instance
                    else:
                        arn = "arn:aws:rds:" + region + ":" + account + ":db:" + rds_instance
                    res = client.describe_pending_maintenance_actions(region, arn, rds_instance)
                    pending_actions = res.get('PendingMaintenanceActions', [])
                    if not pending_actions:
                        continue
                    for pending_action in pending_actions:
                        for action in pending_action.get("PendingMaintenanceActionDetails", []):
                            if action.get("CurrentApplyDate") and action.get("AutoAppliedAfterDate") and action.get(
                                    "ForcedApplyDate"):
                                resource = pending_action.get("ResourceIdentifier", "null")
                                event_action = str(action.get("Action", "null"))
                                event_CurrentApplyDate = str(action.get("CurrentApplyDate", "null"))
                                event_AutoAppliedAfterDate = str(action.get("AutoAppliedAfterDate", "null"))
                                event_ForcedApplyDate = str(action.get("ForcedApplyDate", "null"))
                                event_Description = str(action.get("Description", "null"))
                                check_data = f"Resource: {resource}, Action: {event_action}, CurrentApplyDate: {event_CurrentApplyDate}, \
                                    AutoAppliedAfterDate: {event_AutoAppliedAfterDate}, ForcedApplyDate: {event_ForcedApplyDate}, \
                                    Description: {event_Description}"
                                json_data["results"].append(check_data)
                except Exception as e:
                    logger.error("Failed to check pending events of {instance}: {msg}".format(
                        instance=rds_instance, msg=str(e)
                    ))
                    continue
    return json_data


def run():
    check_pending_res = check_pending_actions()
    json_str = json.dumps(check_pending_res)
    return json_str


if __name__ == "__main__":
    print(check_pending_actions())
