---
name: tencentcloud-terraform
description: 腾讯云 Terraform IaC 管理。当用户说"创建/管理腾讯云资源"、"用 Terraform 写 tf 文件"、"terraform init/plan/apply"、"搭建腾讯云 VPC/CVM/TKE/COS/CLB/MySQL"、"多环境 IaC 管理"、"State 管理"等场景时激活本 skill。
license: MIT
---

# 腾讯云 Terraform IaC 管理

使用官方 Provider [`tencentcloudstack/tencentcloud`](https://github.com/tencentcloudstack/terraform-provider-tencentcloud) 对腾讯云基础设施进行完整的代码化管理。

## 使用前检查

执行任何操作前先收集环境状态：

```bash
# 1. 检查 Terraform 版本（需要 >= 1.5.0）
terraform version

# 2. 检查腾讯云凭证
printenv | grep TENCENTCLOUD

# 3. 当前目录是否已有 tf 项目
ls -la *.tf 2>/dev/null && ls -la .terraform 2>/dev/null || echo "新项目"
```

---

## Phase 1：认证配置

参考：[📋 Provider 配置](./reference/provider.md)

### 优先使用环境变量（推荐所有环境）

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxxxxxxxxxxxxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

### Provider 块（`versions.tf`，必须）

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = "~> 1.81.0"
    }
  }
}

provider "tencentcloud" {
  region = var.region
  # secret_id / secret_key 通过环境变量注入，不写入代码
}
```

> ⚠️ **绝对禁止**将 `secret_id`/`secret_key` 明文写入 `.tf` 文件并提交 Git。

---

## Phase 2：项目结构

### 标准单环境结构

```
project/
├── versions.tf      # Provider 版本锁定
├── backend.tf       # 远端状态（COS）
├── main.tf          # 主资源
├── variables.tf     # 变量声明
├── outputs.tf       # 输出值
├── locals.tf        # 本地计算值 & 公共 Tags
├── terraform.tfvars # 变量值（加入 .gitignore）
└── .gitignore
```

### 多环境推荐结构

```
project/
├── modules/
│   ├── vpc/          # VPC + 子网模块
│   ├── cvm/          # CVM 实例模块
│   ├── tke/          # TKE 集群模块
│   └── cos/          # COS Bucket 模块
└── envs/
    ├── dev/
    │   ├── main.tf
    │   ├── backend.tf
    │   └── terraform.tfvars
    ├── staging/
    └── prod/
```

---

## Phase 3：核心资源编写

根据需要加载对应参考文档：

- [🌐 VPC & 网络](./reference/vpc-networking.md)：VPC、子网、安全组、路由表、NAT、EIP
- [💻 计算 CVM](./reference/compute.md)：CVM 实例、镜像、密钥对、弹性伸缩
- [📦 存储 COS](./reference/storage.md)：COS Bucket、生命周期、CORS、CDN
- [☸️ 容器 TKE](./reference/container-tke.md)：TKE 集群、节点池、托管 Master
- [🗄️ 数据库](./reference/database.md)：CynosDB MySQL、Redis、MongoDB
- [🌐 dns](./reference/dnspod.md)：CynosDB MySQL、Redis、MongoDB
### 公共 Tags（`locals.tf`）

```hcl
locals {
  common_tags = {
    "Project"     = var.project_name
    "Environment" = var.environment
    "ManagedBy"   = "terraform"
    "Owner"       = var.owner
    "CostCenter"  = var.cost_center
  }
}
```

所有资源必须携带 `tags = local.common_tags`，可用 `merge()` 追加资源级 Tag：

```hcl
tags = merge(local.common_tags, { "Role" = "web" })
```

---

## Phase 4：State 管理

参考：[🔒 State 管理](./reference/state-management.md)

### COS 远端 Backend（团队必须，`backend.tf`）

```hcl
terraform {
  backend "cos" {
    region = "ap-guangzhou"
    bucket = "tfstate-<appid>-1234567890"   # 替换为真实 bucket
    prefix = "terraform/state/<project>"
  }
}
```

**初始化 Backend：**

```bash
# 首次初始化或切换 backend
terraform init -reconfigure
```

**多环境 State 隔离：**

```
prefix = "terraform/state/dev/<project>"     # dev
prefix = "terraform/state/prod/<project>"    # prod
```

---

## Phase 5：标准工作流

```bash
# 1. 初始化（首次或新增 provider/module 后���
terraform init

# 2. 格式化（提交前必须）
terraform fmt -recursive

# 3. 语法检查
terraform validate

# 4. 规划（查看变更，不执行）
terraform plan -var-file=terraform.tfvars

# 5. 应用
terraform apply -var-file=terraform.tfvars

# 6. CI/CD 中使用
terraform plan -out=tfplan
terraform apply tfplan

# 7. 销毁（危险！先 plan 确认）
terraform plan -destroy
terraform destroy
```

---

## Phase 6：State 操作

```bash
# 查看已管理的资源列表
terraform state list

# 查看资源详情
terraform state show tencentcloud_vpc.main

# 导入已有腾讯云资源（不重新创建）
terraform import tencentcloud_vpc.main vpc-xxxxxxxx
terraform import tencentcloud_instance.web[0] ins-xxxxxxxx

# 重命名/移动资源（重构时）
terraform state mv tencentcloud_instance.old tencentcloud_instance.new

# 从 State 移除（不删除真实资源）
terraform state rm tencentcloud_instance.web[2]
```

---

## Phase 7：安全规范

1. **`.gitignore` 必须包含：**
   ```gitignore
   *.tfstate
   *.tfstate.backup
   .terraform/
   *.tfvars
   !example.tfvars
   tfplan
   *.tfplan
   .terraform.lock.hcl  # 可选，建议提交以锁定版本
   ```

2. **Provider 版本锁定：** 提交 `.terraform.lock.hcl`
3. **生产资源防误删：**
   ```hcl
   lifecycle { prevent_destroy = true }
   ```
4. **敏感输出：**
   ```hcl
   output "db_password" {
     value     = random_password.db.result
     sensitive = true
   }
   ```
5. **最小权限：** 为 Terraform 子账号仅授予所需 CAM 策略

---

## 常见错误排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `AuthFailure` | Secret ID/Key 错误或权限不足 | 检查环境变量和 CAM 权限 |
| `ResourceExists` | 资源已存在于控制台 | `terraform import` 导入 |
| `InvalidParameterValue` | 参数值不合法（如 az 名称） | 查阅 Provider 文档确认合法值 |
| State Lock | 并发操作冲突 | `terraform force-unlock <ID>` |
| `init` 失败 | Provider 下载超时 | 设置代理 `export HTTPS_PROXY=...` |
y
---

## 腾讯云地域速查

| 代码 | 说明 |
|------|------|
| `ap-guangzhou` | 华南-广州 |
| `ap-beijing` | 华北-北京 |
| `ap-shanghai` | 华东-上海 |
| `ap-chengdu` | 西南-成都 |
| `ap-nanjing` | 华东-南京 |
| `ap-hongkong` | 港澳台-香港 |
| `ap-singapore` | 东南亚-新加坡 |
| `na-siliconvalley` | 美西-硅谷 |

官方 Provider 文档：https://registry.terraform.io/providers/tencentcloudstack/tencentcloud/latest/docs
