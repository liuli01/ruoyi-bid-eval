"""module_eval 完整 API 测试 — 同步请求，无需 asyncio

运行方式（需后端已在运行）：
  cd ruoyi-fastapi-backend
  pytest tests/test_eval_comprehensive.py -v
"""
import os
import json
import time
import urllib.request
import urllib.parse
import pytest

BASE_URL = os.environ.get("TEST_SERVER", "http://localhost:9100")


class ApiClient:
    """同步 API 客户端"""

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.token = ""

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        data = kwargs.get("json")
        params = kwargs.get("params")
        files = kwargs.get("files")
        form = kwargs.get("form")

        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        elif form is not None:
            body = form.encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif files is not None:
            import io
            boundary = "----TestBoundary7MA4YW"
            body_parts = []
            for field_name, (file_name, file_data, content_type) in files.items():
                body_parts.append(f"--{boundary}\r\n")
                body_parts.append(f'Content-Disposition: form-data; name="{field_name}"; filename="{file_name}"\r\n')
                body_parts.append(f"Content-Type: {content_type}\r\n\r\n")
                body_parts.append(file_data.decode() if isinstance(file_data, bytes) else file_data)
                body_parts.append("\r\n")
            # Add form data if present
            extra = kwargs.get("data", {})
            for k, v in extra.items():
                body_parts.append(f"--{boundary}\r\n")
                body_parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n')
                body_parts.append(str(v))
                body_parts.append("\r\n")
            body_parts.append(f"--{boundary}--\r\n")
            body = "".join(body_parts).encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"code": e.code, "msg": e.read().decode()[:200], "success": False}

    def login(self):
        result = self._request("POST", "/login", form="username=admin&password=admin123&code=&uuid=")
        self.token = result.get("token", "")
        return result

    def get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def delete(self, path):
        return self._request("DELETE", path)


@pytest.fixture(scope="module")
def api():
    client = ApiClient()
    client.login()
    assert client.token, "登录失败"
    return client


# ============================================================================
# 测试用例
# ============================================================================


class TestProjectAPI:
    """项目 CRUD"""

    def test_list(self, api):
        r = api.get("/eval/project/list", params={"page_num": 1, "page_size": 10})
        assert r.get("code") == 200
        assert "rows" in r or "data" in r

    def test_create(self, api):
        r = api.post("/eval/project", json={"projectName": "新加坡项目", "country": "新加坡", "stage": "投标"})
        assert r.get("code") == 200, f"创建失败: {r}"
        assert r.get("data", {}).get("projectId") is not None

    def test_create_minimal(self, api):
        r = api.post("/eval/project", json={"projectName": "最小项目"})
        assert r.get("code") == 200

    def test_detail(self, api):
        r = api.get("/eval/project/28")
        assert r.get("code") == 200
        assert r.get("data", {}).get("projectName") is not None

    def test_detail_not_found(self, api):
        r = api.get("/eval/project/99999")
        assert r.get("code") == 200
        assert r.get("data", {}).get("projectId") is None

    def test_delete(self, api):
        r = api.post("/eval/project", json={"projectName": "待删除"})
        pid = r.get("data", {}).get("projectId")
        if pid:
            r = api.delete(f"/eval/project/{pid}")
            assert r.get("code") == 200


class TestMaterialAPI:
    """文件上传"""

    def test_upload_no_category(self, api):
        r = api.post("/eval/project/28/upload",
            data={"category": ""},
            files={"file": ("no_cat.txt", b"no category test", "text/plain")})
        assert r.get("code") == 200
        data = r.get("data", {})
        # 空分类应存为"其他"或保留空
        assert data.get("category") in ("其他", "")

    def test_upload_with_category(self, api):
        r = api.post("/eval/project/28/upload",
            data={"category": "招标文件"},
            files={"file": ("bid.txt", b"bid content", "text/plain")})
        assert r.get("code") == 200
        assert r.get("data", {}).get("category") == "招标文件"

    def test_list(self, api):
        r = api.get("/eval/project/28/materials")
        assert r.get("code") == 200
        materials = r.get("data", [])
        assert isinstance(materials, list)
        if materials:
            assert "fileName" in materials[0]
            assert "category" in materials[0]


class TestReviewAPI:
    """评审流水线"""

    def test_start_review(self, api):
        r = api.post("/eval/review/start", json={"projectId": 28, "reviewMode": "fast"})
        assert r.get("code") == 200, f"启动评审失败: {r}"
        data = r.get("data", {})
        assert data.get("review_id") is not None
        assert data.get("triggered_count") is not None
        if data["triggered_count"] > 0:
            # 等待意见生成
            time.sleep(5)
            r = api.get(f"/eval/review/{data['review_id']}/opinions")
            ops = r.get("data", [])
            assert len(ops) > 0
            assert "ruleId" in ops[0]

    def test_history(self, api):
        r = api.get("/eval/project/28/reviews")
        assert r.get("code") == 200
        assert isinstance(r.get("data"), list)


class TestLlmStatus:
    """LLM 状态"""

    def test_status(self, api):
        r = api.get("/eval/llm/status")
        assert r.get("code") == 200
        d = r.get("data", {})
        assert "configured" in d
        assert "model" in d


class TestAuth:
    """权限"""

    def test_unauthorized(self):
        r = urllib.request.urlopen(f"{BASE_URL}/eval/project/list", timeout=10)
        data = json.loads(r.read().decode())
        assert data.get("code") == 401
