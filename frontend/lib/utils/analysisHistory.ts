import { supabase } from '@/lib/supabaseClient'

export interface AnalysisRecord {
  id: string
  stock_code: string
  stock_name: string
  created_at: string
  agent_scores: any
  radar_data: any
  summary: string
}

export async function saveAnalysis(data: any) {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('未登录')
    const { data: record, error } = await supabase
      .from('analysis_history')
      .insert({ user_id: user.id, ...data })
      .select()
      .single()
    if (error) throw error
    return record
  } catch (error) {
    console.error('保存失败:', error)
    throw error
  }
}

export async function addAnalysisRecord(stockCode: string, stockName: string, analysisData: any) {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('未登录')
    const { data: record, error } = await supabase
      .from('analysis_history')
      .insert({
        user_id: user.id,
        stock_code: stockCode,
        stock_name: stockName,
        agent_scores: analysisData.agent_scores,
        radar_data: analysisData.radar_data,
        summary: analysisData.summary,
        created_at: new Date().toISOString()
      })
      .select()
      .single()
    if (error) throw error
    return record
  } catch (error) {
    console.error('添加失败:', error)
    throw error
  }
}

export async function getAnalysisHistory(stockCode?: string) {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return []
    let query = supabase
      .from('analysis_history')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
    if (stockCode) query = query.eq('stock_code', stockCode)
    const { data, error } = await query
    if (error) throw error
    return data || []
  } catch (error) {
    console.error('获取失败:', error)
    return []
  }
}

export async function getMergedAnalysisHistory(stockCode?: string) {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return []
    let query = supabase
      .from('analysis_history')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
    if (stockCode) query = query.eq('stock_code', stockCode)
    const { data, error } = await query
    if (error) throw error
    const merged = data?.reduce((acc: any, record: any) => {
      const existing = acc.find((r: any) => r.stock_code === record.stock_code)
      if (existing) {
        existing.records.push(record)
      } else {
        acc.push({
          stock_code: record.stock_code,
          stock_name: record.stock_name,
          records: [record]
        })
      }
      return acc
    }, []) || []
    return merged
  } catch (error) {
    console.error('获取失败:', error)
    return []
  }
}

export async function deleteAnalysis(id: string) {
  try {
    const { error } = await supabase
      .from('analysis_history')
      .delete()
      .eq('id', id)
    if (error) throw error
    return true
  } catch (error) {
    console.error('删除失败:', error)
    throw error
  }
}

export async function deleteStockAllRecords(stockCode: string) {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('未登录')
    const { error } = await supabase
      .from('analysis_history')
      .delete()
      .eq('user_id', user.id)
      .eq('stock_code', stockCode)
    if (error) throw error
    return true
  } catch (error) {
    console.error('删除失败:', error)
    throw error
  }
}
