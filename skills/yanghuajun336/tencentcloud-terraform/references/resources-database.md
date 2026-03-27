# 数据库资源（MySQL / Redis）

---

## MySQL

```hcl
resource "tencentcloud_mysql_instance" "main" {
  instance_name     = "${local.name_prefix}-mysql"
  mem_size          = 4000    # MB
  volume_size       = 100     # GB
  engine_version    = "8.0"
  root_password     = var.mysql_password   # sensitive，通过 TF_VAR_mysql_password 注入
  availability_zone = var.availability_zones[0]
  vpc_id            = var.vpc_id
  subnet_id         = var.subnet_ids["private-a"]
  security_groups   = [var.sg_id]
  project_id        = 0
  pay_type          = 1   # 1=按量计费，0=包年包月

  tags = local.common_tags
}
```

---

## Redis

```hcl
resource "tencentcloud_redis_instance" "main" {
  name              = "${local.name_prefix}-redis"
  type_id           = 6       # 6=标准版，4=集群版
  redis_version     = "5.0"
  mem_size          = 1024    # MB
  password          = var.redis_password   # sensitive
  availability_zone = var.availability_zones[0]
  vpc_id            = var.vpc_id
  subnet_id         = var.subnet_ids["private-a"]
  security_groups   = [var.sg_id]
  port              = 6379

  tags = local.common_tags
}
```

---

## Outputs

```hcl
output "mysql_host"     { value = tencentcloud_mysql_instance.main.intranet_ip }
output "mysql_port"     { value = tencentcloud_mysql_instance.main.intranet_port }
output "redis_host"     { value = tencentcloud_redis_instance.main.ip }
output "redis_port"     { value = tencentcloud_redis_instance.main.port }
```
