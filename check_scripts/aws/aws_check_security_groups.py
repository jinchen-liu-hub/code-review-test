import sys
import re
import json
import traceback
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from libs.query_resource_api import get_account_region_dict
from libs.common import get_secret
from libs.aws import AwsApi
from loguru import logger


def check_aws_sg():
    # [account_name, account_id, region, sgid]
    sg_no_used = []
    # [account_name, account_id, region, sgid, ft_port]
    sg_rule_open_to_all = []
    # [account_name, account_id, region, sgid, info]
    sg_special_port_open = []
    special_ports = [3306, 3308, 6379, -1, 22]

    try:
        aws_cn_secret = json.loads(get_secret('aws48'))
        accounts = get_account_region_dict()
        for account_info in accounts.keys():
            account_num, account_name, account_id = account_info.split('_')
            for region in set(accounts[account_info]):
                try:
                    if re.match(r"cn-.+", region):
                        aws_key, aws_secret = list(aws_cn_secret.items())[0]
                        client = AwsApi(access_key=aws_key, secret_key=aws_secret, account=account_id, is_global=False)
                    else:
                        client = AwsApi(account=account_id)
                    security_groups = client.describe_security_groups(region)
                    vpc_cidrs = client.describe_vpcs(region)
                    attached_security_group_ids = client.describe_network_interfaces_security_groups(region)

                    for sg in security_groups:
                        sg_name = sg['GroupName']
                        sgid = sg['GroupId']
                        sginfo = [
                            account_name,
                            account_id,
                            region,
                            sgid,
                            sg_name
                        ]
                        sginfo_port = [
                            account_name,
                            account_id,
                            region,
                            sgid,
                            sg_name
                        ]

                        if sg['GroupName'] == 'default':
                            logger.warning('CHECK_SECURITY_GROUPS: sg: %s is default sg, skip' % sgid)
                            continue

                        if sgid not in attached_security_group_ids:
                            sg_no_used.append(sginfo)
                            continue

                        port_list = []
                        sp_port_list = []

                        for ip_permission in sg['IpPermissions']:
                            if ip_permission['IpProtocol'] in ['icmp', 'icmpv6']:
                                continue

                            f_port = ip_permission.get('FromPort', '')
                            t_port = ip_permission.get('ToPort', '')

                            for ip_range in ip_permission['IpRanges']:

                                if ip_range.get('CidrIp', '') == '0.0.0.0/0' or ip_range.get('CidrIpv6', '') == '::/0':
                                    if f_port == t_port:
                                        port_list.append('%s' % f_port)
                                    else:
                                        port_list.append('%s-%s' % (f_port, t_port))

                                if ip_permission[
                                    'IpProtocol'] == -1 or f_port in special_ports or t_port in special_ports:
                                    if ip_range.get('CidrIp', '') not in vpc_cidrs:
                                        if f_port == t_port:
                                            sp_port_list.append('%s->%s' % (f_port, ip_range.get('CidrIp', '')))
                                        else:
                                            sp_port_list.append(
                                                '%s-%s->%s' % (f_port, t_port, ip_range.get('CidrIp', '')))

                        if port_list:
                            sginfo.append(','.join(port_list))
                            sg_rule_open_to_all.append(sginfo)

                        if sp_port_list:
                            sginfo_port.append(','.join(sp_port_list))
                            sg_special_port_open.append(sginfo_port)
                except Exception as e:
                    logger.error(f"Failed account: {account_id}, {str(e)}")

        return sg_no_used, sg_rule_open_to_all, sg_special_port_open

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
    sg_no_used, sg_rule_open_to_all, sg_special_port_open = check_aws_sg()
    templates = [
        ('sg_no_used', sg_no_used),
        ('sg_rule_open_to_all', sg_rule_open_to_all),
        ('sg_special_port_open', sg_special_port_open)
    ]

    for key, results in templates:
        temp = json_template.copy()
        if key == 'sg_no_used':
            temp['category'] = '未使用的安全组'
            temp['logic'] = '没有在network interfaces中关联的安全组'
        elif key == 'sg_rule_open_to_all':
            temp['category'] = '对外开放所有可访问的安全组'
            temp['logic'] = '对外开放0.0.0.0/0的安全组'
        elif key == 'sg_special_port_open':
            temp['category'] = '对本vpc之外开放的安全组'
            temp['logic'] = '对除本vpc之外的网段开发以下端口(3306, 3308, 6379, -1, 22)的安全组'
        formatted_results = [', '.join(item) for item in results]

        temp['results'] = formatted_results
        json_data.append(temp)
    json_str = json.dumps(json_data)
    return json_str


if __name__ == '__main__':
    run()
