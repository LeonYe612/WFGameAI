-- MySQL分布式账号管理数据库脚本
-- 严格按照WFGameAI多设备并发执行优化方案实现

-- 创建账号管理表
CREATE TABLE IF NOT EXISTS `ai_game_accounts` (
    `account_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '账号ID',
    `username` VARCHAR(100) NOT NULL UNIQUE COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    `status` ENUM('available', 'in_use', 'disabled') DEFAULT 'available' COMMENT '账号状态',
    `locked_by` VARCHAR(100) NULL COMMENT '锁定设备序列号',
    `lock_time` TIMESTAMP NULL COMMENT '锁定时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引优化
    INDEX `idx_status_locked` (`status`, `locked_by`) COMMENT '状态和锁定索引',
    INDEX `idx_locked_by` (`locked_by`) COMMENT '锁定设备索引',
    INDEX `idx_username` (`username`) COMMENT '用户名索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI游戏账号管理表';

-- 创建性能统计表（可选）
CREATE TABLE IF NOT EXISTS `performance_stats` (
    `stat_id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '统计ID',
    `device_count` INT NOT NULL COMMENT '设备数量',
    `execution_time` DECIMAL(10,2) NOT NULL COMMENT '执行时间(秒)',
    `performance_score` DECIMAL(5,3) NOT NULL COMMENT '性能得分',
    `strategy_used` VARCHAR(50) NOT NULL COMMENT '使用的策略',
    `success_rate` DECIMAL(5,4) DEFAULT NULL COMMENT '成功率',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',

    -- 索引
    INDEX `idx_device_count` (`device_count`) COMMENT '设备数量索引',
    INDEX `idx_created_at` (`created_at`) COMMENT '创建时间索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='性能统计表';

-- 插入示例账号数据（仅用于测试）
INSERT IGNORE INTO `game_accounts` (`username`, `password`, `phone`, `status`) VALUES
('test_user_001', 'test123456', '13800000001', 'available'),
('test_user_002', 'test123456', '13800000002', 'available'),
('test_user_003', 'test123456', '13800000003', 'available'),
('test_user_004', 'test123456', '13800000004', 'available'),
('test_user_005', 'test123456', '13800000005', 'available');

-- 查看表结构
SHOW CREATE TABLE `game_accounts`;
SHOW CREATE TABLE `performance_stats`;

-- 查看账号统计
SELECT
    status,
    COUNT(*) as count
FROM game_accounts
GROUP BY status;

-- 查看当前分配状态
SELECT
    locked_by,
    username,
    lock_time
FROM game_accounts
WHERE status = 'in_use'
ORDER BY lock_time DESC;
