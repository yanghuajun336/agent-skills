## 🌐 DNSPod 腾讯云 DNS 解析

### 支持的资源

| 资源名 | 说明 |
|---|---|
| `tencentcloud_dnspod_domain_instance` | 创建域名 |
| `tencentcloud_dnspod_record` | 添加 DNS 解析记录 |
| `tencentcloud_dnspod_record_group` | 创建记录分组 |
| `tencentcloud_dnspod_custom_line` | 自定义线路 |
| `tencentcloud_dnspod_line_group` | 线路分组 |
| `tencentcloud_dnspod_domain_alias` | 域名别名 |
| `tencentcloud_dnspod_domain_lock` | 域名锁定 |
| `tencentcloud_dnspod_snapshot_config` | 快照配置 |
| `tencentcloud_dnspod_package_order` | 套餐购买 |
| `tencentcloud_dnspod_modify_domain_owner_operation` | 转移域名 |

### 典型示例

```hcl
# 添加域名
resource "tencentcloud_dnspod_domain_instance" "example" {
  domain  = "example.com"
  remark  = "my main domain"
  status  = "ENABLE"
}

# 添加 A 记录
resource "tencentcloud_dnspod_record" "a_record" {
  domain      = tencentcloud_dnspod_domain_instance.example.domain
  sub_domain  = "www"
  record_type = "A"
  record_line = "默认"
  value       = "1.2.3.4"
  ttl         = 600
}

# 添加 CNAME 记录
resource "tencentcloud_dnspod_record" "cname_record" {
  domain      = tencentcloud_dnspod_domain_instance.example.domain
  sub_domain  = "cdn"
  record_type = "CNAME"
  record_line = "默认"
  value       = "example.cdn.dnsv1.com"
  ttl         = 600
}

# 添加 MX 记录
resource "tencentcloud_dnspod_record" "mx_record" {
  domain      = tencentcloud_dnspod_domain_instance.example.domain
  sub_domain  = "@"
  record_type = "MX"
  record_line = "默认"
  value       = "mail.example.com"
  mx          = 10
  ttl         = 600
}

# 自定义线路（按 IP 段分流）
resource "tencentcloud_dnspod_custom_line" "example" {
  domain    = tencentcloud_dnspod_domain_instance.example.domain
  name      = "office-network"
  area      = "192.168.0.0/24"
}

# 记录分组
resource "tencentcloud_dnspod_record_group" "example" {
  domain     = tencentcloud_dnspod_domain_instance.example.domain
  group_name = "production"
}

# 域名快照配置
resource "tencentcloud_dnspod_snapshot_config" "example" {
  domain = tencentcloud_dnspod_domain_instance.example.domain
  period = "weekly"
}
```

### 激活场景关键词
- DNSPod / DNS 解析
- 添加 A 记录 / CNAME / MX / TXT 记录
- 域名解析管理
- 自定义线路 / 分区解析
- dnspod_record / dnspod_domain

---
