# API设计文档

## 一、API概览

### 1.1 基本信息

| 项目 | 值 |
|------|-----|
| 基础路径 | `http://localhost:8000` |
| API版本 | v1 |
| 数据格式 | JSON |
| 认证方式 | 无需认证（MVP阶段） |
| 文档地址 | `http://localhost:8000/docs` |

### 1.2 接口清单

| 接口 | 方法 | 说明 | 优先级 |
|------|------|------|--------|
| `/api/v1/vip/query` | GET | 查询用户虚拟IP | P0 |
| `/api/v1/vip/reverse` | GET | 按虚拟IP反查用户 | P0 |
| `/api/v1/vip/history` | GET | 查询历史记录 | P0 |
| `/api/v1/user/list` | GET | 获取用户列表 | P1 |
| `/api/v1/system/health` | GET | 健康检查 | P0 |

---

## 二、接口详细设计

### 2.1 查询用户虚拟IP

**接口地址：** `GET /api/v1/vip/query`

**功能说明：** 根据用户名或显示名查询虚拟IP，优先查询在线用户，再查询历史记录。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 用户名或显示名 |
| source | string | 否 | 数据来源：online(仅在线)、history(仅历史)、all(全部，默认) |

#### 请求示例

```
GET /api/v1/vip/query?name=张三三
GET /api/v1/vip/query?name=zhangsan&source=online
```

#### 响应参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | number | 状态码，0成功 |
| message | string | 提示信息 |
| data | object | 响应数据 |

**data 对象：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| user_name | string | 用户名 |
| display_name | string | 显示名 |
| is_online | boolean | 是否在线 |
| online_vips | array | 在线虚拟IP列表 |
| history_vip | object | 历史虚拟IP记录 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_name": "zhangsan",
    "display_name": "张三三",
    "is_online": true,
    "online_vips": [
      {
        "ip": "10.10.10.100",
        "real_ip": "175.9.142.2",
        "last_login_time": "2026-07-29 10:30:00"
      }
    ],
    "history_vip": {
      "ip": "10.10.10.99",
      "real_ip": "175.9.142.2",
      "timestamp": "2026-07-28 14:30:00",
      "event_type": "syslog_access"
    }
  }
}
```

---

### 2.2 按虚拟IP反查用户

**接口地址：** `GET /api/v1/vip/reverse`

**功能说明：** 根据虚拟IP地址反查关联的用户信息。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| ip | string | 是 | 虚拟IP地址 |
| limit | number | 否 | 返回条数，默认10 |

#### 请求示例

```
GET /api/v1/vip/reverse?ip=10.10.10.100
GET /api/v1/vip/reverse?ip=10.10.10.100&limit=5
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "virtual_ip": "10.10.10.100",
    "records": [
      {
        "user_name": "zhangsan",
        "display_name": "张三三",
        "real_ip": "175.9.142.2",
        "event_type": "online_query",
        "timestamp": "2026-07-29 10:30:00"
      },
      {
        "user_name": "zhangsan",
        "display_name": "张三三",
        "real_ip": "175.9.142.2",
        "event_type": "syslog_access",
        "timestamp": "2026-07-28 14:30:00"
      }
    ]
  }
}
```

---

### 2.3 查询历史记录

**接口地址：** `GET /api/v1/vip/history`

**功能说明：** 查询指定用户的历史虚拟IP记录。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 用户名或显示名 |
| days | number | 否 | 查询天数，默认30 |
| page | number | 否 | 页码，默认1 |
| page_size | number | 否 | 每页条数，默认20 |

#### 请求示例

```
GET /api/v1/vip/history?name=zhangsan
GET /api/v1/vip/history?name=张三三&days=7&page=2&page_size=10
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 25,
    "page": 1,
    "page_size": 20,
    "records": [
      {
        "virtual_ip": "10.10.10.100",
        "real_ip": "175.9.142.2",
        "event_type": "online_query",
        "timestamp": "2026-07-29 10:30:00"
      },
      {
        "virtual_ip": "10.10.10.99",
        "real_ip": "175.9.142.2",
        "event_type": "syslog_access",
        "timestamp": "2026-07-28 14:30:00"
      }
    ]
  }
}
```

---

### 2.4 获取用户列表

**接口地址：** `GET /api/v1/user/list`

**功能说明：** 获取所有用户列表，支持搜索和分页。

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| search | string | 否 | 搜索关键词（用户名/显示名/手机号） |
| page | number | 否 | 页码，默认1 |
| page_size | number | 否 | 每页条数，默认20 |

#### 请求示例

```
GET /api/v1/user/list
GET /api/v1/user/list?search=张
GET /api/v1/user/list?page=2&page_size=10
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "users": [
      {
        "user_name": "zhangsan",
        "display_name": "张三三",
        "phone": "138****0000",
        "directory_name": "本地用户目录",
        "last_vip": "10.10.10.100",
        "last_active": "2026-07-29 10:30:00"
      }
    ]
  }
}
```

---

### 2.5 健康检查

**接口地址：** `GET /api/v1/system/health`

**功能说明：** 检查系统运行状态。

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime": "2h 30m",
    "database": "connected",
    "atrust_api": "available",
    "syslog": "listening"
  }
}
```

---

## 三、错误码定义

### 3.1 通用错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 参数缺失 |
| 2001 | 用户不存在 |
| 2002 | 虚拟IP不存在 |
| 3001 | 数据库错误 |
| 3002 | API调用失败 |
| 4001 | 系统内部错误 |

### 3.2 错误响应格式

```json
{
  "code": 2001,
  "message": "用户不存在",
  "data": null
}
```

---

## 四、数据模型

### 4.1 请求模型

```python
from pydantic import BaseModel
from typing import Optional

class VipQueryRequest(BaseModel):
    name: str
    source: Optional[str] = "all"  # online, history, all

class VipReverseRequest(BaseModel):
    ip: str
    limit: Optional[int] = 10

class VipHistoryRequest(BaseModel):
    name: str
    days: Optional[int] = 30
    page: Optional[int] = 1
    page_size: Optional[int] = 20
```

### 4.2 响应模型

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VipInfo(BaseModel):
    ip: str
    real_ip: Optional[str]
    last_login_time: Optional[str]

class VipRecord(BaseModel):
    virtual_ip: str
    real_ip: Optional[str]
    event_type: str
    timestamp: str

class VipQueryResponse(BaseModel):
    user_name: str
    display_name: Optional[str]
    is_online: bool
    online_vips: List[VipInfo]
    history_vip: Optional[VipRecord]

class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict]
```

---

## 五、调用示例

### 5.1 cURL 示例

```bash
# 查询用户虚拟IP
curl "http://localhost:8000/api/v1/vip/query?name=张三三"

# 按虚拟IP反查
curl "http://localhost:8000/api/v1/vip/reverse?ip=10.10.10.100"

# 查询历史记录
curl "http://localhost:8000/api/v1/vip/history?name=zhangsan&days=7"
```

### 5.2 Python 示例

```python
import requests

# 查询用户虚拟IP
response = requests.get(
    "http://localhost:8000/api/v1/vip/query",
    params={"name": "张三三"}
)
data = response.json()
print(f"虚拟IP: {data['data']['online_vips']}")
```

### 5.3 JavaScript 示例

```javascript
// 查询用户虚拟IP
fetch('http://localhost:8000/api/v1/vip/query?name=张三三')
  .then(response => response.json())
  .then(data => {
    console.log('虚拟IP:', data.data.online_vips);
  });
```

---

## 六、接口调用流程

### 6.1 典型查询流程

```
用户输入: "张三三"
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 调用 /api/v1/vip/query?name=张三三                       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 后端处理                                                 │
│  ─────────────────────────────────────────────────────────  │
│  a. 调用 aTrust API 查询在线用户                              │
│  b. 查询本地数据库获取历史记录                                │
│  c. 合并结果返回                                             │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 返回结果                                                 │
│  ─────────────────────────────────────────────────────────  │
│  {                                                          │
│    "is_online": true,                                       │
│    "online_vips": [{"ip": "10.10.10.100"}],                │
│    "history_vip": {"ip": "10.10.10.99"}                    │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```
