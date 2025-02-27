#!/usr/bin/env python
# -*- coding:utf-8 -*-

# ************************************
# Created by PyCharm
# User: zhenglong
# Date: 2019/7/31
# Time: 16:12
# ************************************

import time
import copy
import hashlib
import traceback
import requests
from multiprocessing.pool import ThreadPool
from loguru import logger

class MetaException(Exception):
    pass

class Meta(object):
    def __init__(self, cloud='aws'):
        self.meta_api = "http://pandora.devops.centurygame.io/api/v1"
        self.meta_key = "fecbf76e93ba06d8b0e143c542b6f192"
        self.meta_name = "devops"
        self.exclude_account = ['583300917620', '758529155342']
        self.cloud = cloud
        if (not self.meta_api) or (not self.meta_key) or (not self.meta_name):
            msg = "meta api，key or name is lost"
            logger.error(msg)
            raise  MetaException(msg)

    def get_meta_token(self):
        timestamp = int(time.time())
        string = self.meta_name + self.meta_key + str(timestamp)
        token = hashlib.md5(string.encode('utf8')).hexdigest()
        auth = '{{"name":"{name}","token":"{token}","timestamp":"{ts}"}}'.format(name=self.meta_name,
                                                                                 token=token, ts=timestamp)
        return auth

    def meta_client(self, uri, params="", tag=""):
        auth = self.get_meta_token()
        url = '{api}{uri}?auth={auth}&{params}'.format(api=self.meta_api, uri=uri, auth=auth, params=params)
        # msg="request meta url: {url}".format(url=url)
        # log(message=msg, level=0)
        try:
            rs = requests.get(url).json()
            if rs.get('code', 0) == 200:
                return rs, tag
            else:
                return False
        except MetaException as e:
            tb = traceback.format_exc()
            msg="Failed to request meta server: " + str(e) + tb
            logger.errir(msg)
            raise

    def projects(self):
        uri = '/projects'
        ret, _ = self.meta_client(uri)
        projects = {}
        for p in ret.get('data', []):
            projects.update({p['id']: p['name']})
        return projects

    def releases(self):
        projects = self.projects()
        project_ids = ",".join([str(pid) for pid, name in projects.items()])
        uri = "/projects/{ids}/releases".format(ids=project_ids)
        ret, _ = self.meta_client(uri)
        releases = {}
        for r in ret.get('data', []):
            pid = r['projectid']
            rid = r['id']
            rname = r['name']
            pname = projects[pid]
            release_dict = dict()
            release_dict[rid] = {"project":pname, "release":rname}
            releases.update(release_dict)
        return releases

    def environments(self):
        releases = self.releases()
        release_ids = [str(rid) for rid in releases]
        uri = "/releases/{ids}/environments".format(ids=",".join(release_ids))
        ret, _ = self.meta_client(uri)
        environments = {}
        for e in ret.get('data', []):
            rid = e['releaseid']
            eid = e['id']
            ename = e['name']
            for release in releases:
                if rid == release:
                    releases[rid].update({"environment": ename})
                    env_dict = dict()
                    env_dict[eid] = copy.deepcopy(releases[rid])
                    environments.update(env_dict)
        return environments

    def services(self):
        environments = self.environments()
        environment_ids = [str(eid) for eid in environments]
        uri = "/environments/{ids}/services".format(ids=",".join(environment_ids))
        ret, _ = self.meta_client(uri)
        services = {}
        for s in ret.get('data', []):
            eid = s['environmentid']
            sid = s['id']
            sname = s['name']
            for environment in environments:
                if eid == environment:
                    environments[eid].update({"service":sname})
                    service_dict = dict()
                    service_dict[sid] = copy.deepcopy(environments[eid])
                    services.update(service_dict)
        return services

    def ec2(self):
        services = self.services()
        ret_pool = []
        thread_pool = ThreadPool(processes=10)
        for sid in services:
            project = services[sid]['project']
            release = services[sid]['release']
            service = services[sid]['service']
            environment = services[sid]['environment']
            # service 'host' is repeated
            if service == 'host':
                continue
            tag = "{project}:{release}:{environment}:{service}".format(
                project=project,release=release,service=service,environment=environment
            )
            uri = "/services/{id}/ec2".format(id=sid)
            params = 'search={{"cloud":"{cloud}"}}'.format(cloud=self.cloud)
            ret = thread_pool.apply_async(self.meta_client, args=(uri, params, tag))
            ret_pool.append(ret)

        thread_pool.close()
        thread_pool.join()
        ec2 = {}
        for ret in ret_pool:
            instances, tag = ret.get()
            for instance in instances.get('data', []):
                if instance['accountId'] in self.exclude_account:
                    continue
                key = "{account_id}:{region}:{tag}".format(account_id=instance['accountId'],
                                                           region=instance['region'],
                                                           tag=tag
                                                           )
                key = instance['instanceId']
                instance['project'] = tag.split(':')[0]
                instance['release'] = tag.split(':')[1]
                instance['environment'] = tag.split(':')[2]
                instance['service'] = tag.split(':')[3]

                if not ec2.get(key):
                    ec2[key] = []
                ec2[key] = instance

        if not ec2:
            msg = "get cvm from meta: no cvm in binding"
            logger.info(msg)
        else:
            msg = f"get cvm from meta: {','.join(ec2)}"
            logger.info(msg)
        return ec2

    def not_attache_exporter_instances(self):
        services = self.services()
        ret_pool = []
        thread_pool = ThreadPool(processes=10)
        results = []
        for sid in services:
            project = services[sid]['project']
            release = services[sid]['release']
            service = services[sid]['service']
            environment = services[sid]['environment']
            # service 'host' is repeated
            if service == 'host':
                continue
            tag = "{project}:{release}:{environment}:{service}".format(
                project=project,release=release,service=service,environment=environment
            )
            uri = "/services/{id}/exporter".format(id=sid)
            ret = thread_pool.apply_async(self.meta_client, args=(uri,"",tag))
            ret_pool.append({"obj":ret,"sid":sid})

        thread_pool.close()
        thread_pool.join()
        
        for ret in ret_pool:
            obj = ret.get('obj')
            sid = ret.get('sid')
            instances, tag = obj.get()
            if not instances.get('data', []):
                ec2_uri = "/services/{id}/ec2".format(id=sid)
                instances, tag = self.meta_client(ec2_uri,"",tag)
                for instance in instances.get('data',[]):
                    instance.update({"tag": tag, "service_sid": sid})
                    results.append(instance)
        return results

if __name__ == '__main__':
    meta = Meta()
    uri = "/services/375/ec2"
    tag = "ff2:us:prod:log"
    print(meta.meta_client(uri,"",tag))