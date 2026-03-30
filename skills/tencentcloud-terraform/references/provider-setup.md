# Provider / Versions / Backend 标准配置

---

## versions.tf

```hcl
tf  {
  required_version = ">= 1.3.0"

  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.81.0"
    }
  }
}
```

---

## provider.tf

```hcl
provider "tencentcloud" {
  region = var.region
  # secret_id / secret_key 通过环境变量注入：
  # export TENCENTCLOUD_SECRET_ID=xxx
  # export TENCENTCLOUD_SECRET_KEY=xxx
}
```

---

## backend.tf（COS 远端 State）

```hcl
tf  {
  backend "cos" {
    region = "ap-guangzhou"
    bucket = "myapp-tfstate-1234567890"   # 格式: <name>-<appid>
    prefix = "myapp/prod/terraform.tfstate"
  }
}
```

> 使用 `scripts/gen_backend.py` 自动生成，避免手写路径出错。

---

## 认证方式

| 方式 | 说明 | 推荐场景 |
|------|------|---------|
| 环境变量 | `TENCENTCLOUD_SECRET_ID` + `TENCENTCLOUD_SECRET_KEY` | CI/CD、本地开发 |
| `~/.tencentcloud/credentials` | 本地配置文件 | 个人开发机 |
| CAM 角色（CVM/TKE 绑定） | 无需密钥 | 云上 Runner |

```bash
# 推荐：环境变量方式
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"
export TENCENTCLOUD_REGION="ap-guangzhou"
tf init
```

---

## 常用地域代码

| 地域 | 代码 |
|------|------|
| 广州 | `ap-guangzhou` |
| 上海 | `ap-shanghai` |
| 北京 | `ap-beijing` |
| 成都 | `ap-chengdu` |
| 香港 | `ap-hongkong` |
| 新加坡 | `ap-singapore` |
| 首尔 | `ap-seoul` |
| 东京 | `ap-tokyo` |