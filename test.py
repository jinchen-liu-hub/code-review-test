data = {
    "pr_id": 111,
    "repo_url": 222,
    "access_token": 333,
    "owner": 444,
    "repository": 555,
    "scan_scope": 666,
    "branch": 777,
}

payload = {
    **data,
    "access_token":"test"
}
print(payload)