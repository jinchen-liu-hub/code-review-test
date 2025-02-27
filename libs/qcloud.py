import json
import traceback
from loguru import logger
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.sts.v20180813 import sts_client, models as sts_models
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

class QcloudApi:

    def __init__(self, account='',key=None, secret=None, profile='', role='cloud-center-role'):
        cred = None
        self.secret_id = None
        self.secret_key = None

        if profile:
            cred = credential.ProfileCredential().get_credential()

        if not cred:
            cred = credential.CVMRoleCredential().get_credential()

        if key and secret:
            cred = credential.Credential(key, secret)

        if cred is None:
            raise Exception('必须提供profile或者secret密钥信息')

        self.cred = cred

        if account:
            self.__assume_role('ap-beijing', account, role)

    def __assume_role(self, region, account, role='cloud-center-role'):
        endpoint = 'sts.tencentcloudapi.com'
        try:
            client_profile = self.__generate_client_profile(endpoint)

            client = sts_client.StsClient(self.cred, region, client_profile)
            req = sts_models.AssumeRoleRequest()
            params = {
                "RoleArn": "qcs::cam::uin/%s:roleName/%s" % (account, role),
                "RoleSessionName": "to-%s" % account
            }
            req.from_json_string(json.dumps(params))

            # 返回的resp是一个AssumeRoleResponse的实例，与请求对象对应
            resp = client.AssumeRole(req)

            self.secret_id = resp.Credentials.TmpSecretId
            self.secret_key = resp.Credentials.TmpSecretKey
            token = resp.Credentials.Token
            self.cred = credential.Credential(self.secret_id, self.secret_key, token)
        except Exception as e:
            logger.error('assume role error:%s' % e)

    def __generate_client_profile(self, endpoint):
        http_profile = HttpProfile(reqTimeout=3)
        http_profile.endpoint = endpoint
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        return client_profile
    
    def describe_security_groups(self, region: str):
        endpoint = 'vpc.tencentcloudapi.com'
        try:
            client_profile = self.__generate_client_profile(endpoint)
            client = vpc_client.VpcClient(self.cred, region, client_profile)

            continue_flag = True
            res_list = []
            offset = 0
            while continue_flag:
                req = vpc_models.DescribeSecurityGroupsRequest()
                req.Limit = '100'
                req.Offset = str(offset)
                resp = client.DescribeSecurityGroups(req)
                continue_flag = True if resp.SecurityGroupSet else False
                res_list += resp.SecurityGroupSet
                offset += 100

            return res_list
        except TencentCloudSDKException as e:
            tb = traceback.format_exc()
            logger.error('%s %s' % (tb, e))
            return []
    
    def describe_security_group_policies(self, region: str, sgid: str):
        endpoint = 'vpc.tencentcloudapi.com'
        try:
            client_profile = self.__generate_client_profile(endpoint)
            client = vpc_client.VpcClient(self.cred, region, client_profile)

            req = vpc_models.DescribeSecurityGroupPoliciesRequest()
            req.SecurityGroupId = sgid
            resp = client.DescribeSecurityGroupPolicies(req)
            return resp.SecurityGroupPolicySet

        except TencentCloudSDKException as e:
            tb = traceback.format_exc()
            logger.error('%s %s' % (tb, e))
            return []
    
    def describe_security_group_association_statistics(self, region: str, sgids: list):
        endpoint = 'vpc.tencentcloudapi.com'
        try:
            client_profile = self.__generate_client_profile(endpoint)
            client = vpc_client.VpcClient(self.cred, region, client_profile)

            res_list = []
            req = vpc_models.DescribeSecurityGroupAssociationStatisticsRequest()
            req.SecurityGroupIds = sgids
            resp = client.DescribeSecurityGroupAssociationStatistics(req)
            res_list += resp.SecurityGroupAssociationStatisticsSet

            return res_list
        except TencentCloudSDKException as e:
            tb = traceback.format_exc()
            logger.error('%s %s' % (tb, e))
            return []
        
    def get_all_security_group_ids(self, region):
        all_security_group_ids = set()
        all_sgs = self.describe_security_groups(region)
        for sg in all_sgs:
            all_security_group_ids.add(sg.SecurityGroupId)

        return list(all_security_group_ids)

    def get_all_security_group_policies(self, region: str, sgids: list):
        all_policys = {}
        for sgid in sgids:
            all_policys.update(
                {
                    sgid: self.describe_security_group_policies(region, sgid)
                }
            )

        return all_policys
    
    def get_unuse_security_group_ids(self, region: str, sgids: list):
        all_unuse_security_group_ids = set()
        if not sgids:
            return []
        all_sgs = self.describe_security_group_association_statistics(region, sgids)
        for sg in all_sgs:
            if sg.TotalCount == 0:
                all_unuse_security_group_ids.add(sg.SecurityGroupId)

        return list(all_unuse_security_group_ids)