# 无管理员权限 Windows 部署快速指南

## 🎯 最简单的方案：SQLite + 便携版软件

### 第一步：下载便携版软件（无需安装）

1. **Python 嵌入版**
   - 下载：https://www.python.org/downloads/windows/
   - 选择 "Windows embeddable package (64-bit)"
   - 解压到：`D:\Tools\Python311`（或任意用户目录）

2. **Node.js 便携版**
   - 下载：https://nodejs.org/dist/v18.19.0/node-v18.19.0-win-x64.zip
   - 解压到：`D:\Tools\nodejs`（或任意用户目录）

### 第二步：获取项目代码

```bash
cd D:\Projects
git clone https://gitee.com/bomingaviation_liugw_4779/workshop.git
```

### 第三步：配置环境

1. **编辑 `配置环境.bat`**
   - 修改 `PYTHON_HOME` 和 `NODE_HOME` 为实际路径

2. **配置后端环境变量**
   ```bash
   cd backend
   copy env.example .env
   notepad .env
   ```
   
   修改内容：
   ```bash
   # 使用 SQLite（不需要安装数据库）
   DATABASE_URL=sqlite:///./aircraft_workcard.db
   
   # 配置你的 API 密钥
   QWEN_API_KEY=你的Qwen_API_Key
   ```

### 第四步：启动服务

1. **启动后端**
   - 双击运行 `启动后端-便携版.bat`
   - 等待依赖安装完成（首次运行）

2. **启动前端**
   - 双击运行 `启动前端-便携版.bat`（新开一个窗口）
   - 等待依赖安装完成（首次运行）

### 第五步：访问应用

- **前端**：http://localhost:3000
- **API文档**：http://localhost:8000/api/v1/docs

---

## 📝 详细说明

完整文档请参考：`Windows无管理员权限部署指南.md`

---

## ⚠️ 注意事项

1. **SQLite 限制**：
   - 不支持高并发写入
   - 适合单用户或小数据量
   - 试用/演示环境完全够用

2. **Redis 可选**：
   - 如果不需要匹配进度功能，可以跳过 Redis
   - 代码中 Redis 主要用于进度跟踪

3. **路径配置**：
   - 所有路径都使用用户目录
   - 不需要系统目录权限

---

## 🆘 常见问题

**Q: Python 找不到？**
A: 检查 `配置环境.bat` 中的 `PYTHON_HOME` 路径是否正确

**Q: 端口被占用？**
A: 运行 `netstat -ano | findstr :8000` 查看占用进程

**Q: 依赖安装慢？**
A: 使用国内镜像源（脚本中已配置）

---

完成！现在你可以在没有管理员权限的 Windows 系统上运行应用了！




