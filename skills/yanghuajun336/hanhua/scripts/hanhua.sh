#!/bin/bash
# hanhua.sh
# 用于自动汉化项目中的注释、介绍、描述类内容
# 依赖：curl（用于调用AI翻译API），diff（生成对比报告），jq（如API返回JSON）
# 用法：./hanhua.sh <目标目录> <对比报告输出路径>

set -e

TARGET_DIR="$1"
REPORT_PATH="$2"
TMP_DIR="/tmp/hanhua_$$"
mkdir -p "$TMP_DIR"

if [[ -z "$TARGET_DIR" || -z "$REPORT_PATH" ]]; then
  echo "用法: $0 <目标目录> <对比报告输出路径>"
  exit 1
fi

# 递归查找常见注释文件和代码文件
find "$TARGET_DIR" -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.go' -o -name '*.java' -o -name '*.sh' -o -name '*.yaml' -o -name '*.yml' -o -name '*.md' -o -name 'Dockerfile' \) | while read file; do
  relpath="${file#$TARGET_DIR/}"
  cp "$file" "$TMP_DIR/$relpath.orig"
  # 只处理注释和描述行，调用AI翻译API（此处用函数mock_translate模拟，实际可接入API）
  awk '{
    if ($0 ~ /^[[:space:]]*#|^[[:space:]]*\/\/|^[[:space:]]*\/\*|^[[:space:]]*\*|^[[:space:]]*--|^[[:space:]]*;|^[[:space:]]*REM |^[[:space:]]*<!--|^[[:space:]]*\"\"\"|^[[:space:]]*\'\'\'/) {
      # 只翻译注释
      cmd = "hanhua_translate '"$0"'"
      cmd | getline result
      close(cmd)
      print result
    } else {
      print $0
    }
  }' "$file" > "$TMP_DIR/$relpath"
  # 生成对比
  diff -u "$TMP_DIR/$relpath.orig" "$TMP_DIR/$relpath" > "$REPORT_PATH/$relpath.diff" || true
  # 覆盖原文件
  mv "$TMP_DIR/$relpath" "$file"
done

echo "汉化完成，对比报告已生成于 $REPORT_PATH"

# hanhua_translate: 注释行翻译函数（需接入实际AI翻译API）
hanhua_translate() {
  # 示例：直接用AI模型API替换此处
  # 这里用echo模拟，实际应调用API
  local text="$1"
  # TODO: 替换为实际API调用
  echo "$text (已翻译为中文)"
}
