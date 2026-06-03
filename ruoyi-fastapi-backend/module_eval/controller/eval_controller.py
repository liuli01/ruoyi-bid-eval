"""评审管理控制器 — 项目CRUD + 评审流水线 + SSE进度 + 文件上传"""
import json
import os
from datetime import datetime
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import Body, Path, Query, Request, Response, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.data_scope import DataScopeDependency
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_eval.entity.do.eval_do import EvalProject, EvalReview
from module_eval.entity.vo.eval_vo import (
    EvalProjectModel, EvalProjectPageQuery, EvalReviewModel,
    EvalOpinionModel, StartReviewModel,
)
from module_eval.service.eval_service import EvalProjectService, EvalPipelineService
from module_eval.service.eval_file_service import EvalFileService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from module_admin.entity.vo.user_vo import CurrentUserModel

eval_controller = APIRouterPro(
    prefix='/eval', order_num=20, tags=['评审管理'], dependencies=[PreAuthDependency()]
)


@eval_controller.get(
    '/dashboard',
    summary='Dashboard统计',
    description='评审系统首页统计概览',
)
async def dashboard(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """Dashboard 统计接口"""
    from sqlalchemy import select, func, desc

    # 项目统计
    total_projects = (await query_db.execute(select(func.count()).select_from(EvalProject))).scalar() or 0
    running_reviews = (await query_db.execute(
        select(func.count()).select_from(EvalReview).where(EvalReview.status == 'running')
    )).scalar() or 0
    done_reviews = (await query_db.execute(
        select(func.count()).select_from(EvalReview).where(EvalReview.status == 'done')
    )).scalar() or 0

    # 最近评审
    recent_rows = (await query_db.execute(
        select(EvalReview).order_by(desc(EvalReview.create_time)).limit(5)
    )).scalars().all()

    # 项目状态分布
    status_counts = {}
    for s in ('pending', 'running', 'completed', 'failed'):
        cnt = (await query_db.execute(
            select(func.count()).select_from(EvalProject).where(EvalProject.status == s)
        )).scalar() or 0
        status_counts[s] = cnt

    from utils.common_util import CamelCaseUtil
    recent = [CamelCaseUtil.transform_result(r) for r in recent_rows]

    return ResponseUtil.success(data={
        'totalProjects': total_projects,
        'runningReviews': running_reviews,
        'doneReviews': done_reviews,
        'projectStatusDistribution': status_counts,
        'recentReviews': recent,
    })


@eval_controller.get(
    '/settings',
    summary='系统设置',
    description='获取评审系统配置',
)
async def get_settings(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """读取评审系统配置"""
    import os
    from sqlalchemy import select, text
    # 从 sys_config 表读取
    keys = ['eval.review_mode', 'eval.llm_concurrency', 'eval.llm_model', 'eval.llm_base_url']
    configs = {}
    for k in keys:
        r = await query_db.execute(
            text("SELECT config_value FROM sys_config WHERE config_key=:key"),
            {'key': k}
        )
        row = r.fetchone()
        configs[k.split('.')[-1]] = row[0] if row else ''

    return ResponseUtil.success(data={
        'reviewMode': configs.get('review_mode', 'standard'),
        'llmConcurrency': int(configs.get('llm_concurrency', '5')),
        'llmModel': configs.get('llm_model', os.environ.get('DS_MODEL', 'deepseek-chat')),
        'llmBaseUrl': configs.get('llm_base_url', os.environ.get('DS_API_BASE', 'https://api.deepseek.com')),
        'llmConfigured': bool(os.environ.get('DS_API_KEY', '')),
    })


@eval_controller.post(
    '/settings',
    summary='保存设置',
    description='保存评审系统配置',
)
async def save_settings(
    request: Request,
    body: Annotated[dict, Body(description='配置项键值对')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """保存评审系统配置"""
    from sqlalchemy import text
    key_map = {
        'reviewMode': 'eval.review_mode',
        'llmConcurrency': 'eval.llm_concurrency',
        'llmModel': 'eval.llm_model',
        'llmBaseUrl': 'eval.llm_base_url',
    }
    try:
        for field, value in body.items():
            config_key = key_map.get(field)
            if not config_key:
                continue
            # upsert
            await query_db.execute(
                text("""
                    INSERT INTO sys_config (config_name, config_key, config_value, config_type, create_by, create_time)
                    VALUES (:name, :key, :value, 'Y', 'admin', NOW())
                    ON DUPLICATE KEY UPDATE config_value=:value2
                """),
                {'name': config_key, 'key': config_key, 'value': str(value), 'value2': str(value)}
            )
        await query_db.commit()
        return ResponseUtil.success(msg='设置已保存')
    except Exception as e:
        await query_db.rollback()
        return JSONResponse(content={'code': 500, 'msg': str(e)[:200]})


@eval_controller.post(
    '/llm/test',
    summary='测试 LLM 连接',
    description='用一条简单 prompt 测试 LLM 是否可用',
)
async def test_llm(request: Request) -> Response:
    """测试 LLM 连接"""
    from module_eval.service.eval_llm_client import EvalLlmClient
    import time
    t0 = time.time()
    try:
        resp = EvalLlmClient.call_llm_sync([
            {'role': 'user', 'content': '回复数字 42 即可。'}
        ])
        elapsed = round(time.time() - t0, 2)
        return JSONResponse(content={'code': 200, 'msg': '连接成功', 'data': {'response': resp.strip()[:100], 'elapsed': elapsed}})
    except Exception as e:
        return JSONResponse(content={'code': 500, 'msg': f'LLM 连接失败: {str(e)[:200]}'})


@eval_controller.get(
    '/rules',
    summary='规则列表',
    description='获取 P 类 / R 类规则列表',
)
async def get_rules(
    request: Request,
    rule_type: Annotated[str, Query(description='p/r/all')] = 'all',
    level: Annotated[str, Query(description='high/medium/low')] = '',
    keyword: Annotated[str, Query(description='搜索规则名或ID')] = '',
) -> Response:
    """从 YAML 读取规则列表"""
    import yaml
    rules_dir = FilePath(__file__).resolve().parent.parent / 'rules'
    all_rules = []
    files = []
    if rule_type in ('all', 'p'):
        files.append(('P', rules_dir / 'p_rules.yaml'))
    if rule_type in ('all', 'r'):
        files.append(('R', rules_dir / 'r_rules.yaml'))

    for rtype, fp in files:
        if fp.exists():
            with open(fp, encoding='utf-8') as f:
                data = yaml.safe_load(f) or []
                for r in data:
                    r['_type'] = rtype
                    all_rules.append(r)

    # 筛选
    if level:
        all_rules = [r for r in all_rules if r.get('level') == level]
    if keyword:
        kw = keyword.lower()
        all_rules = [r for r in all_rules if kw in r.get('rule_id', '').lower() or kw in r.get('name', '').lower()]

    return ResponseUtil.success(data=all_rules)


@eval_controller.get(
    '/project/list',
    summary='获取项目分页列表',
    description='获取评审项目分页列表',
    response_model=PageResponseModel[EvalProjectModel],
    dependencies=[UserInterfaceAuthDependency('eval:project:list')],
)
async def get_project_list(
    request: Request,
    project_query: Annotated[EvalProjectPageQuery, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    data_scope_sql: Annotated[ColumnElement, DataScopeDependency(EvalProject)],
) -> Response:
    result = await EvalProjectService.get_project_list_services(
        query_db, project_query, data_scope_sql, is_page=True
    )
    logger.info('获取成功')
    return ResponseUtil.success(model_content=result)


@eval_controller.get(
    '/project/{project_id}',
    summary='获取项目详情',
    description='获取指定项目详细信息',
    response_model=DataResponseModel[EvalProjectModel],
    dependencies=[UserInterfaceAuthDependency('eval:project:query')],
)
async def get_project_detail(
    request: Request,
    project_id: Annotated[int, Path(description='项目ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await EvalProjectService.project_detail_services(query_db, project_id)
    logger.info(f'获取项目 {project_id} 详情成功')
    return ResponseUtil.success(data=result)


@eval_controller.post(
    '/project',
    summary='新增项目',
    description='新增评审项目',
    dependencies=[UserInterfaceAuthDependency('eval:project:add')],
)
async def add_project(
    request: Request,
    add_project: EvalProjectModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_project.create_by = current_user.user.user_name
    result = await EvalProjectService.add_project_services(query_db, add_project)
    logger.info(result.message)
    return JSONResponse(content={'code': 200, 'msg': result.message, 'data': result.result})


@eval_controller.delete(
    '/project/{project_id}',
    summary='删除项目',
    description='删除评审项目',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('eval:project:remove')],
)
@Log(title='评审项目管理', business_type=BusinessType.DELETE)
async def delete_project(
    request: Request,
    project_id: Annotated[int, Path(description='项目ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await EvalProjectService.delete_project_services(query_db, project_id)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@eval_controller.post(
    '/review/start',
    summary='启动评审',
    description='启动项目的AI评审流水线',
    dependencies=[UserInterfaceAuthDependency('eval:review:start')],
)
async def start_review(
    request: Request,
    start_model: StartReviewModel,
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    """在线程池中执行评审流水线"""
    import concurrent.futures
    import asyncio

    try:
        from module_eval.service.eval_pipeline_runner import _thread_entry
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                _thread_entry,
                start_model.project_id,
                start_model.review_mode,
                current_user.user.user_name,
            )
            result = await asyncio.wrap_future(future)
        return JSONResponse(content={'code': 200, 'msg': '评审完成', 'data': result or {}})
    except Exception as e:
        logger.error(f'评审失败', exc_info=True)
        return JSONResponse(content={'code': 500, 'msg': str(e)[:500], 'success': False})


@eval_controller.get(
    '/llm/status',
    summary='LLM 状态',
    description='查看当前 LLM 配置和连接状态',
)
async def llm_status(request: Request) -> Response:
    """查看 LLM 配置状态"""
    import os
    api_key = os.environ.get('DS_API_KEY', '')
    model = os.environ.get('DS_MODEL', 'deepseek-chat')
    api_base = os.environ.get('DS_API_BASE', 'https://api.deepseek.com')
    return JSONResponse(content={
        'code': 200,
        'msg': 'ok',
        'data': {
            'configured': bool(api_key),
            'key_preview': api_key[:8] + '...' if api_key else '',
            'model': model,
            'apiBase': api_base,
            'provider': os.environ.get('DS_PROVIDER', 'DeepSeek'),
            'maxConcurrency': int(os.environ.get('LLM_MAX_CONCURRENCY', '5')),
        },
    })


@eval_controller.get(
    '/review/list',
    summary='评审列表',
    description='获取所有评审记录分页列表',
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def get_review_list(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    page_num: Annotated[int, Query()] = 1,
    page_size: Annotated[int, Query()] = 10,
    project_id: Annotated[int, Query(description='项目ID（可选筛选）')] = None,
) -> Response:
    """全量评审记录分页列表"""
    from module_eval.dao.eval_dao import EvalReviewDao
    from module_eval.entity.do.eval_do import EvalReview
    from sqlalchemy import desc, select
    from utils.page_util import PageUtil
    from sqlalchemy import ColumnElement

    query = select(EvalReview).order_by(desc(EvalReview.create_time))
    if project_id:
        query = query.where(EvalReview.project_id == project_id)

    result = await PageUtil.paginate(query_db, query, page_num, page_size, is_page=True)
    return ResponseUtil.success(model_content=result)


@eval_controller.get(
    '/project/{project_id}/reviews',
    summary='评审历史',
    description='获取项目的所有评审记录',
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def get_project_reviews(
    request: Request,
    project_id: Annotated[int, Path(description='项目ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """项目评审历史"""
    from module_eval.dao.eval_dao import EvalReviewDao
    from module_eval.entity.vo.eval_vo import EvalReviewModel
    from sqlalchemy import desc, select

    result = await query_db.execute(
        select(EvalReview).where(EvalReview.project_id == project_id).order_by(desc(EvalReview.create_time))
    )
    reviews = result.scalars().all()
    from utils.common_util import CamelCaseUtil
    data = [CamelCaseUtil.transform_result(r) for r in reviews]
    return ResponseUtil.success(data=data)


@eval_controller.get(
    '/review/{review_id}/progress',
    summary='获取评审进度事件流(SSE)',
    description='SSE协议推送评审进度事件',
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def stream_review_progress(
    request: Request,
    review_id: Annotated[int, Path(description='评审ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """SSE 进度推送"""
    from fastapi.responses import StreamingResponse
    from module_eval.service.eval_pipeline_runner import get_progress

    async def event_generator():
        events = get_progress(review_id)
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        # 发送完成事件
        yield f"data: {json.dumps({'step': 'done', 'label': '评审完成', 'status': 'done', 'payload': {}}, ensure_ascii=False)}\n\n"
        yield "event: close\ndata: \n\n"

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'},
    )


@eval_controller.get(
    '/review/{review_id}',
    summary='获取评审进度',
    description='获取指定评审的当前进度和状态',
    response_model=DataResponseModel[EvalReviewModel],
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def get_review_status(
    request: Request,
    review_id: Annotated[int, Path(description='评审ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await EvalPipelineService.get_review_status_services(query_db, review_id)
    logger.info(f'获取评审 {review_id} 进度成功')
    return ResponseUtil.success(data=result)


@eval_controller.post(
    '/project/{project_id}/upload',
    summary='上传项目材料',
    description='上传项目评审材料文件（支持PDF/Word/TXT/ZIP/RAR），可选指定分类',
    dependencies=[UserInterfaceAuthDependency('eval:project:edit')],
)
@Log(title='评审项目管理', business_type=BusinessType.INSERT)
async def upload_material(
    request: Request,
    project_id: Annotated[int, Path(description='项目ID')],
    file: Annotated[UploadFile, File(description='文件')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    category: Annotated[str, Form(description='文件分类: 请示函/招标文件/可研报告/法律意见/其他')] = '',
) -> Response:
    from module_eval.service.eval_file_service import EvalFileService
    result = await EvalFileService.upload_and_parse(file, project_id, query_db, category=category)
    await query_db.commit()
    logger.info(f'项目 {project_id} 上传文件 {file.filename} 成功')
    return ResponseUtil.success(data=result)


@eval_controller.get(
    '/project/{project_id}/materials',
    summary='获取项目材料列表',
    description='获取指定项目的所有上传材料',
    dependencies=[UserInterfaceAuthDependency('eval:project:query')],
)
async def list_materials(
    request: Request,
    project_id: Annotated[int, Path(description='项目ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    from module_eval.entity.do.eval_do import EvalMaterial
    from sqlalchemy import select
    result = await query_db.execute(
        select(EvalMaterial).where(EvalMaterial.project_id == project_id).order_by(EvalMaterial.material_id)
    )
    materials = result.scalars().all()
    from utils.common_util import CamelCaseUtil
    return ResponseUtil.success(data=[CamelCaseUtil.transform_result(m) for m in materials])


@eval_controller.get(
    '/material/{material_id}/download',
    summary='下载材料文件',
    description='下载指定材料文件',
    dependencies=[UserInterfaceAuthDependency('eval:project:query')],
)
async def download_material(
    request: Request,
    material_id: Annotated[int, Path(description='材料ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    from module_eval.entity.do.eval_do import EvalMaterial
    from sqlalchemy import select
    from fastapi.responses import FileResponse
    import os

    result = await query_db.execute(select(EvalMaterial).where(EvalMaterial.material_id == material_id))
    material = result.scalars().first()
    if not material:
        return JSONResponse(content={'code': 404, 'msg': '材料不存在'})

    file_path = material.file_path
    if not os.path.exists(file_path):
        return JSONResponse(content={'code': 404, 'msg': '文件不存在'})

    return FileResponse(file_path, filename=material.file_name)


@eval_controller.get(
    '/review/{review_id}/opinions',
    summary='获取评审意见',
    description='获取指定评审的评审意见列表',
    response_model=DataResponseModel[EvalOpinionModel],
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def get_review_opinions(
    request: Request,
    review_id: Annotated[int, Path(description='评审ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await EvalPipelineService.get_review_opinions_services(query_db, review_id)
    logger.info(f'获取评审 {review_id} 意见成功')
    return ResponseUtil.success(data=result)


@eval_controller.get(
    '/review/{review_id}/export',
    summary='导出评审意见 Word',
    description='导出评审意见为 .docx 文件',
    dependencies=[UserInterfaceAuthDependency('eval:review:query')],
)
async def export_review(
    request: Request,
    review_id: Annotated[int, Path(description='评审ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """导出评审意见为 Word"""
    from module_eval.service.eval_docx_renderer import render_opinions_docx
    from module_eval.dao.eval_dao import EvalReviewDao, EvalOpinionDao, EvalProjectDao
    from module_eval.entity.do.eval_do import EvalProject
    from sqlalchemy import select
    from starlette.responses import Response as BinaryResponse

    # 查评审记录
    review = await EvalReviewDao.get_review_by_id(query_db, review_id)
    if not review:
        return JSONResponse(content={'code': 404, 'msg': '评审不存在'})

    # 查项目
    proj = await EvalProjectDao.get_project_by_id(query_db, review.project_id)

    # 查意见
    opinions = await EvalOpinionDao.get_opinions_by_review(query_db, review_id)

    docx_bytes = render_opinions_docx(
        project_name=proj.project_name if proj else f'项目#{review.project_id}',
        country=getattr(proj, 'country', '') or '',
        amount=getattr(proj, 'amount', '') or '',
        stage=getattr(proj, 'stage', '') or '',
        opinions=[{
            'department': op.department,
            'rule_id': op.rule_id or '',
            'title': op.title or '',
            'content': op.content or '',
            'risk_level': op.risk_level or 'medium',
            'evidence': op.evidence or '',
        } for op in opinions],
        review_time=str(review.create_time) if review.create_time else None,
    )
    filename = f'评审意见_{review_id}_{datetime.now().strftime("%Y%m%d")}.docx'
    # 保存临时文件返回
    tmp_path = os.path.join(os.environ.get('TEMP', '/tmp'), filename)
    with open(tmp_path, 'wb') as f:
        f.write(docx_bytes)
    from fastapi.responses import FileResponse
    return FileResponse(tmp_path, filename=filename, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
