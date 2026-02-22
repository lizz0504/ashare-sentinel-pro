# 腾讯云环境变量配置指南

## 🚀 最快方式：交互式配置向导

```bash
# 1. 连接服务器
ssh root@your-server-ip

# 2. 进入项目目录
cd ashare-sentinel-pro

# 3. 运行配置向导
bash setup-env.sh
```

**向导会引导你输入所有必需的密钥，自动生成 .env 文件**

---

## 📋 方式1：使用 nano 编辑器

```bash
# 1. 连接服务器
ssh root@your-server-ip

# 2. 进入项目目录
cd ashare-sentinel-pro

# 3. 复制模板
cp .env.docker.example .env

# 4. 编辑文件
nano .env
```

**填写示例**：
```bash
# Supabase配置
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImppeXR4a3VidGloeHdqbG54ZHN3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImFudCI6ImEyZ...（完整密钥）
SUPABASE_JWT_SECRET=your-jwt-secret-here
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZXYiLCJyb2xlIjoiYW5vbiIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU

# AI API配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxx

# 数据源配置
TUSHARE_TOKEN=xxxxxxxxxxxxxxxxxxxxx

# 服务器配置
SERVER_IP=123.45.67.89  # 替换为实际IP
```

**保存并退出**：
- `Ctrl + O` → `Enter`（保存）
- `Ctrl + X`（退出）

---

## 📥 方式2：本地编辑后上传

**在本地电脑上**：

```bash
# 1. 复制模板
cp .env.docker.example .env.production

# 2. 使用VSCode或记事本编辑，填入真实密钥

# 3. 上传到服务器
scp .env.production root@your-server-ip:/root/ashare-sentinel-pro/.env
```

---

## 🔑 密钥获取地址汇总

### Supabase 密钥

访问：https://supabase.com/dashboard/project/jxitxkubtehxwjlnxdsw/settings/api

| 密钥名称 | 页面位置 | 格式 |
|---------|---------|------|
| `SUPABASE_URL` | Project URL | `https://jxitxkubtehxwjlnxdsw.supabase.co` |
| `SUPABASE_SERVICE_KEY` | service_role key | `eyJhbGci...`（很长） |
| `SUPABASE_ANON_KEY` | anon/public key | `eyJhbGci...`（很长） |
| `SUPABASE_JWT_SECRET` | JWT Secret | 字符串（通常20-50字符） |

**操作步骤**：
1. 登录 Supabase Dashboard
2. 选择项目：`jxitxkubtehxwjlnxdsw`
3. 左侧菜单 → Settings → API
4. 复制对应的密钥

**注意**：
- `service_role` 密钥有完整权限，**只用于后端**
- `anon` 密钥权限受限，用于**前端**
- `JWT Secret` 在页面底部，**必须复制完整**

### DeepSeek API Key

访问：https://platform.deepseek.com/

**操作步骤**：
1. 注册/登录账号
2. API Keys → Create new key
3. 复制密钥（格式：`sk-xxxxx`）

### Tavily API Key

访问：https://tavily.com/

**操作步骤**：
1. 注册免费账号（每月1000次查询）
2. API Keys section
3. 复制密钥（格式：`tvly-xxxxx`）

### Tushare Token

访问：https://tushare.pro/

**操作步骤**：
1. 注册账号并实名认证
2. 用户中心 → API接口凭证
3. 复制Token（格式：数字字符串）

---

## ✅ 验证配置

配置完成后，运行以下命令验证：

```bash
# 1. 检查文件是否存在
ls -la .env

# 应该显示：
# -rw------- 1 root root xxx Feb 22 10:00 .env

# 2. 测试环境变量加载
source .env
echo $SUPABASE_URL
# 应该输出: https://jxitxkubtehxwjlnxdsw.supabase.co

echo $DEEPSEEK_API_KEY
# 应该输出你的密钥

# 3. 检查所有必需变量
echo "检查配置："
grep -E "SUPABASE_URL|SUPABASE_SERVICE_KEY|SUPABASE_ANON_KEY|DEEPSEEK_API_KEY|TAVILY_API_KEY|TUSHARE_TOKEN" .env
```

---

## 🚀 配置完成后启动

```bash
# 1. 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 2. 查看日志（确认没有错误）
docker-compose -f docker-compose.prod.yml logs -f

# 3. 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 应该看到：
# NAME                STATUS              PORTS
# ashare-backend      Up (healthy)        0.0.0.0:8000->8000/tcp
# ashare-frontend     Up (healthy)        0.0.0.0:3000->3000/tcp
```

---

## ❗ 常见错误排查

### 错误1：Supabase 连接失败
```
Error: Invalid API key
```
**解决**：
- 检查 `SUPABASE_SERVICE_KEY` 是否完整复制（很长，约300字符）
- 确认使用的是 `service_role` 而非 `anon` key

### 错误2：DeepSeek API 错误
```
Error: Incorrect API key provided
```
**解决**：
- 确认密钥格式：`sk-` 开头
- 检查是否有多余空格

### 错误3：环境变量未生效
```
Error: SUPABASE_URL is not defined
```
**解决**：
```bash
# 重新加载环境变量
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔐 安全建议

1. **文件权限**
   ```bash
   chmod 600 .env  # 仅所有者可读写
   ```

2. **不要提交到Git**
   ```bash
   # .gitignore 应包含：
   .env
   .env.local
   .env.*.local
   ```

3. **定期更换密钥**（建议每3-6个月）

---

## 📞 需要帮助？

如果遇到问题：
1. 检查密钥是否完整复制
2. 确认密钥类型正确（service_role vs anon）
3. 查看容器日志：`docker-compose logs backend`
