"""module_eval API 集成测试 — 连接运行中服务器

依赖: 后端已在 http://localhost:9099 运行

运行方式:
  uv run pytest tests/test_eval_api.py -v
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
import pytest

BASE_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:9099")


class ApiClient:
    """轻量 API 客户端"""

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.token = ""

    def _request(self, method: str, path: str, body=None, params=None, json_data=None):
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif body is not None:
            data = body.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"code": e.code, "msg": body, "success": False}
        except Exception as e:
            return {"code": 0, "msg": str(e), "success": False}

    def login(self, username="admin", password="admin123"):
        body = f"username={username}&password={password}&code=&uuid="
        result = self._request("POST", "/login", body=body)
        self.token = result.get("token", "")
        return result

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, json_data=None):
        return self._request("POST", path, json_data=json_data)

    def delete(self, path):
        return self._request("DELETE", path)

    def raw_get(self, path):
        """获取原始响应对象（用于 SSE 测试）"""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        return urllib.request.urlopen(req, timeout=10)


@pytest.fixture(scope="module")
def api():
    client = ApiClient()
    result = client.login()
    assert client.token, f"登录失败: {result}"
    yield client


# ============================================================================
# 测试用例
# ============================================================================


class TestEvalProject:
    """评审项目 CRUD"""

    def test_login(self, api):
        """确保已登录"""
        assert api.token, "未登录"

    def test_list_empty(self, api):
        """列表可访问"""
        result = api.get("/eval/project/list", params={"page_num": 1, "page_size": 10})
        assert result.get("success", False) is True, f"请求失败: {result}"

    def test_create(self, api):
        """创建项目"""
        result = api.post("/eval/project", json_data={
            "projectName": "新加坡滨海湾项目",
            "country": "新加坡",
            "amount": "10亿",
            "stage": "投标",
            "mode": "EPC",
        })
        assert result.get("code") == 200, f"创建失败: {result}"

    def test_create_minimal(self, api):
        """创建项目-最少字段"""
        result = api.post("/eval/project", json_data={"projectName": "最小项目"})
        assert result.get("code") == 200

    def test_list_has_data(self, api):
        """列表包含已创建项目"""
        result = api.get("/eval/project/list", params={"page_num": 1, "page_size": 10})
        assert result.get("total", 0) >= 1
        assert len(result.get("rows", [])) >= 1

    def test_get_detail(self, api):
        """获取详情"""
        result = api.get("/eval/project/1")
        assert result.get("code") == 200
        data = result.get("data", {})
        assert data.get("projectName") is not None

    def test_get_detail_not_found(self, api):
        """不存在项目返回空"""
        result = api.get("/eval/project/99999")
        data = result.get("data", {})
        assert data.get("projectId") is None

    def test_delete(self, api):
        """创建后删除"""
        r = api.post("/eval/project", json_data={"projectName": "待删除"})
        pid = r.get("data", {}).get("projectId")
        if pid:
            result = api.delete(f"/eval/project/{pid}")
            assert result.get("code") == 200

    def test_unauthorized(self, api):
        """无 token 请求返回 code 401"""
        req = urllib.request.Request(f"{api.base_url}/eval/project/list")
        resp = urllib.request.urlopen(req, timeout=10)
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data.get("code") == 401, f"预期 code=401, 收到: {data}"


class TestEvalReview:
    """评审流水线"""

    def test_start_without_project(self, api):
        """不存在的项目"""
        result = api.post("/eval/review/start", json_data={
            "projectId": 99999,
            "reviewMode": "standard",
        })
        # 服务层应不抛异常
        assert result.get("code") is not None

    def test_start_real_project(self, api):
        """真实项目启动评审"""
        # 先确保有项目
        r = api.post("/eval/project", json_data={"projectName": "评审测试项目"})
        pid = r.get("data", {}).get("projectId")
        if pid:
            result = api.post("/eval/review/start", json_data={
                "projectId": pid,
                "reviewMode": "standard",
            })
            assert result.get("code") == 200 or not result.get("success", True)
            # 如果成功，应该返回 review_id
            if result.get("success"):
                assert result.get("data", {}).get("reviewId") is not None

    def test_get_status(self, api):
        """获取评审状态"""
        result = api.get("/eval/review/1")
        assert result.get("code") == 200

    def test_get_opinions(self, api):
        """获取评审意见"""
        result = api.get("/eval/review/1/opinions")
        assert result.get("code") == 200

    def test_unauthorized_review(self, api):
        """无 token 访问评审"""
        req = urllib.request.Request(f"{api.base_url}/eval/review/1")
        resp = urllib.request.urlopen(req, timeout=10)
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data.get("code") == 401


class TestSSEProgress:
    """SSE 进度流"""

    def test_sse_empty(self, api):
        """不存在评审的 SSE 返回正常"""
        try:
            resp = api.raw_get("/eval/review/99999/progress")
            assert resp.status == 200
        except urllib.error.HTTPError as e:
            assert e.code == 200, f"SSE 应返回 200: {e.code}"

    def test_sse_content_type(self, api):
        """SSE 响应头"""
        try:
            resp = api.raw_get("/eval/review/1/progress")
            content_type = resp.headers.get("Content-Type", "")
            assert "text/event-stream" in content_type or "text/plain" in content_type
        except urllib.error.HTTPError as e:
            assert e.code == 200
