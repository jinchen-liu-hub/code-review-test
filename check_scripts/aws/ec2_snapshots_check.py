import os
import sys
import json
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from libs.common import get_secret
from libs.aws import AwsApi
from datetime import datetime, timedelta, timezone
from loguru import logger


def get_ec2_instances():
    """
    get aws all ec2 instances
    :return: ins_list
    """
    # get all available instances
    cnt = 0
    while cnt < 5:
        try:
            ins_list = RcenterSearcher(rcenter_api, rcenter_key).search(
                "ec2",
                json.dumps({
                    "ec2state": "running",
                    "cloud": "aws",
                    "account_id": {
                        "$nin": [
                            "921287511715",  # bi global
                            "135620544099"  # poker
                        ]
                    }
                })
            )
            break
        except Exception as err:
            logger.error(f"Attempt No.{cnt + 1} failed: {str(err)}")
            cnt += 1
            continue
    if cnt == 5:
        logger.error("Failed to get instance list after 5 attempts, exiting...")
        sys.exit(1)

    return ins_list


def get_snapshot_instances():
    """
    Gets the instance information that needs to be checked for the snapshot
    :return:
    """
    snapshot_instances = {}

    # aws ec2
    ec2_instances = get_ec2_instances()
    for ins in ec2_instances:
        tags = ins.get('tags', None)
        service = tags.get('bService', None)
        account_id = ins.get('account_id', None)
        region = ins.get('region', None)
        if service in ['mongo', 'mysql', 'redis']:
            ins["service"] = service
            if account_id not in snapshot_instances:
                snapshot_instances[account_id] = {}
            if region not in snapshot_instances[account_id]:
                snapshot_instances[account_id][region] = []
            snapshot_instances[account_id][region].append(ins)

    return snapshot_instances


def check_snapshots():
    aws_cn_secret = json.loads(get_secret('aws48'))
    snapshot_instances = get_snapshot_instances()
    no_snapshot_instances = {}
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EC2',
        'category': 'no snapshots',
        'logic': '检查出service为mysql、mongo、redis的ec2近25小时内是否有快照。',
        'results': []
    }
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=25)
    for account_id, regions in snapshot_instances.items():
        for region, instances in regions.items():
            try:
                if re.match(r"cn-.+", region):
                    aws_key, aws_secret = list(aws_cn_secret.items())[0]
                    client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account_id, is_global=False)
                else:
                    client = AwsApi(account=account_id)

                for ins in instances:
                    account = ins.get("account")
                    account_name = ins.get("account_name", None)
                    instance_id = ins.get("_id")
                    service = ins.get("service")
                    response = client.describe_snapshots(region, instance_id)

                    has_recent_snapshot = False
                    for snapshot in response['Snapshots']:
                        if snapshot['StartTime'] >= start_time:
                            has_recent_snapshot = True
                            break

                    if not has_recent_snapshot:
                        key = f"{account}_{account_id}_{account_name}_{region}_{service}"
                        if key not in no_snapshot_instances:
                            no_snapshot_instances[key] = []
                        no_snapshot_instances[key].append(instance_id)
            except Exception as e:
                logger.error(f"Failed account: {account_id}, {str(e)}")

    if no_snapshot_instances:
        for key, ins in no_snapshot_instances.items():
            account = "_".join(key.split('_')[0:2])
            region = key.split('_')[-2]
            service = key.split('_')[-1]
            check_data = f"{account}, {region}, {service}, {ins}"
            json_data["results"].append(check_data)

    return json_data


def run():
    check_res = check_snapshots()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    run()
