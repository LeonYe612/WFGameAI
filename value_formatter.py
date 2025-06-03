def format_value_point(point, max_length=80):
    """格式化价值点，确保不超过最大长度"""
    if len(point) <= max_length:
        return point

    # 如果超过长度，尝试在合适位置截断
    parts = point.split('，')
    if len(parts) >= 2:
        return parts[0] + '，...'

    return point[:max_length-3] + '...'
