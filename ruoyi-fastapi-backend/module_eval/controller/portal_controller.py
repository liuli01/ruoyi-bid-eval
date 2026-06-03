"""三门户控制器 — 会商/立项/一事一议"""
import json
from datetime import datetime
from typing import Annotated, Any
from fastapi import Body, Request
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from module_eval.entity.do.eval_do import EvalConsultation, EvalProjectApproval, EvalYiyi
from utils.log_util import logger
from utils.response_util import ResponseUtil
from utils.common_util import CamelCaseUtil

portal_controller = APIRouterPro(
    prefix='/portal', order_num=25, tags=['三门户'], dependencies=[PreAuthDependency()]
)


# ============================================================================
# 会商 (Consultation)
# ============================================================================

@portal_controller.get('/consultation/list')
async def list_consultation(request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """会商列表"""
    result = await query_db.execute(select(EvalConsultation).order_by(desc(EvalConsultation.create_time)))
    rows = result.scalars().all()
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=[CamelCaseUtil.transform_result(r) for r in rows])


@portal_controller.get('/consultation/{consult_id}')
async def get_consultation(consult_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """会商详情"""
    r = (await query_db.execute(select(EvalConsultation).where(EvalConsultation.id == consult_id))).scalars().first()
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=CamelCaseUtil.transform_result(r) if r else None)


@portal_controller.post('/consultation')
async def create_consultation(
    request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()],
    body: Annotated[dict, Body(...)]
):
    """创建会商"""
    from sqlalchemy import text
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    r = await query_db.execute(
        text("INSERT INTO eval_consultation (project_id, status, initiator, materials_json, create_by, create_time) VALUES (:pid, 'draft', :init, :mats, :user, :now)"),
        {'pid': body.get('projectId', 0), 'init': body.get('initiator', ''), 'mats': json.dumps(body.get('materials', []), ensure_ascii=False), 'user': 'admin', 'now': now}
    )
    await query_db.commit()
    return ResponseUtil.success(data={'id': r.lastrowid})


@portal_controller.post('/consultation/{consult_id}/approve')
async def approve_consultation(
    consult_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()],
    body: Annotated[dict, Body(...)]
):
    """会商审批操作: officer_review/draft_doc/leader_approval/office_review/submit/receipt"""
    from sqlalchemy import text
    action = body.get('action', '')
    opinion = body.get('opinion', '')
    col_map = {'officer_review': 'officer_opinion', 'draft_doc': 'draft_doc', 'leader_approval': 'leader_opinion', 'office_review': 'office_opinion', 'submit': '', 'receipt': ''}
    status_map = {'officer_review': 'draft_doc', 'draft_doc': 'leader_approval', 'leader_approval': 'office_review', 'office_review': 'submitted', 'submit': 'submitted', 'receipt': 'receipted'}

    col = col_map.get(action, '')
    new_status = status_map.get(action, 'draft')

    if col and opinion:
        await query_db.execute(text(f"UPDATE eval_consultation SET {col}=:opin, status=:st, update_time=NOW() WHERE id=:id"), {'opin': opinion, 'st': new_status, 'id': consult_id})
    else:
        await query_db.execute(text("UPDATE eval_consultation SET status=:st, update_time=NOW() WHERE id=:id"), {'st': new_status, 'id': consult_id})
    await query_db.commit()
    return ResponseUtil.success(msg=f'已推进至 {new_status}')


# ============================================================================
# 立项 (Project Approval)
# ============================================================================

@portal_controller.get('/approval/list')
async def list_approval(request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """立项列表"""
    result = await query_db.execute(select(EvalProjectApproval).order_by(desc(EvalProjectApproval.create_time)))
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=[CamelCaseUtil.transform_result(r) for r in result.scalars().all()])


@portal_controller.get('/approval/{approval_id}')
async def get_approval(approval_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """立项详情"""
    r = (await query_db.execute(select(EvalProjectApproval).where(EvalProjectApproval.id == approval_id))).scalars().first()
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=CamelCaseUtil.transform_result(r) if r else None)


@portal_controller.post('/approval')
async def create_approval(
    request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()],
    body: Annotated[dict, Body(...)]
):
    """创建立项"""
    from sqlalchemy import text
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    r = await query_db.execute(
        text("INSERT INTO eval_project_approval (project_id, status, trigger_reasons, materials_json, create_by, create_time) VALUES (:pid, 'draft', :reasons, :mats, :user, :now)"),
        {'pid': body.get('projectId', 0), 'reasons': ','.join(body.get('triggerReasons', [])), 'mats': json.dumps(body.get('materials', []), ensure_ascii=False), 'user': 'admin', 'now': now}
    )
    await query_db.commit()
    return ResponseUtil.success(data={'id': r.lastrowid})


# ============================================================================
# 一事一议 (Yishi Yiyi)
# ============================================================================

@portal_controller.get('/yiyi/list')
async def list_yiyi(request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """一事一议列表"""
    result = await query_db.execute(select(EvalYiyi).order_by(desc(EvalYiyi.create_time)))
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=[CamelCaseUtil.transform_result(r) for r in result.scalars().all()])


@portal_controller.get('/yiyi/{yiyi_id}')
async def get_yiyi(yiyi_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """一事一议详情"""
    r = (await query_db.execute(select(EvalYiyi).where(EvalYiyi.id == yiyi_id))).scalars().first()
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=CamelCaseUtil.transform_result(r) if r else None)


@portal_controller.post('/yiyi')
async def create_yiyi(
    request: Request, query_db: Annotated[AsyncSession, DBSessionDependency()],
    body: Annotated[dict, Body(...)]
):
    """创建一事一议"""
    from sqlalchemy import text
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    r = await query_db.execute(
        text("INSERT INTO eval_yiyi (project_id, status, apply_type, materials_json, create_by, create_time) VALUES (:pid, 'draft', :type, :mats, :user, :now)"),
        {'pid': body.get('projectId', 0), 'type': body.get('applyType', ''), 'mats': json.dumps(body.get('materials', []), ensure_ascii=False), 'user': 'admin', 'now': now}
    )
    await query_db.commit()
    return ResponseUtil.success(data={'id': r.lastrowid})


@portal_controller.post('/yiyi/{yiyi_id}/check')
async def check_yiyi(yiyi_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()], body: Annotated[dict, Body(...)]):
    """一事一议受理条件核验"""
    from sqlalchemy import text
    # 模拟核验逻辑
    check_result = {
        'market_category': {'pass': True, 'value': '非受限', 'threshold': '非受限'},
        'safety_level': {'pass': True, 'value': 'B级', 'threshold': '不得超过C级'},
        'amount_threshold': {'pass': body.get('amountThreshold', True), 'value': '达标', 'threshold': '≥500万美元'},
        'funding': {'pass': True, 'value': '已落实', 'threshold': '资金落实'},
        'bid_procedure': {'pass': True, 'value': '合规', 'threshold': '招标程序合规'},
        'compliance': {'pass': True, 'value': '无异常', 'threshold': '合规无风险'},
        'org_setup': {'pass': True, 'value': '已设立', 'threshold': '海外机构已设立'},
    }
    if body.get('applyType') == '股份公司':
        check_result['profit_rate'] = {'pass': body.get('profitRate', 7) >= 6, 'value': f"{body.get('profitRate', 7)}%", 'threshold': '≥6%'}
    elif body.get('applyType') == '非股份公司':
        check_result['profit_rate'] = {'pass': body.get('profitRate', 7) >= 8, 'value': f"{body.get('profitRate', 7)}%", 'threshold': '≥8%'}
        check_result['payment_terms'] = {'pass': body.get('paymentTerms', 85) >= 85, 'value': f"{body.get('paymentTerms', 85)}%", 'threshold': '月进度≥85%'}
        check_result['penalty'] = {'pass': body.get('penaltyRate', 5) <= 7, 'value': f"{body.get('penaltyRate', 5)}%", 'threshold': '工期罚款≤7%'}

    all_pass = all(v['pass'] for v in check_result.values())
    new_status = 'reviewing' if all_pass else 'accept_rejected'
    await query_db.execute(
        text("UPDATE eval_yiyi SET eligibility_json=:json, status=:st WHERE id=:id"),
        {'json': json.dumps(check_result, ensure_ascii=False), 'st': new_status, 'id': yiyi_id}
    )
    await query_db.commit()
    return ResponseUtil.success(data={'checks': check_result, 'passed': all_pass})


@portal_controller.post('/yiyi/{yiyi_id}/llm-check')
async def llm_check_yiyi(yiyi_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()]):
    """一事一议 LLM 核验 — 调用 LLM 分析材料判断受理条件"""
    from sqlalchemy import text

    # 找申请记录
    yiyi = (await query_db.execute(select(EvalYiyi).where(EvalYiyi.id == yiyi_id))).scalars().first()
    if not yiyi:
        return JSONResponse(content={'code':404,'msg':'申请不存在'})

    # 读取项目材料
    from module_eval.service.eval_file_service import EvalFileService
    materials_text = ''

    # 使用同步引擎读取
    from sqlalchemy import create_engine
    from config.env import DataBaseConfig
    sync_url = f'mysql+pymysql://{DataBaseConfig.db_username}:{DataBaseConfig.db_password}@{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT file_name, text_content FROM eval_material WHERE project_id=:pid AND parse_status='done' AND text_content IS NOT NULL AND text_content != ''"),
            {'pid': yiyi.project_id}
        ).fetchall()
        parts = []
        for row in rows:
            parts.append(f"--- {row[0]} ---\n{(row[1] or '')[:3000]}")
        materials_text = '\n\n'.join(parts)

    if not materials_text:
        materials_text = '暂无上传材料'

    # 调用 LLM
    from module_eval.service.eval_llm_client import EvalLlmClient
    apply_type = yiyi.apply_type or ''
    prompt = f"""你是一事一议受理条件审核专家。请根据以下项目材料，判断受理条件是否满足。

承接模式: {apply_type}

检查项:
1. 市场分类 — 项目所在国别是否非受限市场？
2. 安全等级 — 安全风险等级是否不超过C级？
3. 合同额门槛 — 合同额是否≥500万美元？
4. 资金落实 — 项目资金是否已落实？
5. 招标程序 — 招标程序是否合规？
6. 合规风险 — 是否存在合规风险？
7. 机构设置 — 海外机构是否已设立？

{f"附加条件（{apply_type}模式）:" if apply_type else ""}
{f"- 利润率 ≥ {'6%' if apply_type=='股份公司' else '8%'}" if apply_type else ""}
{f"- 月进度付款 ≥ 85%（非股份公司）" if apply_type=='非股份公司' else ""}
{f"- 工期罚款 ≤ {'10%' if apply_type=='股份公司' else '7%'}" if apply_type=='非股份公司' else ""}

项目材料:
{materials_text[:8000]}

请输出 JSON 格式结果，每个检查项包含 pass(bool)、value(实际值)、threshold(阈值)、evidence(材料原文证据):
{{
  "checks": {{
    "market_category": {{"pass": true/false, "value": "...", "threshold": "非受限", "evidence": "..."}},
    ...
  }},
  "summary": "总评",
  "all_pass": true/false
}}
"""
    try:
        resp = EvalLlmClient.call_llm_sync([
            {'role': 'system', 'content': '你是一事一议受理条件审核专家。输出JSON。'},
            {'role': 'user', 'content': prompt},
        ])
        import re
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            result = json.loads(m.group(0))
        else:
            raise ValueError('JSON解析失败')
    except Exception as e:
        return JSONResponse(content={'code':500,'msg':f'LLM核验失败: {str(e)[:200]}'})

    all_pass = result.get('all_pass', False)
    new_status = 'reviewing' if all_pass else 'accept_rejected'
    await query_db.execute(
        text("UPDATE eval_yiyi SET eligibility_json=:json, status=:st WHERE id=:id"),
        {'json': json.dumps(result, ensure_ascii=False), 'st': new_status, 'id': yiyi_id}
    )
    await query_db.commit()
    return ResponseUtil.success(data=result)


@portal_controller.post('/yiyi/{yiyi_id}/approve')
async def approve_yiyi(yiyi_id: int, query_db: Annotated[AsyncSession, DBSessionDependency()], body: Annotated[dict, Body(...)]):
    """一事一议审批"""
    from sqlalchemy import text
    action = body.get('action', '')  # approve / reject
    opinion = body.get('opinion', '')
    new_status = 'approved' if action == 'approve' else 'rejected'
    await query_db.execute(
        text("UPDATE eval_yiyi SET leader_opinion=:opin, status=:st, update_time=NOW() WHERE id=:id"),
        {'opin': opinion, 'st': new_status, 'id': yiyi_id}
    )
    await query_db.commit()
    return ResponseUtil.success(msg=f'已{("同意" if action == "approve" else "拒绝")}')
