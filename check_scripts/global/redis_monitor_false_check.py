import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from loguru import logger


def check_redis_no_monitor():
    # get all available instances
    cnt = 0
    while cnt < 5:
        try:
            ins_list = RcenterSearcher(rcenter_api, rcenter_key).search(
                "elasticache",
                json.dumps({"tags.prometheus:monitor":"false"})
            )
            break
        except Exception as err:
            print("Attempt No.{cnt} failed: {msg}".format(cnt=cnt+1, msg=str(err)))
            cnt += 1
            continue
    if cnt == 5:
        print("Failed to get instance list after 5 attempts, exiting...")
        sys.exit(1)
        
    no_monitor_ins = {}
    
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'Redis',
        'category': 'no monitor redis',
        'logic': '检查出标签prometheus:monitor为false的redis实例',
        'results': []
    }

    for ins in ins_list:
        
        account_id = ins.get("account", None)
        cloud = ins.get("cloud", None)
        region = ins.get("region", None)
        instance_name = ins.get('_id', None)
        key = f"{cloud}_{account_id}_{region}"
        if key not in no_monitor_ins:
            no_monitor_ins[key] = []
        no_monitor_ins[key].append(instance_name)
            
    if no_monitor_ins:
        for key, instance_name in no_monitor_ins.items():
            account = "_".join(key.split('_')[:2])
            region = key.split('_')[-1]
            check_data = f"{account}, {region}, {instance_name}"
            json_data["results"].append(check_data)
        
    return json_data
    
def run():
    check_res = check_redis_no_monitor()
    json_str = json.dumps(check_res)
    return json_str
    
if __name__ == '__main__':
    print(run())