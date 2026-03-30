# skills-translator Examples

## 1. 简单 Python 注释
### Before
```python
# This function adds two numbers
def add(a, b):
    return a + b
```
### After
```python
# This function adds two numbers
# 此函数用于将两个数字相加
def add(a, b):
    return a + b
```

## 2. YAML 注释（前后对比）
### Before
```yaml
# Default values for my chart.
replicaCount: 1
```
### After
```yaml
# Default values for my chart.
# 我的 chart 的默认值。
replicaCount: 1
```

## 3. SKILL.md 多段落示例（上下文判断）
### Before
```markdown
# My Skill

This skill fetches data from the API and returns a parsed object.

Example:
```bash
curl -X GET "https://api.example.com/data?limit=10"
```

Notes:
- Keep your API key secret.
```
### After (示例)
```markdown
# My Skill

此技能从 API 获取数据并返回解析后的对象。

Example:
```bash
curl -X GET "https://api.example.com/data?limit=10"
```

Notes:
- 将你的 API key 保管好。
```

## 4. 多段落上下文敏感 (演示保持命名与代码不翻译)
### Before
```markdown
### Usage
Call `my_skill.run()` to execute the skill. The parameter `user_id` accepts integer IDs.
```
### After
```markdown
### Usage
调用 `my_skill.run()` 来执行该 skill。参数 `user_id` 接受整数 ID。
```
