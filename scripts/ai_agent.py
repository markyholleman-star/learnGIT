#!/usr/bin/env python3
"""
Local AI agent to propose changes:
- Requires: GITHUB_TOKEN, REPO (owner/repo), OPENAI_API_KEY (or other model key)
- Usage: python scripts/ai_agent.py --issue 12
"""
import os
import subprocess
import tempfile
import argparse
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("REPO")  # e.g., "youruser/yourrepo"
MODEL_API_KEY = os.environ.get("MODEL_API_KEY")  # your LLM key
MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT")  # optional

def run(cmd, cwd=None):
    subprocess.check_call(cmd, shell=True, cwd=cwd)

def get_issue(issue_number):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    return r.json()

def call_model(prompt):
    # Minimal example using a generic HTTP API; replace with your provider call
    # This function must be adapted to your LLM provider's API.
    payload = {"prompt": prompt, "max_tokens": 800}
    headers = {"Authorization": f"Bearer {MODEL_API_KEY}"}
    r = requests.post(MODEL_ENDPOINT, json=payload, headers=headers)
    r.raise_for_status()
    return r.json().get("text") or r.text

def create_pr(branch, title, body):
    url = f"https://api.github.com/repos/{REPO}/pulls"
    payload = {"title": title, "head": branch, "base": "main", "body": body}
    r = requests.post(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    return r.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True)
    args = parser.parse_args()

    issue = get_issue(args.issue)
    prompt = f"Repo files: list and context. Issue title: {issue['title']}\nIssue body:\n{issue['body']}\n\nProduce a small patch that updates docs/main-document.md according to the issue. Return only the new file contents and a short commit message."

    with tempfile.TemporaryDirectory() as tmp:
        run(f"git clone https://x-access-token:{GITHUB_TOKEN}@github.com/{REPO}.git .", cwd=tmp)
        branch = f"ai-proposal-{args.issue}"
        run(f"git checkout -b {branch}", cwd=tmp)

        model_output = call_model(prompt)
        # For safety, write model output to a draft file for manual review
        out_path = os.path.join(tmp, "drafts", f"ai-proposal-issue-{args.issue}.md")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(model_output)

        run(f"git add {out_path}", cwd=tmp)
        run(f'git commit -m "AI: propose changes for issue #{args.issue}"', cwd=tmp)
        run(f"git push --set-upstream origin {branch}", cwd=tmp)

        pr = create_pr(branch, f"AI proposal: {issue['title']}", "Automated proposal from local AI agent. Please review.")
        print("PR created:", pr["html_url"])

if __name__ == "__main__":
    main()
