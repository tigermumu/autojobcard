# Gitee 上传部署指南

## 第一步：准备工作

### 1.1 安装 Git
如果还没有安装 Git，请先下载安装：
- 下载地址：https://git-scm.com/download/win
- 安装完成后，在命令行验证：
```bash
git --version
```

### 1.2 配置 Git 用户信息
```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱"
```

### 1.3 创建 Gitee 账号和仓库
1. 访问 https://gitee.com 注册/登录账号
2. 点击右上角 "+" → "新建仓库"
3. 填写仓库信息：
   - 仓库名称：例如 `aircraft-workcard-system`
   - 仓库介绍：飞机方案处理系统
   - 选择"私有"或"公开"（根据需求）
   - **不要**勾选"使用Readme文件初始化仓库"（如果已有代码）
4. 点击"创建"

## 第二步：初始化本地 Git 仓库

### 2.1 在项目根目录初始化 Git
打开 PowerShell 或 CMD，进入项目目录：
```bash
cd C:\AI\demo3
git init
```

### 2.2 添加文件到暂存区
```bash
git add .
```

### 2.3 提交到本地仓库
```bash
git commit -m "初始提交：飞机方案处理系统"
```

## 第三步：连接到 Gitee 远程仓库

### 3.1 添加远程仓库地址
在 Gitee 仓库页面，复制仓库地址（HTTPS 或 SSH），然后执行：

**使用 HTTPS（推荐，简单）：**
```bash
git remote add origin https://gitee.com/你的用户名/仓库名.git
```

**或使用 SSH（需要配置 SSH 密钥）：**
```bash
git remote add origin git@gitee.com:你的用户名/仓库名.git
```

### 3.2 验证远程仓库配置
```bash
git remote -v
```
应该显示你添加的远程仓库地址。

## 第四步：推送到 Gitee

### 4.1 推送到远程仓库
```bash
git push -u origin master
```

如果 Gitee 默认分支是 `main`，使用：
```bash
git push -u origin main
```

### 4.2 输入 Gitee 账号密码
- 如果使用 HTTPS，会提示输入用户名和密码
- 密码：使用 Gitee 账号密码或**个人访问令牌**（推荐）

**获取个人访问令牌：**
1. Gitee → 设置 → 安全设置 → 私人令牌
2. 生成新令牌，勾选 `projects` 权限
3. 复制令牌，推送时密码处输入令牌

## 第五步：验证上传结果

1. 访问你的 Gitee 仓库页面
2. 确认所有文件都已上传
3. 检查 `.gitignore` 是否正确生效（node_modules、venv 等不应显示）

## 常见问题解决

### 问题1：推送被拒绝（rejected）
**原因：** Gitee 仓库已有内容（如 README）
**解决：**
```bash
git pull origin master --allow-unrelated-histories
# 解决可能的冲突后
git push -u origin master
```

### 问题2：认证失败
**解决：**
- 检查用户名密码是否正确
- 使用个人访问令牌代替密码
- 或配置 SSH 密钥

### 问题3：文件太大上传失败
**解决：**
- 检查 `.gitignore` 是否正确忽略大文件
- 使用 Git LFS（Large File Storage）：
```bash
git lfs install
git lfs track "*.xlsx"
git add .gitattributes
git commit -m "添加 LFS 支持"
```

### 问题4：需要更新代码
后续更新代码的流程：
```bash
git add .
git commit -m "更新说明"
git push origin master
```

## 后续操作建议

1. **创建分支管理：**
```bash
git checkout -b develop  # 创建开发分支
git push -u origin develop
```

2. **添加 .gitignore 规则：**
如果发现还有不需要上传的文件，编辑 `.gitignore` 文件添加规则

3. **保护主分支：**
在 Gitee 仓库设置中，可以设置 master/main 分支为保护分支，需要 Pull Request 才能合并

## 下一步：部署到阿里云服务器

上传到 Gitee 后，可以在服务器上通过以下方式拉取代码：
```bash
git clone https://gitee.com/你的用户名/仓库名.git
```

然后按照项目的部署文档进行服务器配置。

