"""Minimal GitLab REST client. In mock mode (no token / EVALGATE_MOCK=1) every
write is recorded to out/gitlab_actions.jsonl instead of hitting the API."""
from __future__ import annotations
import json, os
from pathlib import Path
import httpx

OUT = Path("out")


class GitLab:
    def __init__(self):
        self.url = os.getenv("CI_API_V4_URL", "https://gitlab.com/api/v4")
        self.project = os.getenv("CI_PROJECT_ID", "0")
        self.token = os.getenv("EVALGATE_GITLAB_TOKEN")  # project access token, api scope
        self.mock = os.getenv("EVALGATE_MOCK") == "1" or not self.token

    def _write(self, method: str, path: str, payload: dict) -> dict:
        if self.mock:
            OUT.mkdir(exist_ok=True)
            rec = {"method": method, "path": path, "payload": payload}
            with open(OUT / "gitlab_actions.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")
            return {"mock": True, **rec}
        r = httpx.request(method, f"{self.url}/projects/{self.project}{path}", json=payload, timeout=30,
                          headers={"PRIVATE-TOKEN": self.token})
        r.raise_for_status()
        return r.json()

    def mr_note(self, mr_iid: str, body: str) -> dict:
        return self._write("POST", f"/merge_requests/{mr_iid}/notes", {"body": body})

    def mr_labels(self, mr_iid: str, add: list[str]) -> dict:
        return self._write("PUT", f"/merge_requests/{mr_iid}", {"add_labels": ",".join(add)})

    def issue(self, title: str, description: str, labels: list[str]) -> dict:
        return self._write("POST", "/issues", {"title": title, "description": description, "labels": ",".join(labels)})
