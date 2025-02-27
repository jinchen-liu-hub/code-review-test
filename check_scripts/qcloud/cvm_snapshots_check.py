import os
import sys
import time
import pymysql
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key
from libs.common import json2html, call_duty
from libs.meta import Meta
from datetime import datetime
from loguru import logger

cn_db_host = "10.21.6.27"
cn_db_name = "snapshot"
cn_db_user = "snapshot"
cn_db_pass = "SRaeyug@9fw8"
check_service_list = ['mongo', 'mysql', 'redis']

def get_qcloud_instance():
    """
    get qcloud all instances
    :return:
    """
    cvm = Meta("qcloud").ec2()
    return cvm


def mysql_conn(cloud="aws"):
    try:
        if cloud == "aws":
            conn = pymysql.connect(
                host=global_db_host,
                user=global_db_user,
                password=global_db_pass,
                db=global_db_name,
                port=3306,
                charset="utf8"
            )
        else:
            conn = pymysql.connect(
                host=cn_db_host,
                user=cn_db_user,
                password=cn_db_pass,
                db=cn_db_name,
                port=3306,
                charset="utf8"
            )
    except:
        tb = traceback.format_exc()
        logger.error(tb)
        sys.exit(1)
    return conn


def get_snapshot_instances():
    """
    Gets the instance information that needs to be checked for the snapshot
    :return:
    """
    snapshot_instances = dict()

    # qcloud cvm
    cvm_instances = get_qcloud_instance()
    for cvmid, cvm in cvm_instances.items():
        if cvm["service"] in check_service_list and cvm["stateName"] == 'running':
            snapshot_instances[cvmid] = cvm

    return snapshot_instances


def check_snapshots():
    conn = mysql_conn(cloud="qcloud")
    snapshot_instances = get_snapshot_instances()
    zerotime = time.mktime(datetime.now().date().timetuple())
    no_snapshot_instances = {}
    json_data = {
            "headers": ["Type", "Account", "Region", "Service", "InstanceCount", "InstanceIds"],
            "rows": []
        }
    
    if conn and snapshot_instances:
        cur = conn.cursor()
        sql = (
            "select instanceid "
            "from qcloud_snapshots "
            "where instanceid in {instanceids} and createtime > {zerotime}"
        ).format(
            instanceids=tuple(snapshot_instances.keys()),
            zerotime=zerotime
        )
        try:
            cur.execute(sql)
        except:
            tb = traceback.format_exc()
            logger(tb)
            sys.exit(1)
        rs = cur.fetchall()
        cur.close()
        conn.close()

        if not rs:
            logger("rs is null")
            sys.exit(1)

        current_snapshot_instances = [
            instance[0].encode('utf-8') for instance in rs
        ]

        for ins in snapshot_instances:
            if ins not in current_snapshot_instances:
                project = snapshot_instances[ins].get("project", None)
                account_name = "qcloud-main"
                region = snapshot_instances[ins].get("region", None)
                service = snapshot_instances[ins].get("service", None)
                key = "{account_name}_{project}_{region}_{service}".format(
                    account_name=account_name,
                    project=project,
                    region=region,
                    service=service
                )
                if key not in no_snapshot_instances:
                    no_snapshot_instances[key] = []
                no_snapshot_instances[key].append(ins)
        if no_snapshot_instances:
            rows = []
            for key, ins in no_snapshot_instances.items():
                account = "_".join(key.split('_')[0:2])
                region = key.split('_')[-2]
                service = key.split('_')[-1]
                rows.append({
                    "Type": "no_snapshot_cvms",
                    "Account": account,
                    "Region": region,
                    "Service" : service,
                    "InstanceCount": len(ins),
                    "InstanceIds": ins
                })
            json_data['rows'] = rows
            
        return json_data


def run():
    check_res = check_snapshots()
    if len(check_res.get('rows','')) > 0:
        html_content = json2html(check_res)
        call_duty(html_content, "aws_check_cvm_snapshots", "aws_check_cvm_snapshots") 
        logger.info("Checking cvm snapshots alerts finished successfully")
    else:
        logger.error("Checking cvm snapshots alerts finished with error")


if __name__ == "__main__":
    run()
