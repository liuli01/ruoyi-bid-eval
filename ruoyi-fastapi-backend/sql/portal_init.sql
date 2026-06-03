-- 三门户数据库初始化脚本

-- ----------------------------
-- 会商审批表
-- ----------------------------
DROP TABLE IF EXISTS `eval_consultation`;
CREATE TABLE `eval_consultation` (
    `id`               bigint       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`       bigint       NOT NULL COMMENT '关联项目ID',
    `status`           varchar(20)  NOT NULL DEFAULT 'draft' COMMENT '状态: draft/officer_review/draft_doc/leader_approval/office_review/submitted/receipted',
    `initiator`        varchar(100) DEFAULT '' COMMENT '经办人',
    `materials_json`   text                    COMMENT '上传材料JSON',
    `officer_opinion`  text                    COMMENT '经办人审核意见',
    `draft_doc`        text                    COMMENT '发函草稿',
    `leader_opinion`   text                    COMMENT '领导审批意见',
    `office_opinion`   text                    COMMENT '办公室核稿意见',
    `commerce_receipt` text                    COMMENT '商务部回执',
    `create_by`        varchar(64)  DEFAULT '' COMMENT '创建者',
    `create_time`      datetime                COMMENT '创建时间',
    `update_by`        varchar(64)  DEFAULT '' COMMENT '更新者',
    `update_time`      datetime                COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    KEY `idx_project` (`project_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='重大项目风险会商';

-- ----------------------------
-- 立项审批表
-- ----------------------------
DROP TABLE IF EXISTS `eval_project_approval`;
CREATE TABLE `eval_project_approval` (
    `id`               bigint       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`       bigint       NOT NULL COMMENT '关联项目ID',
    `status`           varchar(20)  NOT NULL DEFAULT 'draft' COMMENT '状态: draft/officer_review/draft_doc/leader_approval/office_review/submitted/receipted',
    `trigger_reasons`  varchar(200) DEFAULT '' COMMENT '触发条件: high_risk/cross_border/territory_dispute',
    `materials_json`   text                    COMMENT '9项附件JSON',
    `officer_opinion`  text                    COMMENT '经办人审核意见',
    `draft_doc`        text                    COMMENT '立项函草稿',
    `leader_opinion`   text                    COMMENT '领导审批意见',
    `office_opinion`   text                    COMMENT '办公室核稿意见',
    `commerce_receipt` text                    COMMENT '商务部批复',
    `create_by`        varchar(64)  DEFAULT '' COMMENT '创建者',
    `create_time`      datetime                COMMENT '创建时间',
    `update_by`        varchar(64)  DEFAULT '' COMMENT '更新者',
    `update_time`      datetime                COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    KEY `idx_project` (`project_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='特定项目立项';

-- ----------------------------
-- 一事一议表
-- ----------------------------
DROP TABLE IF EXISTS `eval_yiyi`;
CREATE TABLE `eval_yiyi` (
    `id`               bigint       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`       bigint       NOT NULL COMMENT '关联项目ID',
    `status`           varchar(20)  NOT NULL DEFAULT 'draft' COMMENT '状态: draft/pending_accept/accept_rejected/reviewing/approved/rejected',
    `apply_type`       varchar(50)  DEFAULT '' COMMENT '承接模式: 股份公司/非股份公司/分包',
    `materials_json`   text                    COMMENT '上传材料JSON',
    `eligibility_json` text                    COMMENT '受理条件核验JSON',
    `officer_opinion`  text                    COMMENT '经办人意见',
    `draft_doc`        text                    COMMENT '批复文单/正文',
    `leader_opinion`   text                    COMMENT '领导审批意见',
    `create_by`        varchar(64)  DEFAULT '' COMMENT '创建者',
    `create_time`      datetime                COMMENT '创建时间',
    `update_by`        varchar(64)  DEFAULT '' COMMENT '更新者',
    `update_time`      datetime                COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    KEY `idx_project` (`project_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='一事一议';
