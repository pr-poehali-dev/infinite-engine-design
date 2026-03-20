"""
Термодинамические расчёты и ИИ-чат по проекту двигателя.
POST /calc — выполнить расчёт (entropy, carnot, heat_balance, second_law)
POST /chat — отправить сообщение ИИ и получить ответ
GET /chat?project_id=N — история чата
GET /calc?project_id=N — история расчётов
"""
import json
import os
import math
import psycopg2

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 't_p12938855_infinite_engine_desi')

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])

# ─── Термодинамические расчёты ────────────────────────────────────────────────

def calc_carnot(T_hot: float, T_cold: float) -> dict:
    """КПД цикла Карно: η = 1 - T_cold/T_hot"""
    if T_hot <= 0 or T_cold <= 0:
        return {'error': 'Температуры должны быть в Кельвинах (> 0)'}
    eta = 1 - (T_cold / T_hot)
    return {
        'eta': round(eta * 100, 4),
        'formula': 'η = 1 - T₂/T₁',
        'T_hot_K': T_hot,
        'T_cold_K': T_cold,
        'verdict': 'КПД не может превышать 100% — второй закон термодинамики' if eta >= 1 else f'Максимальный КПД = {round(eta*100,2)}%'
    }

def calc_entropy(Q: float, T: float) -> dict:
    """Изменение энтропии: ΔS = Q/T"""
    if T <= 0:
        return {'error': 'Температура должна быть в Кельвинах (> 0)'}
    delta_s = Q / T
    return {
        'delta_S': round(delta_s, 6),
        'formula': 'ΔS = Q/T',
        'Q_joules': Q,
        'T_kelvin': T,
        'verdict': 'ΔS > 0 — необратимый процесс' if delta_s > 0 else ('ΔS = 0 — обратимый процесс' if delta_s == 0 else 'ΔS < 0 — невозможно без внешней работы')
    }

def calc_heat_balance(Q_in: float, W_out: float) -> dict:
    """Тепловой баланс: Q_out = Q_in - W_out, η = W/Q_in"""
    Q_out = Q_in - W_out
    eta = (W_out / Q_in * 100) if Q_in > 0 else 0
    delta_S_total = (Q_out / 300) - (Q_in / 600)  # примерные температуры
    return {
        'Q_in': Q_in,
        'W_out': W_out,
        'Q_out': round(Q_out, 4),
        'eta_percent': round(eta, 4),
        'delta_S_total': round(delta_S_total, 6),
        'formula': 'Q_вых = Q_вх - W; η = W/Q_вх',
        'second_law_ok': Q_out >= 0,
        'verdict': 'Закон сохранения энергии соблюдён' if Q_out >= 0 else '⚠ Нарушение первого начала термодинамики!'
    }

def calc_second_law(delta_S_system: float, delta_S_surroundings: float) -> dict:
    """Второй закон: ΔS_universe = ΔS_system + ΔS_surroundings ≥ 0"""
    delta_S_universe = delta_S_system + delta_S_surroundings
    return {
        'delta_S_system': delta_S_system,
        'delta_S_surroundings': delta_S_surroundings,
        'delta_S_universe': round(delta_S_universe, 6),
        'formula': 'ΔS_universe = ΔS_system + ΔS_окружения ≥ 0',
        'second_law_ok': delta_S_universe >= 0,
        'verdict': 'Второй закон соблюдён' if delta_S_universe >= 0 else '⚠ Нарушение второго начала термодинамики — такой процесс невозможен!'
    }

# ─── ИИ-ответы (встроенная база знаний) ──────────────────────────────────────

PHYSICS_KB = {
    'бесконечный двигатель': 'Бесконечный двигатель (perpetuum mobile) первого рода нарушает закон сохранения энергии, второго рода — второй закон термодинамики. Оба запрещены физикой. Однако можно проектировать устройства с максимально высоким КПД, близким к циклу Карно.',
    'кпд': 'Максимальный КПД тепловой машины определяется циклом Карно: η = 1 - T₂/T₁. Чем больше разность температур, тем выше КПД. Реальные машины всегда имеют КПД ниже карновского из-за трений, теплопотерь и необратимостей.',
    'карно': 'Цикл Карно — идеальный обратимый цикл между двумя тепловыми резервуарами. Состоит из: 1) изотермического расширения при T₁, 2) адиабатного расширения, 3) изотермического сжатия при T₂, 4) адиабатного сжатия. η_Карно = 1 - T_холодного/T_горячего.',
    'энтропия': 'Энтропия — мера беспорядка системы. ΔS = Q/T для обратимых процессов. Второй закон: энтропия изолированной системы всегда возрастает или остаётся постоянной. ΔS_universe ≥ 0.',
    'второй закон': 'Второй закон термодинамики: теплота самопроизвольно не переходит от холодного тела к горячему. Формулировка Клаузиуса: невозможно передать теплоту от холодного тела к горячему без совершения работы.',
    'первый закон': 'Первый закон термодинамики: энергия не создаётся и не уничтожается. ΔU = Q - W, где ΔU — изменение внутренней энергии, Q — теплота, W — работа системы.',
    'тепловой насос': 'Тепловой насос переносит теплоту от холодного источника к горячему, потребляя работу. КПД (COP) = Q_горяч / W = T₁ / (T₁ - T₂). Может быть > 1, что не нарушает термодинамику.',
    'турбина': 'Паровая турбина преобразует тепловую энергию пара в механическую работу. Пар расширяется, его энтальпия уменьшается. КПД турбины ограничен циклом Ренкина (~35-45% для современных ТЭС).',
    'схема': 'Типовая схема тепловой машины: Источник тепла → Рабочее тело (пар/газ) → Турбина/поршень → Конденсатор → Насос → обратно к источнику. Разность температур источника и стока определяет максимальный КПД.',
}

def ai_response(message: str) -> str:
    msg_lower = message.lower()
    for key, answer in PHYSICS_KB.items():
        if key in msg_lower:
            return answer
    if any(w in msg_lower for w in ['привет', 'здравствуй', 'привет']):
        return 'Приветствую в лаборатории термодинамики! Я знаю физику тепловых машин, энтропии, циклов Карно и термодинамических законов. Задайте вопрос или опишите устройство — рассчитаю параметры.'
    if any(w in msg_lower for w in ['формула', 'рассчита', 'вычисли']):
        return 'Для расчёта используйте вкладку "Расчёты". Я могу посчитать: КПД цикла Карно, изменение энтропии (ΔS = Q/T), тепловой баланс и проверку второго закона термодинамики.'
    if any(w in msg_lower for w in ['чертёж', 'схем', 'проект', 'конструкц']):
        return 'Для проектирования откройте "Конструктор схем" — там можно добавить компоненты: источник тепла, турбину, конденсатор, насос, маховик. Соедините их тепловыми и рабочими потоками, укажите температуры и давления.'
    return 'Термодинамика — строгая наука. Уточните вопрос: КПД, энтропия, цикл Карно, первый или второй закон? Или опишите устройство, которое хотите спроектировать — подберу оптимальные параметры.'

# ─── Handler ──────────────────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    params = event.get('queryStringParameters') or {}
    path = event.get('path', '/')
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])

    conn = get_conn()
    cur = conn.cursor()

    try:
        # ─── Расчёты ────────────────────────────────
        if 'calc' in path:
            if method == 'GET':
                project_id = params.get('project_id')
                if project_id:
                    cur.execute(
                        f"SELECT id, calc_type, input_params, result, ai_explanation, created_at FROM {SCHEMA}.calculations WHERE project_id = %s ORDER BY created_at DESC LIMIT 50",
                        (int(project_id),)
                    )
                    rows = cur.fetchall()
                    calcs = [{'id': r[0], 'calc_type': r[1], 'input': r[2], 'result': r[3], 'explanation': r[4], 'created_at': str(r[5])} for r in rows]
                    return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'calculations': calcs})}

            elif method == 'POST':
                project_id = body.get('project_id')
                calc_type = body.get('calc_type', 'carnot')
                inp = body.get('params', {})

                result = {}
                if calc_type == 'carnot':
                    result = calc_carnot(float(inp.get('T_hot', 600)), float(inp.get('T_cold', 300)))
                elif calc_type == 'entropy':
                    result = calc_entropy(float(inp.get('Q', 1000)), float(inp.get('T', 300)))
                elif calc_type == 'heat_balance':
                    result = calc_heat_balance(float(inp.get('Q_in', 1000)), float(inp.get('W_out', 300)))
                elif calc_type == 'second_law':
                    result = calc_second_law(float(inp.get('delta_S_system', 0)), float(inp.get('delta_S_surroundings', 0)))
                else:
                    result = {'error': f'Неизвестный тип расчёта: {calc_type}'}

                explanation = result.get('verdict', '')

                if project_id:
                    cur.execute(
                        f"INSERT INTO {SCHEMA}.calculations (project_id, calc_type, input_params, result, ai_explanation) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (project_id, calc_type, json.dumps(inp), json.dumps(result), explanation)
                    )
                    calc_id = cur.fetchone()[0]
                    conn.commit()
                else:
                    calc_id = None

                return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'id': calc_id, 'calc_type': calc_type, 'result': result})}

        # ─── ИИ-чат ────────────────────────────────
        elif 'chat' in path:
            if method == 'GET':
                project_id = params.get('project_id')
                if project_id:
                    cur.execute(
                        f"SELECT id, role, message, created_at FROM {SCHEMA}.ai_chat WHERE project_id = %s ORDER BY created_at ASC LIMIT 100",
                        (int(project_id),)
                    )
                    rows = cur.fetchall()
                    messages = [{'id': r[0], 'role': r[1], 'message': r[2], 'created_at': str(r[3])} for r in rows]
                    return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'messages': messages})}

            elif method == 'POST':
                project_id = body.get('project_id')
                user_message = body.get('message', '')
                if not user_message:
                    return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Пустое сообщение'})}

                ai_answer = ai_response(user_message)

                if project_id:
                    cur.execute(
                        f"INSERT INTO {SCHEMA}.ai_chat (project_id, role, message) VALUES (%s, 'user', %s)",
                        (project_id, user_message)
                    )
                    cur.execute(
                        f"INSERT INTO {SCHEMA}.ai_chat (project_id, role, message) VALUES (%s, 'assistant', %s)",
                        (project_id, ai_answer)
                    )
                    conn.commit()

                return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'reply': ai_answer})}

        return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Маршрут не найден'})}

    finally:
        cur.close()
        conn.close()
