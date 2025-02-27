import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from loguru import logger


def check_elasticache_tags():
    # get all available instances
    cnt = 0
    while cnt < 5:
        try:
            ins_list = RcenterSearcher(rcenter_api, rcenter_key).search(
                "elasticache",
                query_str=json.dumps({"cloud": "aws"})
            )
            break
        except Exception as err:
            logger.info(f"Attempt No.{cnt + 1} failed: {str(err)}")
            cnt += 1
            continue
    if cnt == 5:
        logger.error("Failed to get instance list after 5 attempts, exiting...")
        sys.exit(1)

    # no tags ec2 info
    no_tag_ins = {}
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'Elasticache',
        'category': 'no tags',
        'logic': '检查出没有配置tag的redis。',
        'results': []
    }
    for ins in ins_list:
        CacheClusterId = ins.get('CacheClusterId', None)
        account = ins.get("account", None)
        region = ins.get("region", None)
        tags = ins.get('tags', None)

        if not tags or not all(tags.get(k) for k in ['bProject', 'bRelease', 'bEnvironment', 'bService']):
            key = f"{account}_{region}"
            if key not in no_tag_ins:
                no_tag_ins[key] = []
            no_tag_ins[key].append(CacheClusterId)

    if no_tag_ins:
        for key, clusters in no_tag_ins.items():
            account = key.split('_')[0]
            region = key.split('_')[1]
            check_data = f"{account}, {region}, {clusters}"
            json_data["results"].append(check_data)

    return json_data


def run():
    check_res = check_elasticache_tags()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == "__main__":
    check_elasticache_tags()
