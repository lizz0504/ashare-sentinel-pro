-- ============================================
-- AShare Sentinel - 用户认证数据库迁移脚本
-- Supabase PostgreSQL Migration
-- ============================================

-- 1. 创建 profiles 表
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    is_vip BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 创建 watchlists 表 (用户自选股)
CREATE TABLE IF NOT EXISTS public.watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    cost_price NUMERIC(10, 2),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol) -- 防止同一用户重复添加同一股票
);

-- 3. 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON public.watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_symbol ON public.watchlists(symbol);

-- ============================================
-- 4. 开启行级安全 (RLS)
-- ============================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 5. RLS 策略 (Policies)
-- ============================================

-- profiles 表策略
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- watchlists 表策略
DROP POLICY IF EXISTS "Users can view own watchlist" ON public.watchlists;
CREATE POLICY "Users can view own watchlist" ON public.watchlists
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert to own watchlist" ON public.watchlists;
CREATE POLICY "Users can insert to own watchlist" ON public.watchlists
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own watchlist" ON public.watchlists;
CREATE POLICY "Users can update own watchlist" ON public.watchlists
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete from own watchlist" ON public.watchlists;
CREATE POLICY "Users can delete from own watchlist" ON public.watchlists
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- 6. 自动化 Trigger (新用户注册时自动创建 profile)
-- ============================================

-- 创建自动创建 profile 的函数
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, is_vip)
    VALUES (
        NEW.id,
        NEW.email,
        FALSE
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 删除旧的 trigger（如果存在）
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- 创建 trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- 7. 创建辅助函数（可选）
-- ============================================

-- 获取当前用户的 profile
CREATE OR REPLACE FUNCTION public.get_current_profile()
RETURNS TABLE (
    id UUID,
    email TEXT,
    is_vip BOOLEAN,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.id, p.email, p.is_vip, p.created_at
    FROM public.profiles p
    WHERE p.id = auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 获取当前用户的自选股列表
CREATE OR REPLACE FUNCTION public.get_user_watchlists()
RETURNS TABLE (
    id UUID,
    symbol TEXT,
    cost_price NUMERIC,
    notes TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT w.id, w.symbol, w.cost_price, w.notes, w.created_at
    FROM public.watchlists w
    WHERE w.user_id = auth.uid()
    ORDER BY w.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 添加自选股（带重复检查）
CREATE OR REPLACE FUNCTION public.add_to_watchlist(
    p_symbol TEXT,
    p_cost_price NUMERIC DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    INSERT INTO public.watchlists (user_id, symbol, cost_price, notes)
    VALUES (auth.uid(), p_symbol, p_cost_price, p_notes)
    ON CONFLICT (user_id, symbol) DO UPDATE SET
        cost_price = COALESCE(EXCLUDED.cost_price, watchlists.cost_price),
        notes = COALESCE(EXCLUDED.notes, watchlists.notes),
        created_at = NOW()
    RETURNING jsonb_build_object(
        'success', true,
        'symbol', symbol,
        'cost_price', cost_price,
        'created_at', created_at
    ) INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 从自选股移除
CREATE OR REPLACE FUNCTION public.remove_from_watchlist(p_symbol TEXT)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    DELETE FROM public.watchlists
    WHERE user_id = auth.uid() AND symbol = p_symbol;

    v_result := jsonb_build_object(
        'success', true,
        'symbol', p_symbol
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 执行完成
-- ============================================
-- 迁移脚本执行完毕
-- 你现在可以使用以下 Supabase 客户端功能：
-- - supabase.auth.signUp() 注册用户会自动创建 profile
-- - supabase.from('watchlists').select() 查询自选股（自动过滤用户数据）
-- - supabase.from('watchlists').insert() 添加自选股
-- - supabase.rpc('add_to_watchlist', { p_symbol: '600519' }) 调用存储过程
