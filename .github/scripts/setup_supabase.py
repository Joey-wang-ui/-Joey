"""Configure the authorized, dedicated free todo project from GitHub Actions.

Management credentials stay in the runner. Only an explicitly validated public
project key and a small status record are written back to the public repository.
"""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SITE = "https://joey-wang-ui.github.io/-Joey/"
PROJECT_NAME = "joey-todo"
ORGANIZATION_NAME = "Joey Todo"
ROOT = Path(__file__).resolve().parents[2]


class SetupError(Exception):
    def __init__(self, stage, message, http_status=None):
        super().__init__(message)
        self.stage, self.http_status = stage, http_status


def public_config(ref, records):
    if not re.fullmatch(r"[a-z0-9]{10,40}", ref):
        raise SetupError("public-config", "Project reference is invalid")
    for record in sorted(records, key=lambda row: row.get("type") != "publishable"):
        key = record.get("api_key") or ""
        public = record.get("type") == "publishable" and bool(re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]+", key))
        if not public and record.get("name") == "anon" and key.startswith("eyJ"):
            try:
                value = key.split(".")[1]
                claims = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
                public = claims.get("role") == "anon"
            except (ValueError, IndexError, TypeError):
                public = False
        if public:
            return {"url": f"https://{ref}.supabase.co", "key": key}
    raise SetupError("public-config", "No browser-safe public key was found")


class Management:
    def __init__(self, token, opener=urlopen):
        self.token, self.opener = token, opener

    def request(self, method, path, body=None, stage="management"):
        request = Request("https://api.supabase.com/v1" + path,
            data=None if body is None else json.dumps(body).encode(), method=method,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.opener(request, timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as error:
            # Inspect only a validation message from this non-secret auth payload.
            # Other API bodies (including key/DB responses) are never published.
            detail = ""
            if stage == "auth-update" and error.code == 400:
                try:
                    value = json.load(error).get("message", "")
                    if isinstance(value, list):
                        value = "; ".join(item for item in value if isinstance(item, str))
                    if isinstance(value, str):
                        value = value.replace(self.token, "[redacted]")
                        value = re.sub(r"(?:sbp_|sb_secret_|sb_publishable_)[A-Za-z0-9_-]+", "[redacted]", value)
                        value = re.sub(r"eyJ[A-Za-z0-9_.-]+", "[redacted]", value)
                        value = re.sub(r"[\w.+-]+@[\w.-]+", "[email]", value)
                        detail = ": " + value[:500]
                except (ValueError, AttributeError, OSError):
                    pass
            raise SetupError(stage, f"Management API returned HTTP {error.code}{detail}", error.code) from None
        except (URLError, TimeoutError, OSError):
            raise SetupError(stage, "Management API connection failed") from None
        except (ValueError, UnicodeError):
            raise SetupError(stage, "Management API response was not valid JSON") from None


def project_ref(project):
    ref = project.get("ref") or project.get("id") or ""
    if not re.fullmatch(r"[a-z0-9]{10,40}", ref):
        raise SetupError("project", "Project reference is invalid")
    return ref


def choose_project(api, recorded_ref=None):
    organizations = api.request("GET", "/organizations", stage="organizations-list")
    projects = api.request("GET", "/projects", stage="projects-list")
    if not isinstance(organizations, list) or not isinstance(projects, list):
        raise SetupError("project", "Unexpected organization or project list")
    if recorded_ref:
        matches = [p for p in projects if project_ref(p) == recorded_ref and p.get("name") == PROJECT_NAME]
        if len(matches) != 1:
            raise SetupError("project", "The recorded todo project is no longer available")
        project = matches[0]
        slug = project.get("organization_slug") or project.get("organization_id")
    else:
        dedicated = [o for o in organizations if o.get("name") == ORGANIZATION_NAME]
        if len(dedicated) > 1:
            raise SetupError("organization", "Multiple dedicated organizations need a target selection")
        organization = dedicated[0] if dedicated else api.request("POST", "/organizations", {"name": ORGANIZATION_NAME}, "organization-create")
        slug = organization.get("slug") or organization.get("id")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9_-]+", slug):
            raise SetupError("organization", "Organization identifier is invalid")
        matches = [p for p in projects if (p.get("organization_slug") or p.get("organization_id")) == slug and p.get("name") == PROJECT_NAME]
        if len(matches) > 1:
            raise SetupError("project", "Multiple dedicated projects need a target selection")
        project = matches[0] if matches else None
    organization = api.request("GET", f"/organizations/{slug}", stage="organization-plan")
    if organization.get("plan") != "free":
        raise SetupError("organization-plan", "Automatic setup requires a verified Free organization")
    if project:
        return project
    # The generated DB password is never logged or persisted in this public repo.
    # The owner can reset it later in Supabase; the app uses the Data API instead.
    return api.request("POST", "/projects", {
        "name": PROJECT_NAME, "organization_slug": slug,
        "db_pass": secrets.token_urlsafe(36), "region": "ap-southeast-1",
    }, "project-create")


def wait_ready(api, ref, sleep=time.sleep):
    for attempt in range(48):
        project = api.request("GET", f"/projects/{ref}", stage="project-status")
        status = project.get("status")
        if status == "ACTIVE_HEALTHY":
            return
        if status in {"INIT_FAILED", "REMOVED", "RESTORE_FAILED"}:
            raise SetupError("project-status", "Project provisioning failed")
        if attempt % 6 == 0:
            print("Waiting for the dedicated project to become healthy...", flush=True)
        sleep(10)
    raise SetupError("project-status", "Project initialization is still pending; rerun setup later")


def auth_configuration(custom_smtp=True):
    template = '<h2>登录你的清单</h2><p>本次登录验证码：<strong>{{ .Token }}</strong></p><p>请回到清单网页输入验证码，10 分钟内有效。</p>'
    config = {
        "site_url": SITE, "uri_allow_list": SITE,
        "external_email_enabled": True, "disable_signup": False,
        "mailer_autoconfirm": False, "mailer_otp_length": 6, "mailer_otp_exp": 600,
    }
    if custom_smtp:
        config.update({
            "mailer_subjects_magic_link": "清单登录验证码",
            "mailer_subjects_confirmation": "清单注册验证码",
            "mailer_templates_magic_link_content": template,
            "mailer_templates_confirmation_content": template,
        })
    return config


VERIFY_SQL = """select
  (select relrowsecurity from pg_catalog.pg_class where oid = 'public.joey_todos'::regclass) as rls_enabled,
  (select count(*) from pg_catalog.pg_policies where schemaname='public' and tablename='joey_todos'
    and policyname in ('joey_select_own','joey_insert_own','joey_update_own','joey_delete_own')) as policy_count,
  has_table_privilege('anon','public.joey_todos','SELECT') as anonymous_select,
  (select bool_and(has_table_privilege('authenticated','public.joey_todos', privilege))
    from unnest(array['SELECT','INSERT','UPDATE','DELETE']) as permissions(privilege)) as authenticated_access;"""


def verify_schema(result):
    if not isinstance(result, list) or len(result) != 1:
        raise SetupError("schema-verify", "Unexpected schema verification response")
    row = result[0]
    if row.get("rls_enabled") is not True or int(row.get("policy_count", 0)) != 4 or row.get("anonymous_select") is not False or row.get("authenticated_access") is not True:
        raise SetupError("schema-verify", "Todo table authorization verification failed")


def write_config(root, config):
    # Revalidate immediately before serializing any credential to public files.
    ref = config["url"].split("//", 1)[1].split(".")[0]
    key = config["key"]
    record = {"name": "anon", "type": "publishable" if key.startswith("sb_publishable_") else "legacy", "api_key": key}
    if public_config(ref, [record]) != {"url": config["url"], "key": key}:
        raise SetupError("public-config", "Public project URL validation failed")
    if set(config) - {"url", "key", "emailMode"} or config.get("emailMode", "otp") not in {"otp", "link"}:
        raise SetupError("public-config", "Public project metadata validation failed")
    page = (root / "index.html").read_text(encoding="utf-8")
    replacement = "window.TodoCloudConfig = " + json.dumps(config, ensure_ascii=True) + ";"
    page, count = re.subn(r"window\.TodoCloudConfig\s*=\s*\{[^;]*\}\s*;", lambda match: replacement, page, count=1)
    if count != 1:
        raise SetupError("public-config", "The standalone page configuration entry was not found")
    (root / "index.html").write_text(page, encoding="utf-8")
    (root / "supabase/public-config.json").write_text(json.dumps(config, indent=2)+"\n", encoding="utf-8")


def verify_public_api(config, opener=urlopen, sleep=time.sleep):
    headers = {"apikey": config["key"], "Accept": "application/json"}
    try:
        with opener(Request(config["url"] + "/auth/v1/settings", headers=headers), timeout=30) as response:
            settings = json.load(response)
        if settings.get("external", {}).get("email") is not True:
            raise SetupError("data-api", "Public email authentication endpoint is not enabled")
    except (HTTPError, URLError, ValueError, OSError):
        raise SetupError("data-api", "Public project authentication endpoint is not ready") from None
    for attempt in range(6):
        try:
            with opener(Request(config["url"] + "/rest/v1/joey_todos?select=id&limit=1", headers=headers), timeout=30):
                raise SetupError("anonymous-access", "Anonymous table access was unexpectedly allowed")
        except HTTPError as error:
            try:
                code = json.load(error).get("code")
            except (ValueError, AttributeError):
                code = None
            if error.code in {401, 403} and code == "42501":
                return
            if attempt < 5 and error.code in {404, 502, 503}:
                sleep(10)
                continue
            raise SetupError("data-api", f"Anonymous access verification returned HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError):
            raise SetupError("data-api", "Public project data endpoint is not ready") from None


def configure(api, root, state, sleep=time.sleep, public_check=verify_public_api):
    existing = root / "supabase/public-config.json"
    recorded = state.get("project_ref")
    if existing.exists():
        config = json.loads(existing.read_text())
        recorded = config["url"].split("//", 1)[1].split(".")[0]
    project = choose_project(api, recorded)
    ref = project_ref(project)
    state["project_ref"] = ref
    state["stage"] = "project-initialization"
    (root / "supabase/setup-status.json").write_text(json.dumps(state, indent=2)+"\n")
    wait_ready(api, ref, sleep)
    print("Dedicated Free project is healthy.", flush=True)
    state["stage"] = "schema"
    schema = (root / "supabase/schema.sql").read_text(encoding="utf-8")
    api.request("POST", f"/projects/{ref}/database/query", {"query": schema, "read_only": False}, "schema-apply")
    result = api.request("POST", f"/projects/{ref}/database/query/read-only", {"query": VERIFY_SQL}, "schema-verify")
    verify_schema(result)
    state["schema_verified"] = True
    print("Todo table and account isolation verified.", flush=True)
    state["stage"] = "email-auth"
    current = api.request("GET", f"/projects/{ref}/config/auth", stage="auth-current")
    expected = auth_configuration(custom_smtp=bool(current.get("smtp_host")))
    api.request("PATCH", f"/projects/{ref}/config/auth", expected, "auth-update")
    actual = api.request("GET", f"/projects/{ref}/config/auth", stage="auth-verify")
    if any(actual.get(key) != value for key, value in expected.items()):
        raise SetupError("auth-verify", "Email authentication configuration did not match")
    state["email_configuration_verified"] = True
    state["custom_smtp_configured"] = bool(actual.get("smtp_host"))
    content = actual.get("mailer_templates_magic_link_content") or ""
    email_mode = "otp" if re.search(r"{{\s*\.Token\s*}}", content) else "link"
    state["email_mode"] = email_mode
    print("Email code configuration verified.", flush=True)
    state["stage"] = "public-config"
    keys = api.request("GET", f"/projects/{ref}/api-keys?reveal=true", stage="public-key-read")
    config = public_config(ref, keys)
    config["emailMode"] = email_mode
    public_check(config)
    state["public_api_verified"] = True
    write_config(root, config)
    state.update({"status": "ready", "stage": "complete", "site_url": SITE})
    return config


def main():
    state_path = ROOT / "supabase/setup-status.json"
    state = {"status": "configuring", "stage": "authorization"}
    if state_path.exists():
        prior = json.loads(state_path.read_text())
        if prior.get("project_ref"):
            state["project_ref"] = prior["project_ref"]
    try:
        token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
        if not token:
            raise SetupError("authorization", "SUPABASE_ACCESS_TOKEN is not configured")
        configure(Management(token), ROOT, state)
        code = 0
        print("Cloud project configuration is ready. Actual email delivery still needs a user login test.")
    except SetupError as error:
        state.update({"status": "failed", "stage": error.stage, "message": str(error)})
        if error.http_status:
            state["http_status"] = error.http_status
        print(f"Setup stopped at {error.stage}: {error}")
        code = 1
    except Exception as error:
        state.update({"status": "failed", "message": "Unexpected setup response", "error_type": type(error).__name__})
        print("Setup stopped: unexpected response; no private response was logged.")
        code = 1
    state_path.write_text(json.dumps(state, indent=2)+"\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
