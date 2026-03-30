import requests
from typing import Optional, Dict, Any, List

class PrometheusSkill:
    """
    Prometheus API Skill
    封装 Prometheus HTTP API 所有常用接口，支持 agent/LangChain/LLM 等调用。
    """

    def __init__(self, base_url: str, bearer_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    # ========== 1. 实时查询 ==========
    def instant_query(self, promql: str, time: Optional[float] = None) -> Dict[str, Any]:
        """执行单点PromQL查询 /api/v1/query"""
        params = {"query": promql}
        if time:
            params["time"] = time
        return self._get("/api/v1/query", params)

    # ========== 2. 范围查询 ==========
    def range_query(self, promql: str, start: str, end: str, step: str) -> Dict[str, Any]:
        """执行时序PromQL查询 /api/v1/query_range"""
        params = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step
        }
        return self._get("/api/v1/query_range", params)

    # ========== 3. 获取所有 metric 名字 ==========
    def list_series(self, match: List[str], start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        """列出匹配的时序（可用于探查所有监控项） /api/v1/series"""
        params = [("match[]", m) for m in match]
        if start: params.append(("start", start))
        if end: params.append(("end", end))
        return self._get("/api/v1/series", params)

    def list_labels(self, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        """列出所有label名 /api/v1/labels"""
        params = {}
        if start: params["start"] = start
        if end: params["end"] = end
        return self._get("/api/v1/labels", params)

    def label_values(self, label_name: str, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        """列出某个label的所有 possible value /api/v1/label/{label_name}/values"""
        params = {}
        if start: params["start"] = start
        if end: params["end"] = end
        return self._get(f"/api/v1/label/{{label_name}}/values", params)

    # ========== 4. 获取目标/告警 配置/状态 ==========
    def get_targets(self) -> Dict[str, Any]:
        """获取targets（监控目标） /api/v1/targets"""
        return self._get("/api/v1/targets")

    def get_alerts(self) -> Dict[str, Any]:
        """Prometheus当前所有告警（由Prometheus规则产生） /api/v1/alerts"""
        return self._get("/api/v1/alerts")

    def get_rules(self) -> Dict[str, Any]:
        """获取当前所有Prometheus规则 /api/v1/rules"""
        return self._get("/api/v1/rules")

    def get_active_alertmanagers(self) -> Dict[str, Any]:
        """获取当前活跃的alertmanager列表 /api/v1/alertmanagers"""
        return self._get("/api/v1/alertmanagers")

    def get_status(self) -> Dict[str, Any]:
        """获取Prometheus服务状态 /api/v1/status"""
        return self._get("/api/v1/status")

    def get_flags(self) -> Dict[str, Any]:
        """获取Prometheus启动flags /api/v1/status/flags"""
        return self._get("/api/v1/status/flags")

    def get_config(self) -> Dict[str, Any]:
        """获取Prometheus配置 /api/v1/status/config"""
        return self._get("/api/v1/status/config")

    def get_runtimeinfo(self) -> Dict[str, Any]:
        """Prometheus运行时信息 /api/v1/status/runtimeinfo"""
        return self._get("/api/v1/status/runtimeinfo")

    def get_buildinfo(self) -> Dict[str, Any]:
        """Prometheus构建信息 /api/v1/status/buildinfo"""
        return self._get("/api/v1/status/buildinfo")

    # ========== 5. 内部辅助 ==========
    def _get(self, path: str, params=None) -> Dict[str, Any]:
        url = self.base_url + path
        r = requests.get(url, headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

# ==== 用法示例 ====
if __name__ == "__main__":
    prom = PrometheusSkill(base_url="http://localhost:9090")
    print(prom.instant_query("up"))
    print(prom.get_targets())
    print(prom.list_labels())
    print(prom.get_rules())