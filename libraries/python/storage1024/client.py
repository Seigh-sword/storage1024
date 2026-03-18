import requests
import json

class Storage1024:
    def __init__(self, api_base="https://storage1024.onrender.com/api"):
        self.api_base = api_base
        self.token = None
        self.user_id = None

    def set_token(self, token):
        self.token = token

    def set_userid(self, user_id):
        self.user_id = user_id

    def _get_headers(self):
        if not self.token:
            raise ValueError("Token not set. Use set_token()")
        return {"Authorization": f"Bearer {self.token}"}

    def get_gv(self, name):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/gv/{name}"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json().get("value")

    def add_gv(self, name, value):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/gv"
        payload = {"alias": name, "value": value}
        res = requests.post(url, json=payload, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def gv_json(self):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/gv"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def upload_file(self, alias, file_path):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/upload"
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"alias": alias}
            res = requests.post(url, files=files, data=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def create_project(self, name):
        url = f"{self.api_base}/projects/create"
        res = requests.post(url, json={"name": name})
        res.raise_for_status()
        return res.json()

    def create_token(self, name, token_type="public"):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/tokens"
        payload = {"name": name, "type": token_type}
        res = requests.post(url, json=payload, headers=self._get_headers())
        res.raise_for_status()
        return res.json().get("token")

    def revoke_token(self, token_to_revoke):
        if not self.user_id:
            raise ValueError("User ID not set. Use set_userid()")
        url = f"{self.api_base}/projects/{self.user_id}/tokens/revoke"
        payload = {"token": token_to_revoke}
        res = requests.post(url, json=payload, headers=self._get_headers())
        res.raise_for_status()
        return res.json()
