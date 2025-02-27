import requests
import json
import base64
import os
from github3 import login

def encrypt_token(token, seed=10):
    try:
        if not isinstance(token, str):
            raise ValueError("Token must be a string")

        # 生成随机盐值
        salt = os.urandom(seed)

        # 将token和盐值拼接并进行base64编码
        salted_token = salt + token.encode('utf-8')
        encrypted = base64.b64encode(salted_token)

        return encrypted.decode('utf-8')
    except Exception as e:
        print(f"Error encrypting token: {str(e)}")
        return ""

def send_code_review_request(api_endpoint, api_key, pr_id, repo_url, access_token, owner, repository, scan_scope, branch):
    try:
        enc_token = encrypt_token(access_token)
        url = f"{api_endpoint}codereview"
        data = {
            "pr_id": pr_id,
            "repo_url": repo_url,
            "access_token": enc_token,
            "owner": owner,
            "repository": repository,
            "scan_scope": scan_scope,
            "branch": branch,
        }
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()
    except Exception as e:
        print(f"Error sending code review request: {str(e)}")
        return {}

def comment_on_pr(repo, pr, comment_text):
    try:
        pr.create_comment(comment_text)
        print(f"Successfully added comment to PR #{pr.number}")
    except Exception as e:
        print(f"Error adding comment to PR: {str(e)}")

def main():
    api_endpoint = "https://cnuuox6yi6.execute-api.us-west-2.amazonaws.com/prod/"
    api_key = "MZQ3LjO31I5WmW08HsLHq34QwKSfb9Ht9oN4ldjR"
    owner = "jinchen-liu-hub"
    repo = "code-review-test"
    pr_id = "b3eb5a604c84cdfff7bb5d19dbccba3c1b1d81c5"
    access_token = "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"
    repo_url = "https://github.com/jinchen-liu-hub/code-review-test.git"
    scan_scope="DIFF-Commit"
    branch = "main"
    ui_url = "http://54.68.83.141/reviewList"

    # 发送commit代码审查请求
    response_data = send_code_review_request(api_endpoint, api_key, pr_id,repo_url, access_token, owner, repo, scan_scope, branch)
    print(response_data)
    # 发送total repo 代码审查请求
    scan_scope="ALL"
    response_data = send_code_review_request(api_endpoint, api_key, pr_id,repo_url, access_token, owner, repo, scan_scope, branch)
    print(response_data)
    pr_id = "1"
    scan_scope="DIFF-Pr"
    response_data = send_code_review_request(api_endpoint, api_key, pr_id,repo_url, access_token, owner, repo, scan_scope, branch)
    print(response_data)
    # 添加评论到 PR
    # access_token can be another token which
    gh = login(token=access_token)
    repository = gh.repository(owner, repo)
    pr = repository.pull_request(pr_id)

    comment_text = f"""Claude Code Review Result: {ui_url}?project={owner}/{repo}&pr_id={pr_id}&branch={branch}"""
    comment_on_pr(repository, pr, comment_text)

if __name__ == "__main__":
    main()
