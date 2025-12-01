# 项目内网请求URL清单

本文档列出了项目中所有需要VPN连接才能访问的公司内网请求URL。

## 一、基础配置

### 1. VPN基础地址
- **URL**: `https://vpn.gameco.com.cn`
- **说明**: 公司VPN入口地址，所有内网请求都需要通过此VPN访问
- **配置位置**: 
  - `backend/app/core/config.py` (第39行)
  - `backend/env.example` (第23行)
  - 环境变量: `WORKCARD_IMPORT_BASE_URL`

### 2. 内网服务器地址
- **IP地址**: `10.240.2.131:9080`
- **说明**: 内网应用服务器地址，通过VPN隧道访问
- **特点**: 所有请求URL中都包含VPN参数 `CVPNHost=10.240.2.131:9080`

### 3. 内网打印机路径
- **路径**: `\\lx-ps01\\Prt2Q09L非例卡(机上客舱工艺组)`
- **说明**: 内网打印机共享路径，用于工卡打印配置
- **配置位置**: 
  - `backend/app/core/config.py` (第42行)
  - 环境变量: `WORKCARD_IMPORT_PRINTER`

---

## 二、工单管理相关请求

### 1. 查询工单数据
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/fgm/workOrder/checkData.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?from=manage
  ```
- **请求方法**: POST
- **功能**: 根据飞机号、工单号、工作组等条件查询工卡列表
- **使用位置**: `backend/app/services/workcard_import_service.py` (第130行, 第447行, 第1167行)
- **VPN参数说明**:
  - `CVPNHost=10.240.2.131:9080`: 目标内网服务器
  - `CVPNProtocol=http`: VPN协议类型
  - `CVPNOrg=rel`: VPN组织标识
  - `CVPNExtension=.jsp`: 文件扩展名

### 2. 工单管理首页
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/fgm/workOrder/manageIndex.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?wgp={work_group}&txtParentID=10008&txtMenuID=22800
  ```
- **请求方法**: 作为Referer头使用
- **功能**: 工单管理页面，用于设置请求来源
- **使用位置**: `backend/app/services/workcard_import_service.py` (第440行)

---

## 三、工卡导入相关请求

### 1. 打开批量导入对话框
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/fgm/workOrder/jobcard/copy/bathImportNrcStep.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
  ```
- **请求方法**: GET/POST
- **功能**: 打开工卡批量导入对话框，查询历史工卡和步骤信息
- **使用位置**: `backend/app/services/workcard_import_service.py` (第131行, 第490行, 第550行, 第744行, 第1335行)
- **参数**: 
  - GET: `jcRidArr={工卡ID}`
  - POST: 包含工卡版本、工单号、工作组等

### 2. 执行批量导入
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/fgm/workOrder/jobcard/copy/doBathImportNrcStep.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
  ```
- **请求方法**: POST
- **功能**: 执行工卡步骤的批量导入操作
- **使用位置**: `backend/app/services/workcard_import_service.py` (第132行, 第618行, 第1504行)
- **参数**: 包含工卡ID、版本号、步骤信息（phase, zone, trade, rid）等

---

## 四、NRC系统相关请求

### 1. 获取飞机信息
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/nrc/getACInfo.jsp,CVPNTransDest=0,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
  ```
- **请求方法**: GET
- **功能**: 根据飞机号获取飞机相关信息（用于连通性测试）
- **使用位置**: `backend/app/services/workcard_import_service.py` (第271行)
- **参数**: 
  - `txtFlag`: 标志位
  - `txtACNO`: 飞机号
  - `txtWO`: 工单号
  - `jsoncallback`: JSONP回调函数名

### 2. 内网直连版本（已注释）
- **URL**: `http://10.240.2.131:9080/trace/nrc/getACInfo.jsp`
- **说明**: 直接访问内网服务器（不通过VPN），在 `NRC R.py` 文件中使用，但需要在内网环境
- **使用位置**: `NRC R.py` (第58行)

### 3. 缺陷添加页面（Referer）
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/nrc/fault/faultAdd.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?txtParentID=13112&txtMenuID=13541
  ```
- **请求方法**: 作为Referer头使用
- **功能**: 缺陷添加页面，用于设置请求来源
- **使用位置**: `backend/app/services/workcard_import_service.py` (第283行, 第904行)

### 4. 提交缺陷到NRC系统
- **完整URL**: 
  ```
  https://vpn.gameco.com.cn/Web/trace/nrc/fault/faultAddSend.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
  ```
- **请求方法**: POST
- **功能**: 将缺陷信息提交到NRC系统，创建非例行工卡
- **使用位置**: `backend/app/services/workcard_import_service.py` (第850行, 第932行)
- **返回**: 工卡号（格式：NR/000000299）

---

## 五、NRC R.py 中的内网请求（独立脚本）

### 1. 获取飞机信息（内网直连）
- **URL**: `http://10.240.2.131:9080/trace/nrc/getACInfo.jsp`
- **请求方法**: GET
- **功能**: 获取飞机信息
- **使用位置**: `NRC R.py` (第58行)
- **参数**: `txtACNO={飞机号}`

### 2. 提交发动机工卡
- **URL**: `http://10.240.2.131:9080/trace/nrc/eng/engAddSend.jsp`
- **请求方法**: POST
- **功能**: 提交发动机相关工卡
- **使用位置**: `NRC R.py` (第72行)

### 3. 获取工卡发动机信息
- **URL**: `http://10.240.2.131:9080/trace/nrc/eng/getJCEng.jsp`
- **请求方法**: POST
- **功能**: 获取工卡的发动机相关信息（refNo）
- **使用位置**: `NRC R.py` (第88行)

---

## 六、请求特点说明

### 1. VPN访问要求
- **所有请求都需要VPN连接**: 必须连接到 `https://vpn.gameco.com.cn` VPN后才能访问
- **SSL证书验证**: 默认关闭SSL验证（`WORKCARD_IMPORT_VERIFY_SSL=false`），因为VPN证书可能不受信任
- **Cookie认证**: 需要通过环境变量 `WORKCARD_IMPORT_COOKIES` 配置VPN登录后的Cookie

### 2. URL格式特点
- **VPN参数格式**: URL中包含特殊的VPN参数，格式为：
  ```
  ,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
  ```
- **编码要求**: 请求数据需要使用GBK编码（`encoding='gbk'`）
- **响应编码**: 响应内容使用GBK编码解析（`response.encoding = "GBK"`）

### 3. 请求头要求
- **User-Agent**: 模拟浏览器请求
- **Referer**: 必须设置正确的来源页面URL
- **Origin**: 设置为VPN基础地址
- **Content-Type**: `application/x-www-form-urlencoded`

### 4. 请求频率控制
- **请求间隔**: 每次请求之间等待2秒，避免请求频率过高导致连接断开
- **超时设置**: 请求超时时间设置为30秒

### 5. 内网资源
- **打印机**: 使用内网打印机路径 `\\lx-ps01\\Prt2Q09L非例卡(机上客舱工艺组)`
- **服务器**: 内网应用服务器 `10.240.2.131:9080`

---

## 七、配置说明

### 环境变量配置
在 `backend/.env` 文件中需要配置以下变量：

```env
# VPN基础地址
WORKCARD_IMPORT_BASE_URL=https://vpn.gameco.com.cn

# SSL验证（默认关闭）
WORKCARD_IMPORT_VERIFY_SSL=false

# VPN登录后的Cookie（需要手动获取）
WORKCARD_IMPORT_COOKIES=selected_realm=ssl_vpn; ___fnbDropDownState=1; ...

# 内网打印机路径
WORKCARD_IMPORT_PRINTER=\\lx-ps01\\Prt2Q09L非例卡(机上客舱工艺组)

# 是否保存HTML响应（用于调试）
WORKCARD_IMPORT_SAVE_HTML=true

# HTML保存目录
WORKCARD_IMPORT_OUTPUT_DIR=storage/import_logs
```

### Cookie获取方法
1. 使用浏览器登录VPN: `https://vpn.gameco.com.cn`
2. 打开浏览器开发者工具（F12）
3. 在Network标签中找到任意请求
4. 复制请求头中的Cookie值
5. 配置到环境变量 `WORKCARD_IMPORT_COOKIES` 中

---

## 八、总结

项目中所有与公司内网交互的请求都通过VPN访问，主要涉及：

1. **工单管理系统**: 查询工单、管理工卡
2. **工卡导入系统**: 批量导入工卡步骤
3. **NRC系统**: 缺陷管理、非例行工卡创建
4. **内网资源**: 打印机、内网服务器

**关键特点**:
- ✅ 所有请求都需要VPN连接
- ✅ URL中包含VPN隧道参数
- ✅ 使用GBK编码
- ✅ 需要有效的Cookie认证
- ✅ 请求频率需要控制（间隔2秒）

**注意事项**:
- 在没有VPN连接的情况下，所有请求都会失败
- Cookie会过期，需要定期更新
- 内网服务器地址 `10.240.2.131:9080` 只能通过VPN访问

