---
name: helm-chart-creator
description: 设计、组织和管理 Helm 图表，用于对 Kubernetes 应用程序进行模板化和打包，同时使用可重复使用的配置。在创建 Helm 图表、打包 Kubernetes 应用程序或实现模板化部署时使用。
license: MIT 
---


# Helm 图表模板生成

有关为打包和部署 Kubernetes 应用程序创建、组织和管理 Helm 图表的全面指南。

## 目的

此技能提供了构建可投入生产的 Helm 图表的分步说明，包括图表结构、模板模式、值管理以及验证策略。

## 何时使用此技能

在您需要以下情况时使用此技能：

- 从零开始创建新的 Helm 图表
- 将 Kubernetes 应用程序打包以进行分发
- 使用 Helm 管理多环境部署
- 为可重用的 Kubernetes 清单实现模板化
- 设置 Helm 图表仓库
- 遵循 Helm 最佳实践和约定

## Helm 概述

**Helm** 是 Kubernetes 的包管理器：

- 为可重用性创建 Kubernetes 清单模板
- 管理应用程序的发布和回滚
- 处理图表之间的依赖关系
- 为部署提供版本控制
- 简化跨环境的配置管理

## 分步工作流程

### 1. 初始化图表结构

**创建新图表：**

```bash
helm create my-app
```

**标准图表结构：**

```
my-app/
├── Chart.yaml           # 图表元数据
├── values.yaml          # 默认配置值
├── charts/              # 图表依赖
├── templates/           # Kubernetes 清单模板
│   ├── NOTES.txt       # 安装后说明
│   ├── _helpers.tpl    # 模板辅助函数
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   └── tests/
│       └── test-connection.yaml
└── .helmignore         # 忽略的文件
```

### 2. 配置 Chart.yaml

**图表元数据定义了包：**

```yaml
apiVersion: v2
name: my-app
description: 一个用于我的应用程序的 Helm 图表
type: application
version: 1.0.0 # 图表版本
appVersion: "2.1.0" # 应用程序版本

# 图表发现关键字
keywords:
  - web
  - api
  - backend

# 维护者信息
maintainers:
  - name: yanghuajun336
    email: yanghuajun336@example.com
    url: https://github.com/yanghuajun336/my-app

# 源码仓库
sources:
  - https://github.com/yanghuajun336/my-app

# 主页
home: https://github.com/yanghuajun336

# 图表图标
icon: https://example.com/icon.png

# 依赖
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "17.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
```

**参考:** 请参阅 `assets/Chart.yaml.template` 获取完整示例

### 3. 设计 values.yaml 结构

**按层次组织值：**
```yaml
# 镜像配置
image:
  repository: myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent

# 副本数量
replicaCount: 3

# Service 配置
service:
  type: ClusterIP
  port: 80
  targetPort: 8080

# Ingress 配置
ingress:
  enabled: false
  className: nginx
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix

# 资源限制
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# 自动扩缩容
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

# 环境变量
env:
  - name: LOG_LEVEL
    value: "info"

# ConfigMap 数据
configMap:
  data:
    APP_MODE: production

# 依赖
postgresql:
  enabled: true
  auth:
    database: myapp
    username: myapp

redis:
  enabled: false
```

**参考：** 请参阅 `assets/values.yaml.template` 获取完整结构

### 4. 创建模板文件

**使用 Go 模板语法结合 Helm 函数：**

**templates/deployment.yaml：**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: {{ .Values.service.targetPort }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        env:
          {{- toYaml .Values.env | nindent 12 }}
```

### 5. 创建模板辅助函数

**templates/\_helpers.tpl：**

```yaml
{{/*
展开图表名称。
*/}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
创建默认的完整限定应用名称。
*/}}
{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
通用标签
*/}}
{{- define "my-app.labels" -}}
helm.sh/chart: {{ include "my-app.chart" . }}
{{ include "my-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
选择器标签
*/}}
{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### 6. 管理依赖

**在 Chart.yaml 中添加依赖：**

```yaml
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
```

**更新依赖：**

```bash
helm dependency update
helm dependency build
```

**覆盖依赖的配置值：**

```yaml
# values.yaml
postgresql:
  enabled: true
  auth:
    database: myapp
    username: myapp
    password: changeme
  primary:
    persistence:
      enabled: true
      size: 10Gi
```

### 7. 测试与验证

**验证命令：**

```bash
# 检查图表语法
helm lint my-app/

# 模拟安装（不实际部署）
helm install my-app ./my-app --dry-run --debug

# 渲染模板
helm template my-app ./my-app

# 使用指定值文件渲染模板
helm template my-app ./my-app -f values-prod.yaml

# 显示计算后的值
helm show values ./my-app
```

**验证脚本：**

```bash
#!/bin/bash
set -e

echo "正在检查图表语法..."
helm lint .

echo "正在测试模板渲染..."
helm template test-release . --dry-run

echo "正在检查必填值..."
helm template test-release . --validate

echo "所有验证均已通过！"
```

**参考：** 请参阅 `scripts/validate-chart.sh`

### 8. 打包与分发

**打包图表：**

```bash
helm package my-app/
# 生成文件：my-app-1.0.0.tgz
```

**创建图表仓库：**

```bash
# 生成索引文件
helm repo index .

# 上传到仓库
# AWS S3 示例
aws s3 sync . s3://my-helm-charts/ --exclude "*" --include "*.tgz" --include "index.yaml"
```

**使用图表：**

```bash
helm repo add my-repo https://charts.example.com
helm repo update
helm install my-app my-repo/my-app
```

### 9. 多环境配置

**针对不同环境的值文件：**

```
my-app/
├── values.yaml          # 默认配置
├── values-dev.yaml      # 开发环境
├── values-staging.yaml  # 预发布环境
└── values-prod.yaml     # 生产环境
```

**values-prod.yaml：**

```yaml
replicaCount: 5

image:
  tag: "2.1.0"

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

ingress:
  enabled: true
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix

postgresql:
  enabled: true
  primary:
    persistence:
      size: 100Gi
```

**使用环境值文件安装：**

```bash
helm install my-app ./my-app -f values-prod.yaml --namespace production
```

### 10. 实现 Hook 与测试

**安装前 Hook：**

```yaml
# templates/pre-install-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-app.fullname" . }}-db-setup
  annotations:
    "helm.sh/hook": pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      containers:
      - name: db-setup
        image: postgres:15
        command: ["psql", "-c", "CREATE DATABASE myapp"]
      restartPolicy: Never
```

**测试连接：**

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-app.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
  - name: wget
    image: busybox
    command: ['wget']
    args: ['{{ include "my-app.fullname" . }}:{{ .Values.service.port }}']
  restartPolicy: Never
```

**运行测试：**

```bash
helm test my-app
```

## 常用模式

### 模式 1：条件化资源

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "my-app.fullname" . }}
spec:
  # ...
{{- end }}
```

### 模式 2：遍历列表

```yaml
env:
{{- range .Values.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
```

### 模式 3：引入外部文件

```yaml
data:
  config.yaml: |
    {{- .Files.Get "config/application.yaml" | nindent 4 }}
```

### 模式 4：全局值

```yaml
global:
  imageRegistry: docker.io
  imagePullSecrets:
    - name: regcred

# 在模板中使用：
image: {{ .Values.global.imageRegistry }}/{{ .Values.image.repository }}
```

## 最佳实践

1. **使用语义化版本号** 管理图表和应用版本
2. **为所有配置项添加注释** 在 values.yaml 中
3. **使用模板辅助函数** 处理重复逻辑
4. **打包前验证图表** 确保无误
5. **明确固定依赖版本号**
6. **为可选资源使用条件判断**
7. **遵循命名规范**（小写字母，连字符分隔）
8. **在 NOTES.txt 中** 提供使用说明
9. **通过辅助函数** 统一添加标签
10. **在所有环境中** 测试安装流程

## 故障排查

**模板渲染错误：**

```bash
helm template my-app ./my-app --debug
```

**依赖问题：**

```bash
helm dependency update
helm dependency list
```

**安装失败：**

```bash
helm install my-app ./my-app --dry-run --debug
kubectl get events --sort-by='.lastTimestamp'
```


## 相关技能

- `k8s-manifest-generator` - 用于创建基础 Kubernetes 清单
- `gitops-workflow` - 用于自动化 Helm 图表部署
