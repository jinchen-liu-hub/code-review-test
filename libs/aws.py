import boto3
import datetime
import traceback
from botocore.client import Config
from loguru import logger


class AwsApi:
    session = boto3.Session()
    config = Config(connect_timeout=2, read_timeout=2)

    def __init__(self, account='', access_key='', secret_key='',
                 profile='', role='devops-cloud-center-role', is_global=True):
        '''
        本地开发环境需要account与要切换的role参数
        会切换到对应role
        默认使用 defalut profile
        '''
        if profile:
            self.session = boto3.Session(profile_name=profile)
        if access_key and secret_key:
            self.session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
        token = self.session.get_credentials().token
        if token is None and not account:
            raise Exception('dev env need account to get token')
        if account:
            self.sync_account_role_token(account, role, is_global)

    def __make_boto_client(self, service_name: str, region: str):
        return self.session.client(
            service_name,
            region_name=region,
            config=self.config
        )

    def sync_account_role_token(self, account: str, role: str, is_global: bool):
        if is_global:
            client = self.session.client('sts')
            arn = 'arn:aws:iam::' + str(account) + ':role/' + role
        else:
            client = self.session.client(
                'sts',
                endpoint_url='https://sts.cn-north-1.amazonaws.com.cn',
                region_name='cn-north-1'
            )
            arn = 'arn:aws-cn:iam::' + str(account) + ':role/' + role

        response = client.assume_role(
            RoleArn=arn,
            RoleSessionName='string',
            DurationSeconds=3600
        )
        # self.log.info('get token success')
        access_key = response['Credentials']['AccessKeyId']
        access_secret = response['Credentials']['SecretAccessKey']
        access_token = response['Credentials']['SessionToken']
        token_expiration = response['Credentials']['Expiration']
        self.session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=access_secret,
            aws_session_token=access_token
        )

    def describe_addresses(self, region: str):
        try:
            client = self.__make_boto_client('ec2', region)
            response = client.describe_addresses()
            return response
        except Exception as e:
            logger.error('Aws describe_addresses error: %s' % e)

    def describe_events(self, region: str):
        current_date = datetime.datetime.utcnow()
        try:
            client = self.__make_boto_client('health', region)
            response = client.describe_events(
                filter={
                    'eventTypeCodes': [
                        'AWS_EC2_INSTANCE_AUTO_RECOVERY_SUCCESS', 'AWS_EC2_INSTANCE_AUTO_RECOVERY_NO_ACTION',
                        'AWS_EC2_INSTANCE_AUTO_RECOVERY_FAILURE', 'AWS_RDS_MAINTENANCE_SCHEDULED',
                        'AWS_RDS_SYSTEM_UPGRADE_SCHEDULED'
                    ],
                    'services': ['EC2', 'RDS'],
                    'startTimes': [
                        {
                            # check alert from 1 day and 1 hour ago
                            'from': current_date - datetime.timedelta(days=1, hours=1),
                        },
                    ],
                },
                maxResults=100
            )
            return response
        except Exception as e:
            tb = traceback.format_exc()
            logger.error('Aws describe_events error: %s' % e, tb)

    def describe_affected_entities(self, region: str, arn: str):
        try:
            client = self.__make_boto_client('health', region)
            response = client.describe_affected_entities(
                filter={
                    'eventArns': [
                        arn,
                    ],
                },
                maxResults=100
            )
            return response
        except Exception as e:
            logger.error('Aws describe_addresses error: %s' % e)

    def describe_security_groups(self, region: str):
        client = self.__make_boto_client('ec2', region)
        all_security_groups = []
        next_token = ""
        try:
            while True:
                if not next_token:
                    response = client.describe_security_groups(MaxResults=100)
                else:
                    response = client.describe_security_groups(NextToken=next_token, MaxResults=100)

                if len(response.get('SecurityGroups', '')) == 0:
                    break

                next_token = response.get('NextToken', '')
                for sg in response['SecurityGroups']:
                    all_security_groups.append(sg)

                if not next_token:
                    break
        except Exception as e:
            logger.error('describe security groups error: %s' % e)
        finally:
            return all_security_groups

    def describe_vpcs(self, region):
        client = self.__make_boto_client('ec2', region)
        all_vpc_cidrs = set()
        # 初始化添加23账号和9账号cidr
        all_vpc_cidrs.add('10.13.148.0/23')
        all_vpc_cidrs.add('10.13.0.0/21')
        next_token = ""
        try:
            while True:
                if not next_token:
                    response = client.describe_vpcs(MaxResults=100)
                else:
                    response = client.describe_vpcs(NextToken=next_token, MaxResults=100)

                if len(response.get('Vpcs', '')) == 0:
                    break

                next_token = response.get('NextToken', '')
                for vpc in response['Vpcs']:
                    for cidr in vpc['CidrBlockAssociationSet']:
                        all_vpc_cidrs.add(cidr['CidrBlock'])

                if not next_token:
                    break
        except Exception as e:
            logger.error('describe vpcs error: %s' % e)
        finally:
            return list(all_vpc_cidrs)

    def describe_network_interfaces_security_groups(self, region: str):
        client = self.__make_boto_client('ec2', region)
        all_security_groups = set()
        next_token = ""
        try:
            while True:
                if not next_token:
                    response = client.describe_network_interfaces(MaxResults=100)
                else:
                    response = client.describe_network_interfaces(NextToken=next_token, MaxResults=100)

                if len(response.get('NetworkInterfaces', '')) == 0:
                    break

                next_token = response.get('NextToken', '')
                for ni in response['NetworkInterfaces']:
                    for group in ni['Groups']:
                        all_security_groups.add(group['GroupId'])

                if not next_token:
                    break
        except Exception as e:
            logger.error('describe network interfaces error: %s' % e)
        finally:
            return list(all_security_groups)

    def describe_pending_maintenance_actions(self, region: str, arn: str, instance: str):
        try:
            client = self.__make_boto_client('rds', region)
            response = client.describe_pending_maintenance_actions(
                ResourceIdentifier=arn,
                Filters=[
                    {
                        'Name': 'db-instance-id',
                        'Values': [instance, ]
                    },
                ]
            )
            return response
        except Exception as e:
            logger.error('Aws describe_pending_maintenance_actions error: %s' % e)

    def describe_db_instances(self, region: str):
        try:
            client = self.__make_boto_client('rds', region)
            response = client.describe_db_instances()
            return response
        except Exception as e:
            logger.error('Aws describe_db_instances error: %s' % e)

    def list_tags_for_resource(self, region: str, arn: str):
        try:
            client = self.__make_boto_client('rds', region)
            response = client.list_tags_for_resource(ResourceName=arn)
            return response
        except Exception as e:
            logger.error('Aws describe_db_instances error: %s' % e)

    def describe_volumes(self, region: str):
        try:
            client = self.__make_boto_client('ec2', region)
            response = client.describe_volumes(Filters=[
                {
                    "Name": "status",
                    "Values": [
                        "available"
                    ]
                }
            ])
            return response
        except Exception as e:
            logger.error('Aws describe_volumes error: %s' % e)

    def describe_snapshots(self, region: str, instance_id: str):
        try:
            client = self.__make_boto_client('ec2', region)
            response = client.describe_snapshots(
                Filters=[
                    {'Name': 'description', 'Values': [f"*{instance_id}*"]},
                ]
            )
            return response
        except Exception as e:
            logger.error('Aws describe_snapshots error: %s' % e)

    def upload_file_to_s3(self, file_path: str, bucket_name: str, s3_key):
        try:
            client = self.__make_boto_client('s3', 'us-west-2')
            client.upload_file(file_path, bucket_name, s3_key, ExtraArgs={'ContentType': 'text/html'})
            return True
        except Exception as e:
            logger.error('Aws upload_file_to_s3 error: %s' % e)
            return False
