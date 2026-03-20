"""
Управление компонентами и связями схемы двигателя.
GET /?project_id=N — получить схему (компоненты + связи)
POST /component — добавить компонент
PUT /component — обновить позицию/параметры компонента
POST /connection — добавить связь между компонентами
"""
import json
import os
import psycopg2

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 't_p12938855_infinite_engine_desi')

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])

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
        # GET /?project_id=N — вся схема
        if method == 'GET':
            project_id = params.get('project_id')
            if not project_id:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Не указан project_id'})}

            cur.execute(
                f"SELECT id, type, label, pos_x, pos_y, params FROM {SCHEMA}.components WHERE project_id = %s ORDER BY id",
                (int(project_id),)
            )
            components = [
                {'id': r[0], 'type': r[1], 'label': r[2],
                 'pos_x': float(r[3]), 'pos_y': float(r[4]), 'params': r[5]}
                for r in cur.fetchall()
            ]

            cur.execute(
                f"SELECT id, from_component_id, to_component_id, flow_type, value FROM {SCHEMA}.connections WHERE project_id = %s ORDER BY id",
                (int(project_id),)
            )
            connections = [
                {'id': r[0], 'from_id': r[1], 'to_id': r[2],
                 'flow_type': r[3], 'value': float(r[4]) if r[4] else None}
                for r in cur.fetchall()
            ]

            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'components': components, 'connections': connections})}

        # POST — добавить компонент или связь
        elif method == 'POST':
            if 'component' in path:
                project_id = body.get('project_id')
                comp_type = body.get('type', 'generic')
                label = body.get('label', comp_type)
                pos_x = body.get('pos_x', 0)
                pos_y = body.get('pos_y', 0)
                comp_params = json.dumps(body.get('params', {}))
                cur.execute(
                    f"INSERT INTO {SCHEMA}.components (project_id, type, label, pos_x, pos_y, params) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (project_id, comp_type, label, pos_x, pos_y, comp_params)
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                return {'statusCode': 201, 'headers': CORS, 'body': json.dumps({'id': new_id, 'message': 'Компонент добавлен'})}

            elif 'connection' in path:
                project_id = body.get('project_id')
                from_id = body.get('from_id')
                to_id = body.get('to_id')
                flow_type = body.get('flow_type', 'heat')
                value = body.get('value')
                cur.execute(
                    f"INSERT INTO {SCHEMA}.connections (project_id, from_component_id, to_component_id, flow_type, value) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (project_id, from_id, to_id, flow_type, value)
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                return {'statusCode': 201, 'headers': CORS, 'body': json.dumps({'id': new_id, 'message': 'Связь добавлена'})}

        # PUT — обновить компонент
        elif method == 'PUT':
            comp_id = body.get('id')
            if not comp_id:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Не указан id компонента'})}
            fields = []
            values = []
            for field in ['label', 'pos_x', 'pos_y']:
                if field in body:
                    fields.append(f"{field} = %s")
                    values.append(body[field])
            if 'params' in body:
                fields.append("params = %s")
                values.append(json.dumps(body['params']))
            if fields:
                values.append(int(comp_id))
                cur.execute(
                    f"UPDATE {SCHEMA}.components SET {', '.join(fields)} WHERE id = %s",
                    values
                )
                conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'message': 'Компонент обновлён'})}

        return {'statusCode': 405, 'headers': CORS, 'body': json.dumps({'error': 'Метод не поддерживается'})}

    finally:
        cur.close()
        conn.close()
