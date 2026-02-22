# 🚀 腾讯云超简单部署指南

## 前提条件
- ✅ 已购买腾讯云轻量服务器
- ✅ 已连接到服务器（SSH或网页版）

---

## 📝 三步完成部署

### 第1步：连接服务器

```bash
ssh root@43.134.183.223
```

或在腾讯云控制台使用**网页版SSH**

### 第2步：拉取代码并配置

```bash
# 克隆代码
cd /root
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro

# 运行配置向导
bash setup-env.sh
```

**按提示输入密钥**（从各平台复制粘贴）：
- SUPABASE_URL: `https://jxitxkubtehxwjlnxdsw.supabase.co`（直接回车）
- SUPABASE_SERVICE_KEY: 你的service_role密钥
- SUPABASE_JWT_SECRET: 你的JWT密钥
- SUPABASE_ANON_KEY: 你的anon密钥
- DEEPSEEK_API_KEY: 你的DeepSeek密钥
- TAVILY_API_KEY: 你的Tavily密钥
- TUSHARE_TOKEN: 你的Tushare Token

### 第3步：一键部署

```bash
bash deploy-simple.sh
```

**等待10-15分钟**，部署完成后会显示访问地址。

---

## ✅ 验证部署

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 应该看到两个容器都是 Up 状态
```

---

## 🌐 访问应用

- **前端**: http://43.134.183.223:3000
- **后端**: http://43.134.183.223:8000
- **API文档**: http://43.134.183.223:8000/docs

---

## 🔑 密钥获取地址

| 密钥 | 获取地址 |
|------|----------|
| Supabase密钥 | https://supabase.com/dashboard/project/jxitxkubtehxwjlnxdsw/settings/api |
| DeepSeek | https://platform.deepseek.com/ |
| Tavily | https://tavily.com/ |
| Tushare | https://tushare.pro/ |

---

## ❓ 常见问题

### Q: 如何查看日志？
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Q: 如何重启服务？
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Q: 如何更新代码？
```bash
git pull
bash deploy-simple.sh
```

---

## 📞 需要帮助？

查看完整文档：
- [QUICK_START.md](QUICK_START.md)
- [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md)
