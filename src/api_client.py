import json
import re
import time
import gzip
import ssl
import base64
import logging
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO
from src.utils import Colors
from src.i18n import t

logger = logging.getLogger(__name__)

MAX_TRAFFIC_RESULTS = 200000
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


def _extract_id(href):
    """Extract the last segment from an Illumio HREF path."""
    return href.split('/')[-1] if href else ""


class ApiClient:
    def __init__(self, config_manager):
        self.cm = config_manager
        self.api_cfg = self.cm.config["api"]
        self.base_url = f"{self.api_cfg['url']}/api/v2/orgs/{self.api_cfg['org_id']}"
        self._auth_header = self._build_auth_header()
        self._ssl_ctx = self._build_ssl_context()
        # Caches for rule scheduler features
        self.label_cache = {}
        self.ruleset_cache = []

    def _build_auth_header(self):
        credentials = f"{self.api_cfg['key']}:{self.api_cfg['secret']}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
        return f"Basic {encoded}"

    def _build_ssl_context(self):
        ctx = ssl.create_default_context()
        if not self.api_cfg.get('verify_ssl', True):
            logger.warning("SSL verification disabled — API connections are not secure")
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _request(self, url, method="GET", data=None, headers=None, timeout=15, stream=False):
        """
        Core HTTP helper with retry logic.
        Returns (status_code, response_body_bytes | None).
        For stream=True, returns (status_code, raw_response_object) — caller must close it.
        """
        if headers is None:
            headers = {}
        headers.setdefault("Authorization", self._auth_header)
        headers.setdefault("Accept", "application/json")

        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            headers.setdefault("Content-Type", "application/json")

        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                resp = urllib.request.urlopen(req, timeout=timeout, context=self._ssl_ctx)
                if stream:
                    return resp.status, resp
                resp_body = resp.read()
                return resp.status, resp_body
            except urllib.error.HTTPError as e:
                status = e.code
                resp_body = e.read()
                if status == 429 and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"Rate limited (429). Retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    last_exc = e
                    continue
                if status in (502, 503, 504) and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"Server error ({status}). Retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    last_exc = e
                    continue
                return status, resp_body
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"Connection error: {e}. Retrying in {wait}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(wait)
                    last_exc = e
                    continue
                logger.error(f"Connection failed after {MAX_RETRIES} attempts: {e}")
                return 0, str(e).encode('utf-8')

        # Should not reach here, but safety fallback
        return 0, str(last_exc).encode('utf-8') if last_exc else b""

    def check_health(self):
        url = f"{self.api_cfg['url']}/api/v2/health"
        try:
            status, body = self._request(url, timeout=10)
            text = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else str(body)
            return status, text
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return 0, str(e)

    def fetch_events(self, start_time_str, end_time_str=None, max_results=5000):
        try:
            p = {
                "timestamp[gte]": start_time_str,
                "max_results": max_results
            }
            if end_time_str:
                p["timestamp[lte]"] = end_time_str
            params = urllib.parse.urlencode(p)
            url = f"{self.base_url}/events?{params}"
            status, body = self._request(url, timeout=30)
            if status != 200:
                err_msg = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else str(body)
                logger.error(f"Get Events Failed: {status} - {err_msg}")
                print(f"{Colors.FAIL}{t('api_get_events_failed', status=status, error=err_msg[:500])}{Colors.ENDC}")
                return []
            return json.loads(body)
        except Exception as e:
            logger.error(f"Fetch Events Error: {e}")
            print(f"{Colors.FAIL}{t('api_fetch_events_error', error=str(e))}{Colors.ENDC}")
            return []

    def execute_traffic_query_stream(self, start_time_str, end_time_str, policy_decisions):
        """
        Executes an async traffic query and yields results row by row to save memory.
        """
        import urllib.parse

        payload = {
            "start_date": start_time_str, "end_date": end_time_str,
            "policy_decisions": policy_decisions,
            "max_results": MAX_TRAFFIC_RESULTS,
            "query_name": "Traffic_Monitor_Query",
            "sources": {"include": [], "exclude": []},
            "destinations": {"include": [], "exclude": []},
            "services": {"include": [], "exclude": []}
        }

        print(t('submitting_query', start=start_time_str, end=end_time_str))
        logger.info(f"Submitting traffic query ({start_time_str} to {end_time_str})")
        try:
            url = f"{self.base_url}/traffic_flows/async_queries"
            status, body = self._request(url, method="POST", data=payload, timeout=10)

            if status not in (201, 202):
                text = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else str(body)
                logger.error(f"API Error {status}: {text}")
                print(t("api_error_status", status=status, text=text))
                return

            result = json.loads(body)
            job_url = result.get("href")
            print(t('waiting_traffic', default='Waiting for traffic calculation...'), end="", flush=True)

            # Polling
            poll_url = f"{self.api_cfg['url']}/api/v2{job_url}"
            for _ in range(60):  # Wait up to 2 mins
                time.sleep(2)
                poll_status, poll_body = self._request(poll_url, timeout=15)
                if poll_status != 200:
                    continue

                state = json.loads(poll_body).get("status")
                if state == "completed":
                    print(f" {t('done')}")
                    logger.info("Traffic query completed.")
                    break
                if state == "failed":
                    print(f" {t('query_failed', default='Failed.')}")
                    logger.error("Traffic query failed.")
                    return
                print(".", end="", flush=True)
            else:
                print(f" {t('api_timeout')}")
                logger.error("Traffic query timed out.")
                return

            # Stream Download
            dl_url = f"{self.api_cfg['url']}/api/v2{job_url}/download"
            dl_status, dl_body = self._request(dl_url, timeout=60)
            if dl_status != 200:
                logger.error(f"Download failed: {dl_status}")
                return

            buffer = BytesIO(dl_body)

            # Handle Gzip
            try:
                with gzip.GzipFile(fileobj=buffer, mode='rb') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            if line == b'[' or line == b']':
                                continue
                            if line.endswith(b','):
                                line = line[:-1]
                            data = json.loads(line)
                            if isinstance(data, list):
                                for item in data:
                                    yield item
                            else:
                                yield data
                        except json.JSONDecodeError as je:
                            logger.debug(f"Skipping unparseable line: {je}")
            except (gzip.BadGzipFile, OSError):
                # Fallback if not gzip
                buffer.seek(0)
                text_data = buffer.read().decode('utf-8', errors='replace')
                for line in text_data.splitlines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if isinstance(data, list):
                            for item in data:
                                yield item
                        else:
                            yield data
                    except json.JSONDecodeError as je:
                        logger.debug(f"Skipping unparseable line: {je}")

        except Exception as e:
            logger.error(f"Query Exception: {e}")
            print(t("api_query_exception", error=str(e)))
            return

    def fetch_traffic_for_report(self, start_time_str, end_time_str,
                                 policy_decisions=None):
        """
        Convenience wrapper for report generation.
        Collects all results from execute_traffic_query_stream() into a list.
        Returns: list[dict] — all flow records, or empty list on failure.
        """
        if policy_decisions is None:
            policy_decisions = ["blocked", "potentially_blocked", "allowed"]

        stream = self.execute_traffic_query_stream(
            start_time_str, end_time_str, policy_decisions
        )
        if stream is None:
            return []
        return list(stream)

    # ═══════════════════════════════════════════════════════════════════════════════
    # Quarantine Feature: Labels and Workloads
    # ═══════════════════════════════════════════════════════════════════════════════

    def get_labels(self, key: str) -> list:
        try:
            params = urllib.parse.urlencode({"key": key})
            url = f"{self.base_url}/labels?{params}"
            status, body = self._request(url, timeout=10)
            if status != 200:
                logger.error(f"Get Labels Failed: {status}")
                return []
            return json.loads(body)
        except Exception as e:
            logger.error(f"Fetch Labels Error: {e}")
            return []

    def create_label(self, key: str, value: str) -> dict:
        try:
            url = f"{self.base_url}/labels"
            payload = {"key": key, "value": value}
            status, body = self._request(url, method="POST", data=payload, timeout=10)
            if status == 201:
                return json.loads(body)
            logger.error(f"Create Label Failed: {status} - {body.decode(errors='replace')}")
            return {}
        except Exception as e:
            logger.error(f"Create Label Error: {e}")
            return {}

    def check_and_create_quarantine_labels(self):
        """Ensure Quarantine labels (Mild, Moderate, Severe) exist in the PCE. Returns list of their hrefs."""
        existing_labels = self.get_labels("Quarantine")
        existing_values = {lbl.get("value"): lbl.get("href") for lbl in existing_labels if lbl.get("value")}
        
        target_levels = ["Mild", "Moderate", "Severe"]
        label_hrefs = {}
        for level in target_levels:
            if level in existing_values:
                label_hrefs[level] = existing_values[level]
            else:
                logger.info(f"Creating missing Quarantine label: {level}")
                new_lbl = self.create_label("Quarantine", level)
                if new_lbl and "href" in new_lbl:
                    label_hrefs[level] = new_lbl["href"]
        return label_hrefs

    def get_workload(self, href: str) -> dict:
        """Fetch a specific workload by its href"""
        try:
            # href usually looks like /orgs/1/workloads/xx-yy-zz
            url = f"{self.api_cfg['url']}/api/v2{href}"
            status, body = self._request(url, timeout=10)
            if status == 200:
                return json.loads(body)
            logger.error(f"Get Workload Failed: {status} for {href}")
            return {}
        except Exception as e:
            logger.error(f"Get Workload Error: {e}")
            return {}

    def update_workload_labels(self, href: str, labels: list) -> bool:
        """Update a workload's labels. labels list should contain dicts with 'href' keys."""
        try:
            url = f"{self.api_cfg['url']}/api/v2{href}"
            payload = {"labels": labels}
            status, body = self._request(url, method="PUT", data=payload, timeout=10)
            if status == 204:
                return True
            logger.error(f"Update Workload Labels Failed: {status} - {body.decode(errors='replace')}")
            return False
        except Exception as e:
            logger.error(f"Update Workload Labels Error: {e}")
            return False

    def fetch_managed_workloads(self, max_results: int = 10000) -> list:
        """Fetch all VEN-managed workloads (those with an active VEN agent)."""
        try:
            params = urllib.parse.urlencode({'managed': 'true', 'max_results': max_results})
            url = f"{self.base_url}/workloads?{params}"
            status, body = self._request(url, timeout=30)
            if status == 200:
                return json.loads(body)
            err_msg = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else str(body)
            logger.error(f"Fetch Managed Workloads Failed: {status} - {err_msg}")
            return []
        except Exception as e:
            logger.error(f"Fetch Managed Workloads Error: {e}")
            return []

    def search_workloads(self, params: dict) -> list:
        """Search workloads matching query params (e.g., name, hostname, ip_address, labels)"""
        try:
            query_str = urllib.parse.urlencode(params, doseq=True)
            url = f"{self.base_url}/workloads?{query_str}"
            status, body = self._request(url, timeout=15)
            if status == 200:
                return json.loads(body)
            logger.error(f"Search Workloads Failed: {status}")
            return []
        except Exception as e:
            logger.error(f"Search Workloads Error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════════
    # Rule Scheduler Features: RuleSet/Rule management, provisioning, notes
    # ═══════════════════════════════════════════════════════════════════════════════

    def _api_get(self, endpoint, timeout=15):
        """GET a PCE API endpoint. Returns (status_code, parsed_json_or_None)."""
        url = f"{self.api_cfg['url']}/api/v2{endpoint}"
        try:
            status, body = self._request(url, timeout=timeout)
            if status == 200:
                return status, json.loads(body)
            if status == 204:
                return status, {}
            return status, None
        except Exception as e:
            logger.error(f"API GET {endpoint}: {e}")
            return 0, None

    def _api_put(self, endpoint, payload, timeout=15):
        """PUT a PCE API endpoint. Returns status_code."""
        url = f"{self.api_cfg['url']}/api/v2{endpoint}"
        try:
            status, body = self._request(url, method="PUT", data=payload, timeout=timeout)
            return status
        except Exception as e:
            logger.error(f"API PUT {endpoint}: {e}")
            return 0

    def _api_post(self, endpoint, payload, timeout=15):
        """POST a PCE API endpoint. Returns (status_code, parsed_json_or_None)."""
        url = f"{self.api_cfg['url']}/api/v2{endpoint}"
        try:
            status, body = self._request(url, method="POST", data=payload, timeout=timeout)
            if status in (200, 201):
                return status, json.loads(body) if body else {}
            return status, None
        except Exception as e:
            logger.error(f"API POST {endpoint}: {e}")
            return 0, None

    def update_label_cache(self, silent=False):
        """Cache labels, IP lists, and services for display resolution."""
        org = self.api_cfg['org_id']
        try:
            status, data = self._api_get(f"/orgs/{org}/labels?max_results=10000")
            if status == 200 and data:
                for i in data:
                    self.label_cache[i['href']] = f"{i.get('key')}:{i.get('value')}"

            status, data = self._api_get(f"/orgs/{org}/sec_policy/draft/ip_lists?max_results=10000")
            if status == 200 and data:
                for i in data:
                    val = f"[IPList] {i.get('name')}"
                    self.label_cache[i['href']] = val
                    self.label_cache[i['href'].replace('/draft/', '/active/')] = val

            status, data = self._api_get(f"/orgs/{org}/sec_policy/draft/services?max_results=10000")
            if status == 200 and data:
                for i in data:
                    name = i.get('name')
                    ports = []
                    for svc in i.get('service_ports', []):
                        p = svc.get('port')
                        if p:
                            proto = "UDP" if svc.get('proto') == 17 else "TCP"
                            top = f"-{svc['to_port']}" if svc.get('to_port') else ""
                            ports.append(f"{proto}/{p}{top}")
                    port_str = f" ({','.join(ports)})" if ports else ""
                    val = f"{name}{port_str}"
                    self.label_cache[i['href']] = val
                    self.label_cache[i['href'].replace('/draft/', '/active/')] = val
        except Exception as e:
            if not silent:
                logger.warning(f"Label cache update error: {e}")

    def resolve_actor_str(self, actors):
        """Resolve actor list to human-readable string using label_cache."""
        if not actors:
            return "Any"
        names = []
        for a in actors:
            if 'label' in a:
                names.append(self.label_cache.get(a['label']['href'], "Label"))
            elif 'ip_list' in a:
                names.append(self.label_cache.get(a['ip_list']['href'], "IPList"))
            elif 'actors' in a:
                names.append(str(a.get('actors')))
        return ", ".join(names)

    def resolve_service_str(self, services):
        """Resolve service references to display strings."""
        if not services:
            return "All Services"
        svcs = []
        for s in services:
            if 'port' in s:
                p, proto = s.get('port'), "UDP" if s.get('proto') == 17 else "TCP"
                top = f"-{s['to_port']}" if s.get('to_port') else ""
                svcs.append(f"{proto}/{p}{top}")
            elif 'href' in s:
                svcs.append(self.label_cache.get(s['href'], f"Service({_extract_id(s['href'])})"))
            else:
                svcs.append("RefObj")
        return ", ".join(svcs)

    def get_all_rulesets(self, force_refresh=False):
        """Get all rulesets from PCE (cached unless force_refresh)."""
        if self.ruleset_cache and not force_refresh:
            return self.ruleset_cache
        org = self.api_cfg['org_id']
        status, data = self._api_get(f"/orgs/{org}/sec_policy/draft/rule_sets?max_results=10000")
        if status == 200 and data:
            self.ruleset_cache = data
            return self.ruleset_cache
        return []

    def search_rulesets(self, keyword):
        """Search cached rulesets by keyword."""
        all_rs = self.get_all_rulesets()
        return [rs for rs in all_rs if keyword.lower() in rs.get('name', '').lower()]

    def get_ruleset_by_id(self, rs_id):
        """Get a single ruleset by ID."""
        org = self.api_cfg['org_id']
        status, data = self._api_get(f"/orgs/{org}/sec_policy/draft/rule_sets/{rs_id}")
        return data if status == 200 else None

    def provision_changes(self, rs_href):
        """Dependency-aware provisioning: discovers required dependencies first."""
        org = self.api_cfg['org_id']

        # Step 1: Check dependencies
        dep_payload = {"change_subset": {"rule_sets": [{"href": rs_href}]}}
        dep_status, deps = self._api_post(f"/orgs/{org}/sec_policy/draft/dependencies", dep_payload)

        # Step 2: Build complete change_subset including all dependencies
        final_subset = {"rule_sets": [{"href": rs_href}]}

        if dep_status == 200 and deps:
            for obj_type in ['rule_sets', 'ip_lists', 'services', 'label_groups',
                             'virtual_services', 'firewall_settings', 'enforcement_boundaries',
                             'virtual_servers', 'secure_connect_gateways']:
                dep_items = deps.get(obj_type, [])
                if dep_items:
                    existing = final_subset.get(obj_type, [])
                    existing_hrefs = {item['href'] for item in existing}
                    for item in dep_items:
                        if item.get('href') and item['href'] not in existing_hrefs:
                            existing.append({"href": item['href']})
                    final_subset[obj_type] = existing

        # Step 3: Provision with full dependency set
        payload = {
            "update_description": "Auto-Scheduler: Status/Note Update",
            "change_subset": final_subset
        }
        prov_status, _ = self._api_post(f"/orgs/{org}/sec_policy", payload)
        if prov_status == 201:
            return True
        logger.error(f"Provision failed for RuleSet {_extract_id(rs_href)}: status {prov_status}")
        return False

    def toggle_and_provision(self, href, target_enabled, is_ruleset=False):
        """Enable/disable a rule or ruleset and provision the change."""
        draft_href = href.replace("/active/", "/draft/")
        put_status = self._api_put(draft_href, {"enabled": target_enabled})
        if put_status != 204:
            logger.error(f"Toggle failed for {_extract_id(href)}: status {put_status}")
            return False
        rs_href = draft_href if is_ruleset else "/".join(draft_href.split("/")[:7])
        return self.provision_changes(rs_href)

    def update_rule_note(self, href, schedule_info, remove=False):
        """Add/update/remove schedule tags in a rule's description field on the PCE."""
        draft_href = href.replace("/active/", "/draft/")
        status, data = self._api_get(draft_href)
        if status != 200 or not data:
            return False

        current_desc = data.get('description', '') or ''

        # Strip existing schedule tags
        clean_desc = re.sub(r'\s*\[📅[^\]]*\]', '', current_desc)
        clean_desc = re.sub(r'\s*\[⏳[^\]]*\]', '', clean_desc)
        clean_desc = clean_desc.strip()

        new_desc = clean_desc
        if not remove:
            new_desc = f"{clean_desc}\n{schedule_info}".strip() if clean_desc else schedule_info

        if new_desc == current_desc:
            return True

        put_status = self._api_put(draft_href, {"description": new_desc})
        if put_status == 204:
            rs_href = "/".join(draft_href.split("/")[:7])
            return self.provision_changes(rs_href)
        return False

    def get_live_item(self, href):
        """Try both active and draft paths to find the item. Returns (status, data) or (0, None)."""
        # Try active first
        active_href = href.replace("/draft/", "/active/")
        status, data = self._api_get(active_href)
        if status == 200:
            return status, data
        # Fallback to draft
        draft_href = href.replace("/active/", "/draft/")
        if draft_href != active_href:
            status, data = self._api_get(draft_href)
            if status == 200:
                return status, data
        return status, data

    def get_provision_state(self, href):
        """Check provision state: 'active' if provisioned, 'draft' if draft-only, 'unknown' on error."""
        active_href = href.replace("/draft/", "/active/")
        url = f"{self.api_cfg['url']}/api/v2{active_href}"
        try:
            status, body = self._request(url, timeout=10)
            if status == 200:
                return 'active'
            return 'draft'
        except Exception:
            return 'unknown'

    def is_provisioned(self, href):
        """Check if a rule/ruleset has been provisioned."""
        return self.get_provision_state(href) == 'active'
