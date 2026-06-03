"""评审管理服务层"""
import json
import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from config.env import AppConfig, UploadConfig
from exceptions.exception import ServiceException
from module_eval.dao.eval_dao import EvalProjectDao, EvalReviewDao, EvalOpinionDao
from module_eval.entity.do.eval_do import EvalProject, EvalReview
from module_eval.entity.vo.eval_vo import (
    EvalProjectModel, EvalProjectPageQuery, EvalReviewModel,
    EvalOpinionModel, RuleJudgmentVO, PipelineProgressVO,
)
from utils.common_util import CamelCaseUtil
from utils.log_util import logger

# 规则目录
RULES_DIR = Path(__file__).resolve().parent.parent / 'rules'
CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'
PROJECTS_DIR = Path(UploadConfig.UPLOAD_PATH) / 'eval_projects'


class EvalProjectService:
    """评审项目管理服务"""

    @classmethod
    async def get_project_list_services(
        cls, query_db: AsyncSession, query_object: EvalProjectPageQuery, data_scope_sql: ColumnElement, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await EvalProjectDao.get_project_list(query_db, query_object, data_scope_sql, is_page)

    @classmethod
    async def add_project_services(cls, query_db: AsyncSession, project: EvalProjectModel) -> CrudResponseModel:
        from sqlalchemy import text
        try:
            # Use raw SQL to avoid ORM greenlet issue
            result = await query_db.execute(
                text("INSERT INTO eval_project (project_name, country, amount, stage, mode, status, create_by, create_time) VALUES (:name, :country, :amount, :stage, :mode, 'pending', :user, NOW())"),
                {'name': project.project_name or '', 'country': project.country or '', 'amount': project.amount or '', 'stage': project.stage or '', 'mode': project.mode or '', 'user': project.create_by or 'system'}
            )
            await query_db.commit()
            project_id = result.lastrowid
            return CrudResponseModel(is_success=True, message='新增成功', result={'projectId': project_id})
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def delete_project_services(cls, query_db: AsyncSession, project_id: int) -> CrudResponseModel:
        project = await EvalProjectDao.get_project_by_id(query_db, project_id)
        if not project:
            raise ServiceException(message='项目不存在')
        try:
            await EvalProjectDao.delete_project(query_db, project_id)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def project_detail_services(cls, query_db: AsyncSession, project_id: int) -> EvalProjectModel:
        project = await EvalProjectDao.get_project_by_id(query_db, project_id)
        result = EvalProjectModel(**CamelCaseUtil.transform_result(project)) if project else EvalProjectModel()
        return result


class EvalPipelineService:
    """评审流水线服务 - 适配 os-bid-eval-web 核心逻辑"""

    @classmethod
    def _load_rules(cls) -> dict[str, Any]:
        """加载规则 YAML 文件"""
        import yaml
        rules = {'p_rules': [], 'r_rules': [], 'trigger_chains': {}}
        for key, filename in [('p_rules', 'p_rules.yaml'), ('r_rules', 'r_rules.yaml'), ('trigger_chains', 'trigger_chains.yaml')]:
            path = RULES_DIR / filename
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    rules[key] = data or ([] if key != 'trigger_chains' else {})
        return rules

    @classmethod
    def _get_project_dir(cls, project_id: int) -> Path:
        """获取项目文件目录"""
        project_dir = PROJECTS_DIR / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    @classmethod
    async def start_review_services(
        cls,
        query_db: AsyncSession,
        project_id: int,
        review_mode: str = 'complete',
        user_name: str = '',
    ) -> CrudResponseModel:
        """启动评审流水线"""
        project = await EvalProjectDao.get_project_by_id(query_db, project_id)
        if not project:
            raise ServiceException(message='项目不存在')

        # 创建评审记录
        review_data = {
            'project_id': project_id,
            'review_mode': review_mode,
            'status': 'running',
            'current_step': 'step0',
            'create_by': user_name or 'system',
        }
        try:
            review = await EvalReviewDao.add_review(query_db, review_data)
            await query_db.commit()
            return CrudResponseModel(
                is_success=True,
                message='评审已启动',
                data={'review_id': review.review_id},
            )
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def _run_llm_judgment(
        cls,
        rules: list[dict],
        materials_text: str,
        project_context: dict[str, Any] | None = None,
        review_mode: str = 'complete',
    ) -> dict[str, Any]:
        """执行规则判断 (封装 rule_judgment_engine 核心逻辑)

        此方法将逐步适配为通过 RuoYi module_ai 的 LiteLLM 调用，
        当前保留原有逻辑结构。
        """
        batch_config_path = CONFIG_DIR / 'rule_batches.yaml'
        import yaml

        # 1. 加载批次配置
        batches = []
        if batch_config_path.exists():
            with open(batch_config_path, 'r', encoding='utf-8') as f:
                batch_config = yaml.safe_load(f)
                batches = batch_config.get('batches', [])

        # 2. 按维度分组规则
        dim_groups: dict[str, list[dict]] = {}
        for rule in rules:
            dim = rule.get('dimension', rule.get('category', 'default'))
            if dim not in dim_groups:
                dim_groups[dim] = []
            dim_groups[dim].append(rule)

        # 3. 批次分配（简化版）
        batch_assignments: dict[str, list[dict]] = {}
        for batch in batches:
            bid = batch.get('id', 'default')
            keywords = batch.get('keywords', [])
            batch_rules = []
            for rule in rules:
                rule_text = str(rule.get('full_text', '')) + str(rule.get('name', ''))
                if any(kw in rule_text for kw in keywords):
                    batch_rules.append(rule)
            if batch_rules:
                batch_assignments[bid] = batch_rules

        # 4. 执行判断（当前为占位，后续接入 LiteLLM）
        triggered_rules = []
        insufficient_rules = []
        all_judgments = {}

        for bid, batch_rules in batch_assignments.items():
            # 构建 prompt
            batch_prompt = cls._build_batch_prompt(bid, batch_rules, materials_text, project_context)

            # TODO: 通过 RuoYi module_ai 的 AiUtil 调用 LLM
            # 当前使用 os-bid-eval-web 原有 llm_client 逻辑的简化版
            judgments = await cls._call_llm_for_batch(batch_prompt, batch_rules)

            triggered = [j for j in judgments if j.get('triggered') is True]
            insufficient = [j for j in judgments if j.get('triggered') == 'insufficient']

            triggered_rules.extend(j['rule_id'] for j in triggered)
            insufficient_rules.extend(
                {'rule_id': j['rule_id'], 'reason': j.get('reason', ''), 'evidence': j.get('evidence', '')}
                for j in insufficient
            )
            all_judgments[bid] = judgments

        # 5. 应用触发链
        all_judgments = cls._apply_trigger_chains(all_judgments, triggered_rules, materials_text)

        return {
            'triggered_rules': list(set(triggered_rules)),
            'insufficient_rules': insufficient_rules,
            'judgments': all_judgments,
            'llm_calls': len(batch_assignments),
        }

    @classmethod
    def _build_batch_prompt(
        cls, batch_id: str, rules: list[dict], materials_text: str, project_context: dict[str, Any] | None
    ) -> str:
        """构建批次提示词"""
        import datetime
        now = datetime.datetime.now()
        prompt = f"""你是一个专业的海外工程项目风险评审专家。
当前时间：{now.strftime('%Y-%m-%d %H:%M')}

## 项目上下文
"""
        if project_context:
            for k, v in project_context.items():
                if isinstance(v, str):
                    prompt += f"- {k}: {v}\n"

        prompt += f"""

## 评审规则（批次：{batch_id}）

请逐条阅读以下规则，根据项目材料判断每条规则是否触发：

"""
        for i, rule in enumerate(rules, 1):
            prompt += f"""
### 规则 {i}: {rule.get('rule_id', '')} - {rule.get('name', '')}
风险等级: {rule.get('level', 'medium')}
规则原文: {rule.get('full_text', '')}
制度依据: {rule.get('basis', '')}
"""

        prompt += f"""

## 项目材料

{materials_text[:12000]}

## 输出要求

请对每条规则输出JSON格式的判断结果：
```json
{{"rule_id": "xxx", "triggered": true/false/"insufficient", "evidence": "原文证据", "source": "来源", "reason": "判断理由"}}
```
"""
        return prompt

    @classmethod
    async def _call_llm_for_batch(cls, prompt: str, rules: list[dict]) -> list[dict]:
        """调用 LLM 执行批次判断

        后续将改为通过 RuoYi module_ai 的 AiUtil / LiteLLM 调用
        """
        # 简化实现：返回占位结果
        # TODO: 通过 RuoYi module_ai 的 AiUtil.get_model_from_factory() 调用 LLM
        results = []
        for rule in rules:
            results.append({
                'rule_id': rule.get('rule_id', ''),
                'triggered': 'insufficient',
                'evidence': '',
                'source': '',
                'reason': 'LLM 调用待适配 RuoYi module_ai',
                'inference_type': 'material_based',
            })
        return results

    @classmethod
    def _apply_trigger_chains(
        cls, judgments: dict[str, list[dict]], triggered: list[str], materials_text: str
    ) -> dict[str, list[dict]]:
        """应用触发链规则（简化版）"""
        chain_path = RULES_DIR / 'trigger_chains.yaml'
        if not chain_path.exists():
            return judgments

        import yaml
        with open(chain_path, 'r', encoding='utf-8') as f:
            chains = yaml.safe_load(f) or {}

        for chain in chains.get('chains', []):
            condition = chain.get('condition', {})
            ctype = condition.get('type', '')
            keyword = condition.get('keyword', '')
            target = chain.get('target_rule', '')
            action = chain.get('action', '')

            # 条件匹配
            matched = False
            if ctype == 'keyword_in_raw_text' and keyword and keyword in materials_text:
                matched = True
            elif ctype == 'keyword_in_trigger_content' and keyword:
                matched = any(keyword in r for r in triggered)

            if matched and action == 'trigger':
                # 添加触发规则到对应批次
                target_found = False
                for bid, judgments_list in judgments.items():
                    for j in judgments_list:
                        if j.get('rule_id') == target:
                            j['triggered'] = True
                            j['reason'] = f'触发链 {chain.get("chain_id", "")} 级联触发'
                            target_found = True
                            break
                    if target_found:
                        break

        return judgments

    @classmethod
    def _validate_results(
        cls, judgment_result: dict[str, Any], materials_text: str
    ) -> dict[str, Any]:
        """交叉验证（简化版）

        后续可集成 os-bid-eval-web 的 validation_layer.validate()
        """
        triggered = judgment_result.get('triggered_rules', [])
        insufficient = judgment_result.get('insufficient_rules', [])

        recommendations = []

        # 规则数量检查
        if len(triggered) > 60:
            recommendations.append('规则触发数量超过60条，请人工复核')
        elif len(triggered) < 5:
            recommendations.append('规则触发数量少于5条，可能遗漏风险')

        # 置信度检查
        if len(insufficient) > len(triggered):
            recommendations.append('无法判断数量超过触发数量，请人工复核')

        # 占位符检查
        for j_list in judgment_result.get('judgments', {}).values():
            for j in j_list:
                if '{' in j.get('evidence', '') and '}' in j.get('evidence', ''):
                    recommendations.append(f"规则 {j.get('rule_id', '')} evidence 含占位符")
                    break

        return {
            'overall_status': 'warning' if recommendations else 'ok',
            'rule_count': len(triggered),
            'insufficient_count': len(insufficient),
            'recommendations': recommendations,
        }

    @classmethod
    async def get_review_status_services(cls, query_db: AsyncSession, review_id: int) -> EvalReviewModel:
        """获取评审进度"""
        review = await EvalReviewDao.get_review_by_id(query_db, review_id)
        result = EvalReviewModel(**CamelCaseUtil.transform_result(review)) if review else EvalReviewModel()
        return result

    @classmethod
    async def get_review_opinions_services(cls, query_db: AsyncSession, review_id: int) -> list[EvalOpinionModel]:
        """获取评审意见"""
        opinions = await EvalOpinionDao.get_opinions_by_review(query_db, review_id)
        return [EvalOpinionModel(**CamelCaseUtil.transform_result(o)) for o in opinions]

    @classmethod
    async def run_full_pipeline(
        cls,
        project_id: int,
        review_mode: str = 'standard',
        user_name: str = '',
    ) -> CrudResponseModel:
        """执行完整评审流水线（在同步线程中运行）"""
        logger.info(f'run_full_pipeline 开始: project_id={project_id}')
        from module_eval.service.eval_pipeline_runner import run_pipeline as _run

        try:
            result = await _run(project_id, review_mode, user_name)
            logger.info(f'run_full_pipeline 完成: {result}')
            return CrudResponseModel(
                is_success=True,
                message='评审完成',
                result=result,
            )
        except Exception as e:
            logger.error(f'run_full_pipeline 失败: {e}', exc_info=True)
            raise ServiceException(message=str(e)[:300])
