#!/usr/bin/env python
# -*- coding:utf-8 -*-


from hashlib import md5
import json
import logging
import requests
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


rcenter_api = "ams-api.socialgamenet.com"
rcenter_key = "98a23oy9ctw3py98r2ntw783dj289tw3o2oy9t8w3o48n7ydtq3n4o9813p0d34t89"


class RcenterSearcher(object):
    def __init__(self, rcenter_host, rcenter_token):
        self.rcenter_host = rcenter_host
        self.rcenter_token = rcenter_token
        self.default_timeout = 300

    def __gen_header(self):
        try:
            ts = str(int(time.time()))
            token_bytes = (self.rcenter_token + ts).encode('utf-8')
            header = {
                'TIMESTAMP': ts,
                'CLIENTTOKEN': md5(token_bytes).hexdigest(),
                'Content-Type': 'application/json',
            }
            return header
        except Exception as err:
            logger.error("Error generating request header: {}".format(err))
            return None

    def search(self, ins_type="ec2", query_str="{}"):
        try:
            header = self.__gen_header()
            if not header:
                return None
            resp_json = requests.post(
                "http://" + self.rcenter_host + "/api/{}/search".format("instance" if ins_type == "ec2" else ins_type),
                data=query_str,
                headers=self.__gen_header(),
                timeout=self.default_timeout
            ).json()
            logger.info(resp_json)
            if resp_json['head']['status'] == "ok":
                return resp_json['body']['instances']
            else:
                logger.error("Query rcenter api failed: {}".format(resp_json['head']['info']))
            return None
        except Exception as err:
            logger.error("Query failed with query({}): {}".format(query_str, err))


if __name__ == '__main__':
    # usage examples
    s = RcenterSearcher(rcenter_api, rcenter_key)
    print(json.dumps(s.search("rds", query_str=json.dumps({"cloud": "aws"})), indent=2))
    # print len(s.search("ec2", query_str=json.dumps({"cloud": "aws", "ec2state": "running"})))
    # print len(s.search("ec2", query_str=json.dumps({})))
