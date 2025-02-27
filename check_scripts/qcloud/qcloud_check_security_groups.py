import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import traceback
from libs.qcloud import QcloudApi
from libs.common import load_config, get_secret
from loguru import logger

# aws info from env(passed in by jenkins)
QCLOUD_ROLE = "cloud-center-role"

qcloud_cn_secret = json.loads(get_secret('qcloud1'))
qcloud_cn_key, qcloud_cn_secret = list(qcloud_cn_secret.items())[0]

def check_qcloud_sg():
    qcloud_accounts = load_config('qcloud.yaml')
    # [account_name, account_id, region, sgid]
    sg_no_used = []
    # [account_name, account_id, region, sgid, ft_port]
    sg_rule_open_to_all = []
    # [account_name, account_id, region, sgid, info]
    '''腾讯云安全组不绑定vpc,所以无法确定某个端口是否对外部vpc使用'''

    try:
        for k, v in qcloud_accounts.items():
            account_id = v.get('account_id', '')
            regions = v.get('regions', '')
            qcloud_client = QcloudApi(
                account=account_id,
                key=qcloud_cn_key,
                secret=qcloud_cn_secret
            )

            for region in regions:
                all_sgids = qcloud_client.get_all_security_group_ids(region)
                all_sg_policys = qcloud_client.get_all_security_group_policies(region, all_sgids)
                unuse_sg_ids = qcloud_client.get_unuse_security_group_ids(region, all_sgids)
                for sgid, policys in all_sg_policys.items():
                    sginfo = [
                        k,
                        account_id,
                        region,
                        sgid
                    ]
                    if sgid in unuse_sg_ids:
                        sg_no_used.append(sginfo)
                        continue
                    port_list = []

                    for ingress in policys.Ingress:
                        if ingress.Protocol.lower() in ['icmp', 'icmpv6']:
                            continue

                        if ingress.CidrBlock == '0.0.0.0/0' or ingress.Ipv6CidrBlock == '::/0':
                            port_list.append(ingress.Port)

                    if port_list:
                        sginfo.append(','.join(port_list))
                        sg_rule_open_to_all.append(sginfo)

        return sg_no_used, sg_rule_open_to_all
    except Exception as e:
        tb = traceback.format_exc()
        logger.error('CHECK_SECURITY_GROUPS: Unexpected exceptions: %s %s' % (e, tb))


def run():
    json_data = []
    json_template = {
        'template': 'template_1.html',
        'cloud_product': 'Security Groups',
        'category': '',
        'logic': '',
        'results': []
    }
    sg_no_used, sg_rule_open_to_all = check_qcloud_sg()
    templates = [
        ('sg_no_used', sg_no_used),
        ('sg_rule_open_to_all', sg_rule_open_to_all)
    ]

    for key, results in templates:
        temp = json_template.copy()
        if key == 'sg_no_used':
            temp['category'] = '未使用的安全组'
            temp['logic'] = '没有关联任何示例的安全组'
        elif key == 'sg_rule_open_to_all':
            temp['category'] = '对外开放所有可访问的安全组'
            temp['logic'] = '对外开放0.0.0.0/0的安全组'
        formatted_results = [", ".join(map(str, item)) for item in results]

        temp['results'] = formatted_results
        json_data.append(temp)
    json_str = json.dumps(json_data)
    return json_str


if __name__ == '__main__':
    print(run())
