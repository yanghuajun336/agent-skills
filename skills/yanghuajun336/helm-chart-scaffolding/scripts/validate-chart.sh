#!/bin/bash
set -e

CHART_DIR="${1:-.}"
RELEASE_NAME="test-release"

echo "═══════════════════════════════════════════════════════"
echo "  Helm Chart Validation"
echo "═══════════════════════════════════════════════════════"
echo "═══════════════════════════════════════════════════════"
echo "  Helm Chart 校验"
echo "═══════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
# 颜色

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Helm is installed
if ! command -v helm &> /dev/null; then
    error "未检测到 Helm，请先安装 Helm"
    exit 1
fi

echo "📦 Chart directory: $CHART_DIR"
echo ""
echo "📦 Chart 目录: $CHART_DIR"

# 1. Check chart structure
echo "1️⃣  Checking chart structure..."
echo "1️⃣  检查 Chart 结构..."
if [ ! -f "$CHART_DIR/Chart.yaml" ]; then
    error "未找到 Chart.yaml"
    exit 1
fi
success "Chart.yaml exists"

if [ ! -f "$CHART_DIR/values.yaml" ]; then
    error "未找到 values.yaml"
    exit 1
fi
success "values.yaml exists"

if [ ! -d "$CHART_DIR/templates" ]; then
    error "未找到 templates/ 目录"
    exit 1
fi
success "templates/ directory exists"
echo ""

# 2. Lint the chart
echo "2️⃣  Linting chart..."
echo "2️⃣  Lint 检查..."
if helm lint "$CHART_DIR"; then
    success "Lint 检查通过"
else
    error "Lint 检查未通过"
    exit 1
fi
echo ""

# 3. Check Chart.yaml
echo "3️⃣  Validating Chart.yaml..."
echo "3️⃣  校验 Chart.yaml..."
CHART_NAME=$(grep "^name:" "$CHART_DIR/Chart.yaml" | awk '{print $2}')
CHART_VERSION=$(grep "^version:" "$CHART_DIR/Chart.yaml" | awk '{print $2}')
APP_VERSION=$(grep "^appVersion:" "$CHART_DIR/Chart.yaml" | awk '{print $2}' | tr -d '"')

if [ -z "$CHART_NAME" ]; then
    error "未找到 Chart 名称"
    exit 1
fi
success "Chart name: $CHART_NAME"

if [ -z "$CHART_VERSION" ]; then
    error "未找到 Chart 版本"
    exit 1
fi
success "Chart version: $CHART_VERSION"

if [ -z "$APP_VERSION" ]; then
    warning "未指定 App 版本"
else
    success "App 版本: $APP_VERSION"
fi
echo ""

# 4. Test template rendering
echo "4️⃣  Testing template rendering..."
echo "4️⃣  测试模板渲染..."
if helm template "$RELEASE_NAME" "$CHART_DIR" > /dev/null 2>&1; then
    success "模板渲染成功"
else
    error "模板渲染失败"
    helm template "$RELEASE_NAME" "$CHART_DIR"
    exit 1
fi
echo ""

# 5. Dry-run installation
echo "5️⃣  Testing dry-run installation..."
echo "5️⃣  Dry-run 安装测试..."
if helm install "$RELEASE_NAME" "$CHART_DIR" --dry-run --debug > /dev/null 2>&1; then
    success "Dry-run 安装成功"
else
    error "Dry-run 安装失败"
    exit 1
fi
echo ""

# 6. Check for required Kubernetes resources
echo "6️⃣  Checking generated resources..."
echo "6️⃣  检查生成的资源..."
MANIFESTS=$(helm template "$RELEASE_NAME" "$CHART_DIR")

if echo "$MANIFESTS" | grep -q "kind: Deployment"; then
    success "检测到 Deployment"
else
    warning "未检测到 Deployment"
fi

if echo "$MANIFESTS" | grep -q "kind: Service"; then
    success "检测到 Service"
else
    warning "未检测到 Service"
fi

if echo "$MANIFESTS" | grep -q "kind: ServiceAccount"; then
    success "检测到 ServiceAccount"
else
    warning "未检测到 ServiceAccount"
fi
echo ""

# 7. Check for security best practices
echo "7️⃣  Checking security best practices..."
echo "7️⃣  检查安全最佳实践..."
if echo "$MANIFESTS" | grep -q "runAsNonRoot: true"; then
    success "已设置非 root 用户运行"
else
    warning "未显式设置非 root 用户运行"
fi

if echo "$MANIFESTS" | grep -q "readOnlyRootFilesystem: true"; then
    success "已启用只读根文件系统"
else
    warning "未启用只读根文件系统"
fi

if echo "$MANIFESTS" | grep -q "allowPrivilegeEscalation: false"; then
    success "已禁用权限提升"
else
    warning "未显式禁用权限提升"
fi
echo ""

# 8. Check for resource limits
echo "8️⃣  Checking resource configuration..."
echo "8️⃣  检查资源配置..."
if echo "$MANIFESTS" | grep -q "resources:"; then
    if echo "$MANIFESTS" | grep -q "limits:"; then
        success "已定义资源 limits"
    else
        warning "未定义资源 limits"
    fi
    if echo "$MANIFESTS" | grep -q "requests:"; then
        success "已定义资源 requests"
    else
        warning "未定义资源 requests"
    fi
else
    warning "未定义资源配置"
fi
echo ""

# 9. Check for health probes
echo "9️⃣  Checking health probes..."
echo "9️⃣  检查健康探针..."
if echo "$MANIFESTS" | grep -q "livenessProbe:"; then
    success "已配置 livenessProbe"
else
    warning "未配置 livenessProbe"
fi

if echo "$MANIFESTS" | grep -q "readinessProbe:"; then
    success "已配置 readinessProbe"
else
    warning "未配置 readinessProbe"
fi
echo ""

# 10. Check dependencies
if [ -f "$CHART_DIR/Chart.yaml" ] && grep -q "^dependencies:" "$CHART_DIR/Chart.yaml"; then
    echo "🔟 检查依赖..."
    if helm dependency list "$CHART_DIR" > /dev/null 2>&1; then
        success "依赖项有效"

        if [ -f "$CHART_DIR/Chart.lock" ]; then
            success "Chart.lock 文件存在"
        else
            warning "缺少 Chart.lock 文件（请运行 'helm dependency update'）"
        fi
    else
        error "依赖检查失败"
    fi
    echo ""
fi

# 11. Check for values schema
if [ -f "$CHART_DIR/values.schema.json" ]; then
    echo "1️⃣1️⃣ 校验 values.schema.json..."
    success "values.schema.json present"

    # Validate schema if jq is available
    if command -v jq &> /dev/null; then
        if jq empty "$CHART_DIR/values.schema.json" 2>/dev/null; then
            success "values.schema.json 是有效 JSON"
        else
            error "values.schema.json 不是有效 JSON"
            exit 1
        fi
    fi
    echo ""
fi

# Summary
echo "═══════════════════════════════════════════════════════"
echo "  Validation Complete!"
echo "  校验完成！"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Chart: $CHART_NAME"
echo "Version: $CHART_VERSION"
echo "版本: $CHART_VERSION"
if [ -n "$APP_VERSION" ]; then
    echo "App 版本: $APP_VERSION"
fi
echo ""
success "All validations passed!"
success "所有校验均通过！"
echo ""
echo "Next steps:"
echo "  • helm package $CHART_DIR"
echo "  • helm package $CHART_DIR"
echo "  • helm install my-release $CHART_DIR"
echo "  • helm test my-release"
echo "  • helm install my-release $CHART_DIR"
echo "  • helm test my-release"
echo ""
