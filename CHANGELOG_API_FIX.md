# API 对接修复记录

## 修复日期

2026-07-30

## 修复概述

修复了 aTrust API 对接功能，使系统能够正确连接到零信任设备并查询在线用户和虚拟IP信息。

---

## 修复内容

### 1. 签名算法重写 (P0 - 关键)

**问题**: 原有签名算法完全错误，导致所有 API 请求认证失败。

**修复**: 实现了正确的 HMAC-SHA256 签名算法：

```python
# 签名串构造
sign_str = path + "?" + sorted_query_params + "&" + body

# 签名密钥构造
key_str = f"appId={api_id}&appSecret={api_key}&timestamp={timestamp}&nonce={nonce}"

# 签名计算
sign = hmac.new(key_str.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
```

### 2. 请求头字段名修正 (P0 - 关键)

| 原字段名 | 修正后 |
| ---------- | -------- |
| `X-API-ID` | `x-ca-key` |
| `X-Timestamp` | `x-ca-timestamp` |
| `X-Signature` | `x-ca-sign` |
| ❌ 缺失 | `x-ca-nonce` (新增必需字段) |

### 3. API 路径修正 (P0 - 关键)

| 功能 | 原路径 | 修正后 |
|------|--------|--------|
| 查询在线用户 | `/api/v1/user/status` | `/api/v1/monitor/getUserStatus` |
| 健康检查 | `/api/v1/system/health` | `/api/v1/admin/getConfig` |

### 4. 返回数据解析修正 (P1 - 重要)

**问题**: 虚拟IP字段解析错误。

**修复**:

```python
# 原代码（错误）
virtual_ip = user_data.get("virtualIp")

# 修正后
vips = user_data.get("vips", [])
for vip in vips:
    ip = vip.get("ip", "")
```

### 5. 代理设置处理 (P2 - 改进)

添加了 `trust_env = False` 禁用环境变量代理设置，避免内网设备连接问题。

---

## 新增功能

### 1. 重试机制

- 自动重试 3 次
- 重试间隔 1 秒

### 2. 更完善的异常处理

- `AtrustApiError` 自定义异常类
- 区分 SSL 错误、超时、连接错误等

### 3. 新增查询方法

- `query_user_by_display_name()` - 按显示名查询
- `query_user_by_name()` - 按用户名查询
- `get_all_online_users()` - 自动分页获取所有用户
- `query_devices()` - 查询终端信息

---

## 测试结果

### 测试设备

- 地址: `10.5.40.161:4433`
- API ID: `2240982`
- 设备版本: aTrust 2.6.10

### 测试项目

| 测试项 | 结果 |
| -------- | ------ |
| 客户端创建 | ✅ 通过 |
| 连接测试 | ✅ 通过 |
| 获取在线用户 | ✅ 通过 |
| 按显示名查询 | ✅ 通过 |
| 获取所有在线用户 | ✅ 通过 |
| 查询终端信息 | ✅ 通过 |
| 健康检查 | ✅ 通过 |

### 测试数据

- 总会话数: 3
- 在线用户数: 2 (去重后)
- 终端总数: 73

---

## 修改的文件

| 文件 | 修改类型 |
| ------ | ---------- |
| `src/collector/api_collector.py` | 重写 |
| `config.yaml` | 更新配置 |
| `test_api_collector.py` | 新增测试 |
| `CHANGELOG_API_FIX.md` | 本文件 |

---

## 后续待办

1. **集成到 React 前端** - 添加实时查询按钮
2. **定时任务** - 自动同步在线用户数据
3. **监控告警** - API 连接异常告警

---

## 参考资料

- [aTrust OpenAPI 文档](./docs/)
- [测试脚本](./query_vip.py)
- [API 分析报告](./ANALYSIS_API_integration.md)
