#!/bin/bash
# 自动提交脚本 - 帮助快速提交修复

echo "🚀 自动提交工具"
echo "================================"

# 1. 运行质量检查
echo ""
echo "📋 步骤1: 运行质量检查..."
./check_quality.sh
if [ $? -ne 0 ]; then
    echo "❌ 质量检查未通过，取消提交"
    exit 1
fi

# 2. 显示修改的文件
echo ""
echo "📝 步骤2: 查看修改..."
git status --short

# 3. 询问提交信息
echo ""
echo "请输入提交信息 (默认: 'fix: 修复问题'):"
read COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="fix: 修复问题"
fi

# 4. 添加所有修改
echo ""
echo "➕ 步骤3: 添加修改到暂存区..."
git add .

# 5. 提交
echo ""
echo "💾 步骤4: 提交代码..."
git commit -m "$COMMIT_MSG"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 提交成功！"
    echo ""
    echo "📊 提交信息:"
    git log -1 --oneline
    echo ""
    echo "💡 推送到远程: git push"
else
    echo ""
    echo "❌ 提交失败"
    exit 1
fi
