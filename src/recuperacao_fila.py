"""Recuperação delimitada e projeção de linhagem, sem repetir efeitos aplicados."""
import json
from coordenador import ContractError
from nucleo import Conflict, Invalid
from conhecimento import refs


def _object(raw):
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise Invalid('entrada da recuperação não é um objeto')
    return value


def _ineligible(old, steps, allow_superseded=False):
    statuses = ('queued', 'failed', 'superseded') if allow_superseded else ('queued', 'failed')
    if not old or old['status'] not in statuses or not steps:
        return 'demanda indisponível ou em estado incompatível'
    if old['status'] == 'failed' and old['error'] != 'prazo total excedido':
        return 'falha não causada apenas por prazo'
    if any(step['status'] in ('running', 'uncertain') or
           (step['capability'] == 'apply_contribution' and step['status'] in ('completed', 'failed'))
           for step in steps):
        return 'efeito aplicado, falho ou incerto exige revisão'
    return None


def _reference(payload):
    reference = payload.get('source_ref')
    if (payload.get('kind') != 'contribution' or payload.get('recovery_of') or
            not isinstance(reference, dict) or not isinstance(reference.get('record_id'), str) or not reference['record_id'] or
            type(reference.get('revision')) is not int or reference['revision'] < 1):
        raise Invalid('tipo não elegível ou recuperação já tentada')
    return reference


def _proves_successor(old_id, before, after):
    return (after.get('kind') == 'contribution' and after.get('recovery_of') == old_id and
            after.get('source_ref') == before.get('source_ref'))


def _ensure_tables(queue):
    with queue.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS recovery_links(old_job TEXT PRIMARY KEY, new_demand TEXT NOT NULL, new_job TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS recovery_review(old_job TEXT PRIMARY KEY, reason TEXT NOT NULL)')
        c.execute('CREATE INDEX IF NOT EXISTS recovery_candidates ON executions(kind,execution_status,error,created,id)')


def _defer(queue, old_job, reason):
    with queue.connect() as c:
        inserted = c.execute('INSERT OR IGNORE INTO recovery_review VALUES(?,?)', (old_job, reason)).rowcount
        if inserted:
            queue.event(c, old_job, 'recovery_deferred', {'reason': reason})


def retry_review(queue, old_job):
    """Libera explicitamente um deferido para outra avaliação; não executa nada.

    Retorna True apenas quando remove uma revisão pendente. Repetir a chamada
    ou indicar trabalho já recuperado retorna False, sem renovar orçamento.
    """
    queue.authorize()
    if not isinstance(old_job, str) or not 1 <= len(old_job) <= 120:
        raise Invalid('trabalho de revisão inválido')
    _ensure_tables(queue)
    with queue.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM recovery_links WHERE old_job=?', (old_job,)).fetchone():
            return False
        review = c.execute('SELECT reason FROM recovery_review WHERE old_job=?', (old_job,)).fetchone()
        if not review:
            return False
        c.execute('DELETE FROM recovery_review WHERE old_job=?', (old_job,))
        queue.event(c, old_job, 'recovery_review_released', {'previous_reason': review['reason']})
        return True


def _successor_job(c, new_demand, job_id=None):
    condition, value = ('e.id=?', job_id) if job_id is not None else ('e.request_key=?', 'demand-' + new_demand)
    job = c.execute("SELECT e.id,e.kind,i.payload FROM executions e LEFT JOIN execution_inputs i ON i.execution_id=e.id WHERE " + condition,
                    (value,)).fetchone()
    if job and (job['kind'] != 'plan_demand' or _object(job['payload']).get('execution_id') != new_demand):
        raise Conflict('trabalho da sucessora não comprova a linhagem')
    return dict(job) if job else None


def recover_expired(queue, engine, limit=1, *, max_candidates=10):
    """Examina até max_candidates e publica no máximo limit recuperações.

    Deferidos ficam em quarentena até retry_review(). A original torna-se
    superseded, vinculada à sucessora no coordenador, antes do enqueue. O
    espelho recovery_links é publicado depois; quedas retomam a mesma sucessora.
    """
    queue.authorize()
    if not engine.q.authorize():
        raise Invalid('coordenação desabilitada')
    if type(limit) is not int or not 1 <= limit <= 10:
        raise Invalid('limite de recuperação inválido')
    if type(max_candidates) is not int or not 1 <= max_candidates <= 100:
        raise Invalid('limite de candidatos inválido')
    _ensure_tables(queue)
    with queue.connect() as c:
        candidates = c.execute("""SELECT e.id,i.payload FROM executions e
            JOIN execution_inputs i ON i.execution_id=e.id
            LEFT JOIN recovery_links r ON r.old_job=e.id
            LEFT JOIN recovery_review v ON v.old_job=e.id
            WHERE e.kind='plan_demand' AND e.execution_status='failed'
              AND e.error='prazo total excedido' AND r.old_job IS NULL AND v.old_job IS NULL
            ORDER BY e.created,e.id LIMIT ?""", (max_candidates,)).fetchall()
    recovered = []
    for job in candidates:
        if len(recovered) >= limit:
            break
        queue.authorize()
        if not engine.q.authorize():
            raise Invalid('coordenação desabilitada')
        try:
            old_id = _object(job['payload']).get('execution_id')
            if not isinstance(old_id, str) or not old_id:
                raise Invalid('identidade da demanda inválida')
        except (Invalid, ValueError, TypeError):
            _defer(queue, job['id'], 'entrada do trabalho inválida')
            continue
        key = 'recuperar-' + job['id'].replace('-', '')
        with engine.q.connect() as c:
            old = c.execute('SELECT status,payload,error FROM demands WHERE id=?', (old_id,)).fetchone()
            steps = c.execute('SELECT capability,status FROM steps WHERE demand_id=?', (old_id,)).fetchall()
            lineage = c.execute('SELECT * FROM demand_supersessions WHERE old_demand=?', (old_id,)).fetchone()
            prior = c.execute('SELECT id,payload FROM demands WHERE request_key=?', (key,)).fetchone()
        reason = _ineligible(old, steps, allow_superseded=bool(lineage))
        if reason:
            _defer(queue, job['id'], reason)
            continue
        if lineage and (lineage['old_job'] != job['id'] or old['status'] != 'superseded'):
            _defer(queue, job['id'], 'original vinculada a outra recuperação ou estado')
            continue
        try:
            payload = _object(old['payload'])
            reference = _reference(payload)
            if prior and not _proves_successor(old_id, payload, _object(prior['payload'])):
                raise Invalid('sucessora não comprova a origem da recuperação')
            if lineage and (not prior or lineage['new_demand'] != prior['id']):
                raise Invalid('sucessora durável ausente ou conflitante')
        except (Invalid, ValueError, TypeError) as failure:
            _defer(queue, job['id'], str(failure))
            continue
        try:
            with queue.connect() as c:
                published = _successor_job(c, prior['id']) if prior else None
        except (Invalid, Conflict, ValueError, TypeError) as failure:
            _defer(queue, job['id'], 'trabalho da sucessora inválido: ' + str(failure))
            continue
        if not published:
            try:
                source = queue.sources.read(reference['record_id'])
            except (Invalid, Conflict, KeyError, OSError):
                _defer(queue, job['id'], 'origem indisponível ou com conflito')
                continue
            if source['revision'] != reference['revision']:
                _defer(queue, job['id'], 'origem corrigida desde a demanda')
                continue
            records, _, issues = engine.k.catalog()
            if issues:
                _defer(queue, job['id'], 'catálogo com inconsistências')
                continue
            if any(record['id'] != reference['record_id'] and
                   any(ref.get('record_id') == reference['record_id'] for ref in refs(record.get('payload', {})))
                   for record in records.values()):
                _defer(queue, job['id'], 'origem já utilizada por outro registro')
                continue
            with engine.q.connect() as c:
                owner = c.execute('SELECT execution_id FROM owned_sources WHERE id=? AND revision=?',
                                  (reference['record_id'], reference['revision'])).fetchone()
            if owner and owner['execution_id'] not in (old_id, prior['id'] if prior else old_id):
                _defer(queue, job['id'], 'origem já atribuída a outra demanda')
                continue
        if prior:
            new_demand = prior['id']
        else:
            text = source['payload']['content']
            entry = {'text': text, 'title': source['title'], 'source_ref': reference,
                     'query': payload.get('query', text[:500]), 'recovery_of': old_id}
            new_demand = engine.start(key, 'contribution', entry)
        try:
            engine.q.supersede(old_id, new_demand, job['id'])
        except ContractError as failure:
            queue.authorize()
            if not engine.q.authorize():
                raise
            _defer(queue, job['id'], 'estado mudou durante a recuperação: ' + str(failure))
            continue
        new_job = published or queue.enqueue('demand-' + new_demand, 'plan_demand', payload={'execution_id': new_demand})
        queue.authorize()
        with queue.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            previous = c.execute('SELECT new_demand,new_job FROM recovery_links WHERE old_job=?', (job['id'],)).fetchone()
            if previous and (previous['new_demand'] != new_demand or previous['new_job'] != new_job['id']):
                raise Conflict('vínculo de recuperação conflitante')
            c.execute('INSERT OR IGNORE INTO recovery_links VALUES(?,?,?)', (job['id'], new_demand, new_job['id']))
            c.execute('DELETE FROM recovery_review WHERE old_job=?', (job['id'],))
            if not previous:
                queue.event(c, job['id'], 'recovered', {'old_demand': old_id, 'new_demand': new_demand, 'new_job': new_job['id']})
        recovered.append({'old_job': job['id'], 'new_demand': new_demand, 'new_job': new_job['id']})
    return recovered


def reconcile_lineage(queue, engine, demands, *, authorize=None):
    """Projeta até 100 demandas, inclusive recovery_links legados, sem escritas.

    API da ponte: records = reconcile_lineage(queue, engine, records, authorize=authorized).
    Sem callback, exige as autorizações operacionais da fila e do coordenador.
    Um callback explícito deve retornar True antes de qualquer leitura e
    substitui somente essas checagens para esta consulta, sem habilitar execução.
    Não consulta fontes, catálogo ou capacidades.
    Preserva raw_status e devolve status='superseded', superseded_by,
    recovery_job_id, recovery_pending e runnable=False somente após validar
    original, sucessora e trabalhos. Conflitos aparecem em lineage_issue e
    nunca escondem uma pendência. Não altera status, limites ou tabelas.
    """
    if authorize is None:
        queue.authorize()
        if not engine.q.authorize():
            raise Invalid('coordenação desabilitada')
    elif not callable(authorize) or authorize() is not True:
        raise Invalid('consulta de linhagem não autorizada')
    if (not isinstance(demands, list) or len(demands) > 100 or
            any(not isinstance(d, dict) or not isinstance(d.get('id'), str) or not d['id'] for d in demands)):
        raise Invalid('demandas da projeção inválidas')
    projected = []
    with engine.q.connect() as c, queue.connect() as qc:
        c.execute('BEGIN')
        qc.execute('BEGIN')
        local_table = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='demand_supersessions'").fetchone()
        legacy_table = qc.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recovery_links'").fetchone()
        legacy_by_old = {}
        if legacy_table and demands:
            placeholders = ','.join('?' for _ in demands)
            links = qc.execute("""SELECT r.old_job,r.new_demand,r.new_job,
                CASE WHEN json_valid(i.payload) THEN json_extract(i.payload,'$.execution_id') END AS old_demand
                FROM recovery_links r JOIN execution_inputs i ON i.execution_id=r.old_job
                WHERE CASE WHEN json_valid(i.payload) THEN json_extract(i.payload,'$.execution_id') END IN (""" + placeholders + ')',
                               tuple(d['id'] for d in demands)).fetchall()
            for link in links:
                legacy_by_old.setdefault(link['old_demand'], []).append(link)
        for record in demands:
            item = dict(record)
            old_id = record['id']
            old = c.execute('SELECT status,payload,error,deadline FROM demands WHERE id=?', (old_id,)).fetchone()
            raw_status = old['status'] if old else record.get('raw_status', record.get('status'))
            item.update(status=raw_status, raw_status=raw_status, superseded_by=None, recovery_job_id=None,
                        recovery_old_job=None, recovery_pending=False, lineage_verified=False,
                        lineage_source=None, lineage_issue=None)
            item['expired'] = bool(old and engine.q.clock() >= old['deadline'])
            item['runnable'] = False if item['expired'] or raw_status not in ('queued', 'blocked') else None
            projected.append(item)
            if not old:
                item['lineage_issue'] = 'demanda inexistente'
                continue
            local = c.execute('SELECT * FROM demand_supersessions WHERE old_demand=?', (old_id,)).fetchone() if local_table else None
            legacy = legacy_by_old.get(old_id, [])
            if not local and not legacy:
                if raw_status == 'superseded':
                    item['lineage_issue'] = 'original substituída sem vínculo verificável'
                continue
            try:
                if len(legacy) > 1:
                    raise Invalid('múltiplos vínculos de recuperação para a original')
                link = local if local else legacy[0]
                if local and (raw_status != 'superseded' or (legacy and
                        (legacy[0]['old_job'] != local['old_job'] or legacy[0]['new_demand'] != local['new_demand']))):
                    raise Invalid('linhagem durável e espelho da fila divergem')
                steps = c.execute('SELECT capability,status FROM steps WHERE demand_id=?', (old_id,)).fetchall()
                reason = _ineligible(old, steps, allow_superseded=bool(local))
                if reason:
                    raise Invalid(reason)
                before = _object(old['payload'])
                _reference(before)
                successor = c.execute('SELECT payload FROM demands WHERE id=?', (link['new_demand'],)).fetchone()
                if not successor or not _proves_successor(old_id, before, _object(successor['payload'])):
                    raise Invalid('sucessora não comprova a origem da recuperação')
                old_job = qc.execute("""SELECT e.kind,e.execution_status,e.error,i.payload FROM executions e
                    LEFT JOIN execution_inputs i ON i.execution_id=e.id WHERE e.id=?""", (link['old_job'],)).fetchone()
                if (not old_job or old_job['kind'] != 'plan_demand' or old_job['execution_status'] != 'failed' or
                        old_job['error'] != 'prazo total excedido' or _object(old_job['payload']).get('execution_id') != old_id):
                    raise Invalid('trabalho antigo não comprova a recuperação por prazo')
                successor_job = _successor_job(qc, link['new_demand'], legacy[0]['new_job'] if legacy else None)
                if legacy and not successor_job:
                    raise Invalid('trabalho da sucessora inexistente')
                item.update(status='superseded', superseded_by=link['new_demand'], recovery_old_job=link['old_job'],
                            recovery_job_id=successor_job['id'] if successor_job else None,
                            recovery_pending=successor_job is None, runnable=False, lineage_verified=True,
                            lineage_source='coordinator' if local else 'recovery_links')
            except (Invalid, Conflict, ValueError, TypeError, KeyError) as failure:
                item['lineage_issue'] = str(failure)
    return projected
