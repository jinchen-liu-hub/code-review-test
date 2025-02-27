import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from loguru import logger


def check_ec2_no_monitor():
    # get all available instances
    cnt = 0
    while cnt < 5:
        try:
            ins_list = RcenterSearcher(rcenter_api, rcenter_key).search(
                "ec2",
                json.dumps({"tags.prometheus:monitor": "false"})
            )
            break
        except Exception as err:
            logger.error("Attempt No.{cnt} failed: {msg}".format(cnt=cnt + 1, msg=str(err)))
            cnt += 1
            continue
    if cnt == 5:
        logger.error("Failed to get instance list after 5 attempts, exiting...")
        sys.exit(1)

    no_monitor_ins = {}

    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EC2',
        'category': 'no monitor ec2',
        'logic': '检查出标签prometheus:monitor为false的ec2实例',
        'results': []
    }

    for ins in ins_list:

        account_id = ins.get("account_id", None)
        account = ins.get("account", None)
        account_name = ins.get("account_name", None)
        region = ins.get("region", None)
        tags = ins.get('tags', None)
        instance_name = tags.get('Name', None)
        key = f"{account}_{account_name}_{account_id}_{region}"
        if key not in no_monitor_ins:
            no_monitor_ins[key] = []
        no_monitor_ins[key].append(instance_name)

    if no_monitor_ins:
        for key, instance_name in no_monitor_ins.items():
            account = "_".join(key.split('_')[0:2])
            region = key.split('_')[-1]
            check_data = f"{account}, {region}, {instance_name}"
            json_data["results"].append(check_data)

    return json_data


def run():
    check_res = check_ec2_no_monitor()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == '__main__':
    print(run())
