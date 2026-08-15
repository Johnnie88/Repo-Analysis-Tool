#!/usr/bin/env python3
# Repository Intelligence CLI Tool
# Copyright (c) 2024 Repository Intelligence Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
TUI Backend Helper for Repo Analysis Tool
Handles GitHub & Azure DevOps API integration, web token URLs, repo formatting, and tag resolution for TUI dialogs.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser


def sanitize_str(s):
    """Sanitizes strings to avoid shell expansion issues (backticks, $, backslashes, quotes)."""
    if not s:
        return ""
    return (
        s.replace("`", "")
        .replace("$", "")
        .replace("\\", "")
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", "")
    )


def get_github_web_token_url():
    """Returns direct web URL to create a GitHub PAT with required scopes pre-filled."""
    scopes = "repo,read:org,read:user"
    description = "Repo_Analysis_Tool_TUI"
    return f"https://github.com/settings/tokens/new?description={description}&scopes={scopes}"


def get_azure_web_token_url(org_name):
    """Returns direct web URL to create Azure DevOps PAT."""
    return f"https://dev.azure.com/{org_name}/_usersSettings/tokens"


def open_web_page(url):
    """Opens browser to specified URL."""
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def check_company_exists_github(target, token=None):
    """
    Checks if a GitHub company, organization, or user exists before attempting to fetch repositories.
    """
    if target.lower() in ["me", "self", "@me"] and token:
        return True, "Authenticated user ('me')"

    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Repo-Analysis-TUI/3.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Try Organization endpoint first
    org_url = f"https://api.github.com/orgs/{target}"
    try:
        req = urllib.request.Request(org_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            display_name = data.get("name") or data.get("login") or target
            return True, f"Organization '{display_name}' found on GitHub."
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return True, f"GitHub entity '{target}' exists (Auth status {e.code})."
        elif e.code != 404:
            return False, f"GitHub API error: {e.code} {e.reason}"
    except Exception as e:
        return False, f"Network error checking GitHub target '{target}': {e}"

    # Try User endpoint
    user_url = f"https://api.github.com/users/{target}"
    try:
        req = urllib.request.Request(user_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            display_name = data.get("name") or data.get("login") or target
            return True, f"User '{display_name}' found on GitHub."
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"Company / User '{target}' does not exist on GitHub (404 Not Found)."
        elif e.code in (401, 403):
            return True, f"GitHub User '{target}' exists (Auth status {e.code})."
        else:
            return False, f"GitHub API error: {e.code} {e.reason}"
    except Exception as e:
        return False, f"Network error checking GitHub user '{target}': {e}"


def check_company_exists_azure(org, token=None):
    """
    Checks if an Azure DevOps organization exists before attempting to fetch repositories.
    """
    url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.0"
    headers = {"User-Agent": "Repo-Analysis-TUI/3.0", "Accept": "application/json"}
    if token:
        auth_str = f":{token}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {b64_auth}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_body = resp.read().decode("utf-8")
            if (
                raw_body.lstrip().startswith("<")
                or "html" in resp.headers.get("Content-Type", "").lower()
            ):
                return (
                    True,
                    f"Azure DevOps Organization '{org}' exists (Authentication token recommended).",
                )
            data = json.loads(raw_body)
            count = data.get("count", 0)
            return True, f"Azure DevOps Organization '{org}' exists ({count} projects found)."
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return True, f"Azure DevOps Organization '{org}' exists (Auth status {e.code})."
        elif e.code == 404:
            return False, f"Azure DevOps Organization '{org}' does not exist (404 Not Found)."
        return False, f"Azure DevOps API error: {e.code} {e.reason}"
    except Exception as e:
        return False, f"Network error checking Azure DevOps org '{org}': {e}"


def check_company(provider, target, token=None):
    """
    Unified company/organization existence check.
    """
    if provider.lower() == "github":
        return check_company_exists_github(target, token)
    else:
        return check_company_exists_azure(target, token)


def fetch_github_repos(target, token=None, max_repos=5000, visibility="all"):
    """
    Fetches GitHub repositories for a given user or org with full multi-page pagination.
    Allows fetching > 100 repositories (up to max_repos).
    visibility: "all", "public", "private"
    """
    print(
        f"[DEBUG] fetch_github_repos: target={target}, visibility={visibility}, has_token={bool(token)}",
        file=sys.stderr,
    )
    exists, msg = check_company_exists_github(target, token)
    if not exists:
        sys.stderr.write(f"[!] Company/User Validation Failed: {msg}\n")
        return []

    repos = []
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Repo-Analysis-TUI/3.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    urls_to_try = []
    is_authenticated_user = target.lower() in ["me", "self", "@me"] and token

    if is_authenticated_user:
        # Authenticated user can see their own private repos
        urls_to_try.append(
            ("user", f"https://api.github.com/user/repos?per_page=100&type={visibility}")
        )
    else:
        # For orgs, try orgs endpoint first (supports type=private with proper token)
        urls_to_try.append(
            ("org", f"https://api.github.com/orgs/{target}/repos?per_page=100&type={visibility}")
        )

        # For users, only public repos are accessible via /users/{username}/repos
        # type=private is NOT supported for other users
        if visibility == "private":
            print(
                f"[DEBUG] Target '{target}' is not authenticated user; /users/{{user}}/repos doesn't support type=private. Private repos only accessible for orgs with token or authenticated user.",
                file=sys.stderr,
            )
        else:
            urls_to_try.append(
                (
                    "user",
                    f"https://api.github.com/users/{target}/repos?per_page=100&type={visibility}",
                )
            )

    print(f"[DEBUG] URLs to try: {urls_to_try}", file=sys.stderr)

    for endpoint_type, base_url in urls_to_try:
        page = 1
        page_success = False
        print(f"[DEBUG] Trying {endpoint_type} endpoint: {base_url}", file=sys.stderr)
        while len(repos) < max_repos:
            url = f"{base_url}&page={page}"
            print(f"[DEBUG] Fetching page {page}: {url}", file=sys.stderr)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, list) and len(data) > 0:
                        page_success = True
                        for repo in data:
                            name = sanitize_str(repo.get("full_name") or repo.get("name"))
                            clone_url = repo.get("clone_url") or repo.get("html_url")
                            raw_desc = repo.get("description") or "No description"
                            desc = sanitize_str(raw_desc)
                            if len(desc) > 40:
                                desc = desc[:37] + "..."
                            is_private = repo.get("private", False)
                            desc_str = f"[{'Private' if is_private else 'Public'}] {desc}"

                            if token and clone_url and clone_url.startswith("https://"):
                                auth_clone_url = clone_url.replace(
                                    "https://", f"https://x-access-token:{token}@"
                                )
                            else:
                                auth_clone_url = clone_url

                            repos.append({"name": name, "url": auth_clone_url, "desc": desc_str})
                        if len(data) < 100:
                            break
                        page += 1
                    else:
                        break
            except urllib.error.HTTPError as e:
                if e.code == 404 and page == 1:
                    sys.stderr.write(
                        f"[fetch_github_repos] {endpoint_type} endpoint returned 404\n"
                    )
                    break
                elif e.code == 403:
                    sys.stderr.write(
                        f"[fetch_github_repos] {endpoint_type} endpoint returned 403 (rate limit or no access)\n"
                    )
                    break
                else:
                    sys.stderr.write(f"GitHub API HTTP error on page {page}: {e}\n")
                    break
            except Exception as e:
                sys.stderr.write(f"GitHub fetch error on page {page}: {e}\n")
                break

        if page_success:
            sys.stderr.write(
                f"[fetch_github_repos] Successfully fetched {len(repos)} repos from {endpoint_type} endpoint\n"
            )
            break

    # Filter by visibility client-side as a safety net
    if visibility == "public":
        repos = [r for r in repos if "[Public]" in r["desc"]]
    elif visibility == "private":
        repos = [r for r in repos if "[Private]" in r["desc"]]

    return repos


def fetch_azure_repos(org, token=None, project=None, max_repos=5000, visibility="all"):
    """
    Fetches Azure DevOps repositories for an organization with pagination support ($top & $skip).
    Allows fetching > 100 repositories (up to max_repos).
    visibility: "all", "public", "private" - filtered client-side as Azure API doesn't support server-side filtering
    """
    exists, msg = check_company_exists_azure(org, token)
    if not exists:
        sys.stderr.write(f"[!] Azure DevOps Org Validation Failed: {msg}\n")
        return []

    repos = []
    skip = 0
    top = 100

    headers = {"User-Agent": "Repo-Analysis-TUI/3.0", "Accept": "application/json"}
    if token:
        auth_str = f":{token}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {b64_auth}"

    while len(repos) < max_repos:
        if project:
            url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories?api-version=7.0&$top={top}&$skip={skip}"
        else:
            url = f"https://dev.azure.com/{org}/_apis/git/repositories?api-version=7.0&$top={top}&$skip={skip}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("value", [])
                if not items:
                    break
                for item in items:
                    repo_name = sanitize_str(item.get("name"))
                    proj_name = sanitize_str(item.get("project", {}).get("name", "Project"))
                    full_name = f"{proj_name}/{repo_name}"
                    remote_url = item.get("remoteUrl") or item.get("webUrl") or ""

                    # Check visibility - Azure DevOps repos have isPrivate field
                    is_private = item.get("isPrivate", False)
                    if visibility == "public" and is_private:
                        continue
                    if visibility == "private" and not is_private:
                        continue

                    clean_url = (
                        re.sub(r"https://[^/@]+@", "https://", remote_url) if remote_url else ""
                    )
                    if token and clean_url and clean_url.startswith("https://"):
                        auth_remote_url = clean_url.replace("https://", f"https://{token}@")
                    else:
                        auth_remote_url = clean_url

                    repos.append(
                        {"name": full_name, "url": auth_remote_url, "desc": f"Project: {proj_name}"}
                    )
                if len(items) < top:
                    break
                skip += len(items)
        except Exception as e:
            sys.stderr.write(f"Azure DevOps API error: {e}\n")
            break

    return repos


def summarize_high_rating_tui(output_dir="./outputs", fmt="dialog"):
    """
    Summarizes repositories from output_dir that match:
      repo_rating.rating > 5.0
      repo_rating.label != "poor" (case-insensitive)
    Outputs formatted summary for TUI / dialog / stdout.
    """
    import csv
    import glob

    repos = []
    seen = set()

    report_files = glob.glob(os.path.join(output_dir, "*", "*_report.json")) + glob.glob(
        os.path.join(output_dir, "*_report.json")
    )
    for rf in report_files:
        try:
            with open(rf, encoding="utf-8") as f:
                data = json.load(f)
            r_name = data.get("repo", os.path.basename(os.path.dirname(rf)))
            rating_obj = data.get("heuristics", {}).get("repo_rating", {})
            rating = float(rating_obj.get("rating", 0.0))
            label = str(rating_obj.get("label", "")).strip()

            if rating > 5.0 and label.lower() != "poor":
                git_info = data.get("ground_truth", {}).get("git", {})
                loc_info = data.get("ground_truth", {}).get("loc", {}).get("breakdown", {})
                langs_dict = data.get("ground_truth", {}).get("languages", {}).get("breakdown", {})
                langs_str = (
                    ", ".join(list(langs_dict.keys())[:3])
                    if isinstance(langs_dict, dict)
                    else "N/A"
                )
                fws_dict = data.get("heuristics", {}).get("frameworks", {})
                fws_str = (
                    ", ".join(list(fws_dict.keys())[:3]) if isinstance(fws_dict, dict) else "N/A"
                )

                repos.append(
                    {
                        "name": r_name,
                        "rating": rating,
                        "label": label,
                        "commits": git_info.get("commit_count", 0),
                        "contributors": git_info.get("unique_contributors", 0),
                        "loc": loc_info.get("code", 0),
                        "languages": langs_str,
                        "frameworks": fws_str,
                    }
                )
                seen.add(r_name)
        except Exception:
            continue

    csv_file = os.path.join(output_dir, "summary_all.csv")
    if os.path.isfile(csv_file):
        try:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    r_name = row.get("repo_name", "")
                    if r_name and r_name not in seen:
                        try:
                            rating = float(row.get("repo_rating_score", 0.0))
                            label = str(row.get("repo_rating_label", "")).strip()
                            if rating > 5.0 and label.lower() != "poor":
                                repos.append(
                                    {
                                        "name": r_name,
                                        "rating": rating,
                                        "label": label,
                                        "commits": int(row.get("commits", 0)),
                                        "contributors": int(row.get("contributors", 0)),
                                        "loc": int(row.get("loc_code", 0)),
                                        "languages": row.get("languages", "N/A"),
                                        "frameworks": row.get("frameworks", "N/A"),
                                    }
                                )
                                seen.add(r_name)
                        except Exception:
                            continue
        except Exception:
            pass

    repos.sort(key=lambda x: x["rating"], reverse=True)

    if fmt == "json":
        print(json.dumps(repos, indent=2))
        return

    lines = []
    lines.append("==========================================================================")
    lines.append("  HIGH-RATING REPOSITORIES SUMMARY (repo_rating: rating > 5.0 & label != poor)")
    lines.append("==========================================================================")
    lines.append(f" Total Repositories Matching Criteria: {len(repos)}")
    lines.append("--------------------------------------------------------------------------")

    if not repos:
        lines.append(" No repositories found matching rating > 5.0 and label != poor.")
    else:
        for idx, r in enumerate(repos, 1):
            lines.append(f" [{idx}] Repository : {r['name']}")
            lines.append(f"     Rating Score : {r['rating']:.2f} / 10.0  (Label: {r['label']})")
            lines.append(
                f"     Metrics      : LOC: {r['loc']:,} | Commits: {r['commits']:,} | Contributors: {r['contributors']}"
            )
            lines.append(
                f"     Tech Stack   : Languages: {r['languages']} | Frameworks: {r['frameworks']}"
            )
            lines.append(
                "--------------------------------------------------------------------------"
            )

    out_text = "\n".join(lines)
    print(out_text)


def main():
    parser = argparse.ArgumentParser(description="TUI Backend Helper")
    subparsers = parser.add_subparsers(dest="command")

    # Command: get-url
    url_parser = subparsers.add_parser("get-url")
    url_parser.add_argument("--provider", choices=["github", "azure"], required=True)
    url_parser.add_argument("--org", default="")

    # Command: open-browser
    browser_parser = subparsers.add_parser("open-browser")
    browser_parser.add_argument("--url", required=True)

    # Command: fetch-repos
    fetch_parser = subparsers.add_parser("fetch-repos")
    fetch_parser.add_argument("--provider", choices=["github", "azure"], required=True)
    fetch_parser.add_argument(
        "--target", required=True, help="Username/Org name for GitHub or Org name for Azure"
    )
    fetch_parser.add_argument("--token", default=None)
    fetch_parser.add_argument("--project", default=None)
    fetch_parser.add_argument("--visibility", choices=["all", "public", "private"], default="all")
    fetch_parser.add_argument(
        "--format", choices=["dialog", "json", "urls", "null"], default="dialog"
    )

    # Command: get-dialog-args
    subparsers.add_parser("get-dialog-args")

    # Command: resolve-selected
    resolve_parser = subparsers.add_parser("resolve-selected")
    resolve_parser.add_argument(
        "--tags", required=True, help="Space or quote separated list of tags (e.g., 'R1 R2 R3')"
    )
    resolve_parser.add_argument("--out", default="batch_repos.txt", help="Output batch file path")

    # Command: check-company
    check_parser = subparsers.add_parser("check-company")
    check_parser.add_argument("--provider", choices=["github", "azure"], required=True)
    check_parser.add_argument("--target", required=True, help="Company / Org / Username")
    check_parser.add_argument("--token", default=None)

    # Command: summarize-rating
    sum_parser = subparsers.add_parser("summarize-rating")
    sum_parser.add_argument(
        "--output-dir",
        default="./outputs",
        help="Output directory containing JSON reports or summary_all.csv",
    )
    sum_parser.add_argument("--format", choices=["dialog", "json", "text"], default="dialog")

    args = parser.parse_args()

    if args.command == "check-company":
        exists, msg = check_company(args.provider, args.target, args.token)
        if exists:
            print(f"EXISTS:{msg}")
            sys.exit(0)
        else:
            print(f"NOT_FOUND:{msg}")
            sys.exit(1)

    elif args.command == "get-url":
        if args.provider == "github":
            print(get_github_web_token_url())
        else:
            print(get_azure_web_token_url(args.org or "myorg"))

    elif args.command == "open-browser":
        success = open_web_page(args.url)
        print("OK" if success else "FAILED")

    elif args.command == "fetch-repos":
        if args.provider == "github":
            repos = fetch_github_repos(args.target, args.token, visibility=args.visibility)
        else:
            repos = fetch_azure_repos(
                args.target, args.token, args.project, visibility=args.visibility
            )

        mapping_file = ".tui_repo_map.json"
        mapping = {"R0": {"name": "SELECT ALL", "url": "ALL", "desc": "ALL"}}
        mapping.update({f"R{idx}": r for idx, r in enumerate(repos, 1)})
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)

        if args.format == "json":
            print(json.dumps(repos, indent=2))
        elif args.format == "urls":
            for r in repos:
                print(r["url"])
        elif args.format == "dialog":
            items = []
            items.append('"R0" "=== [SELECT ALL REPOSITORIES] ===" "ON"')
            for idx, r in enumerate(repos, 1):
                tag = f"R{idx}"
                name = r["name"]
                desc = r["desc"]
                items.append(f'"{tag}" "{name} ({desc})" "ON"')
            print("\n".join(items))

    elif args.command == "get-dialog-args":
        mapping_file = ".tui_repo_map.json"
        if not os.path.exists(mapping_file):
            sys.exit(1)
        with open(mapping_file, encoding="utf-8") as f:
            mapping = json.load(f)

        for tag, item in mapping.items():
            if tag == "R0":
                label = "=== [SELECT ALL REPOSITORIES] ==="
            else:
                label = f"{item['name']} ({item['desc']})"
            sys.stdout.write(f"{tag}\0{label}\0ON\0")
        sys.stdout.flush()

    elif args.command == "resolve-selected":
        mapping_file = ".tui_repo_map.json"
        if not os.path.exists(mapping_file):
            print("ERROR: Mapping file not found")
            sys.exit(1)

        with open(mapping_file, encoding="utf-8") as f:
            mapping = json.load(f)

        raw_tags = args.tags.replace('"', " ").replace("'", " ").split()
        selected_urls = []

        if "R0" in raw_tags:
            for tag, item in mapping.items():
                if tag != "R0":
                    selected_urls.append(item["url"])
        else:
            for tag in raw_tags:
                tag_clean = tag.strip()
                if tag_clean in mapping and tag_clean != "R0":
                    selected_urls.append(mapping[tag_clean]["url"])

        with open(args.out, "w", encoding="utf-8") as f:
            for url in selected_urls:
                f.write(url + "\n")

        print(f"SAVED:{len(selected_urls)}")

    elif args.command == "summarize-rating":
        summarize_high_rating_tui(output_dir=args.output_dir, fmt=args.format)


if __name__ == "__main__":
    main()
