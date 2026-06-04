-- 评审模块数据库初始化脚本
-- 适用于 MySQL 5.7+

-- ----------------------------
-- Table structure for eval_project
-- ----------------------------
DROP TABLE IF EXISTS `eval_project`;
CREATE TABLE `eval_project` (
    `project_id`    bigint       NOT NULL AUTO_INCREMENT COMMENT '项目主键',
    `project_name`  varchar(200) NOT NULL COMMENT '项目名称',
    `country`       varchar(100)          DEFAULT NULL COMMENT '国别',
    `amount`        varchar(100)          DEFAULT NULL COMMENT '合同金额',
    `stage`         varchar(50)           DEFAULT NULL COMMENT '阶段',
    `mode`          varchar(50)           DEFAULT NULL COMMENT '模式',
    `status`        varchar(20)  NOT NULL DEFAULT 'pending' COMMENT '状态 pending/running/completed/failed',
    `project_path`  varchar(500)          DEFAULT NULL COMMENT '项目文件路径',
    `material_hash` varchar(64)           DEFAULT NULL COMMENT '材料哈希(缓存用)',
    `create_by`     varchar(64)           DEFAULT '' COMMENT '创建者',
    `create_time`   datetime              DEFAULT NULL COMMENT '创建时间',
    `update_by`     varchar(64)           DEFAULT '' COMMENT '更新者',
    `update_time`   datetime              DEFAULT NULL COMMENT '更新时间',
    `remark`        varchar(500)          DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`project_id`) USING BTREE,
    KEY `idx_project_name` (`project_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='评审项目表';

-- ----------------------------
-- Table structure for eval_review
-- ----------------------------
DROP TABLE IF EXISTS `eval_review`;
CREATE TABLE `eval_review` (
    `review_id`         bigint       NOT NULL AUTO_INCREMENT COMMENT '评审主键',
    `project_id`        bigint       NOT NULL COMMENT '项目ID',
    `review_mode`       varchar(20)  NOT NULL DEFAULT 'complete' COMMENT '模式 complete/standard/fast',
    `status`            varchar(20)  NOT NULL DEFAULT 'running' COMMENT '状态 running/done/error',
    `current_step`      varchar(20)           DEFAULT NULL COMMENT '当前步骤 step0~step6',
    `triggered_count`   int                   DEFAULT 0 COMMENT '触发规则数',
    `insufficient_count` int                  DEFAULT 0 COMMENT '无法判断数',
    `llm_calls`         int                   DEFAULT 0 COMMENT 'LLM调用次数',
    `elapsed_sec`       decimal(10,2)          DEFAULT NULL COMMENT '耗时(秒)',
    `result_json`       text                   DEFAULT NULL COMMENT '结果JSON',
    `error_msg`         varchar(1000)          DEFAULT NULL COMMENT '错误信息',
    `create_by`         varchar(64)           DEFAULT '' COMMENT '创建者',
    `create_time`       datetime              DEFAULT NULL COMMENT '创建时间',
    PRIMARY KEY (`review_id`) USING BTREE,
    KEY `idx_project_id` (`project_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='评审流水线运行记录表';

-- ----------------------------
-- Table structure for eval_opinion
-- ----------------------------
DROP TABLE IF EXISTS `eval_opinion`;
CREATE TABLE `eval_opinion` (
    `opinion_id`   bigint       NOT NULL AUTO_INCREMENT COMMENT '意见主键',
    `review_id`    bigint       NOT NULL COMMENT '评审ID',
    `department`   varchar(100) NOT NULL COMMENT '部门',
    `rule_id`      varchar(50)           DEFAULT NULL COMMENT '规则ID',
    `title`        varchar(200)          DEFAULT NULL COMMENT '标题',
    `content`      text                   DEFAULT NULL COMMENT '内容',
    `risk_level`   varchar(20)           DEFAULT NULL COMMENT '风险等级 high/medium/low',
    `evidence`     text                   DEFAULT NULL COMMENT '证据原文',
    `source_path`  varchar(500)          DEFAULT NULL COMMENT '来源文件',
    `sort_order`   int                   DEFAULT 0 COMMENT '排序',
    `create_time`  datetime              DEFAULT NULL COMMENT '创建时间',
    PRIMARY KEY (`opinion_id`) USING BTREE,
    KEY `idx_review_id` (`review_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='评审意见表';

-- ----------------------------
-- Table structure for eval_material
-- ----------------------------
DROP TABLE IF EXISTS `eval_material`;
CREATE TABLE `eval_material` (
    `material_id`   bigint       NOT NULL AUTO_INCREMENT COMMENT '材料主键',
    `project_id`    bigint       NOT NULL COMMENT '项目ID',
    `file_name`     varchar(200) NOT NULL COMMENT '文件名',
    `file_path`     varchar(500) NOT NULL COMMENT '文件路径',
    `file_size`     bigint                DEFAULT NULL COMMENT '文件大小',
    `file_type`     varchar(50)           DEFAULT NULL COMMENT '文件类型',
    `category`      varchar(50)           DEFAULT '' COMMENT '文件分类: 请示函/招标文件/可研报告/法律意见/其他',
    `text_content`  text                   DEFAULT NULL COMMENT '提取的文本内容',
    `parse_status`  varchar(20)  NOT NULL DEFAULT 'pending' COMMENT '解析状态 pending/done/error',
    `create_time`   datetime              DEFAULT NULL COMMENT '创建时间',
    PRIMARY KEY (`material_id`) USING BTREE,
    KEY `idx_prj_material` (`project_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='评审材料表';

-- ----------------------------
-- 菜单权限初始化（需要根据实际菜单ID调整）
-- ----------------------------
-- 父菜单: 评审管理
-- INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
-- VALUES (2000, '评审管理', 0, 5, 'eval', 'layout', 0, 0, 'M', 0, 0, '', 'validate', 'admin', sysdate());

-- 子菜单: 项目管理
-- INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
-- VALUES (2001, '项目管理', 2000, 1, 'project', 'eval/project/index', 0, 0, 'C', 0, 0, 'eval:project:list', 'table', 'admin', sysdate());

-- 按钮权限:
-- eval:project:list    项目列表
-- eval:project:query   项目查询
-- eval:project:add    新增项目
-- eval:project:remove 删除项目
-- eval:review:start   启动评审
-- eval:review:query   查看评审

-- ----------------------------
-- 测试用户初始化（密码均为 admin123）
-- ----------------------------
INSERT INTO sys_user(user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, password, status, del_flag, create_by, create_time)
VALUES
(100, 103, 'waishi', '外事专员', '00', 'waishi@qq.com', '15888888888', '0', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', sysdate()),
(101, 103, 'yiyi', '一事一议专员', '00', 'yiyi@qq.com', '15888888888', '0', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', sysdate()),
(102, 103, 'reviewer', '评审专员', '00', 'reviewer@qq.com', '15888888888', '0', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', sysdate()),
(103, 101, 'leader', '海外部领导', '00', 'leader@qq.com', '15888888888', '0', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', sysdate());

-- 用户-角色关联
INSERT IGNORE INTO sys_user_role(user_id, role_id) VALUES
(100, 2),  -- waishi -> 普通角色
(101, 2),  -- yiyi -> 普通角色
(102, 2),  -- reviewer -> 普通角色
(103, 1);  -- leader -> 管理员角色

-- ----------------------------
-- 菜单权限初始化
-- ----------------------------
-- 评审概览（在评审管理目录下）
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (2001, '评审概览', 2000, 0, 'dashboard', 'eval/dashboard', 0, 0, 'C', 0, 0, 'eval:dashboard', 'dashboard', 'admin', sysdate());

-- 父菜单: 评审管理
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (2000, '评审管理', 0, 5, 'eval', NULL, 0, 0, 'M', 0, 0, '', 'validate', 'admin', sysdate());

-- 子菜单
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES
(2002, '项目管理', 2000, 1, 'project', 'eval/project/index', 0, 0, 'C', 0, 0, 'eval:project:list', 'table', 'admin', sysdate()),
(2005, '评审管理', 2000, 2, 'review', 'eval/review/index', 0, 0, 'C', 0, 0, 'eval:review:query', 'table', 'admin', sysdate()),
(2007, '规则管理', 2000, 3, 'rules', 'eval/rules', 0, 0, 'C', 0, 0, 'eval:rules', 'list', 'admin', sysdate()),
(2008, '系统设置', 2000, 4, 'settings', 'eval/settings', 0, 0, 'C', 0, 0, 'eval:settings', 'setting', 'admin', sysdate()),
(2012, '审计追溯', 2000, 5, 'audit', 'eval/audit', 0, 0, 'C', 0, 0, 'eval:audit', 'date', 'admin', sysdate()),
(2013, 'F3签报', 2000, 6, 'f3', 'eval/f3', 0, 0, 'C', 0, 0, 'eval:f3', 'upload', 'admin', sysdate()),
(2014, '国别字典', 2000, 7, 'country', 'eval/country', 0, 0, 'C', 0, 0, 'eval:country', 's-platform', 'admin', sysdate());

-- 按钮权限
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, menu_type, visible, status, perms, create_by, create_time)
VALUES
(2003, '新增项目', 2002, 1, '', 'F', 0, 0, 'eval:project:add', 'admin', sysdate()),
(2004, '删除项目', 2002, 2, '', 'F', 0, 0, 'eval:project:remove', 'admin', sysdate()),
(2006, '启动评审', 2005, 1, '', 'F', 0, 0, 'eval:review:start', 'admin', sysdate());

-- 一级门户菜单（目录类型，子菜单空路径保持URL不变）
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES
(2009, '风险会商', 0, 6, '/portal/consultation', NULL, 0, 0, 'M', 0, 0, '', 's-flag', 'admin', sysdate()),
(2010, '项目立项', 0, 7, '/portal/approval', NULL, 0, 0, 'M', 0, 0, '', 's-marketing', 'admin', sysdate()),
(2011, '一事一议', 0, 8, '/portal/yiyi', NULL, 0, 0, 'M', 0, 0, '', 's-check', 'admin', sysdate());

-- 门户子菜单（空路径=URL不变）
INSERT INTO sys_menu(menu_id, menu_name, parent_id, order_num, path, component, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES
(2015, '风险会商', 2009, 1, '', 'eval/consultation', 0, 0, 'C', 0, 0, 'portal:consultation', 's-flag', 'admin', sysdate()),
(2016, '项目立项', 2010, 1, '', 'eval/approval', 0, 0, 'C', 0, 0, 'portal:approval', 's-marketing', 'admin', sysdate()),
(2017, '一事一议', 2011, 1, '', 'eval/yiyi', 0, 0, 'C', 0, 0, 'portal:yiyi', 's-check', 'admin', sysdate());

-- 分配给管理员角色
INSERT INTO sys_role_menu(role_id, menu_id)
SELECT 1, menu_id FROM sys_menu WHERE menu_id >= 2000;
