# 网络资源参考（VPC / 子网 / 安全组 / NAT / CLB）

> 目录
> - [VPC](#vpc)
> - [子网](#子网)
> - [安全组](#安全组)
> - [路由表](#路由表)
> - [NAT 网关](#nat-网关)
> - [弹性 IP（EIP）](#弹性-ip)
> - [VPN 网关](#vpn-网关)
> - [对等连接](#对等连接)
> - [CLB 负载均衡](#clb-负载均衡)
> - [完整三层网络示例](#完整三层网络示例)

---

## VPC

```hcl
resource "tencentcloud_vpc" "main" {
  name       = "${var.project_name}-${var.environment}-vpc"
  cidr_block = "10.0.0.0/16"

  # 开启组播（默认 false，通常不需要）
  is_multicast = false

  # 自定义 DNS（不填则使用腾讯云默认）
  dns_servers = ["183.60.83.19", "183.60.82.98"]

  tags = local.common_tags
}
```

**CIDR 规划建议：**

| 环境 | VPC CIDR | 用途说明 |
|------|----------|---------|
| dev | `10.0.0.0/16` | 开发环境 |
| staging | `10.1.0.0/16` | 预发布 |
| prod | `10.2.0.0/16` | 生产 |

各环境 VPC 不重叠，方便后续做对等连接。

---

## 子网

```hcl
# 公有子网（放 CLB、NAT Gateway、Bastion）
resource "tencentcloud_subnet" "public_a" {
  name              = "${var.project_name}-${var.environment}-public-a"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}-1"   # ap-guangzhou-1
  is_multicast      = false
  tags              = local.common_tags
}

resource "tencentcloud_subnet" "public_b" {
  name              = "${var.project_name}-${var.environment}-public-b"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}-2"
  tags              = local.common_tags
}

# 私有子网（放 CVM 应用层）
resource "tencentcloud_subnet" "private_a" {
  name              = "${var.project_name}-${var.environment}-private-a"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.region}-1"
  tags              = local.common_tags
}

resource "tencentcloud_subnet" "private_b" {
  name              = "${var.project_name}-${var.environment}-private-b"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.region}-2"
  tags              = local.common_tags
}

# 数据层子网（放 MySQL、Redis）
resource "tencentcloud_subnet" "data_a" {
  name              = "${var.project_name}-${var.environment}-data-a"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = "10.0.20.0/24"
  availability_zone = "${var.region}-1"
  tags              = local.common_tags
}
```

**可用区代码规律：** `<region>-1`，`<region>-2`，`<region>-3`，`<region>-4`（视地域实际可用区数量）。
`ap-guangzhou` 有 `-1` `-2` `-3` `-4` `-6` `-7`（注意没有 `-5`）。

---

## 安全组

### 方式一：lite_rule（简洁，推荐小型项目）

```hcl
resource "tencentcloud_security_group" "web" {
  name        = "${var.project_name}-${var.environment}-web-sg"
  description = "Web 服务器安全组，允许 80/443 入站"
  project_id  = 0
  tags        = local.common_tags
}

resource "tencentcloud_security_group_lite_rule" "web" {
  security_group_id = tencentcloud_security_group.web.id

  # 格式：POLICY#SOURCE#PORT#PROTOCOL
  # POLICY: ACCEPT / DROP
  # SOURCE: CIDR / 安全组 ID / 0.0.0.0/0
  # PORT: 端口号 / ALL
  # PROTOCOL: TCP / UDP / ICMP / ALL
  ingress = [
    "ACCEPT#0.0.0.0/0#80#TCP",
    "ACCEPT#0.0.0.0/0#443#TCP",
    "ACCEPT#10.0.0.0/8#22#TCP",   # 仅 VPC 内可 SSH
    "ACCEPT#0.0.0.0/0#ALL#ICMP",  # 允许 ping
    "DROP#0.0.0.0/0#ALL#ALL",
  ]

  egress = [
    "ACCEPT#0.0.0.0/0#ALL#ALL",
  ]
}
```

### 方式二：security_group_rule（精细，推荐生产）

```hcl
# 允许 HTTPS 入站
resource "tencentcloud_security_group_rule" "allow_https" {
  security_group_id = tencentcloud_security_group.web.id
  type              = "ingress"
  cidr_ip           = "0.0.0.0/0"
  ip_protocol       = "tcp"
  port_range        = "443"
  policy            = "ACCEPT"
  description       = "Allow HTTPS from internet"
}

# 允许同安全组内互访
resource "tencentcloud_security_group_rule" "allow_self" {
  security_group_id        = tencentcloud_security_group.web.id
  type                     = "ingress"
  source_sgid              = tencentcloud_security_group.web.id  # 引用自身
  ip_protocol              = "ALL"
  port_range               = "ALL"
  policy                   = "ACCEPT"
  description              = "Allow intra-sg communication"
}

# 允许从特定安全组访问（例如 CLB → Web）
resource "tencentcloud_security_group_rule" "from_clb" {
  security_group_id        = tencentcloud_security_group.web.id
  type                     = "ingress"
  source_sgid              = tencentcloud_security_group.clb.id
  ip_protocol              = "tcp"
  port_range               = "8080"
  policy                   = "ACCEPT"
  description              = "Allow from CLB security group"
}
```

---

## 路由表

```hcl
resource "tencentcloud_route_table" "private" {
  name   = "${var.project_name}-${var.environment}-private-rt"
  vpc_id = tencentcloud_vpc.main.id
  tags   = local.common_tags
}

# 私有子网默认路由指向 NAT
resource "tencentcloud_route_table_entry" "nat_default" {
  route_table_id         = tencentcloud_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  next_type              = "NAT"          # NAT/EIP/VPN/PEERCONN/CCN
  next_hub               = tencentcloud_nat_gateway.main.id
  description            = "Default route to NAT"
}

# 子网关联路由表
resource "tencentcloud_route_table_association" "private_a" {
  subnet_id      = tencentcloud_subnet.private_a.id
  route_table_id = tencentcloud_route_table.private.id
}
```

---

## NAT 网关

```hcl
# 先申请 EIP
resource "tencentcloud_eip" "nat" {
  name       = "${var.project_name}-${var.environment}-nat-eip"
  tags       = local.common_tags
}

resource "tencentcloud_nat_gateway" "main" {
  name   = "${var.project_name}-${var.environment}-nat"
  vpc_id = tencentcloud_vpc.main.id

  # 带宽上限 Mbps：100/200/500/1000
  bandwidth = 100

  # 最大并发连接数：1000000/3000000/10000000
  max_concurrent = 1000000

  # 绑定的 EIP（可以多个）
  assigned_eip_set = [tencentcloud_eip.nat.public_ip]

  tags = local.common_tags
}
```

---

## 弹性 IP

```hcl
# 申请 EIP
resource "tencentcloud_eip" "web" {
  name              = "${var.project_name}-${var.environment}-web-eip"
  internet_charge_type       = "TRAFFIC_POSTPAID_BY_HOUR"
  internet_max_bandwidth_out = 100
  tags              = local.common_tags
}

# 绑定到 CVM 实例
resource "tencentcloud_eip_association" "web" {
  eip_id      = tencentcloud_eip.web.id
  instance_id = tencentcloud_instance.web.id
}
```

---

## VPN 网关

用于连接本地 IDC 与腾讯云 VPC：

```hcl
resource "tencentcloud_vpn_gateway" "main" {
  name      = "${var.project_name}-${var.environment}-vpngw"
  vpc_id    = tencentcloud_vpc.main.id
  bandwidth = 5   # Mbps

  # prepaid（包年包月）或 postpaid（按量）
  charge_type = "POSTPAID_BY_HOUR"
  tags        = local.common_tags
}

resource "tencentcloud_vpn_customer_gateway" "idc" {
  name       = "idc-cgw"
  public_ip_address = "203.0.113.1"   # IDC 公网 IP
  tags       = local.common_tags
}

resource "tencentcloud_vpn_connection" "main" {
  name                = "${var.project_name}-vpn-conn"
  vpc_id              = tencentcloud_vpc.main.id
  vpn_gateway_id      = tencentcloud_vpn_gateway.main.id
  customer_gateway_id = tencentcloud_vpn_customer_gateway.idc.id
  pre_share_key       = var.vpn_psk   # 预共享密钥，用 sensitive variable

  ike_proto_encry_algorithm  = "3DES-CBC"
  ike_proto_authen_algorithm = "MD5"
  ike_exchange_mode          = "MAIN"
  ike_local_identity         = "ADDRESS"
  ike_remote_identity        = "ADDRESS"
  ike_dh_group_name          = "GROUP2"
  ike_sa_lifetime_seconds    = 86400

  ipsec_encrypt_algorithm   = "3DES-CBC"
  ipsec_integrity_algorithm = "MD5"
  ipsec_sa_lifetime_seconds = 3600
  ipsec_pfs_dh_group        = "NULL"

  security_group_policy {
    local_cidr_block  = "10.0.0.0/16"
    remote_cidr_block = ["192.168.0.0/24"]
  }
}
```

---

## 对等连接

连接同账号或跨账号的两个 VPC：

```hcl
# 同账号、同地域对等连接
resource "tencentcloud_vpc_peering_connection" "main" {
  name           = "prod-to-shared-peering"
  vpc_id         = tencentcloud_vpc.prod.id
  peer_vpc_id    = tencentcloud_vpc.shared.id
  peer_region    = var.region   # 同地域可省略

  tags = local.common_tags
}

# 对等连接创建后，双向路由都需要添加
resource "tencentcloud_route_table_entry" "to_shared" {
  route_table_id         = tencentcloud_route_table.prod_private.id
  destination_cidr_block = "10.10.0.0/16"   # shared VPC CIDR
  next_type              = "PEERCONN"
  next_hub               = tencentcloud_vpc_peering_connection.main.id
}
```

---

## CLB 负载均衡

### 公网 CLB

```hcl
resource "tencentcloud_clb_instance" "web" {
  clb_name     = "${var.project_name}-${var.environment}-web-clb"
  network_type = "OPEN"   # OPEN=公网，INTERNAL=内网
  project_id   = 0
  vpc_id       = tencentcloud_vpc.main.id

  # 公网带宽计费（OPEN 类型需要）
  internet_charge_type       = "BANDWIDTH_POSTPAID_BY_HOUR"
  internet_bandwidth_max_out = 10   # Mbps

  security_groups = [tencentcloud_security_group.clb.id]
  tags            = local.common_tags
}

# HTTP 监听器
resource "tencentcloud_clb_listener" "http" {
  clb_id        = tencentcloud_clb_instance.web.id
  listener_name = "http-80"
  port          = 80
  protocol      = "HTTP"
}

# HTTPS 监听器（需要 SSL 证书）
resource "tencentcloud_clb_listener" "https" {
  clb_id           = tencentcloud_clb_instance.web.id
  listener_name    = "https-443"
  port             = 443
  protocol         = "HTTPS"
  certificate_ssl_mode = "UNIDIRECTIONAL"
  certificate_id       = var.ssl_cert_id   # 从证书服务获取
}

# 转发规则（七层）
resource "tencentcloud_clb_listener_rule" "api" {
  clb_id      = tencentcloud_clb_instance.web.id
  listener_id = tencentcloud_clb_listener.https.listener_id
  domain      = "api.example.com"
  url         = "/"
  scheduler   = "WRR"   # WRR/IP_HASH/LEAST_CONN

  health_check_switch            = true
  health_check_interval_time     = 5
  health_check_health_num        = 2
  health_check_unhealth_num      = 2
  health_check_http_code         = 2   # 2xx 视为健康
  health_check_http_path         = "/health"
  health_check_http_domain       = "api.example.com"
  health_check_http_method       = "GET"

  session_expire_time = 0   # 0=不开启会话保持
}

# 后端绑定
resource "tencentcloud_clb_attachment" "web" {
  clb_id      = tencentcloud_clb_instance.web.id
  listener_id = tencentcloud_clb_listener.https.listener_id
  rule_id     = tencentcloud_clb_listener_rule.api.rule_id

  dynamic "targets" {
    for_each = tencentcloud_instance.web[*]
    content {
      instance_id = targets.value.id
      port        = 8080
      weight      = 10
    }
  }
}
```

### 内网 CLB（微服务场景）

```hcl
resource "tencentcloud_clb_instance" "internal" {
  clb_name     = "${var.project_name}-${var.environment}-internal-clb"
  network_type = "INTERNAL"
  project_id   = 0
  vpc_id       = tencentcloud_vpc.main.id
  subnet_id    = tencentcloud_subnet.private_a.id   # 内网 CLB 需要指定子网
  tags         = local.common_tags
}
```

---

## 完整三层网络示例

生产级三层网络架构（公网层 / 应用层 / 数据层）完整模板：

```hcl
# ── VPC ──────────────────────────────────────────────────────
resource "tencentcloud_vpc" "main" {
  name       = "${var.project_name}-${var.environment}-vpc"
  cidr_block = "10.0.0.0/16"
  tags       = local.common_tags
}

# ── 公网子网（CLB、NAT）───────────────────────────────────────
resource "tencentcloud_subnet" "public" {
  for_each = {
    "a" = { cidr = "10.0.1.0/24", az = "${var.region}-1" }
    "b" = { cidr = "10.0.2.0/24", az = "${var.region}-2" }
  }
  name              = "${var.project_name}-${var.environment}-public-${each.key}"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = local.common_tags
}

# ── 应用子网（CVM、TKE Node）─────────────────────────────────
resource "tencentcloud_subnet" "app" {
  for_each = {
    "a" = { cidr = "10.0.10.0/24", az = "${var.region}-1" }
    "b" = { cidr = "10.0.11.0/24", az = "${var.region}-2" }
  }
  name              = "${var.project_name}-${var.environment}-app-${each.key}"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = local.common_tags
}

# ── 数据子网（MySQL、Redis）──────────────────────────────────
resource "tencentcloud_subnet" "data" {
  for_each = {
    "a" = { cidr = "10.0.20.0/24", az = "${var.region}-1" }
    "b" = { cidr = "10.0.21.0/24", az = "${var.region}-2" }
  }
  name              = "${var.project_name}-${var.environment}-data-${each.key}"
  vpc_id            = tencentcloud_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags              = local.common_tags
}

# ── EIP + NAT ────────────────────────────────────────────────
resource "tencentcloud_eip" "nat" {
  name = "${var.project_name}-${var.environment}-nat-eip"
  tags = local.common_tags
}

resource "tencentcloud_nat_gateway" "main" {
  name             = "${var.project_name}-${var.environment}-nat"
  vpc_id           = tencentcloud_vpc.main.id
  bandwidth        = 100
  max_concurrent   = 1000000
  assigned_eip_set = [tencentcloud_eip.nat.public_ip]
  tags             = local.common_tags
}

# ── 私有路由表 → NAT ─────────────────────────────────────────
resource "tencentcloud_route_table" "private" {
  name   = "${var.project_name}-${var.environment}-private-rt"
  vpc_id = tencentcloud_vpc.main.id
  tags   = local.common_tags
}

resource "tencentcloud_route_table_entry" "nat_default" {
  route_table_id         = tencentcloud_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  next_type              = "NAT"
  next_hub               = tencentcloud_nat_gateway.main.id
}

# 应用子网和数据子网都关联私有路由表
resource "tencentcloud_route_table_association" "app" {
  for_each       = tencentcloud_subnet.app
  subnet_id      = each.value.id
  route_table_id = tencentcloud_route_table.private.id
}

resource "tencentcloud_route_table_association" "data" {
  for_each       = tencentcloud_subnet.data
  subnet_id      = each.value.id
  route_table_id = tencentcloud_route_table.private.id
}
```
