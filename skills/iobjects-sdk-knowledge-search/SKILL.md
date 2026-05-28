---
name: iobjects-sdk-knowledge-search
description: 搜索 SuperMap iObjects Java SDK API 文档。当你遇到来自 UGO 的类、接口、注解或方法调用时，必须使用此技能查询文档。
---

# SDK Knowledge Base Search

搜索 SuperMap iObjects Java SDK API，通过语义查询找到相关的类和方法

## 使用方法

```bash
# 基本查询
node search.js "如何创建数据源"

# 指定返回结果数量
node search.js "Workspace 打开方法" 10
```

环境变量 `SDK_API_URL` 可覆盖默认 API 地址（默认：http://172.27.16.134:8000）。

## 输出格式

返回 Markdown 格式的搜索结果，包含：
- 类名和方法名
- 相似度百分比
- 方法签名
- 方法描述
