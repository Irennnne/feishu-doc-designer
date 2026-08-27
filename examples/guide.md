# 发布服务快速指南

## 准备

需要 Python 3.9+，并确认当前目录包含 `config.json`。

## 执行

```bash
python3 deploy.py --config ./config.json
```

## 流程

```mermaid
graph LR
  A[读取配置] --> B[执行检查]
  B --> C[发布]
  C --> D[验证]
```

## 失败处理

如果检查失败，不要绕过校验。修复配置后重新运行一次。
