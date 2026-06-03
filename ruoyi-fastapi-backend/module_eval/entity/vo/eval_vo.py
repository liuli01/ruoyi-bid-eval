"""评审模块 Pydantic VO 模型"""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class EvalProjectModel(BaseModel):
    """评审项目 VO"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    project_id: int | None = Field(default=None, description='项目主键')
    project_name: str | None = Field(default=None, description='项目名称')
    country: str | None = Field(default=None, description='国别')
    amount: str | None = Field(default=None, description='合同金额')
    stage: str | None = Field(default=None, description='阶段')
    mode: str | None = Field(default=None, description='模式')
    status: str | None = Field(default=None, description='状态')
    project_path: str | None = Field(default=None, description='项目文件路径')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')


class EvalProjectPageQuery(EvalProjectModel):
    """项目分页查询"""
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EvalReviewModel(BaseModel):
    """评审记录 VO"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    review_id: int | None = Field(default=None, description='评审主键')
    project_id: int | None = Field(default=None, description='项目ID')
    review_mode: str | None = Field(default=None, description='模式')
    status: str | None = Field(default=None, description='状态')
    current_step: str | None = Field(default=None, description='当前步骤')
    triggered_count: int | None = Field(default=None, description='触发规则数')
    insufficient_count: int | None = Field(default=None, description='无法判断数')
    llm_calls: int | None = Field(default=None, description='LLM调用次数')
    elapsed_sec: float | None = Field(default=None, description='耗时')
    error_msg: str | None = Field(default=None, description='错误信息')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')


class EvalOpinionModel(BaseModel):
    """评审意见 VO"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    opinion_id: int | None = Field(default=None, description='意见主键')
    review_id: int | None = Field(default=None, description='评审ID')
    department: str | None = Field(default=None, description='部门')
    rule_id: str | None = Field(default=None, description='规则ID')
    title: str | None = Field(default=None, description='标题')
    content: str | None = Field(default=None, description='内容')
    risk_level: str | None = Field(default=None, description='风险等级')
    evidence: str | None = Field(default=None, description='证据')
    sort_order: int | None = Field(default=None, description='排序')


class StartReviewModel(BaseModel):
    """启动评审请求"""
    model_config = ConfigDict(alias_generator=to_camel)

    project_id: int = Field(description='项目ID')
    review_mode: Literal['complete', 'standard', 'fast'] = Field(default='complete', description='评审模式')


class RuleJudgmentVO(BaseModel):
    """单条规则判断结果"""
    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(default='', description='规则ID')
    triggered: bool | Literal['insufficient'] = Field(default=False, description='是否触发')
    evidence: str = Field(default='', description='证据')
    source: str = Field(default='', description='来源')
    reason: str = Field(default='', description='理由')
    inference_type: str = Field(default='material_based', description='推理类型')


class PipelineProgressVO(BaseModel):
    """流水线进度"""
    step: str = Field(description='步骤名')
    label: str = Field(description='步骤标签')
    status: Literal['running', 'done', 'error'] = Field(description='状态')
    payload: dict[str, Any] | None = Field(default=None, description='附加数据')
