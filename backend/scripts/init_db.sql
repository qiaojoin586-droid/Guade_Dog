-- ============================================================
-- 导盲AI智能体 - 数据库初始化脚本
-- 目标: MySQL 8.x, 字符集 utf8mb4
--
-- 用法:
--   mysql -u root -p < scripts/init_db.sql
--   (或 mysql -u root -p < init_db.sql 在 backend 目录下)
--
-- 说明:
--   [users]         与 alembic 迁移 001_initial_users.py 完全一致
--   [其余表]        骨架表, 依据 backend_design_plan.md §5 设计;
--                   各模块 models.py 尚未实现, 字段待模块负责人确认
--   如需重置数据库: 先执行文件末尾注释中的 DROP 语句再重跑本脚本
-- ============================================================

SET NAMES utf8mb4;

-- ---------- 1. 建库 ----------
CREATE DATABASE IF NOT EXISTS guide_dog
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE guide_dog;

-- ---------- 2. 建用户并授权 ----------
-- 与 backend/app/config.py 默认值一致; 若你的 .env 改了账号密码, 请同步修改
CREATE USER IF NOT EXISTS 'guide_dog_user'@'localhost' IDENTIFIED BY 'change-me';
CREATE USER IF NOT EXISTS 'guide_dog_user'@'%' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON guide_dog.* TO 'guide_dog_user'@'localhost';
GRANT ALL PRIVILEGES ON guide_dog.* TO 'guide_dog_user'@'%';
FLUSH PRIVILEGES;

-- ============================================================
-- 3. 建表
-- 通用约定:
--   * 主键统一 BIGINT UNSIGNED AUTO_INCREMENT
--   * 时间字段: created_at / updated_at
--   * 外键均建索引 (InnoDB 最佳实践)
-- ============================================================

-- ---------- 3.1 users (Conversation 模块, 与 alembic 迁移一致) ----------
CREATE TABLE IF NOT EXISTS users (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  phone         VARCHAR(20)     NULL COMMENT '手机号(登录凭证)',
  email         VARCHAR(120)    NULL COMMENT '邮箱',
  password_hash VARCHAR(256)    NOT NULL COMMENT '密码哈希(bcrypt)',
  name          VARCHAR(50)     NOT NULL COMMENT '姓名',
  role          VARCHAR(20)     NOT NULL DEFAULT 'blind' COMMENT '角色: blind/family/admin',
  status        VARCHAR(20)     NOT NULL DEFAULT 'active' COMMENT '状态: active/disabled',
  avatar_url    VARCHAR(512)    NULL COMMENT '头像URL',
  medical_notes TEXT            NULL COMMENT '健康备注',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY ix_users_phone (phone),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ---------- 3.2 family_bindings (Conversation 模块) ----------
-- 盲人用户与家属绑定关系
CREATE TABLE IF NOT EXISTS family_bindings (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  blind_user_id BIGINT UNSIGNED NOT NULL COMMENT '盲人用户ID',
  family_user_id BIGINT UNSIGNED NOT NULL COMMENT '家属用户ID',
  status        VARCHAR(20)     NOT NULL DEFAULT 'pending' COMMENT '状态: pending/accepted/rejected',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_bind_pair (blind_user_id, family_user_id),
  KEY ix_family_user (family_user_id),
  CONSTRAINT fk_bind_blind  FOREIGN KEY (blind_user_id)  REFERENCES users (id),
  CONSTRAINT fk_bind_family FOREIGN KEY (family_user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='家属绑定表';

-- ---------- 3.3 user_devices (Conversation 模块) ----------
-- 用户设备/推送令牌, last_seen_at 用于在线状态心跳 (设计文档 §5.3)
CREATE TABLE IF NOT EXISTS user_devices (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id       BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  device_token  VARCHAR(255)    NOT NULL COMMENT '推送设备标识',
  platform      VARCHAR(20)     NULL COMMENT '平台: android/ios/other',
  last_seen_at  DATETIME        NULL COMMENT '最近心跳时间(在线状态)',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_device_token (device_token),
  KEY ix_devices_user (user_id),
  CONSTRAINT fk_devices_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户设备表';

-- ---------- 3.4 user_locations (Conversation 模块) ----------
-- 实时位置 (WebSocket 推送 + 家属端查询, 设计文档 §5.3)
CREATE TABLE IF NOT EXISTS user_locations (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id      BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  lat          DECIMAL(9,6)    NOT NULL COMMENT '纬度',
  lng          DECIMAL(9,6)    NOT NULL COMMENT '经度',
  accuracy     DECIMAL(9,2)    NULL COMMENT '定位精度(米)',
  source       VARCHAR(20)     NULL COMMENT '定位来源: gps/network/wifi',
  captured_at  DATETIME        NOT NULL COMMENT '定位采集时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
  PRIMARY KEY (id),
  KEY ix_locations_user_time (user_id, captured_at),
  CONSTRAINT fk_locations_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户实时位置表';

-- ---------- 3.5 sos_events (Safety 模块) ----------
-- dedup_key 唯一约束用于 60s 防重复触发 (设计文档 §5.3)
CREATE TABLE IF NOT EXISTS sos_events (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id      BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  lat          DECIMAL(9,6)    NULL COMMENT '求救纬度',
  lng          DECIMAL(9,6)    NULL COMMENT '求救经度',
  sos_type     VARCHAR(20)     NOT NULL DEFAULT 'sos' COMMENT '类型: sos/fall/custom',
  status       VARCHAR(20)     NOT NULL DEFAULT 'active' COMMENT '状态: active/processing/resolved/expired',
  dedup_key    VARCHAR(64)     NOT NULL COMMENT '去重键(用户+时间窗)',
  voice_msg    TEXT            NULL COMMENT '语音求助内容',
  triggered_at DATETIME        NOT NULL COMMENT '触发时间',
  resolved_at  DATETIME        NULL COMMENT '解决时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_sos_dedup (dedup_key),
  KEY ix_sos_user_time (user_id, triggered_at),
  CONSTRAINT fk_sos_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SOS求救事件表';

-- ---------- 3.6 navigation_history (Navigation 模块) ----------
CREATE TABLE IF NOT EXISTS navigation_history (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id      BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  start_lat    DECIMAL(9,6)    NULL COMMENT '起点纬度',
  start_lng    DECIMAL(9,6)    NULL COMMENT '起点经度',
  end_lat      DECIMAL(9,6)    NULL COMMENT '终点纬度',
  end_lng      DECIMAL(9,6)    NULL COMMENT '终点经度',
  mode         VARCHAR(20)     NULL COMMENT '出行方式: walking/bus/other',
  distance_m   INT             NULL COMMENT '距离(米)',
  duration_sec INT             NULL COMMENT '耗时(秒)',
  route_data   JSON            NULL COMMENT '路线详情(高德返回)',
  status       VARCHAR(20)     NOT NULL DEFAULT 'completed' COMMENT '状态: navigating/completed/aborted/failed',
  started_at   DATETIME        NULL COMMENT '开始时间',
  ended_at     DATETIME        NULL COMMENT '结束时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY ix_nav_user_time (user_id, started_at),
  CONSTRAINT fk_nav_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='导航历史表';

-- ---------- 3.7 reminders (Perception 模块) ----------
CREATE TABLE IF NOT EXISTS reminders (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id      BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  title        VARCHAR(100)    NOT NULL COMMENT '提醒标题',
  content      TEXT            NULL COMMENT '提醒内容',
  remind_at    DATETIME        NOT NULL COMMENT '提醒时间',
  repeat_rule  VARCHAR(50)     NULL COMMENT '重复规则: once/daily/weekly/YYYY-MM-DD...',
  status       VARCHAR(20)     NOT NULL DEFAULT 'pending' COMMENT '状态: pending/triggered/cancelled',
  triggered_at DATETIME        NULL COMMENT '实际触发时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY ix_reminders_user_time (user_id, remind_at),
  CONSTRAINT fk_reminders_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提醒表';

-- ---------- 3.8 medicines (Safety 模块) ----------
CREATE TABLE IF NOT EXISTS medicines (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id       BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  name          VARCHAR(100)    NOT NULL COMMENT '药品名称',
  dosage        VARCHAR(100)    NULL COMMENT '用量(如: 每次1片)',
  frequency     VARCHAR(100)    NULL COMMENT '频次(如: 每日3次)',
  schedule_json JSON            NULL COMMENT '服用时间点 [{"time":"08:00","dose":"1片"}]',
  start_date    DATE            NULL COMMENT '开始日期',
  end_date      DATE            NULL COMMENT '结束日期',
  notes         TEXT            NULL COMMENT '备注',
  status        VARCHAR(20)     NOT NULL DEFAULT 'active' COMMENT '状态: active/paused/stopped',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY ix_medicines_user (user_id),
  CONSTRAINT fk_medicines_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='药品表';

-- ---------- 3.9 ocr_records (Perception 模块) ----------
CREATE TABLE IF NOT EXISTS ocr_records (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id     BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  image_url   VARCHAR(512)    NULL COMMENT '原图地址',
  text        TEXT            NULL COMMENT '识别文本',
  result_json JSON            NULL COMMENT '完整识别结果',
  duration_ms INT             NULL COMMENT '识别耗时(毫秒)',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY ix_ocr_user_time (user_id, created_at),
  CONSTRAINT fk_ocr_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OCR识别记录表';

-- ---------- 3.10 conversation_logs (Conversation 模块) ----------
-- session_expire_at 用于定时清理过期会话 (设计文档 §5.3)
CREATE TABLE IF NOT EXISTS conversation_logs (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id           BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  session_id        VARCHAR(64)     NOT NULL COMMENT '会话ID',
  role              VARCHAR(20)     NOT NULL COMMENT '角色: user/assistant/system',
  content           TEXT            NOT NULL COMMENT '消息内容',
  intent            VARCHAR(50)     NULL COMMENT '意图标签(Orchestrator 判定)',
  audio_url         VARCHAR(512)    NULL COMMENT '音频地址',
  session_expire_at DATETIME        NULL COMMENT '会话过期时间(过期后清理)',
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY ix_clogs_session (session_id),
  KEY ix_clogs_user_time (user_id, created_at),
  CONSTRAINT fk_clogs_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话记录表';

-- ---------- 3.11 weather_cache (Perception 模块) ----------
-- 30min 内直接返回缓存 (设计文档 §5.3)
CREATE TABLE IF NOT EXISTS weather_cache (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  location_key VARCHAR(64)     NOT NULL COMMENT '位置键(城市名或 lat,lng)',
  weather_json JSON            NOT NULL COMMENT '天气数据(和风返回)',
  expires_at   DATETIME        NOT NULL COMMENT '过期时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_weather_key (location_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天气缓存表';

-- ---------- 3.12 user_addresses (常用地址簿) ----------
-- 用户对地址增删改查; 语音“我要去公司”按 label 别名匹配
CREATE TABLE IF NOT EXISTS user_addresses (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id    BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  label      VARCHAR(20)     NOT NULL COMMENT '别名: 家/公司/健身房',
  address    VARCHAR(255)    NOT NULL COMMENT '详细地址',
  lat        DOUBLE          NULL COMMENT '纬度',
  lng        DOUBLE          NULL COMMENT '经度',
  is_default TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否默认地址',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_addresses_label (user_id, label),
  KEY ix_user_addresses_user (user_id),
  CONSTRAINT fk_addresses_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='常用地址表';

-- ============================================================
-- 重置数据库(可选, 取消注释后执行)
--   DROP TABLE IF EXISTS weather_cache, conversation_logs, ocr_records,
--     medicines, reminders, navigation_history, sos_events,
--     user_locations, user_devices, family_bindings, users;
--   DROP DATABASE IF EXISTS guide_dog;
-- ============================================================
