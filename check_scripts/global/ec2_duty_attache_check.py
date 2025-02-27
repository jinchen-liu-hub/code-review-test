import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.meta import Meta

meta = Meta()


def check_ec2_no_exporter():
    meta_res = meta.not_attache_exporter_instances()
    json_data = {
        'template': 'template_1.html',
        'cloud_product': 'EC2',
        'category': 'no attache exporter',
        'logic': '通过meta数据检查ec2是否绑定exporter，检查逻辑为exporter数量小于1个',
        'results': []
    }

    exclude_service = ['k8snode']

    for ins in meta_res:
        tag = ins.get('tag')
        service = tag.split(':')[-1]
        if service in exclude_service:
            continue
        ins_id = ins.get('instanceId')
        ins_name = ins.get('instanceName')
        account_id = ins.get('accountId')
        account_name = ins.get('accountName')
        region = ins.get('region')
        check_data = f"{account_id}, {account_name}, {region}, {ins_name}, {ins_id}, {tag}"
        json_data["results"].append(check_data)
    return json_data


def run():
    check_res = check_ec2_no_exporter()
    json_str = json.dumps(check_res)
    return json_str


if __name__ == '__main__':
    print(run())
