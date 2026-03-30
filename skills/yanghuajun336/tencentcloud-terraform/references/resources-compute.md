# 计算资源参考（CVM / 密钥对 / 弹性伸缩）

> 目录
> - [查询镜像](#查询镜像)
> - [查询实例规格](#查询实例规格)
> - [CVM 实例（单个）](#cvm-实例)
> - [CVM 实例（多个，count vs for_each）](#多实例部署)
> - [SSH 密钥对](#ssh-密钥对)
> - [云盘（CBS）](#云盘)
> - [弹性伸缩 AS](#弹性伸缩-as)
> - [instance_type 规格速查](#instance_type-规格速查)

---

## 查询镜像

```hcl
# 查询腾讯云公共镜像（Ubuntu 22.04）
data "tencentcloud_images" "ubuntu22" {
  image_type       = ["PUBLIC_IMAGE"]
  os_name          = "ubuntu"
  image_name_regex = "Ubuntu Server 22.04 LTS"
  # 不指定 image_name_regex 会返回所有 ubuntu 镜像，取 .0 为最新
}

# 腾讯 TLinux（生产推荐，性能更好）
data "tencentcloud_images" "tlinux" {
  image_type       = ["PUBLIC_IMAGE"]
  os_name          = "tlinux"
  image_name_regex = "TencentOS Server 3.1"
}

# CentOS 7（不推荐新项目，已 EOL）
data "tencentcloud_images" "centos7" {
  image_type       = ["PUBLIC_IMAGE"]
  os_name          = "centos"
  image_name_regex = "CentOS 7.9"
}

# 输出镜像 ID（调试用）
output "ubuntu_image_id" {
  value = data.tencentcloud_images.ubuntu22.images.0.image_id
}
```

---

## 查询实例规格

```hcl
# 查询指定可用区支持的实例规格
data "tencentcloud_instance_types" "available" {
  # 按 CPU/内存过滤
  cpu_core_count = 4
  memory_size    = 8

  # 按可用区过滤
  availability_zone = "${var.region}-1"

  # 排除不支持的
  exclude_sold_out = true
}
```

---

## CVM 实例

```hcl
resource "tencentcloud_instance" "web" {
  # ── 基本信息 ──────────────────────────────────────────────
  instance_name     = "${var.project_name}-${var.environment}-web"
  availability_zone = "${var.region}-1"
  image_id          = data.tencentcloud_images.ubuntu22.images.0.image_id
  instance_type     = var.instance_type   # 例：SA3.MEDIUM4

  # ── 网络 ─────────────────────────────────────────────────
  vpc_id    = tencentcloud_vpc.main.id
  subnet_id = tencentcloud_subnet.private_a.id

  # 公网带宽（0 = 不分配公网 IP，生产推荐用 CLB，CVM 不分配公网）
  internet_max_bandwidth_out = 0
  # internet_charge_type = "TRAFFIC_POSTPAID_BY_HOUR"  # 需要公网时设置

  # ── 安全组 ────────────────────────────────────────────────
  security_groups = [tencentcloud_security_group.web.id]

  # ── 磁盘 ──────────────────────────────────────────────────
  system_disk_type = "CLOUD_PREMIUM"   # CLOUD_PREMIUM / CLOUD_SSD / CLOUD_HSSD
  system_disk_size = 50                # GB

  # 数据盘（可选，多个）
  data_disks {
    data_disk_type = "CLOUD_SSD"
    data_disk_size = 100
    # data_disk_snapshot_id = ""   # 从快照恢复
    delete_with_instance = true   # 随实例销毁
  }

  # ── 登录认证（key_ids 和 password 二选一，强烈推荐 key_ids）──
  key_ids = [tencentcloud_key_pair.deploy.id]
  # password = var.instance_password  # 敏感变量，不推荐

  # ── 初始化脚本（user_data）────────────────────────────────
  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e
    apt-get update -y
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
    echo "instance: ${var.project_name}-${var.environment}" > /var/www/html/index.html
  EOF
  )

  # ── 实例计费 ──────────────────────────────────────────────
  # instance_charge_type = "POSTPAID_BY_HOUR"   # 默认，按量
  # instance_charge_type = "PREPAID"             # 包年包月
  # instance_charge_type_prepaid_period = 1      # 月数
  # instance_charge_type_prepaid_renew_flag = "NOTIFY_AND_AUTO_RENEW"

  # ── 标签 ──────────────────────────────────────────────────
  tags = merge(local.common_tags, {
    "Role" = "web"
  })

  # ── 生命周期 ──────────────────────────────────────────────
  lifecycle {
    # 镜像更新时不触发重建（通常不希望因镜像 ID 变化重建生产实例）
    ignore_changes  = [image_id, user_data]
    # 生产环境防止误 destroy
    prevent_destroy = var.environment == "prod" ? true : false
  }
}
```

---

## 多实例部署

### 推荐：for_each（稳定标识符，删除中间元素不影响其他）

```hcl
variable "web_instances" {
  type = map(object({
    az     = string
    subnet = string
  }))
  default = {
    "web-01" = { az = "ap-guangzhou-1", subnet = "private_a" }
    "web-02" = { az = "ap-guangzhou-2", subnet = "private_b" }
    "web-03" = { az = "ap-guangzhou-3", subnet = "private_a" }
  }
}

resource "tencentcloud_instance" "web" {
  for_each = var.web_instances

  instance_name     = "${var.project_name}-${var.environment}-${each.key}"
  availability_zone = each.value.az
  image_id          = data.tencentcloud_images.ubuntu22.images.0.image_id
  instance_type     = var.instance_type

  vpc_id    = tencentcloud_vpc.main.id
  subnet_id = tencentcloud_subnet.app[each.value.subnet].id

  system_disk_type = "CLOUD_PREMIUM"
  system_disk_size = 50
  key_ids          = [tencentcloud_key_pair.deploy.id]
  security_groups  = [tencentcloud_security_group.web.id]
  internet_max_bandwidth_out = 0

  tags = merge(local.common_tags, { "Name" = each.key })

  lifecycle {
    ignore_changes = [image_id]
  }
}
```

### count（同质资源，简单场景）

```hcl
resource "tencentcloud_instance" "worker" {
  count = var.worker_count   # 例：3

  instance_name     = format("%s-%s-worker-%02d", var.project_name, var.environment, count.index + 1)
  # 跨可用区分布：count.index % length(var.availability_zones)
  availability_zone = var.availability_zones[count.index % length(var.availability_zones)]
  image_id          = data.tencentcloud_images.ubuntu22.images.0.image_id
  instance_type     = var.worker_instance_type

  vpc_id    = tencentcloud_vpc.main.id
  subnet_id = tencentcloud_subnet.app[count.index % 2 == 0 ? "a" : "b"].id

  system_disk_type = "CLOUD_PREMIUM"
  system_disk_size = 100
  key_ids          = [tencentcloud_key_pair.deploy.id]
  security_groups  = [tencentcloud_security_group.worker.id]
  internet_max_bandwidth_out = 0

  tags = merge(local.common_tags, { "Index" = tostring(count.index) })

  lifecycle {
    ignore_changes = [image_id]
  }
}
```

---

## SSH 密钥对

```hcl
# 方式一：使用本地已有公钥
resource "tencentcloud_key_pair" "deploy" {
  key_name   = "${var.project_name}-${var.environment}-deploy"
  public_key = var.ssh_public_key   # 通过变量传入，不硬编码

  tags = local.common_tags
}

# 方式二：读取文件（本地 terraform apply 时）
resource "tencentcloud_key_pair" "deploy" {
  key_name   = "${var.project_name}-${var.environment}-deploy"
  public_key = file("~/.ssh/id_rsa.pub")
}

# CI/CD 中：通过环境变量传入
# export TF_VAR_ssh_public_key="ssh-rsa AAAA..."
variable "ssh_public_key" {
  description = "SSH 公钥，通过 TF_VAR_ssh_public_key 环境变量注入"
  type        = string
  sensitive   = false
}
```

---

## 云盘（CBS）

单独管理的云盘（与实例分离，适合数据盘）：

```hcl
# 创建独立云盘
resource "tencentcloud_cbs_storage" "data" {
  storage_name      = "${var.project_name}-${var.environment}-data-disk"
  storage_type      = "CLOUD_SSD"
  storage_size      = 200   # GB
  availability_zone = "${var.region}-1"
  project_id        = 0
  encrypt           = false

  tags = local.common_tags
}

# 挂载到实例
resource "tencentcloud_cbs_storage_attachment" "data" {
  storage_id  = tencentcloud_cbs_storage.data.id
  instance_id = tencentcloud_instance.web.id
}

# 云盘快照
resource "tencentcloud_snapshot" "data_backup" {
  storage_id    = tencentcloud_cbs_storage.data.id
  snapshot_name = "${var.project_name}-data-snapshot"
}
```

---

## 弹性伸缩 AS

```hcl
# 启动配置（相当于 AWS Launch Template）
resource "tencentcloud_as_scaling_config" "web" {
  configuration_name = "${var.project_name}-${var.environment}-web-lc"
  image_id           = data.tencentcloud_images.ubuntu22.images.0.image_id
  instance_types     = [var.instance_type]
  project_id         = 0

  system_disk {
    disk_type = "CLOUD_PREMIUM"
    disk_size = 50
  }

  data_disk {
    disk_type = "CLOUD_PREMIUM"
    disk_size = 100
  }

  key_ids            = [tencentcloud_key_pair.deploy.id]
  security_group_ids = [tencentcloud_security_group.web.id]

  internet_charge_type       = "TRAFFIC_POSTPAID_BY_HOUR"
  internet_max_bandwidth_out = 0   # 不分配公网 IP，通过 CLB 访问

  # 实例初始化脚本
  user_data = base64encode(file("${path.module}/scripts/init.sh"))

  # 多实例类型（按顺序尝试，前一种不可用时使用下一种）
  instance_types = ["SA3.MEDIUM4", "SA3.LARGE8", "S5.MEDIUM4"]
}

# 伸缩组
resource "tencentcloud_as_scaling_group" "web" {
  scaling_group_name = "${var.project_name}-${var.environment}-web-asg"
  configuration_id   = tencentcloud_as_scaling_config.web.id
  max_size           = var.asg_max_size     # 例：10
  min_size           = var.asg_min_size     # 例：2
  desired_capacity   = var.asg_desired      # 例：3
  project_id         = 0

  vpc_id     = tencentcloud_vpc.main.id
  subnet_ids = [
    tencentcloud_subnet.app["a"].id,
    tencentcloud_subnet.app["b"].id,
  ]

  # 绑定 CLB
  load_balancer_ids = [tencentcloud_clb_instance.web.id]

  # 健康检查宽限期（实例启动后多少秒开始健康检查）
  health_check_type    = "CLB"   # EC2 / CLB
  lb_health_check_grace_period = 300

  # 扩缩容策略
  retry_policy         = "INCREMENTAL_INTERVALS"
  termination_policies = ["NEWEST_INSTANCE"]

  tags = local.common_tags
}

# 扩容策略：CPU > 70% 触发
resource "tencentcloud_as_scale_out_attachment" "cpu_high" {
  scaling_group_id = tencentcloud_as_scaling_group.web.id

  # 使用告警触发策略
}

# 定时任务（业务低峰期缩容）
resource "tencentcloud_as_schedule" "scale_down_night" {
  scaling_group_id    = tencentcloud_as_scaling_group.web.id
  schedule_action_name = "scale-down-night"
  max_size            = 4
  min_size            = 1
  desired_capacity    = 1
  start_time          = "2026-01-01T22:00:00+08:00"
  recurrence          = "0 22 * * *"   # 每天 22:00
  end_time            = "2030-12-31T22:00:00+08:00"
}
```

---

## instance_type 规格速查

| 规格族 | 示例规格 | vCPU | 内存 | 适用场景 |
|--------|---------|------|------|---------|
| 标准型 SA3 | `SA3.SMALL1` | 1 | 1G | 极低负载 |
| 标准型 SA3 | `SA3.MEDIUM4` | 2 | 4G | Web/API |
| 标准型 SA3 | `SA3.LARGE8` | 4 | 8G | 中等负载 |
| 标准型 SA3 | `SA3.2XLARGE16` | 8 | 16G | 高负载 |
| 标准型 SA3 | `SA3.4XLARGE32` | 16 | 32G | 大型服务 |
| 内存型 M6 | `M6.MEDIUM16` | 4 | 16G | Redis/DB |
| 内存型 M6 | `M6.LARGE32` | 8 | 32G | 内存密集 |
| 计算型 C3 | `C3.LARGE8` | 4 | 8G | 计算密集 |
| 高 IO 型 IT5 | `IT5.LARGE8` | 4 | 8G | 本地 SSD |
| GPU 型 GN10X | `GN10X.2XLARGE40` | 8 | 40G | AI/ML 推理 |

完整规格列表：https://cloud.tencent.com/document/product/213/11518
