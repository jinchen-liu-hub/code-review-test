import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from loguru import logger


def check_ec2_tags():
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
                            "135620544099",  # aws29
                            "921287511715",  # bi global
                            "569535923312",  # bi cn

                        ]
                    }
                })
            )
            break
        except Exception as err:
            logger.warning("Attempt No.{cnt} failed: {msg}".format(cnt=cnt + 1, msg=str(err)))
            cnt += 1
            continue
    if cnt == 5:
        logger.error("Failed to get instance list after 5 attempts, exiting...")
        sys.exit(1)

    # no tags ec2 info
    no_tag_ins = {}
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EC2',
        'category': 'no tags',
        'logic': '检查出没有配置tag的EC2。',
        'results': []
    }
    for ins in ins_list:
        account_id = ins.get("account_id", None)
        account = ins.get("account", None)
        account_name = ins.get("account_name", None)
        privateip = ins.get("privateip", None)
        region = ins.get("region", None)
        tags = ins.get('tags', None)

        if not tags or not all(tags.get(k) for k in ['bProject', 'bRelease', 'bEnvironment', 'bService']):
            key = f"{account}_{account_name}_{account_id}_{region}"
            if key not in no_tag_ins:
                no_tag_ins[key] = []
            no_tag_ins[key].append(privateip)

    if no_tag_ins:
        for key, privateips in no_tag_ins.items():
            account = "_".join(key.split('_')[0:2])
            region = key.split('_')[-1]
            check_data = f"{account}, {region}, {privateips}"
            json_data["results"].append(check_data)

    return json_data


def run():
    check_res = check_ec2_tags()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    print(run())
