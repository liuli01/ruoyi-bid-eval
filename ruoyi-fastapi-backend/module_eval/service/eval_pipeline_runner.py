"""评审流水线执行器 — 全量批次执行 + 触发链 + 交叉验证"""
import json
import re
import time
from pathlib import Path
from typing import Any

from utils.log_util import logger

# SSE 进度
_pipeline_progress: dict[int, list[dict]] = {}
RULES_DIR = Path(__file__).resolve().parent.parent / 'rules'


def get_progress(review_id: int) -> list[dict]:
    return list(_pipeline_progress.get(review_id, []))


def _emit(review_id: int, step: str, label: str, status: str, payload: dict | None = None):
    if review_id not in _pipeline_progress:
        _pipeline_progress[review_id] = []
    _pipeline_progress[review_id].append({
        'step': step, 'label': label, 'status': status,
        'payload': payload or {}, 'timestamp': time.time(),
    })


# ---------------------------------------------------------------------------
# 规则加载
# ---------------------------------------------------------------------------

def _load_all_rules() -> list[dict]:
    """加载 P 类和 R 类全部规则"""
    import yaml
    rules = []
    for fname in ['p_rules.yaml', 'r_rules.yaml']:
        fp = RULES_DIR / fname
        if fp.exists():
            with open(fp, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    rules.extend(data if isinstance(data, list) else [data])
    return rules


def _load_batch_config() -> list[dict]:
    """加载批次配置"""
    import yaml
    bp = RULES_DIR.parent / 'config' / 'rule_batches.yaml'
    if bp.exists():
        with open(bp, encoding='utf-8') as f:
            bc = yaml.safe_load(f) or {}
            return bc.get('batches', [])
    return []


def _load_trigger_chains() -> dict:
    """加载触发链"""
    import yaml
    fp = RULES_DIR / 'trigger_chains.yaml'
    if fp.exists():
        with open(fp, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _assign_rules_to_batches(rules: list[dict], batches: list[dict]) -> dict[str, list[dict]]:
    """将规则分配到各批次（按 keyword 匹配）"""
    assignment: dict[str, list[dict]] = {}
    for rule in rules:
        rule_text = str(rule.get('full_text', '')) + str(rule.get('name', '')) + str(rule.get('rule_id', ''))
        best_batch = None
        best_score = 0
        for batch in batches:
            bid = batch.get('id', 'default')
            keywords = batch.get('keywords', [])
            if not keywords:
                continue
            score = sum(2 if kw in rule_text else 0 for kw in keywords)
            if score > best_score:
                best_score = score
                best_batch = bid
        if best_batch is None:
            best_batch = 'default'
        if best_batch not in assignment:
            assignment[best_batch] = []
        assignment[best_batch].append(rule)
    return assignment


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------

def _call_llm(prompt: str) -> list[dict]:
    """同步调用 LLM，返回 judgment 列表"""
    from module_eval.service.eval_llm_client import EvalLlmClient
    messages = [
        {'role': 'system', 'content': '你是海外工程项目风险评审专家。严格按 JSON 格式输出，不要多余文字。'},
        {'role': 'user', 'content': prompt},
    ]
    resp = EvalLlmClient.call_llm_sync(messages)
    # 提取 JSON
    m = re.search(r'\[.*?\]', resp, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    m2 = re.search(r'\{.*\}', resp, re.DOTALL)
    if m2:
        try:
            r = json.loads(m2.group(0))
            if isinstance(r, dict):
                return [r]
        except json.JSONDecodeError:
            pass
    logger.warning(f'LLM JSON 解析失败: {resp[:200]}')
    return []


def _build_batch_prompt(batch_id: str, rules: list[dict], materials: str, max_rules: int = 10) -> str:
    """构建批次 prompt，每次最多 max_rules 条"""
    group_label = batch_id.replace('_', ' ').title()
    prompt = f"### {group_label} 风险审查\n\n逐条判断以下规则是否触发：\n\n"
    for i, r in enumerate(rules[:max_rules], 1):
        prompt += (
            f"{i}. {r.get('rule_id', '')} — {r.get('name', '')}\n"
            f"   风险等级: {r.get('level', 'medium')}\n"
            f"   规则原文: {r.get('full_text', '')}\n"
        )
        if r.get('basis'):
            prompt += f"   制度依据: {r['basis']}\n"
        prompt += "\n"
    if materials:
        prompt += f"### 项目材料\n{materials[:8000]}\n\n"
    else:
        prompt += "### 项目材料\n（暂无上传材料）\n\n"
    prompt += (
        '### 输出\n'
        '输出 JSON 数组：\n'
        '[{"rule_id":"...","triggered":true/false/"insufficient","evidence":"原文证据","source":"来源","reason":"判断理由"}]\n'
        '只输出 JSON。'
    )
    return prompt


# ---------------------------------------------------------------------------
# 交叉验证
# ---------------------------------------------------------------------------

def _validate(judgments: list[dict]) -> dict:
    """交叉验证"""
    triggered = [j for j in judgments if j.get('triggered') is True]
    insufficient = [j for j in judgments if j.get('triggered') == 'insufficient']
    recs = []
    if len(triggered) > 60:
        recs.append('触发规则超过60条')
    elif len(triggered) < 2:
        recs.append('触发规则少于2条，可能遗漏风险')
    if len(insufficient) > len(triggered) and len(triggered) > 0:
        recs.append(f'无法判断数({len(insufficient)})超过触发数({len(triggered)})')
    # 证据空值检查
    empty_ev = [j['rule_id'] for j in triggered if not j.get('evidence', '').strip()]
    if empty_ev:
        recs.append(f'{len(empty_ev)} 条触发规则无证据: {",".join(empty_ev[:5])}')
    return {'overall_status': 'warning' if recs else 'ok', 'rule_count': len(triggered), 'recommendations': recs}


# ---------------------------------------------------------------------------
# 触发链
# ---------------------------------------------------------------------------

def _apply_chains(judgments: list[dict], materials: str) -> list[dict]:
    """应用触发链"""
    chains = _load_trigger_chains()
    triggered_ids = {j['rule_id'] for j in judgments if j.get('triggered') is True}
    jmap = {j['rule_id']: j for j in judgments}
    for chain in chains.get('chains', []):
        cond = chain.get('condition', {})
        target = chain.get('target_rule', '')
        action = chain.get('action', '')
        if action != 'trigger' or target not in jmap:
            continue
        matched = False
        ctype = cond.get('type', '')
        keyword = cond.get('keyword', '')
        if ctype == 'keyword_in_raw_text' and keyword and keyword in materials:
            matched = True
        elif ctype == 'keyword_in_trigger_content' and keyword:
            matched = any(keyword in j.get('evidence', '') or keyword in j.get('reason', '') for j in judgments if j.get('triggered') is True)
        if matched:
            jmap[target]['triggered'] = True
            cid = chain.get('chain_id', '')
            cname = chain.get('name', '')
            jmap[target]['reason'] = f'[触发链] {cid}: {cname}'
            logger.info(f'触发链 {cid} -> {target}')
    return list(jmap.values())


# ---------------------------------------------------------------------------
# 深度复查
# ---------------------------------------------------------------------------

def _deep_review(judgments: list[dict], materials: str) -> list[dict]:
    """对第一轮 false 的规则做二次复查"""
    falses = [j for j in judgments if j.get('triggered') is False]
    if not falses:
        return judgments
    # 只复查高价值规则（带有 trigger_keywords 或风险等级 high 的）
    high_value = [j for j in falses
                  if j.get('risk_level') == 'high'
                  or any(kw in str(j.get('reason', '')) for kw in ['可能', '建议', '不确定'])]
    if not high_value:
        return judgments
    prompt = "### 深度复查\n以下规则在第一轮中被判定为未触发，请用完整材料重新确认：\n\n"
    for i, j in enumerate(high_value, 1):
        prompt += f"{i}. {j.get('rule_id','')}\n   第一轮理由: {j.get('reason','')}\n\n"
    prompt += f"### 项目材料\n{materials[:10000]}\n\n"
    prompt += '输出 JSON 数组：[{"rule_id":"...","triggered":true/false/"insufficient","evidence":"...","reason":"..."}]'
    try:
        deep_results = _call_llm(prompt)
        jmap = {j['rule_id']: j for j in judgments}
        for dr in deep_results:
            if dr.get('rule_id') in jmap:
                # 只有改判为 triggered 才更新
                if dr.get('triggered') is True:
                    jmap[dr['rule_id']]['triggered'] = True
                    jmap[dr['rule_id']]['evidence'] = dr.get('evidence', '')
                    jmap[dr['rule_id']]['reason'] = f"[深度复查] {dr.get('reason', '')}"
                    logger.info(f'深度复查改判: {dr["rule_id"]} → True')
        return list(jmap.values())
    except Exception as e:
        logger.warning(f'深度复查失败: {e}')
        return judgments


# ---------------------------------------------------------------------------
# 主流水线
# ---------------------------------------------------------------------------

def _run_sync(review_id: int, project_id: int, review_mode: str, user_name: str, engine: Any = None) -> dict:
    """同步执行完整评审流水线"""
    if engine is None:
        from sqlalchemy import create_engine
        from config.env import DataBaseConfig
        url = f'mysql+pymysql://{DataBaseConfig.db_username}:{DataBaseConfig.db_password}@{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
        engine = create_engine(url)
    from sqlalchemy import text
    started = time.time()
    llm_calls = 0

    try:
        # --- Step 0: 材料聚合 ---
        _emit(review_id, 'step0', '材料聚合', 'running')
        combined_text = _load_materials(engine, project_id)
        _emit(review_id, 'step0', '材料聚合', 'done', {'text_length': len(combined_text)})

        # --- Step 1: 完整性扫描 ---
        _emit(review_id, 'step1', '完整性扫描', 'running')
        _emit(review_id, 'step1', '完整性扫描', 'done')

        # --- Step 2: 分批规则审查 ---
        _emit(review_id, 'step2', '规则审查', 'running')
        with engine.connect() as conn:
            conn.execute(text("UPDATE eval_review SET current_step='step2_running' WHERE review_id=:rid"), {'rid': review_id})
            conn.commit()

        all_rules = _load_all_rules()
        batches = _load_batch_config()
        assignments = _assign_rules_to_batches(all_rules, batches)

        all_judgments: list[dict] = []
        batch_order = sorted(assignments.keys())
        total_batches = len(batch_order)

        # 执行各批次
        for idx, bid in enumerate(batch_order, 1):
            batch_rules = assignments[bid]
            if not batch_rules:
                continue
            _emit(review_id, 'step2', f'批次 {bid}', 'running', {'batch': idx, 'total': total_batches, 'rules': len(batch_rules)})

            # 分批内再切分（LLM token 限制）
            chunk_size = 8
            for chunk_start in range(0, len(batch_rules), chunk_size):
                chunk = batch_rules[chunk_start:chunk_start + chunk_size]
                prompt = _build_batch_prompt(bid, chunk, combined_text)
                try:
                    judgments = _call_llm(prompt)
                    llm_calls += 1
                except Exception as e:
                    logger.error(f'批次 {bid} 失败: {e}')
                    err_msg = str(e)[:100]
                    judgments = [{'rule_id': r.get('rule_id', ''), 'triggered': 'insufficient', 'evidence': '', 'source': '', 'reason': f'LLM错误: {err_msg}'} for r in chunk]
                all_judgments.extend(judgments)

            _emit(review_id, 'step2', f'批次 {bid}', 'done')

        # --- 深度复查（仅 complete 模式） ---
        if review_mode == 'complete' or review_mode == 'standard':
            deep_count = len([j for j in all_judgments if j.get('triggered') is False])
            if deep_count > 0:
                _emit(review_id, 'step2', '深度复查', 'running')
                all_judgments = _deep_review(all_judgments, combined_text)
                _emit(review_id, 'step2', '深度复查', 'done')

        # --- 触发链 ---
        all_judgments = _apply_chains(all_judgments, combined_text)

        # --- Step 3: 交叉验证 ---
        _emit(review_id, 'step3', '交叉验证', 'running')
        validation = _validate(all_judgments)
        _emit(review_id, 'step3', '交叉验证', 'done', validation)

        # --- Step 4: 跟进意见 ---
        _emit(review_id, 'step4', '跟进意见', 'running')
        insufficient = [j for j in all_judgments if j.get('triggered') == 'insufficient']
        follow_up = []
        if insufficient:
            follow_up.append({'question': f'以下规则无法判断：{",".join(j["rule_id"] for j in insufficient[:10])}', 'type': 'llm_insufficient'})
        _emit(review_id, 'step4', '跟进意见', 'done', {'count': len(follow_up)})

        # --- Step 5: 意见生成 ---
        _emit(review_id, 'step5', '意见生成', 'running')
        triggered = [j for j in all_judgments if j.get('triggered') is True]
        opinions = []
        for j in triggered:
            rid = j.get('rule_id', '')
            dept = rid.split('-')[0] if '-' in rid else '综合'
            opinions.append({
                'review_id': review_id, 'rule_id': rid,
                'department': dept,
                'title': f'规则 {rid}: {j.get("evidence","")[:60]}',
                'content': j.get('evidence', ''),
                'risk_level': j.get('risk_level', 'medium'),
                'evidence': j.get('evidence', ''),
                'source_path': j.get('source', ''),
                'sort_order': len(opinions),
            })

        if opinions:
            with engine.connect() as conn:
                for op in opinions:
                    conn.execute(
                        text("INSERT INTO eval_opinion (review_id, rule_id, department, title, content, risk_level, evidence, source_path, sort_order, create_time) VALUES (:rid, :rule, :dept, :title, :content, :risk, :ev, :src, :sort, NOW())"),
                        {'rid': op['review_id'], 'rule': op['rule_id'], 'dept': op['department'], 'title': op['title'], 'content': op['content'], 'risk': op['risk_level'], 'ev': op['evidence'], 'src': op['source_path'], 'sort': op['sort_order']}
                    )
                conn.commit()

        _emit(review_id, 'step5', '意见生成', 'done', {'count': len(opinions)})

        # --- Step 6: 完成 ---
        elapsed = round(time.time() - started, 2)
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE eval_review SET status='done', current_step='done', triggered_count=:tc, insufficient_count=:ic, llm_calls=:lc, elapsed_sec=:el, result_json=:rj WHERE review_id=:rid"),
                {'rid': review_id, 'tc': len(triggered), 'ic': len(insufficient), 'lc': llm_calls, 'el': elapsed, 'rj': json.dumps({'triggered_rules': [j['rule_id'] for j in triggered], 'insufficient_count': len(insufficient), 'llm_calls': llm_calls}, ensure_ascii=False)}
            )
            conn.commit()

        _emit(review_id, 'step6', '评审完成', 'done')
        logger.info(f'评审 #{review_id} 完成: {len(triggered)} 触发 / {len(insufficient)} 不足 / {llm_calls} 次调用 / {elapsed:.1f}s')

        return {'review_id': review_id, 'triggered_count': len(triggered), 'insufficient_count': len(insufficient), 'opinion_count': len(opinions), 'llm_calls': llm_calls, 'elapsed_sec': elapsed}

    except Exception as e:
        elapsed = round(time.time() - started, 2)
        logger.error(f'评审 #{review_id} 失败: {e}')
        try:
            with engine.connect() as conn:
                conn.execute(text("UPDATE eval_review SET status='error', error_msg=:msg, elapsed_sec=:el WHERE review_id=:rid"), {'rid': review_id, 'msg': str(e)[:500], 'el': elapsed})
                conn.commit()
        except Exception:
            pass
        raise


def _load_materials(engine: Any, project_id: int) -> str:
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT file_name, text_content FROM eval_material WHERE project_id=:pid AND parse_status='done' AND text_content IS NOT NULL AND text_content != '' ORDER BY material_id"),
                {'pid': project_id}
            ).fetchall()
        if not rows:
            return ''
        parts, total = [], 0
        for row in rows:
            header = f"--- {row[0]} ---\n"
            content = (row[1] or '')[:15000]
            parts.append(header + content)
            total += len(header) + len(content)
            if total > 50000:
                parts.append('...(截断)')
                break
        return '\n\n'.join(parts)
    except Exception as e:
        logger.warning(f'读取材料失败: {e}')
        return ''


async def run_pipeline(project_id: int, review_mode: str = 'standard', user_name: str = '') -> dict:
    import asyncio
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_thread_entry, project_id, review_mode, user_name)
        return await asyncio.wrap_future(future)


def _thread_entry(project_id: int, review_mode: str, user_name: str) -> dict:
    from sqlalchemy import create_engine, text
    from config.env import DataBaseConfig
    url = f'mysql+pymysql://{DataBaseConfig.db_username}:{DataBaseConfig.db_password}@{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO eval_review (project_id, review_mode, status, current_step, create_by, create_time) VALUES (:pid, :mode, 'running', 'step0', :user, NOW())"),
            {'pid': project_id, 'mode': review_mode, 'user': user_name or 'system'}
        )
        conn.commit()
        review_id = result.lastrowid
    logger.info(f'评审 #{review_id} 启动')
    return _run_sync(review_id, project_id, review_mode, user_name, engine)
