# JSESSIONID 说明文档

## 为什么会有两个不同的 JSESSIONID？

在内网Java Web应用中，出现两个不同的JSESSIONID是**正常现象**，常见原因如下：

### 1. **不同的Context Path（应用上下文路径）**
Java Web应用可能部署在不同的上下文路径下，每个路径会生成独立的Session：
- `/trace` 路径 → `JSESSIONID=xxx1`
- `/Web/trace` 路径 → `JSESSIONID=xxx2`

### 2. **负载均衡器/代理服务器**
如果系统使用了负载均衡器或反向代理：
- 负载均衡器可能生成自己的Session ID
- 后端应用服务器生成自己的Session ID

### 3. **不同的应用模块**
同一个服务器上可能运行多个Java应用：
- 主应用 → `JSESSIONID=xxx1`
- 子应用/模块 → `JSESSIONID=xxx2`

### 4. **Session粘性（Session Affinity）**
在集群环境中，不同服务器节点会生成不同的Session ID。

---

## Cookie格式示例

**您看到的Cookie格式（实际格式）**：

```
JSESSIONID=ABC123DEF456; JSESSIONID=XYZ789UVW012
```

这是**完全正常**的格式！两个JSESSIONID用分号（`;`）分隔。

### 为什么会有两个JSESSIONID？

内网Java Web应用中，这种情况很常见：

1. **不同的应用路径**：
   - `/trace` 路径生成第一个JSESSIONID
   - `/Web/trace` 路径生成第二个JSESSIONID

2. **不同的服务器节点**：
   - 负载均衡器可能分配不同的服务器
   - 每个服务器维护自己的Session

3. **应用模块分离**：
   - 主应用和子应用各自维护Session

### 其他可能的格式

有些情况下，Cookie可能包含Path信息：

```
JSESSIONID=ABC123DEF456; Path=/trace; JSESSIONID=XYZ789UVW012; Path=/Web/trace
```

但最常见的就是您看到的格式：`JSESSIONID=xxx; JSESSIONID=yyy`

---

## 当前代码的处理方式

### 后端Cookie解析逻辑

在 `workcard_import_service.py` 的 `_parse_cookies` 方法中：

```python
def _parse_cookies(self, raw: Optional[str] = None) -> Dict[str, str]:
    source = raw.strip() if isinstance(raw, str) else settings.WORKCARD_IMPORT_COOKIES.strip()
    if not source:
        return {}
    
    cookies: Dict[str, str] = {}
    for segment in source.split(";"):
        if "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        cookies[name.strip()] = value.strip()  # ⚠️ 这里会覆盖同名Cookie
    return cookies
```

### ⚠️ 潜在问题

**当前实现的问题**：
- 如果Cookie字符串中有两个 `JSESSIONID`，后面的会**覆盖**前面的
- 只保留了最后一个 `JSESSIONID` 的值
- 可能丢失重要的Session信息

---

## 解决方案

### 方案1：保留所有Cookie（推荐）

修改Cookie解析逻辑，支持同名Cookie的多个值：

```python
def _parse_cookies(self, raw: Optional[str] = None) -> Dict[str, str]:
    source = raw.strip() if isinstance(raw, str) else settings.WORKCARD_IMPORT_COOKIES.strip()
    if not source:
        return {}
    
    cookies: Dict[str, str] = {}
    for segment in source.split(";"):
        segment = segment.strip()
        if "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        name = name.strip()
        value = value.strip()
        
        # 如果已存在同名Cookie，合并值（用分号连接）
        if name in cookies:
            cookies[name] = f"{cookies[name]}; {value}"
        else:
            cookies[name] = value
    
    return cookies
```

### 方案2：使用Cookie列表（更精确）

使用列表存储同名Cookie的多个值：

```python
from typing import Dict, List, Union

def _parse_cookies(self, raw: Optional[str] = None) -> Dict[str, Union[str, List[str]]]:
    source = raw.strip() if isinstance(raw, str) else settings.WORKCARD_IMPORT_COOKIES.strip()
    if not source:
        return {}
    
    cookies: Dict[str, List[str]] = {}
    for segment in source.split(";"):
        segment = segment.strip()
        if "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        name = name.strip()
        value = value.strip()
        
        if name not in cookies:
            cookies[name] = []
        cookies[name].append(value)
    
    # 对于单个值的Cookie，返回字符串；多个值的返回列表
    result = {}
    for name, values in cookies.items():
        if len(values) == 1:
            result[name] = values[0]
        else:
            result[name] = values  # 或者用分号连接: "; ".join(values)
    
    return result
```

### 方案3：直接传递原始Cookie字符串（最简单）

不解析Cookie，直接传递给requests库：

```python
def _create_session(self, raw_cookies: Optional[str] = None) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    
    # 直接设置Cookie头，而不是解析后设置
    if raw_cookies:
        session.headers['Cookie'] = raw_cookies.strip()
    elif settings.WORKCARD_IMPORT_COOKIES:
        session.headers['Cookie'] = settings.WORKCARD_IMPORT_COOKIES.strip()
    
    return session
```

---

## 推荐方案

**推荐使用方案3（直接传递原始Cookie字符串）**，因为：

1. ✅ **最简单**：不需要复杂的解析逻辑
2. ✅ **保留所有信息**：不会丢失任何Cookie值
3. ✅ **兼容性好**：浏览器发送的Cookie格式就是这样的
4. ✅ **支持复杂场景**：可以处理Path、Domain等Cookie属性

---

## 前端输入说明

在前端Cookie输入框中，用户应该：

1. **直接复制浏览器中的完整Cookie字符串**
2. **保持原始格式**，包括所有分号分隔的Cookie
3. **不需要手动处理**，系统会自动处理

**示例输入**：
```
JSESSIONID=ABC123DEF456; JSESSIONID=XYZ789UVW012; other_cookie=value
```

---

## 测试建议

1. **测试两个JSESSIONID的场景**：
   - 输入包含两个JSESSIONID的Cookie字符串
   - 验证请求是否成功
   - 检查后端日志中的Cookie值

2. **测试单个JSESSIONID的场景**：
   - 输入只有一个JSESSIONID的Cookie
   - 验证功能正常

3. **测试无Cookie的场景**：
   - 不输入Cookie（如果内网不需要认证）
   - 验证功能是否正常

---

## 总结

- **两个JSESSIONID是正常的**，通常是因为不同的应用路径或服务器节点
- **当前代码可能会丢失Cookie值**（后面的覆盖前面的）
- **推荐修改为直接传递原始Cookie字符串**，避免解析丢失
- **前端用户直接复制浏览器Cookie即可**，不需要特殊处理

