# Provider 配置参考

> 目录
> - [完整 Provider 配置](#完整-provider-配置)
> - [versions.tf 模板](#versionstf-模板)
> - [多 Region（Provider Alias）](#多-region)
> - [跨账号 AssumeRole](#跨账号-assumerole)
> - [企业代理配置](#企业代理配置)
> - [环境变量一览](#环境变量一览)
> - [Provider 版本锁定策略](#provider-版本锁定策略)

---

## 完整 Provider 配置

`versions.tf`（每个项目必须有此文件）：

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = "~> 1.81.0"
      # ~> 1.81.0 表示允许 1.81.x 的 patch 更新，不允许 minor/major 升级
      # 团队协作必须锁定版本，避免成员间 provider 版本不一致
    }
  }
}

provider "tencentcloud" {
  region = var.region

  # 认证优先级（从高到低）：
  # 1. provider 块内 secret_id / secret_key 字段（不推荐，禁止提交 Git）
  # 2. 环境变量 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY
  # 3. CAM 角色（在腾讯云 CVM / TKE 节点上运行时自动获取临时凭证）
  #
  # 生产环境统一使用环境变量，本地开发也用环境变量
}
```

配套 `variables.tf` 中的 region 变量：

```hcl
variable "region" {
  description = "腾讯云地域，例如 ap-guangzhou、ap-beijing、ap-shanghai"
  type        = string
  default     = "ap-guangzhou"

  validation {
    condition = contains([
      "ap-guangzhou", "ap-beijing", "ap-shanghai", "ap-chengdu",
      "ap-nanjing", "ap-hongkong", "ap-singapore", "ap-bangkok",
      "ap-jakarta", "ap-seoul", "ap-tokyo", "na-siliconvalley",
      "na-ashburn", "eu-frankfurt", "eu-moscow"
    ], var.region)
    error_message = "请使用合法的腾讯云地域代码。"
  }
}
```

---

## 多 Region

需要同时在多个地域创建资源时使用 Provider Alias：

```hcl
# versions.tf 中的主 provider 配置保持不变
provider "tencentcloud" {
  region = "ap-guangzhou"
}

# 声明别名 provider
provider "tencentcloud" {
  alias  = "beijing"
  region = "ap-beijing"
}

provider "tencentcloud" {
  alias  = "singapore"
  region = "ap-singapore"
}

# 资源指定 provider
resource "tencentcloud_vpc" "gz_vpc" {
  # 使用默认 provider（ap-guangzhou）
  name       = "gz-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "tencentcloud_vpc" "bj_vpc" {
  provider   = tencentcloud.beijing  # 显式指定
  name       = "bj-vpc"
  cidr_block = "10.1.0.0/16"
}

# 模块也可以传入 provider
module "beijing_network" {
  source = "./modules/network"
  providers = {
    tencentcloud = tencentcloud.beijing
  }
  cidr_block = "10.1.0.0/16"
}
```

---

## 跨账号 AssumeRole

企业多账号管理场景，主账号扮演子账号角色：

```hcl
# 方式一：provider 块中配置
provider "tencentcloud" {
  region = "ap-guangzhou"
  # 主账号凭证通过环境变量注入

  assume_role {
    role_arn         = "qcs::cam::uin/123456789:roleName/TerraformRole"
    session_name     = "terraform-${var.environment}"
    session_duration = 7200   # 秒，最长 43200（12小时）
    # policy           = ""   # 可选：进一步限制临时凭证权限
  }
}

# 方式二：多账号场景，不同 provider alias 对应不同子账号
provider "tencentcloud" {
  alias  = "prod_account"
  region = "ap-guangzhou"

  assume_role {
    role_arn     = "qcs::cam::uin/PROD_ACCOUNT_UIN:roleName/TerraformRole"
    session_name = "terraform-prod"
  }
}

provider "tencentcloud" {
  alias  = "dev_account"
  region = "ap-guangzhou"

  assume_role {
    role_arn     = "qcs::cam::uin/DEV_ACCOUNT_UIN:roleName/TerraformRole"
    session_name = "terraform-dev"
  }
}
```

CAM 角色信任策略配置（在腾讯云控制台设置）：

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "principal": {
        "qcs": ["qcs::cam::uin/<主账号UIN>:root"]
      },
      "action": ["name/sts:AssumeRole"]
    }
  ]
}
```

---

## 企业代理配置

在有网络代理的企业环境中：

```bash
# 全局代理（推荐）
export HTTPS_PROXY="http://proxy.company.com:8080"
export HTTP_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,169.254.169.254"  # 保留元数据服务

# 或在 Provider 中指定（仅影响 tencentcloud API 调用）
```

```hcl
provider "tencentcloud" {
  region   = var.region
  protocol = "https"
  # 腾讯云 Provider 会自动读取 HTTPS_PROXY 环境变量
}
```

---

## 环境变量一览

| 变量名 | 说明 | 必填 | 示例 |
|--------|------|------|------|
| `TENCENTCLOUD_SECRET_ID` | CAM 密钥 ID | ✅ | `AKID9HH4OpqLJ5f6LPr4iIm5GF2s` |
| `TENCENTCLOUD_SECRET_KEY` | CAM 密钥 Key | ✅ | `72pQp14tWKUglrnX5RbaNEtN` |
| `TENCENTCLOUD_REGION` | 默认地域 | ✅ | `ap-guangzhou` |
| `TENCENTCLOUD_APPID` | 账号 AppId | COS 必须 | `1234567890` |
| `TENCENTCLOUD_SECURITY_TOKEN` | 临时会话 Token | STS 时必须 | - |
| `TF_LOG` | Terraform 日志级别 | 调试用 | `DEBUG`/`INFO`/`WARN` |
| `TF_LOG_PATH` | 日志写入文件 | 调试用 | `/tmp/tf.log` |
| `TF_VAR_<name>` | 覆盖同名变量 | 按需 | `TF_VAR_db_password=xxx` |
| `HTTPS_PROXY` | 企业代理 | 企业网络 | `http://proxy:8080` |

---

## Provider 版本锁定策略

```hcl
# 版本约束语法说明
version = "= 1.81.5"    # 精确锁定，最严格
version = "~> 1.81.0"   # 允许 1.81.x，推荐
version = "~> 1.81"     # 允许 1.81.x 和 1.82.x，较宽松
version = ">= 1.81.0"   # 下限约束，不推荐（可能引入 breaking change）
```

**最佳实践：** 使用 `~> 1.81.0`，并将 `.terraform.lock.hcl` 提交到 Git，确保所有团队成员和 CI/CD 使用完全一致的 Provider 版本。

升级 Provider：

```bash
# 查看当前版本
terraform version

# 升级到约束范围内的最新版
terraform init -upgrade

# 查看 lock 文件中的实际版本
cat .terraform.lock.hcl

# 验证升级后无 breaking change
terraform plan  # 应无意外变更
```

检查新版本 changelog：https://github.com/tencentcloudstack/terraform-provider-tencentcloud/releases
