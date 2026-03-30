# 最佳实践（多环境 / 模块化 / CI-CD / 安全）

> 目录
> - [项目目录结构](#项目目录结构)
> - [变量规范](#变量规范)
> - [locals 与公共 Tags](#locals-与公共-tags)
> - [for_each vs count 选型](#for_each-vs-count)
> - [模块化设计](#模块化设计)
> - [多环境管理](#多环境管理)
> - [安全规范清单](#安全规范清单)
> - [CI/CD 集成（GitHub Actions）](#cicd-github-actions)
> - [.gitignore 模板](#gitignore-模板)
> - [代码风格约定](#代码风格约定)

---

## 项目目录结构

### 单环境（快速启动）

```
myproject/
├── versions.tf          # Provider 版本锁定（必须）
├── backend.tf           # COS 远端 State（必须）
├── main.tf              # 主资源入口
├── locals.tf            # 本地变量（Tags 等）
├── variables.tf         # 输入变量声明
├── outputs.tf           # 输出值
├── terraform.tfvars     # 变量值（加入 .gitignore）
├── example.tfvars       # 示例（可提交 Git，无敏感信息）
└── .gitignore
```

### 多环境（推荐生产）

```
myproject/
├── modules/
│   ├── network/             # VPC/子网/安全组/NAT
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/             # CVM/AS 伸缩组
│   ├── database/            # MySQL/Redis
│   └── tke/                 # TKE 集群
│
├── envs/
│   ├── dev/
│   │   ├── main.tf          # 调用 modules
│   │   ├── backend.tf       # dev 专用 backend prefix
│   │   ├── versions.tf      # 同根目录版本约束
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars # 不提交 Git
│   ├── staging/
│   └── prod/
│
└── .github/
    └── workflows/
        └── terraform.yml
```

---

## 变量规范

```hcl
# variables.tf 完整示例

# ── 必填变量（无 default）────────────────────────────────────
variable "project_name" {
  description = "项目名称，用于所有资源命名前缀和 Tag。格式：小写字母+数字+连字符"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$", var.project_name))
    error_message = "project_name 只能包含小写字母、数字和连字符，长度 3-20 位。"
  }
}

variable "environment" {
  description = "部署环境标识符"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment 必须是 dev、staging 或 prod。"
  }
}

# ── 有默认值的变量 ────────────────────────────────────────────
variable "region" {
  description = "腾讯云地域代码"
  type        = string
  default     = "ap-guangzhou"
}

variable "owner" {
  description = "资源负责人（用于 Tag），通常是团队名或工单号"
  type        = string
  default     = "platform-team"
}

variable "cost_center" {
  description = "成本中心（用于 Tag 和费用分摊）"
  type        = string
  default     = "engineering"
}

# ── 敏感变量 ──────────────────────────────────────────────────
variable "mysql_password" {
  description = "MySQL root 密码。通过 TF_VAR_mysql_password 注入，禁止写入 .tfvars 文件"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH 公钥内容（ssh-rsa AAAA...），通过 TF_VAR_ssh_public_key 注入"
  type        = string
  sensitive   = false
}

# ── 复杂类型变量 ──────────────────────────────────────────────
variable "availability_zones" {
  description = "使用的可用区列表"
  type        = list(string)
  default     = ["ap-guangzhou-1", "ap-guangzhou-2"]
}

variable "instance_count_by_env" {
  description = "各环境的实例数量"
  type        = map(number)
  default = {
    dev     = 1
    staging = 2
    prod    = 4
  }
}

# 使用：var.instance_count_by_env[var.environment]
```

---

## locals 与公共 Tags

```hcl
# locals.tf

locals {
  # ── 公共 Tags（所有资源必须携带）──────────────────────────
  common_tags = {
    "Project"     = var.project_name
    "Environment" = var.environment
    "ManagedBy"   = "terraform"
    "Owner"       = var.owner
    "CostCenter"  = var.cost_center
    # "CreatedAt" = formatdate("YYYY-MM-DD", timestamp())
    # ⚠️ 不要用 timestamp()，每次 plan 都会产生 diff
  }

  # ── 命名前缀（统一格式）──────────────────────────────────
  name_prefix = "${var.project_name}-${var.environment}"

  # ── 环境相关计算 ────────���───────────────────────────────
  is_prod        = var.environment == "prod"
  instance_count = var.instance_count_by_env[var.environment]

  # ── 可用区处理 ─────────────────────────────────────────
  az_count = length(var.availability_zones)
}
```

---

## for_each vs count

**选择原则：**

- 需要**稳定标识符**（删除/添加元素不影响其他）→ `for_each`
- 纯**同质资源**，仅数量不同 → `count`

```hcl
# ✅ 推荐：for_each，删除 web-02 不影响 web-01 和 web-03
resource "tencentcloud_instance" "web" {
  for_each = toset(["web-01", "web-02", "web-03"])

  instance_name = "${local.name_prefix}-${each.key}"
  # ...
}

# ⚠️ 谨慎：count，删除索引 1（web-02）会导致 web-03 重建
resource "tencentcloud_instance" "web" {
  count = 3

  instance_name = "${local.name_prefix}-web-${format("%02d", count.index + 1)}"
  # ...
}

# ✅ 子网 for_each（map 形式，包含元数据）
variable "subnets" {
  default = {
    "pub-gz1"  = { cidr = "10.0.1.0/24", az = "ap-guangzhou-1" }
    "pub-gz2"  = { cidr = "10.0.2.0/24", az = "ap-guangzhou-2" }
    "priv-gz1" = { cidr = "10.0.10.0/24", az = "ap-guangzhou-1" }
  }
}

resource "tencentcloud_subnet" "all" {
  for_each          = var.subnets
  name              = "${local.name_prefix}-${each.key}"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = local.common_tags
}
```

---

## 模块化设计

### 模块编写规范

```hcl
# modules/network/main.tf
resource "tencentcloud_vpc" "this" {
  name       = var.name
  cidr_block = var.cidr_block
  tags       = var.tags
}

resource "tencentcloud_subnet" "this" {
  for_each          = var.subnets
  name              = "${var.name}-${each.key}"
  vpc_id            = tencentcloud_vpc.this.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = var.tags
}

# modules/network/variables.tf
variable "name"       { type = string; description = "VPC 名称前缀" }
variable "cidr_block" { type = string; description = "VPC CIDR" }
variable "tags"       { type = map(string); default = {} }
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
  description = "子网配置 map"
  default = {}
}

# modules/network/outputs.tf
output "vpc_id"      { value = tencentcloud_vpc.this.id }
output "subnet_ids"  { value = { for k, v in tencentcloud_subnet.this : k => v.id } }
```

### 调用模块

```hcl
# envs/prod/main.tf
module "network" {
  source = "../../modules/network"

  name       = "${var.project_name}-${var.environment}"
  cidr_block = "10.2.0.0/16"
  tags       = local.common_tags

  subnets = {
    "public-a"  = { cidr = "10.2.1.0/24",  az = "ap-guangzhou-1" }
    "public-b"  = { cidr = "10.2.2.0/24",  az = "ap-guangzhou-2" }
    "private-a" = { cidr = "10.2.10.0/24", az = "ap-guangzhou-1" }
    "private-b" = { cidr = "10.2.11.0/24", az = "ap-guangzhou-2" }
  }
}

# 使用模块输出
module "compute" {
  source = "../../modules/compute"

  vpc_id    = module.network.vpc_id
  subnet_id = module.network.subnet_ids["private-a"]
  # ...
}
```

---

## 多环境管理

### terraform.tfvars 示例

```hcl
# envs/dev/terraform.tfvars（不提交 Git）
project_name = "myapp"
environment  = "dev"
region       = "ap-guangzhou"
owner        = "dev-team"

instance_type  = "SA3.MEDIUM4"
worker_count   = 1
```

```hcl
# envs/prod/terraform.tfvars（不提交 Git）
project_name = "myapp"
environment  = "prod"
region       = "ap-guangzhou"
owner        = "platform-team"

instance_type  = "SA3.LARGE8"
worker_count   = 4
```

### 环境变量注入敏感值

```bash
# dev
export TF_VAR_mysql_password="Dev@123456"
export TF_VAR_redis_password="Dev@123456"
terraform -chdir=envs/dev apply

# prod（CI/CD 中从 Secrets 注入）
export TF
