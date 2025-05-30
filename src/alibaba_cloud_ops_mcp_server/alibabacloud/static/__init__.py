from importlib import resources

with (
    resources.files('alibaba_cloud_ops_mcp_server.alibabacloud.static')
    .joinpath('PROMPT_UNDERSTANDING.md')
    .open('r', encoding='utf-8') as f
):
    PROMPT_UNDERSTANDING = f.read()
