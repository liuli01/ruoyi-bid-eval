"""评审项目数据库模型"""
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, String, Text, Integer, Float
from config.database import Base
from config.env import DataBaseConfig
from utils.common_util import SqlalchemyUtil


class EvalProject(Base):
    """评审项目表"""
    __tablename__ = 'eval_project'
    __table_args__ = {'comment': '评审项目表'}

    project_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='项目主键')
    project_name = Column(String(200), nullable=False, comment='项目名称')
    country = Column(String(100), nullable=True, comment='国别')
    amount = Column(String(100), nullable=True, comment='合同金额')
    stage = Column(String(50), nullable=True, comment='阶段')
    mode = Column(String(50), nullable=True, comment='模式')
    status = Column(String(20), nullable=False, server_default='pending', comment='状态 pending/running/completed/failed')
    project_path = Column(String(500), nullable=True, comment='项目文件路径')
    material_hash = Column(String(64), nullable=True, comment='材料哈希(缓存用)')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    remark = Column(String(500), nullable=True, comment='备注')


class EvalReview(Base):
    """评审流水线运行记录表"""
    __tablename__ = 'eval_review'
    __table_args__ = {'comment': '评审流水线运行记录表'}

    review_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='评审主键')
    project_id = Column(BigInteger, nullable=False, comment='项目ID')
    review_mode = Column(String(20), nullable=False, server_default='complete', comment='模式 complete/standard/fast')
    status = Column(String(20), nullable=False, server_default='running', comment='状态 running/done/error')
    current_step = Column(String(20), nullable=True, comment='当前步骤 step0~step6')
    triggered_count = Column(Integer, nullable=True, default=0, comment='触发规则数')
    insufficient_count = Column(Integer, nullable=True, default=0, comment='无法判断数')
    llm_calls = Column(Integer, nullable=True, default=0, comment='LLM调用次数')
    elapsed_sec = Column(Float, nullable=True, comment='耗时(秒)')
    result_json = Column(Text, nullable=True, comment='结果JSON')
    error_msg = Column(String(1000), nullable=True, comment='错误信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class EvalOpinion(Base):
    """评审意见表"""
    __tablename__ = 'eval_opinion'
    __table_args__ = {'comment': '评审意见表'}

    opinion_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='意见主键')
    review_id = Column(BigInteger, nullable=False, comment='评审ID')
    department = Column(String(100), nullable=False, comment='部门')
    rule_id = Column(String(50), nullable=True, comment='规则ID')
    title = Column(String(200), nullable=True, comment='标题')
    content = Column(Text, nullable=True, comment='内容')
    risk_level = Column(String(20), nullable=True, comment='风险等级 high/medium/low')
    evidence = Column(Text, nullable=True, comment='证据原文')
    source_path = Column(String(500), nullable=True, comment='来源文件')
    sort_order = Column(Integer, nullable=True, default=0, comment='排序')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class EvalMaterial(Base):
    """评审材料表"""
    __tablename__ = 'eval_material'
    __table_args__ = {'comment': '评审材料表'}

    material_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='材料主键')
    project_id = Column(BigInteger, nullable=False, comment='项目ID')
    file_name = Column(String(200), nullable=False, comment='文件名')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, nullable=True, comment='文件大小')
    file_type = Column(String(50), nullable=True, comment='文件类型')
    category = Column(String(50), nullable=True, server_default="''", comment='文件分类: 请示函/招标文件/可研报告/法律意见/其他')
    text_content = Column(Text, nullable=True, comment='提取的文本内容')
    parse_status = Column(String(20), nullable=False, server_default='pending', comment='解析状态 pending/done/error')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
