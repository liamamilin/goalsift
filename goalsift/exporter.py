"""Reports and JSON derive from one frozen research and annotation snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from .adoption import handoff_annotations
from .repository import Repository
from .security import redact_secrets


def _attach_source_context(result: dict) -> None:
    evidence = {item["id"]: item for item in result.get("evidence", [])}
    for review in result.get("source_reviews", {}).values():
        for source in review.get("match_context", []):
            saved = evidence.get(source.get("evidence_id"))
            if saved is None:
                source["excerpt_status"] = "UNAVAILABLE"
                continue
            text = saved.get("excerpt_or_summary") or ""
            ranges = source.get("excerpt_ranges") or []
            valid = bool(ranges) and all(isinstance(pair, list) and len(pair) == 2
                        and isinstance(pair[0], int) and isinstance(pair[1], int)
                        and 0 <= pair[0] <= pair[1] <= len(text) for pair in ranges)
            source.update({
                "retrieved_at": saved.get("retrieved_at"),
                "source_version": saved.get("source_version"),
                "excerpt_status": "AVAILABLE" if valid else "RANGE_UNAVAILABLE",
                "excerpt_offset_unit": "Unicode code points; half-open [start, end)",
                "supplied_excerpt": (
                    "\n[省略；以下为原文片段]\n".join(text[a:b] for a, b in ranges)
                    if valid else None
                ),
            })


def to_json(
    repo: Repository,
    job_id: str,
    *,
    view: dict | None = None,
    annotation_cursor: int | None = None,
) -> dict:
    with repo.transaction():
        frozen_view = view if view is not None else repo.current_view(job_id)
        max_cursor = repo.max_event_rowid(job_id)
        cursor = max_cursor if annotation_cursor is None else annotation_cursor
        if cursor < 0 or cursor > max_cursor:
            raise ValueError("注记游标超出该任务的事件范围")
        result = json.loads(json.dumps(frozen_view, ensure_ascii=False))
        result["exported_at"] = datetime.now(timezone.utc).isoformat()
        _attach_source_context(result)
        result["handoff"] = handoff_annotations(repo, job_id, result, cursor)
        return json.loads(redact_secrets(json.dumps(result, ensure_ascii=False)))


def to_markdown(
    repo: Repository,
    job_id: str,
    *,
    view: dict | None = None,
    annotation_cursor: int | None = None,
    data: dict | None = None,
) -> str:
    d = data if data is not None else to_json(
        repo, job_id, view=view, annotation_cursor=annotation_cursor
    )
    goal, proposal = d.get("goal"), d.get("proposal")
    lines = ['# GoalSift 研究交接包', '', f'- 任务：{job_id}',
             f'- 研究修订：{d["revision"]}', f'- 状态：{d["status"]}',
             f'- 导出时间：{d["exported_at"]}',
             f'- 注记截止：事件游标 {d["handoff"]["annotation_cursor"]}；'
             f'{d["handoff"]["annotation_cutoff_at"] or "尚无用户注记"}',
             '- 范围：公开来源的方案研究；方案尚未执行，来源支持不等于目标环境验收。', '', '## 目标', '']
    usage = d.get("budget_usage") or {}
    cost = usage.get("cost_usd")
    known_cost = usage.get("known_cost_usd")
    if cost is None:
        cost_note = (f"未知（已知记录 ${known_cost}；仍有费用未能核实）"
                     if known_cost is not None else "未知（本修订没有完整费用记录）")
    else:
        cost_note = f"已记录 ${cost}；这不等同于服务商账单"
    lines.insert(8, '- 研究费用：' + cost_note)
    if goal:
        lines += [goal['statement'], '', '**用户原话：** ' + goal['original_user_text']]
        for name, label in [('constraints', '用户要求与已确认前提'), ('assumptions', '未确认假设'), ('open_questions', '待确认问题')]:
            if goal.get(name):
                lines += ['', '**' + label + '**']
                for item in goal[name]:
                    lines.append('- ' + (f"[{item.get('provenance', 'SYSTEM_ASSUMED')}] " + item.get('text', str(item)) if isinstance(item, dict) else str(item)))
        for decision in goal.get('condition_decisions', []):
            if decision['action'] == 'remove': lines.append(f"- 已移出目标（r{decision['revision']}）：{decision['original_statement']}")
    lines += ['', '## 候选路径', '']
    if proposal:
        lines += ['### ' + proposal['title'], '', proposal['summary'], '',
                  '**研究建议理由：** ' + proposal['recommendation_reason'], '']
        for key, label in [('integration_work', '集成工作'), ('new_work', '补充工作'), ('risks', '风险'), ('assumptions', '假设')]:
            if proposal.get(key): lines += ['**' + label + '**', *['- ' + x for x in proposal[key]], '']
        lines += ['实施费用：' + json.dumps(proposal['costs'], ensure_ascii=False), '']
    else: lines += ['当前没有有依据的候选路径。', '']

    handoff = d["handoff"]
    lines += ['## 方案决定与采用前检查', '']
    state_labels = {
        "SELECTED": "本修订已记录倾向方案",
        "NEEDS_RECONFIRMATION": "需要在本修订重新确认；之前的选择不会自动沿用",
        "PENDING_DECISION": "待决策；当前没有已记录的倾向方案",
    }
    lines += [f'- 决定状态：{state_labels[handoff["status"]]}']
    selected = handoff.get("decision")
    previous = handoff.get("previous_decision")
    if selected and selected.get("active"):
        chosen = selected.get("proposal") or {}
        lines += [f'- 所选方案：{chosen.get("title") or selected["proposal_id"]}（研究修订 r{selected["source_revision"]}）',
                  '- 用户理由：' + (selected.get("reason") or '未填写'),
                  f'- 决定注记版本：{selected["annotation_version"]}']
    elif handoff["status"] == "NEEDS_RECONFIRMATION" and previous:
        old = previous.get("proposal") or {}
        lines += [f'- 上一修订选择：{old.get("title") or previous["proposal_id"]}（r{previous["source_revision"]}）',
                  '- 上次用户理由：' + (previous.get("reason") or '未填写'),
                  f'- 上次决定注记版本：{previous["annotation_version"]}']
    else:
        lines += ['- 本报告描述研究候选，不代表用户已选择或开始实施。']

    checklist = handoff["checklist"]
    if checklist["active"]:
        lines += ['', '### 检查清单', '']
        if checklist["items"]:
            for item in checklist["items"]:
                lines += [f'- **{item["status"]}**：{item["title"]}（依据状态：{item.get("assessment_status") or "未评估"}；注记版本 {item["annotation_version"]}）',
                          '  - 下一步：' + item["next_step"]]
                for gap in item.get("gaps", []): lines.append('  - 缺口：' + gap)
                for evidence_item in item.get("evidence", []):
                    lines.append(f'  - 依据来源：{evidence_item.get("source_ref", "未知来源")}（{evidence_item.get("locator", "")}）')
                if item.get("notes"): lines.append('  - 用户记录：' + item["notes"])
        else:
            lines += ['当前方案没有派生出检查项。']
        lines += ['', '清单状态和用户记录只表示准备进度，不证明条件已通过或任务已执行。']
    elif checklist.get("history"):
        lines += ['', '### 历史检查注记', '', '此前的记录保留在历史中，不作为当前选择或当前检查结果。']
        for item in checklist["history"]:
            lines.append(f'- {item.get("title") or item["item_id"]}：{item["status"]}（版本 {item["annotation_version"]}）' +
                         (f'；记录：{item["notes"]}' if item.get("notes") else ''))

    lines += ['', '## 成立条件', '']
    conditions = {c['id']: c for c in d.get('conditions', [])}
    resources = {r['id']: r for r in d.get('resources', [])}
    evidence = {e['id']: e for e in d.get('evidence', [])}
    if d.get('research_scope'):
        scope = d['research_scope']
        lines += ['## 本轮定向补查', '', f"- 基于修订：{scope['base_revision']}；本轮费用上限：${scope['budget_usd']}",
                  '- 调查条件：' + '；'.join(conditions[cid]['statement'] for cid in scope['condition_ids'] if cid in conditions),
                  '- 调查问题：' + (scope['question'] or '核查所选条件的依据与缺口'),
                  f"- 沿用评价：{len(d.get('reused_assessment_ids', []))} 项；新增资料可能影响同一候选的其他条件。", '']
    for c in conditions.values():
        lines += [f'- **[{c["obligation"]} / {c["dimension"]}]** {c["statement"]} (`{c["id"]}`)',
                  '  - 确认来源：' + c.get('provenance', 'SYSTEM_ASSUMED'),
                  '  - 依据：' + c['origin'], '  - 验收方式：' + (c.get('verification_method') or '未确认')]
    lines += ['', '## 资源、许可与实际摘录', '']
    for r in resources.values():
        review = d.get('source_reviews', {}).get(r['id'], {})
        lines += [f'- **{r["name"]}** — 许可：{r.get("license_claim") or "UNKNOWN"}',
                  '  - 来源：' + r['canonical_source'], '  - ' + r['description']]
        for doc in review.get('documents', []):
            lines.append(f"  - 补充文档（{doc['category']}）：{doc['url']}；版本 {doc.get('version') or 'UNKNOWN'}")
        for source in review.get('match_context', []):
            source_version = source.get('source_version') or 'UNKNOWN'
            retrieved = source.get('retrieved_at') or '旧记录未保存读取时间'
            ranges = ', '.join(f'[{a}, {b})' for a, b in source.get('excerpt_ranges', [])) or '旧记录未保存范围'
            lines.append(f"  - 匹配资料：{source['url']}；保存 {source['stored_characters']} 码点，实际提供 {source['supplied_characters']} 码点；范围 {ranges}；读取于 {retrieved}；版本 {source_version}")
            excerpt = source.get('supplied_excerpt')
            if excerpt is not None:
                lines += ['    实际提供给模型的原文摘录：', '    > ' + excerpt.replace('\n', '\n    > ')]
            elif source.get('excerpt_status') == 'RANGE_UNAVAILABLE':
                lines.append('    实际摘录无法重建：保存的范围与资料文本不匹配。')
            if source.get('is_partial'):
                lines.append('    说明：这是所选片段，不能据此判断整份资料不存在某项能力。')
        if not review.get('match_context') and (review.get('documents') or review.get('notes')):
            lines.append('  - 旧记录未保存模型实际收到的摘录范围，无法确认具体阅读片段。')
        for note in review.get('notes', []):
            lines.append('  - 读取限制：' + note)
    lines += ['', '## 条件匹配与证据', '']
    for a in d.get('assessments', []):
        condition = conditions.get(a['condition_id'], {}).get('statement', a['condition_id'])
        names = '、'.join(resources[r]['name'] for r in a['resource_ids'] if r in resources)
        lines += [f'### {a["status"]}：{condition}', '', f'资源：{names}', a['explanation']]
        for gap in a['gaps']: lines.append('- 缺口：' + gap)
        for eid in a['evidence_ids']:
            e = evidence.get(eid)
            if e: lines += [f'- 来源：{e["source_ref"]}（{e["locator"]}；读取于 {e["retrieved_at"]}）',
                            '  > ' + e['excerpt_or_summary'][:700].replace('\n', '\n  > ')]
        lines.append('')
    lines += ['## 研究范围与限制', '']
    for note in d.get('delivery_notes', []): lines.append('- ' + note)
    if d.get('stopped_reason'): lines.append('- 中止原因：' + d['stopped_reason'])
    lines += ['', '研究用量：' + json.dumps(d.get('budget_usage', {}), ensure_ascii=False)]
    rendered = '\n'.join(lines)
    rendered = '\n'.join(line.rstrip() for line in rendered.splitlines()).rstrip() + '\n'
    return redact_secrets(rendered)
