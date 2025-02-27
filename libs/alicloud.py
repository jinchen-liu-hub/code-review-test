import os
import sys
import traceback
import calendar
import datetime
import time
import requests
import pytz

from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_credentials.models import Config as CredConfig
from alibabacloud_credentials.utils import auth_util
from alibabacloud_credentials.exceptions import CredentialException
from alibabacloud_sts20150401.client import Client as Sts20150401Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from alibabacloud_sts20150401 import models as sts_20150401_models
from alibabacloud_resourcedirectorymaster20220419.client import Client as ResourceDirectoryMaster20220419Client
from alibabacloud_resourcedirectorymaster20220419 import models as resource_directory_master_20220419_models
from alibabacloud_cdn20180510.client import Client as Cdn20180510Client
from alibabacloud_cdn20180510 import models as cdn_20180510_models
from loguru import logger


class AlicloudApi:
    regions = []

    def __init__(self,
                 access_key_id: str = '',
                 access_key_secret: str = '',
                 account: str = '',
                 profile: str = 'default',
                 role_name: str = 'cloud-center-role'
                 ):

        self.cred = None
        self.runtime = util_models.RuntimeOptions(
            autoretry=True,
            max_attempts=3,
            connect_timeout=3000
        )

        auth_util.client_type = profile

        try:
            cred = CredClient()
            if cred:
                self.cred = cred
                logger.info('this time use default credential')
            # self.__get_region('dev')
        except CredentialException as ce:
            config = CredConfig(
                type='ecs_ram_role'
            )
            cred = CredClient(config=config)
            if cred:
                self.cred = cred
                logger.info('this time use ecs ram role credential')
        except Exception as e:
            tb = traceback.format_exc()
            logger.error('get default cerdential error %s\n traceback: %s' % (e, tb))

        try:
            if access_key_id and access_key_secret:
                config = CredConfig(
                    type='access_key',
                    access_key_id=access_key_id,
                    access_key_secret=access_key_secret
                )
                cred = CredClient(config)
                if cred:
                    self.cred = cred
        except Exception as e:
            tb = traceback.format_exc()
            logger.error('get cerdential with ak error %s\n traceback: %s' % (e, tb))

        try:
            if account:
                cred = self.__assume_role(account, role_name)

                config = CredConfig(
                    type='sts',
                    access_key_id=cred.access_key_id,
                    access_key_secret=cred.access_key_secret,
                    security_token=cred.security_token
                )
                self.cred = CredClient(config)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error('assume role error %s\n traceback: %s' % (e, tb))

        # if not self.regions:
        #     self.__get_region()

    def __make_config(self, endpoint: str):
        try:
            config = open_api_models.Config(
                credential=self.cred, endpoint=endpoint, connect_timeout=3000)
            return config
        except Exception as e:
            tb = traceback.format_exc()
            logger.error('get config error %s\n traceback: %s' % (e, tb))

    def __assume_role(self, account: str, role_name: str):
        endpoint = 'sts.cn-beijing.aliyuncs.com'
        config = self.__make_config(endpoint)
        client = Sts20150401Client(config)
        assume_role_request = sts_20150401_models.AssumeRoleRequest(
            role_arn='acs:ram::%s:role/%s' % (account, role_name),
            role_session_name='to-%s' % account
        )
        cred = client.assume_role_with_options(assume_role_request, self.runtime)
        return cred.body.credentials

    def __get_time_range(self):
        """计算 StartTime（前一天 00:00）和 EndTime（当天 00:00），使用北京时间（UTC+8）"""
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - datetime.timedelta(days=1)
        return start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def list_accounts(self):
        endpoint = 'resourcedirectory.aliyuncs.com'
        config = self.__make_config(endpoint)
        client = ResourceDirectoryMaster20220419Client(config)
        list_accounts_request = resource_directory_master_20220419_models.ListAccountsRequest(
            max_results=100
        )
        response = client.list_accounts_with_options(list_accounts_request, self.runtime).body
        return response

    def describe_cdn_sublist(self):
        endpoint = 'cdn.aliyuncs.com'
        config = self.__make_config(endpoint)
        client = Cdn20180510Client(config)
        response = client.describe_cdn_sub_list_with_options(self.runtime).body.content
        return response

    def describe_cdn_report(self):
        endpoint = 'cdn.aliyuncs.com'
        config = self.__make_config(endpoint)
        client = Cdn20180510Client(config)
        sublist = self.describe_cdn_sublist()
        start_time, end_time = self.__get_time_range()
        domains = []
        for item in sublist.get('data', {}):
            if 'domains' in item:
                domains.extend(item['domains'])

        report_dict = {}
        for domain in domains:
            if domain not in report_dict:
                report_dict[domain] = []
            describe_cdn_report_request = cdn_20180510_models.DescribeCdnReportRequest(
                domain_name=domain,
                report_id=13,
                start_time=start_time,
                end_time=end_time
            )
            try:
                response = client.describe_cdn_report_with_options(describe_cdn_report_request,
                                                                   self.runtime).body.content
                ip_data = response.get('data', [])

                for item in ip_data:
                    for traffic_info in item.get('data', []):
                        traffic_value = traffic_info.get('traf', 0)
                        if traffic_value > 10737418240:
                            report_dict[domain].append(traffic_info)
            except Exception as error:
                logger.error(error)
        if report_dict:
            return [report_dict]
        else:
            return


if __name__ == '__main__':
    ali = AlicloudApi(profile='cloud-center-global', account='5558812050979135')
    # res = ali.get_endpoint('R-kvstore', 'us-east-1')
