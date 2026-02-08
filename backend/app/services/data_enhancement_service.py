# -*- coding: utf-8 -*-
"""
数据增强服务 - 智能估算缺失的财务指标

当Tushare数据缺失时，基于可用数据和行业特征进行智能估算
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 行业默认研发费率
INDUSTRY_RD_RATES = {
    "半导体": 12.0,
    "软件服务": 10.0,
    "电子": 8.0,
    "通信": 7.0,
    "医药生物": 6.0,
    "电气设备": 5.0,
    "机械设备": 4.0,
    "汽车": 4.0,
    "化工": 3.0,
    "食品饮料": 2.0,
    "纺织服装": 1.5,
    "建筑材料": 1.5,
    "房地产": 1.0,
    "银行": 1.0,
    "钢铁": 1.0,
    "采掘": 1.0,
    "交通运输": 1.0,
    "公用事业": 1.0,
    "商业贸易": 1.0,
    "休闲服务": 2.0,
    "农林牧渔": 2.0,
    "传媒": 3.0,
    "计算机": 10.0,
    "国防军工": 5.0,
    "家用电器": 3.0,
    "轻工制造": 2.0,
}

# 行业营收增长率默认值（基于行业生命周期）
INDUSTRY_GROWTH_RATES = {
    "半导体": 25.0,
    "软件服务": 20.0,
    "电子": 18.0,
    "通信": 15.0,
    "医药生物": 12.0,
    "电气设备": 15.0,
    "汽车": 10.0,
    "机械设备": 12.0,
    "化工": 8.0,
    "食品饮料": 8.0,
    "纺织服装": 5.0,
    "建筑材料": 6.0,
    "房地产": 3.0,
    "银行": 5.0,
    "钢铁": 4.0,
    "采掘": 5.0,
    "交通运输": 4.0,
    "公用事业": 3.0,
    "商业贸易": 6.0,
    "休闲服务": 10.0,
    "农林牧渔": 6.0,
    "传媒": 12.0,
    "计算机": 20.0,
    "国防军工": 12.0,
    "家用电器": 8.0,
    "轻工制造": 6.0,
}


def calculate_peg_ratio(pe_ratio: Optional[float], revenue_growth: Optional[float]) -> Optional[float]:
    """
    计算PEG比率

    PEG = PE / 营收增长率

    Args:
        pe_ratio: 市盈率
        revenue_growth: 营收增长率（百分比，如20表示20%）

    Returns:
        PEG比率，如果无法计算返回None
    """
    if pe_ratio is None or revenue_growth is None or revenue_growth == 0:
        return None

    try:
        peg = pe_ratio / revenue_growth
        return round(peg, 2)
    except (TypeError, ZeroDivisionError):
        return None


def estimate_revenue_growth(metrics_data: Dict[str, Any], industry: Optional[str] = None) -> Optional[float]:
    """
    估算营收增长率

    优先级：
    1. 使用 revenue_growth_cagr（如果存在）
    2. 使用 ROE 作为成长性代理指标
    3. 使用行业默认增长率

    Args:
        metrics_data: 指标数据字典
        industry: 所属行业

    Returns:
        估算的营收增长率（百分比）
    """
    # 1. 直接使用营收增长率（如果存在）
    if 'revenue_growth_cagr' in metrics_data and metrics_data['revenue_growth_cagr'] is not None:
        return metrics_data['revenue_growth_cagr']

    # 2. 使用ROE作为成长性代理（假设合理公司的增长率接近ROE）
    if 'roe' in metrics_data and metrics_data['roe'] is not None:
        roe = metrics_data['roe']
        if isinstance(roe, str):
            roe = float(roe.replace('%', ''))
        # 成长公司的增长率通常略高于ROE，保守估计用ROE的80%
        estimated_growth = roe * 0.8
        return round(estimated_growth, 1)

    # 3. 使用行业默认增长率
    if industry:
        for industry_key, growth_rate in INDUSTRY_GROWTH_RATES.items():
            if industry_key in industry:
                logger.info(f"[ESTIMATE] Using industry default growth rate for {industry}: {growth_rate}%")
                return growth_rate

    # 4. 最后使用保守估计10%
    logger.warning(f"[ESTIMATE] Using conservative growth rate 10% for unknown industry")
    return 10.0


def estimate_rd_intensity(metrics_data: Dict[str, Any], industry: Optional[str] = None) -> Optional[float]:
    """
    估算研发费率

    优先级：
    1. 使用 rd_intensity（如果存在）
    2. 使用行业默认研发费率

    Args:
        metrics_data: 指标数据字典
        industry: 所属行业

    Returns:
        估算的研发费率（百分比）
    """
    # 1. 直接使用研发费率（如果存在）
    if 'rd_intensity' in metrics_data and metrics_data['rd_intensity'] is not None:
        return metrics_data['rd_intensity']

    # 2. 使用行业默认研发费率
    if industry:
        for industry_key, rd_rate in INDUSTRY_RD_RATES.items():
            if industry_key in industry:
                logger.info(f"[ESTIMATE] Using industry default R&D rate for {industry}: {rd_rate}%")
                return rd_rate

    # 3. 使用保守估计3%（制造业平均水平）
    logger.warning(f"[ESTIMATE] Using conservative R&D rate 3% for unknown industry")
    return 3.0


def enhance_financial_metrics(
    metrics_data: Dict[str, Any],
    industry: Optional[str] = None
) -> Dict[str, Any]:
    """
    增强财务数据，智能填充缺失字段

    Args:
        metrics_data: 原始指标数据
        industry: 所属行业

    Returns:
        增强后的指标数据
    """
    enhanced = metrics_data.copy()

    # 估算营收增长率
    if 'revenue_growth_cagr' not in enhanced or enhanced['revenue_growth_cagr'] is None:
        estimated_growth = estimate_revenue_growth(enhanced, industry)
        if estimated_growth is not None:
            enhanced['revenue_growth_cagr'] = estimated_growth
            enhanced['revenue_growth_estimated'] = True
            logger.info(f"[ENHANCE] Estimated revenue growth: {estimated_growth}%")

    # 估算研发费率
    if 'rd_intensity' not in enhanced or enhanced['rd_intensity'] is None:
        estimated_rd = estimate_rd_intensity(enhanced, industry)
        if estimated_rd is not None:
            enhanced['rd_intensity'] = estimated_rd
            enhanced['rd_intensity_estimated'] = True
            logger.info(f"[ENHANCE] Estimated R&D intensity: {estimated_rd}%")

    # 计算PEG比率
    pe_ratio = enhanced.get('pe_ratio')
    if isinstance(pe_ratio, str):
        pe_ratio = float(pe_ratio) if pe_ratio != 'N/A' else None

    revenue_growth = enhanced.get('revenue_growth_cagr')
    if revenue_growth is not None:
        # 确保是百分比形式
        if revenue_growth < 1:  # 如果是小数形式，转换为百分比
            revenue_growth = revenue_growth * 100

    calculated_peg = calculate_peg_ratio(pe_ratio, revenue_growth)
    if calculated_peg is not None:
        enhanced['peg_ratio'] = calculated_peg
        enhanced['peg_ratio_calculated'] = True
        logger.info(f"[ENHANCE] Calculated PEG ratio: {calculated_peg}")

    return enhanced


def create_ai_context_with_estimates(
    metrics_data: Dict[str, Any],
    industry: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, str]:
    """
    创建AI上下文，包含估算值的说明

    Args:
        metrics_data: 指标数据
        industry: 所属行业
        symbol: 股票代码

    Returns:
        格式化的上下文字典
    """
    # 先增强数据
    enhanced = enhance_financial_metrics(metrics_data, industry)

    # 构建上下文
    context = {}

    # PEG比率
    if enhanced.get('peg_ratio') is not None:
        if enhanced.get('peg_ratio_calculated'):
            context['peg_ratio'] = f"{enhanced['peg_ratio']:.1f} (基于PE和营收增长率计算)"
        else:
            context['peg_ratio'] = f"{enhanced['peg_ratio']:.1f}"
    else:
        context['peg_ratio'] = "N/A"

    # 营收增长率
    if enhanced.get('revenue_growth_cagr') is not None:
        if enhanced.get('revenue_growth_estimated'):
            context['revenue_growth'] = f"{enhanced['revenue_growth_cagr']:.1f}% (基于ROE或行业平均值估算)"
        else:
            context['revenue_growth'] = f"{enhanced['revenue_growth_cagr']:.1f}%"
    else:
        context['revenue_growth'] = "N/A"

    # 研发费率
    if enhanced.get('rd_intensity') is not None:
        if enhanced.get('rd_intensity_estimated'):
            context['rd_expense'] = f"{enhanced['rd_intensity']:.1f}% (基于行业平均值估算)"
        else:
            context['rd_expense'] = f"{enhanced['rd_intensity']:.1f}%"
    else:
        context['rd_expense'] = "N/A"

    # 记录估算信息
    estimates = []
    if enhanced.get('revenue_growth_estimated'):
        estimates.append(f"营收增长率: {enhanced['revenue_growth_cagr']:.1f}%")
    if enhanced.get('rd_intensity_estimated'):
        estimates.append(f"研发费率: {enhanced['rd_intensity']:.1f}%")
    if enhanced.get('peg_ratio_calculated'):
        estimates.append(f"PEG比率: {enhanced['peg_ratio']:.1f}")

    if estimates and symbol:
        logger.info(f"[ESTIMATE] {symbol} - 使用估算值: {', '.join(estimates)}")

    return context
