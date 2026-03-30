# TKE 集群 / 节点池

---

## TKE 集群

```hcl
resource "tencentcloud_kubernetes_cluster" "main" {
  cluster_name        = "${local.name_prefix}-tke"
  cluster_version     = "1.28.3"
  cluster_cidr        = "172.16.0.0/16"
  service_cidr        = "10.96.0.0/16"
  vpc_id              = var.vpc_id
  cluster_os          = "tlinux2.4(tkernel4)x86_64"
  cluster_type        = "MANAGED_CLUSTER"
  cluster_max_pod_num = 64

  # 网络插件
  network_type = "GR"   # GR（GlobalRouter）或 VPC-CNI

  # Master 节点（托管集群无需配置）
  managed_cluster_internet_security_policies = ["0.0.0.0/0"]

  tags = local.common_tags
}
```

---

## 节点池

```hcl
resource "tencentcloud_kubernetes_node_pool" "default" {
  name                     = "${local.name_prefix}-nodepool"
  cluster_id               = tencentcloud_kubernetes_cluster.main.id
  max_size                 = 10
  min_size                 = 1
  vpc_id                   = var.vpc_id
  subnet_ids               = [var.subnet_ids["private-a"], var.subnet_ids["private-b"]]
  retry_policy             = "INCREMENTAL_INTERVALS"
  desired_capacity         = var.worker_count
  enable_auto_scale        = true
  deletion_protection      = local.is_prod

  auto_scaling_config {
    instance_type      = var.instance_type   # 例如 SA3.LARGE8
    system_disk_type   = "CLOUD_PREMIUM"
    system_disk_size   = 50
    security_group_ids = [var.sg_id]
    key_ids            = [var.key_pair_id]

    data_disk {
      disk_type = "CLOUD_PREMIUM"
      disk_size = 100
    }

    internet_charge_type       = "TRAFFIC_POSTPAID_BY_HOUR"
    internet_max_bandwidth_out = 0
    public_ip_assigned         = false
  }

  node_config {
    extra_args = [
      "root-dir=/var/lib/kubelet"
    ]
  }

  labels = merge(local.common_tags, {
    "node-pool" = "default"
  })
}
```

---

## 获取 Kubeconfig

```hcl
# 集群内网访问地址
output "cluster_id"       { value = tencentcloud_kubernetes_cluster.main.id }
output "cluster_endpoint" { value = tencentcloud_kubernetes_cluster.main.pgw_endpoint }
output "kubeconfig"       {
  value     = tencentcloud_kubernetes_cluster.main.kube_config
  sensitive = true
}
```

---

## 附加组件（Addon）

```hcl
# 安装 metrics-server
resource "tencentcloud_kubernetes_addon_attachment" "metrics_server" {
  cluster_id = tencentcloud_kubernetes_cluster.main.id
  name       = "metrics-server"
  version    = "0.6.1"
}

# 安装 NodeLocal DNSCache
resource "tencentcloud_kubernetes_addon_attachment" "node_local_dns" {
  cluster_id = tencentcloud_kubernetes_cluster.main.id
  name       = "node-local-dns"
}
```
