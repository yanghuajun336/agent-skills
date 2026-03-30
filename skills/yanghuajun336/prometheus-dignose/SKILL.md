# Prometheus-dignose Skill

**为 AI Agent/LangChain/Copilot/LlamaIndex等插件系统提供 Prometheus 指标、状态、告警等所有常规 API 封装。**

- 项目：prometheus_skill.py
- 适用范围：Kubernetes、服务器集群、PaaS 云、微服务基础设施监控
- 协议：MIT

---

## 能力简介

本 Skill 封装 Prometheus HTTP API 的主要功能，支持直接调用 Prometheus 查询/管理接口，可用于 Agent 自动化巡检、故障诊断、数据挖掘等场景。

- 支持常规 PromQL 查询（即时/时序/标签/label取值等）
- 支持获取监控 targets、alertmanagers、活跃告警
- 支持查询成员、规则、服务启动配置、构建版本信息
- 支持取当前服务运行状态与配置信息

---

## 用法示例

```python
from scripts.prometheus_skill import PrometheusSkill

prom = PrometheusSkill(base_url="http://localhost:9090")

# 1. 实时 PromQL 查询
result = prom.instant_query("sum(up)")
print(result)

# 2. 某段时间序列查询
r = prom.range_query("rate(http_requests_total[5m])", start="2026-03-30T00:00:00Z", end="2026-03-30T01:00:00Z", step="60s")
print(r)

# 3. 列出所有label名
print(prom.list_labels())

# 4. 获得所有 targets（采集对象）
print(prom.get_targets())

# 5. 当前所有活跃告警
print(prom.get_alerts())

# 6. 当前Prometheus服务配置信息
print(prom.get_config())
```

---

## 支持的API与方法

| 方法名                        | Prometheus API 路径                           | 说明                 |
|------------------------------|-----------------------------------------------|----------------------|
| instant_query(promql, time)  | `/api/v1/query`                               | 实时点查             |
| range_query(promql, start, end, step) | `/api/v1/query_range`                  | 历史范围序列点查     |
| list_series(match[], start, end)      | `/api/v1/series`                       | 所有匹配序列         |
| list_labels(start, end)      | `/api/v1/labels`                              | 所有label名          |
| label_values(label, start, end) | `/api/v1/label/<label>/values`             | 指定label所有取值    |
| get_targets()                | `/api/v1/targets`                             | 当前采集目标         |
| get_alerts()                 | `/api/v1/alerts`                              | 当前活跃告警         |
| get_rules()                  | `/api/v1/rules`                               | 当前所有规则         |
| get_active_alertmanagers()   | `/api/v1/alertmanagers`                       | 活跃Alertmanager     |
| get_status()                 | `/api/v1/status`                              | 服务整体状态         |
| get_flags()                  | `/api/v1/status/flags`                        | 启动参数             |
| get_config()                 | `/api/v1/status/config`                       | prometheus.yml配置   |
| get_runtimeinfo()            | `/api/v1/status/runtimeinfo`                  | 运行时信息           |
| get_buildinfo()              | `/api/v1/status/buildinfo`                    | 构建信息             |

---

## Skill 集成说明

1. 在 LLM agent 的 tools/skills 配置中注册（如 LangChain、Flowise、LlamaIndex等）
2. PromQL 表达式可由 AI Agent 文本解析生成
3. 支持 Bearer Token，生产环境下可通过 __init__ 传递，可安全鉴权

### 依赖
- Python 3.x
- requests

### 安装
```bash
pip install requests
```

---

## 参考

- [Prometheus 官方 Query API 文档](https://hulining.gitbook.io/prometheus/prometheus/querying/api)
- [Prometheus 官方文档](https://prometheus.io/docs/prometheus/latest/querying/api/)

---

## 作者

Copilot定制 & yanghuajun336
