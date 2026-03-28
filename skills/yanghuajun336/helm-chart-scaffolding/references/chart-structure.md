# Helm Chart 结构参考

Helm Chart 组织结构、文件规范与最佳实践完整指南。

## 标准 Chart 目录结构

```
my-app/
├── Chart.yaml              # Chart 元数据（必需）
├── Chart.lock              # 依赖锁定文件（自动生成）
├── values.yaml             # 默认配置值（必需）
├── values.schema.json      # values 验证 JSON Schema
├── .helmignore             # 打包时忽略的文件模式
├── README.md               # Chart 文档
├── LICENSE                 # Chart 许可证
├── charts/                 # Chart 依赖（打包内置）
│   └── postgresql-12.0.0.tgz
├── crds/                   # 自定义资源定义（CRD）
│   └── my-crd.yaml
├── templates/              # Kubernetes 清单模板（必需）
│   ├── NOTES.txt          # 安装后说明
│   ├── _helpers.tpl       # 模板辅助函数
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── networkpolicy.yaml
│   └── tests/
│       └── test-connection.yaml
└── files/                  # 附加文件
    └── config/
        └── app.conf
```

## Chart.yaml 规范

### API 版本 v2（Helm 3+）

```yaml
apiVersion: v2 # 必需：API 版本
name: my-application # 必需：Chart 名称
version: 1.2.3 # 必需：Chart 版本（SemVer）
appVersion: "2.5.0" # 应用版本
description: A Helm chart for my application # 必需
type: application # Chart 类型：application 或 library
keywords: # 搜索关键词
  - web
  - api
  - backend
home: https://example.com # 项目主页
sources: # 源码地址
  - https://github.com/example/my-app
maintainers: # 维护者列表
  - name: John Doe
    email: john@example.com
    url: https://github.com/johndoe
icon: https://example.com/icon.png # Chart 图标 URL
kubeVersion: ">=1.24.0" # 兼容的 Kubernetes 版本
deprecated: false # 标记为已弃用
annotations: # 自定义注解
  example.com/release-notes: https://example.com/releases/v1.2.3
dependencies: # Chart 依赖
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
    import-values:
      - child: database
        parent: database
    alias: db
```

## Chart 类型

### Application Chart（应用 Chart）

```yaml
type: application
```

- 标准 Kubernetes 应用
- 可安装和管理
- 包含 K8s 资源模板

### Library Chart（库 Chart）

```yaml
type: library
```

- 共享模板辅助函数
- 不可直接安装
- 作为其他 Chart 的依赖使用
- 无 templates/ 目录

## Values 文件组织

### values.yaml（默认值）

```yaml
# 全局值（与子 Chart 共享）
global:
  imageRegistry: docker.io
  imagePullSecrets: []

# 镜像配置
image:
  registry: docker.io
  repository: myapp/web
  tag: "" # 默认使用 .Chart.AppVersion
  pullPolicy: IfNotPresent

# Deployment 配置
replicaCount: 1
revisionHistoryLimit: 10

# Pod 配置
podAnnotations: {}
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

# 容器安全
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL

# Service
service:
  type: ClusterIP
  port: 80
  targetPort: http
  annotations: {}

# 资源限制
resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi

# 自动伸缩
autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 100
  targetCPUUtilizationPercentage: 80

# 节点选择
nodeSelector: {}
tolerations: []
affinity: {}

# 监控
serviceMonitor:
  enabled: false
  interval: 30s
```

### values.schema.json（值校验）

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"]
        }
      }
    }
  },
  "required": ["image"]
}
```

## 模板文件

### 模板命名规范

- **小写加连字符**：`deployment.yaml`、`service-account.yaml`
- **局部模板**：以下划线开头，如 `_helpers.tpl`
- **测试文件**：放在 `templates/tests/` 目录下
- **CRD**：放在 `crds/` 目录下（不做模板化）

### 常用模板

#### \_helpers.tpl

```yaml
{{/*
标准命名辅助函数
*/}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "my-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

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
{{- end -}}

{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
镜像名称辅助函数
*/}}
{{- define "my-app.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- end -}}
```

#### NOTES.txt

```
感谢安装 {{ .Chart.Name }}。

您的 Release 名称为 {{ .Release.Name }}。

查看 Release 详情，请运行：

  $ helm status {{ .Release.Name }}
  $ helm get all {{ .Release.Name }}

{{- if .Values.ingress.enabled }}

应用访问地址：
{{- range .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ .host }}{{ .path }}
{{- end }}
{{- else }}

通过以下命令获取应用访问地址：
  export POD_NAME=$(kubectl get pods --namespace {{ .Release.Namespace }} -l "app.kubernetes.io/name={{ include "my-app.name" . }}" -o jsonpath="{.items[0].metadata.name}")
  kubectl port-forward $POD_NAME 8080:80
  echo "访问 http://127.0.0.1:8080"
{{- end }}
```

## 依赖管理

### 声明依赖

```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled # 通过 values 启用/禁用
    tags: # 依赖分组
      - database
    import-values: # 从子 Chart 导入 values
      - child: database
        parent: database
    alias: db # 通过 .Values.db 引用
```

### 管理依赖

```bash
# 更新依赖
helm dependency update

# 列出依赖
helm dependency list

# 构建依赖
helm dependency build
```

### Chart.lock

由 `helm dependency update` 自动生成：

```yaml
dependencies:
  - name: postgresql
    repository: https://charts.bitnami.com/bitnami
    version: 12.0.0
digest: sha256:abcd1234...
generated: "2024-01-01T00:00:00Z" # 生成时间
```

## .helmignore

从 Chart 包中排除的文件：

```
# 开发文件
.git/
.gitignore
*.md
docs/

# 构建产物
*.swp
*.bak
*.tmp
*.orig

# CI/CD
.travis.yml
.gitlab-ci.yml
Jenkinsfile

# 测试
test/
*.test

# IDE
.vscode/
.idea/
*.iml
```

## 自定义资源定义（CRDs）

将 CRD 放在 `crds/` 目录下：

```
crds/
├── my-app-crd.yaml
└── another-crd.yaml
```

**CRD 重要说明：**

- CRD 在所有模板之前安装
- CRD 不支持模板化（不可使用 `{{ }}` 语法）
- CRD 不会随 Chart 升级或删除
- 使用 `helm install --skip-crds` 可跳过安装

## Chart 版本管理

### 语义化版本

- **Chart 版本**：Chart 有变更时递增
  - MAJOR：不兼容的破坏性变更
  - MINOR：新功能，向后兼容
  - PATCH：Bug 修复

- **App 版本**：所部署应用的版本号
  - 可为任意字符串
  - 不强制遵循 SemVer

```yaml
version: 2.3.1 # Chart 版本
appVersion: "1.5.0" # 应用版本
```

## Chart 测试

### 测试文件

```yaml
# templates/tests/test-connection.yaml（连接测试）
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-app.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  containers:
  - name: wget
    image: busybox
    command: ['wget']
    args: ['{{ include "my-app.fullname" . }}:{{ .Values.service.port }}']
  restartPolicy: Never
```

### 运行测试

```bash
helm test my-release
helm test my-release --logs
```

## Hooks（钩子）

Helm Hooks 允许在特定生命周期节点介入执行：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-app.fullname" . }}-migration
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

### Hook 类型

- `pre-install`：模板渲染前执行
- `post-install`：所有资源加载完成后执行
- `pre-delete`：任何资源删除前执行
- `post-delete`：所有资源删除后执行
- `pre-upgrade`：升级前执行
- `post-upgrade`：升级后执行
- `pre-rollback`：回滚前执行
- `post-rollback`：回滚后执行
- `test`：配合 `helm test` 执行

### Hook 权重

控制 Hook 执行顺序（-5 到 5，数值越小越先执行）

### Hook 删除策略

- `before-hook-creation`：创建新 Hook 前删除上一个
- `hook-succeeded`：执行成功后删除
- `hook-failed`：执行失败后删除

## 最佳实践

1. **使用辅助函数**处理重复的模板逻辑
2. **字符串加引号**：`{{ .Values.name | quote }}`
3. **使用 values.schema.json** 校验 values
4. **在 values.yaml 中注释所有字段**
5. **使用语义化版本**管理 Chart 版本
6. **精确锁定依赖版本**
7. **包含 NOTES.txt** 提供使用说明
8. **为关键功能编写测试**
9. **使用 Hooks** 处理数据库迁移
10. **保持 Chart 职责单一**——每个 Chart 只负责一个应用

## Chart 仓库结构

```
helm-charts/
├── index.yaml
├── my-app-1.0.0.tgz
├── my-app-1.1.0.tgz
├── my-app-1.2.0.tgz
└── another-chart-2.0.0.tgz
```

### 创建仓库索引

```bash
helm repo index . --url https://charts.example.com
```

## 相关资源

- [Helm 官方文档](https://helm.sh/docs/)
- [Chart 模板指南](https://helm.sh/docs/chart_template_guide/)
- [最佳实践](https://helm.sh/docs/chart_best_practices/)
