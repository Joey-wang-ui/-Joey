"""Read-only management API check; never disclose tokens or account resources."""

import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AccessCheckError(Exception):
    """An error safe to show in a public workflow log."""


def resource_count(resource, token, opener=urlopen):
    request = Request(
        f"https://api.supabase.com/v1/{resource}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with opener(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 401:
            raise AccessCheckError("管理令牌无效或已过期，请在仓库 Secrets 中更新。") from None
        if error.code == 403:
            raise AccessCheckError("管理令牌没有所需的组织或项目读取权限。") from None
        raise AccessCheckError(f"Supabase 管理 API 返回 HTTP {error.code}，请稍后重试。") from None
    except (URLError, TimeoutError, OSError):
        raise AccessCheckError("暂时无法连接 Supabase 管理 API，请稍后重试。") from None
    except (ValueError, UnicodeError):
        raise AccessCheckError("Supabase 管理 API 返回了无法识别的数据。") from None
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise AccessCheckError("Supabase 管理 API 返回的数据格式不符合预期。")
    return len(payload)


def main(environ=None, output=None, opener=urlopen):
    environ = os.environ if environ is None else environ
    output = sys.stdout if output is None else output
    token = environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        print("尚未设置 SUPABASE_ACCESS_TOKEN。请先在仓库 Settings → Secrets and variables → Actions 中保存管理令牌。", file=output)
        return 0
    try:
        organizations = resource_count("organizations", token, opener)
        projects = resource_count("projects", token, opener)
    except AccessCheckError as error:
        print(f"授权检查未通过：{error}", file=output)
        return 1
    message = f"Supabase 只读授权检查通过。组织数量：{organizations}；项目数量：{projects}。"
    print(message, file=output)
    if environ.get("GITHUB_OUTPUT"):
        with Path(environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
            handle.write("authorized=true\n")
    if environ.get("GITHUB_STEP_SUMMARY"):
        with Path(environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
