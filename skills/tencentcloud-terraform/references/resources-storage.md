# 存储资源（COS / CFS）

---

## COS 对象存储

### Bucket

```hcl
resource "tencentcloud_cos_bucket" "main" {
  bucket = "${local.name_prefix}-${data.tencentcloud_user_info.current.app_id}"
  acl    = "private"
  region = var.region

  versioning_enable = false

  lifecycle_rules {
    filter_prefix = "logs/"
    expiration {
      days = 90
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }

  tags = local.common_tags
}

data "tencentcloud_user_info" "current" {}
```

### 上传对象（示例）

```hcl
resource "tencentcloud_cos_bucket_object" "config" {
  bucket       = tencentcloud_cos_bucket.main.bucket
  key          = "configs/app.json"
  content      = jsonencode({ env = var.environment })
  content_type = "application/json"
}
```

### Outputs

```hcl
output "cos_bucket_name" { value = tencentcloud_cos_bucket.main.bucket }
output "cos_bucket_url"  { value = "https://${tencentcloud_cos_bucket.main.bucket}.cos.${var.region}.myqcloud.com" }
```

---

## CFS 文件存储

### CFS 文件系统

```hcl
resource "tencentcloud_cfs_file_system" "main" {
  name              = "${local.name_prefix}-cfs"
  availability_zone = var.availability_zones[0]
  access_group_id   = tencentcloud_cfs_access_group.main.id
  protocol          = "NFS"           # NFS 或 CIFS
  storage_type      = "SD"            # SD=标准存储, HP=高性能存储
  vpc_id            = var.vpc_id
  subnet_id         = var.subnet_ids["private-a"]

  tags = local.common_tags
}
```

### CFS 权限组

```hcl
resource "tencentcloud_cfs_access_group" "main" {
  name        = "${local.name_prefix}-cfs-ag"
  description = "CFS 权限组 for ${var.environment}"
}

resource "tencentcloud_cfs_access_rule" "allow_vpc" {
  access_group_id = tencentcloud_cfs_access_group.main.id
  auth_client_ip  = var.vpc_cidr      # 允许整个 VPC CIDR 访问
  priority        = 1
  rw_permission   = "RWP"             # RWP=读写, ROP=只读
  user_permission = "no_squash"
}
```

### Outputs

```hcl
output "cfs_id"          { value = tencentcloud_cfs_file_system.main.id }
output "cfs_mount_ip"    { value = tencentcloud_cfs_file_system.main.mount_ip }
# 挂载命令: mount -t nfs -o vers=4 <mount_ip>:/ /mnt/cfs
```

### CVM 挂载 CFS（user_data 示例）

```hcl
locals {
  cfs_mount_script = <<-EOT
    #!/bin/bash
    yum install -y nfs-utils
    mkdir -p /mnt/cfs
    mount -t nfs -o vers=4,noresvport ${tencentcloud_cfs_file_system.main.mount_ip}:/ /mnt/cfs
    echo "${tencentcloud_cfs_file_system.main.mount_ip}:/ /mnt/cfs nfs vers=4,noresvport 0 0" >> /etc/fstab
  EOT
}
```

---

## 安全注意事项

- CFS 应放在**私有子网**，不对公网暴露
- 权限组 `auth_client_ip` 收敛到 VPC CIDR，避免 `0.0.0.0/0`
- COS Bucket ACL 默认 `private`，按需开启 CDN 或 Website 托管
