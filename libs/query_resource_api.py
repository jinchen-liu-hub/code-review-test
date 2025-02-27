import requests
import time
import hashlib
import json
from libs.search_instance import RcenterSearcher, rcenter_api, rcenter_key

META_API_URL = "http://pandora.devops.centurygame.io/api/v1/"
META_API_TOKEN_NAME = "devops"
META_API_TOKEN_KEY = "fecbf76e93ba06d8b0e143c542b6f192"
META_API_QUERY_SUCCESS_CODE = 200


def get_meta_token():
    name = META_API_TOKEN_NAME
    key = META_API_TOKEN_KEY
    timestamp = int(time.time())
    string = (name + key + str(timestamp)).encode('utf-8')
    m = hashlib.md5()
    m.update(string)
    token = m.hexdigest()
    auth = '{"name":"' + name + '","token":"' + token + '","timestamp":"' + str(timestamp) + '"}'
    return auth


def get_account_region_rds_dict():
    """
    Get rds info from meta api. Regenerate a dict for convenient.
    :return: a dict containing all rds and related region and account info like below
        {
            "412250787286": {
                "us-east-1": [
                    "prod-slayone-1"
                ],
                "ap-southeast-1": [
                    "dev-slayone-rds01"
                ],
                ...
            },
            ...
        }
    """
    try:
        instance_dict = {}
        res_rds = requests.get(META_API_URL + "rds/?auth=" + get_meta_token()).json()
        if res_rds['code'] == META_API_QUERY_SUCCESS_CODE:
            for rds in res_rds['data']:
                # only check RDS in aws
                if rds["cloud"] != "aws":
                    continue
                instance_dict.setdefault(rds['accountId'], {})
                instance_dict[rds['accountId']].setdefault(rds['region'], [])
                instance_dict[rds['accountId']][rds['region']].append(rds["instanceId"])
        return instance_dict
    except Exception as e:
        print("Get RDS list failed: %s" % str(e))
        return None


def get_account_region_ec2_dict():
    try:
        ec2_dict = {}
        cnt = 0
        while cnt < 5:
            try:
                ins_list = RcenterSearcher(rcenter_api, rcenter_key).search("ec2", json.dumps({}))
                break
            except Exception as err:
                print("Attempt No.{cnt} failed: {msg}".format(cnt=cnt + 1, msg=str(err)))
                cnt += 1
                continue
        if cnt == 5:
            print("Failed to get ec2 list after 5 attempts, exiting...")
            return None

        for ec2 in ins_list:
            # only filter running instances in AWS
            if ec2.get("cloud", "") == "aws" and ec2.get("ec2state", "") == "running" and ec2.get("spot_instance_request_id", "") == '':
                ec2_dict.setdefault(ec2["account_id"], {})
                ec2_dict[ec2["account_id"]].setdefault(ec2["region"], [])
                ec2_dict[ec2["account_id"]][ec2["region"]].append(ec2["instanceid"])
        return ec2_dict

    except Exception as e:
        print("Get ec2 dict failed: %s" % str(e))
        return None


def get_account_name_dict():
    """
    Query mongo using Rcenter and get all accounts with their name
    :return: a set containing all accounts and names
    """
    try:
        accounts_dict = {}
        cnt = 0
        while cnt < 5:
            try:
                ins_list = RcenterSearcher(rcenter_api, rcenter_key).search("ec2", json.dumps({}))
                break
            except Exception as err:
                print("Attempt No.{cnt} failed: {msg}".format(cnt=cnt + 1, msg=str(err)))
                cnt += 1
                continue
        if cnt == 5:
            print("Failed to get instance list after 5 attempts, exiting...")
            return None

        for ec2 in ins_list:
            if ec2.get("cloud", "") == "aws":
                if ec2["account_id"] not in accounts_dict:
                    accounts_dict[ec2["account_id"]] = ec2["account_name"]
        return accounts_dict

    except Exception as e:
        print("Get account dict failed: %s" % str(e))
        return None

def get_account_region_dict():
    """
    Query mongo using Rcenter and get all accounts with their name
    :return: a set containing all accounts and names
    """
    try:
        accounts_dict = {}
        cnt = 0
        while cnt < 5:
            try:
                ins_list = RcenterSearcher(rcenter_api, rcenter_key).search("ec2", json.dumps({}))
                break
            except Exception as err:
                print("Attempt No.{cnt} failed: {msg}".format(cnt=cnt + 1, msg=str(err)))
                cnt += 1
                continue
        if cnt == 5:
            print("Failed to get instance list after 5 attempts, exiting...")
            return None

        for ec2 in ins_list:
            if ec2.get("cloud", "") == "aws":
                account_info = ec2["account"] + "_" + ec2["account_name"] + "_" + ec2["account_id"] 
                if account_info not in accounts_dict:
                    accounts_dict[account_info] = ec2["region"].split()
                else:
                    accounts_dict[account_info].append(ec2["region"])
        return accounts_dict

    except Exception as e:
        print("Get account dict failed: %s" % str(e))
        return None


if __name__ == "__main__":
    # res = get_account_region_rds_dict()
    # if res:
    #     print json.dumps(res, indent=2)

    # res = get_account_region_ec2_dict()
    # if res:
    #     print json.dumps(res, indent=2)

    res = get_account_region_dict()
    if res:
        print(json.dumps(res, indent=2))
