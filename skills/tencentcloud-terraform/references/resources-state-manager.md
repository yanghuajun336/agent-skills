# State 管理参考（COS Backend / import / 迁移）

> 目录
> - [COS Backend 完整配置](#cos-backend-完整配置)
> - [Backend 初始化与迁移](#backend-初始化与迁移)
> - [多环境 State 隔离](#多环境-state-隔离)
> - [terraform import 详细指南](#terraform-import)
> - [state mv / rm / push / pull](#state-操作命令)
> - [跨模块引用 State](#跨模块引用-state)
> - [State 锁机制](#state-锁机制)
> - [常见 State 问题排查](#state-问题排查)

---

## COS Backend 完整配置

`backend.tf`：

```hcl
terraform {
  backend "cos" {
    # ── 必填 ──────────────────────────────────────────────
    region = "ap-guangzhou"
    bucket = "tfstate-1234567890"   # 格式：<name>-<appid>
    prefix = "terraform/state/myproject/prod"   # State 文件路径前缀

    # ── 可选 ──────────────────────────────────────────────
    # 服务端加密（推荐生产开启）
    # encrypt = true

    # 加速域名（跨地域 CI/CD 时使用）
    # accelerate = true

    # 自定义 endpoint
    # endpoint = "cos.ap-guangzhou.myqcloud.com"
  }
}
```

> **注意：** `backend` 块内不支持变量插值（`${var.xxx}` 不可用）。
> 多环境使用不同 `prefix`，或通过 `-backend-config` 动态注入：
>
> ```bash
> terraform init -backend-config="prefix=terraform/state/${ENV}/myproject"
> ```

**提前创建 COS Bucket（仅需一次）：**

```bash
# 用腾讯云 CLI 创建（也可在控制台手动创建）
tccli cos create-bucket \
  --Bucket "tfstate-1234567890" \
  --Region "ap-guangzhou"

# 强烈推荐：开启版本控制，防止 state 文件意外覆盖
tccli cos put-bucket-versioning \
  --Bucket "tfstate-1234567890" \
  --Region "ap-guangzhou" \
  --Status "Enabled"

# 可选：开启服务端加密
tccli cos put-bucket-encryption \
  --Bucket "tfstate-1234567890" \
  --Region "ap-guangzhou"
```

---

## Backend 初始化与迁移

```bash
# 首次初始化（下载 provider + 配置 backend）
terraform init

# 修改 backend 配置后重新初始化
terraform init -reconfigure

# 本地 state → COS（添加 backend.tf 后执行）
# Terraform 会询问是否迁移，选择 yes
terraform init -migrate-state

# 验证迁移成功
terraform state list   # 应能正常列出资源
terraform plan         # 应显示 No changes
```

---

## 多环境 State 隔离

### 方案 A：不同 prefix，同一 bucket（推荐小团队）

```
tfstate-1234567890/
├── terraform/state/dev/myproject/    # dev 环境
├── terraform/state/staging/myproject/
└── terraform/state/prod/myproject/
```

```bash
# dev 初始化
cd envs/dev
terraform init -backend-config="prefix=terraform/state/dev/myproject"

# prod 初始化
cd envs/prod
terraform init -backend-config="prefix=terraform/state/prod/myproject"
```

### 方案 B：不同 bucket，强隔离（推荐大团队/生产与非��产隔离）

```hcl
# envs/prod/backend.tf
terraform {
  backend "cos" {
    region = "ap-guangzhou"
    bucket = "tfstate-prod-1234567890"   # prod 专用 bucket，严格 IAM 控制
    prefix = "terraform/state/myproject"
  }
}

# envs/dev/backend.tf
terraform {
  backend "cos" {
    region = "ap-guangzhou"
    bucket = "tfstate-nonprod-1234567890"   # 非生产共用
    prefix = "terraform/state/dev/myproject"
  }
}
```

---

## terraform import

将已存在于腾讯云控制台（手动创建或通过其他工具创建）的资源导入 Terraform State：

### 常用资源导入 ID 格式

```bash
# VPC
terraform import tencentcloud_vpc.main vpc-xxxxxxxx

# 子网
terraform import tencentcloud_subnet.public_a subnet-xxxxxxxx

# 安全组
terraform import tencentcloud_security_group.web sg-xxxxxxxx

# CVM 实例
terraform import tencentcloud_instance.web ins-xxxxxxxx

# CVM（count 语法，导入到数组第 0 个）
terraform import 'tencentcloud_instance.web[0]' ins-xxxxxxxx

# CVM（for_each 语法）
terraform import 'tencentcloud_instance.web["web-01"]' ins-xxxxxxxx

# COS Bucket
terraform import tencentcloud_cos_bucket.assets myproject-dev-assets-1234567890

# TKE 集群
terraform import tencentcloud_kubernetes_cluster.main cls-xxxxxxxx

# TKE 节点池
terraform import tencentcloud_kubernetes_node_pool.default cls-xxxxxxxx#np-xxxxxxxx

# CynosDB 集群
terraform import tencentcloud_cynosdb_cluster.main cynosdbmysql-xxxxxxxx

# Redis 实例
terraform import tencentcloud_redis_instance.main crs-xxxxxxxx

# CLB 实例
terraform import tencentcloud_clb_instance.web lb-xxxxxxxx

# NAT 网关
terraform import tencentcloud_nat_gateway.main nat-xxxxxxxx

# EIP
terraform import tencentcloud_eip.nat eip-xxxxxxxx

# 密钥对
terraform import tencentcloud_key_pair.deploy skey-xxxxxxxx

# 路由表
terraform import tencentcloud_route_table.private rtb-xxxxxxxx
```

### 批量导入工作流

```bash
# 1. 先写好 .tf 资源定义（即使参数不全也没关系）
# 2. 执行 import
terraform import tencentcloud_vpc.main vpc-abc12345

# 3. 查看 state，了解真实属性
terraform state show tencentcloud_vpc.main

# 4. 根据 state show 的输出补全 .tf 中的参数
# 5. 执行 plan，确保 No changes（说明 .tf 与实际状态一致）
terraform plan
```

---

## State 操作命令

```bash
# ── 查看 ──────────────────────────────────────────────────
# 列出所有 managed 资源
terraform state list

# 按前缀过滤
terraform state list 'module.vpc.*'
terraform state list 'tencentcloud_instance.*'

# 查看资源完整 state（包括所有属性）
terraform state show tencentcloud_vpc.main
terraform state show 'tencentcloud_instance.web[0]'

# 拉取远端 state 查看完整 JSON
terraform state pull | python3 -m json.tool | less

# ── 重命名/移动 ────────────────────────────────────────────
# 重构资源名（不删除真实资源）
terraform state mv tencentcloud_vpc.old tencentcloud_vpc.main

# 将顶层资源移入模块
terraform state mv \
  tencentcloud_vpc.main \
  module.network.tencentcloud_vpc.main

# 将模块内资源移出
terraform state mv \
  module.network.tencentcloud_vpc.main \
  tencentcloud_vpc.main

# ── 删除 ──────────────────────────────────────────────────
# 从 state 移除（真实资源不删除，terraform 不再管理此资源）
terraform state rm tencentcloud_instance.old
terraform state rm 'tencentcloud_instance.web[2]'

# ── 推送 ──────────────────────────────────────────────────
# 将本地 state 强制推送到远端（谨慎使用）
terraform state push terraform.tfstate

# ── 解锁 ─────────────────────────────────��────────────────
# 强制解锁（确认无并发操作后使用）
terraform force-unlock <LOCK_ID>
```

---

## 跨模块引用 State

在多个独立 Terraform 项目之间共享输出：

```hcl
# 消费方（例如 compute 项目引用 network 项目的输出）
data "terraform_remote_state" "network" {
  backend = "cos"
  config = {
    region = "ap-guangzhou"
    bucket = "tfstate-1234567890"
    prefix = "terraform/state/prod/network"
  }
}

# 使用跨项目输出
resource "tencentcloud_instance" "app" {
  vpc_id    = data.terraform_remote_state.network.outputs.vpc_id
  subnet_id = data.terraform_remote_state.network.outputs.app_subnet_ids[0]
  # ...
}

# network 项目的 outputs.tf 需要输出这些值
output "vpc_id" {
  value = tencentcloud_vpc.main.id
}
output "app_subnet_ids" {
  value = [for k, v in tencentcloud_subnet.app : v.id]
}
```

---

## State 锁机制

Terraform 使用 State Lock 防止并发操作导致 State 损坏。

COS Backend 通过在 COS 上创建 `.lock` 文件实现锁。

**常见 Lock 错误：**

```
Error: Error locking state: Error acquiring the state lock
Lock Info:
  ID:        xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Path:      terraform/state/prod/myproject/terraform.tfstate
  Operation: OperationTypePlan
  Who:       user@hostname
  Version:   1.5.7
  Created:   2026-03-27 10:00:00 +0000 UTC
```

**解锁步骤：**

1. 确认上面的 `Who` 和 `Created` 信息，确保之前的操作已经结束
2. 执行解锁：`terraform force-unlock <ID>`

---

## State 问题排查

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| `state pull` 返回 404 | Bucket 或 prefix 不存在 | 检查 backend.tf 配置，确认 Bucket 已创建 |
| `terraform plan` 显示大量 `~` | .tf 与 state 不匹配 | 对比 `state show` 输出，补全 .tf 参数 |
| state 锁无法释放 | CI/CD 任务异常中断 | `terraform force-unlock <ID>` |
| `import` 后 plan 仍显示变更 | .tf 配置与实际资源不一致 | 根据 `state show` 调整 .tf 参数 |
| 不同人 plan 结果不同 | Provider 版本不一致 | 提交并使用 `.terraform.lock.hcl` |
| state 文件意外损坏 | 未开启版本控制 | 在 COS Bucket 开启版本控制后恢复历史版本 |
