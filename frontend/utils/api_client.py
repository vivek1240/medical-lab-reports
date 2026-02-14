import os

import requests
import streamlit as st

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ApiClient:
    def __init__(self, token: str | None = None):
        self.token = token

    @property
    def headers(self):
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def register(self, email: str, password: str, full_name: str | None = None):
        return requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": password, "full_name": full_name}, timeout=120)

    def login(self, email: str, password: str):
        return requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=120)

    def upload_report(self, file_obj):
        return requests.post(f"{BASE_URL}/api/reports/upload", files={"file": file_obj}, headers=self.headers, timeout=600)

    def reports(self):
        return requests.get(f"{BASE_URL}/api/reports", headers=self.headers, timeout=120)

    def report(self, doc_id: str):
        return requests.get(f"{BASE_URL}/api/reports/{doc_id}", headers=self.headers, timeout=120)

    def biomarker_summary(self):
        return requests.get(f"{BASE_URL}/api/biomarkers/summary", headers=self.headers, timeout=120)

    def biomarker_categories(self):
        return requests.get(f"{BASE_URL}/api/biomarkers/categories", headers=self.headers, timeout=120)

    def biomarker_history(self, biomarker_id: int):
        return requests.get(f"{BASE_URL}/api/biomarkers/{biomarker_id}/history", headers=self.headers, timeout=120)

    def biomarker_unmapped(self):
        return requests.get(f"{BASE_URL}/api/biomarkers/unmapped", headers=self.headers, timeout=120)

    def trends_overview(self):
        return requests.get(f"{BASE_URL}/api/trends/overview", headers=self.headers, timeout=120)


# ---------------------------------------------------------------------------
# Cached data fetchers — return parsed JSON, cached for 60 seconds.
# These are standalone functions so @st.cache_data can hash the arguments.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def cached_reports(token: str) -> tuple[bool, list | dict]:
    res = requests.get(f"{BASE_URL}/api/reports", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []


@st.cache_data(ttl=60, show_spinner=False)
def cached_report_detail(token: str, doc_id: str) -> tuple[bool, dict]:
    res = requests.get(f"{BASE_URL}/api/reports/{doc_id}", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else {}


@st.cache_data(ttl=60, show_spinner=False)
def cached_biomarker_summary(token: str) -> tuple[bool, list]:
    res = requests.get(f"{BASE_URL}/api/biomarkers/summary", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []


@st.cache_data(ttl=60, show_spinner=False)
def cached_biomarker_categories(token: str) -> tuple[bool, list]:
    res = requests.get(f"{BASE_URL}/api/biomarkers/categories", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []


@st.cache_data(ttl=60, show_spinner=False)
def cached_biomarker_history(token: str, biomarker_id: int) -> tuple[bool, list]:
    res = requests.get(f"{BASE_URL}/api/biomarkers/{biomarker_id}/history", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []


@st.cache_data(ttl=60, show_spinner=False)
def cached_biomarker_unmapped(token: str) -> tuple[bool, list]:
    res = requests.get(f"{BASE_URL}/api/biomarkers/unmapped", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []


@st.cache_data(ttl=60, show_spinner=False)
def cached_trends_overview(token: str) -> tuple[bool, list]:
    res = requests.get(f"{BASE_URL}/api/trends/overview", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    return res.ok, res.json() if res.ok else []
