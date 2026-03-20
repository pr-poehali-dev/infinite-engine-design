"""
CRUD для проектов бесконечного двигателя.
GET / — список проектов
POST / — создать проект
GET /?id=N — получить проект
PUT / — обновить проект
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
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])

    conn = get_conn()
    cur = conn.cursor()

    try:
        if method == 'GET':
            project_id = params.get('id')
            if project_id:
                cur.execute(
                    f"SELECT id, name, description, status, efficiency, created_at, updated_at FROM {SCHEMA}.projects WHERE id = %s",
                    (int(project_id),)
                )
                row = cur.fetchone()
                if not row:
                    return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Проект не найден'})}
                data = {
                    'id': row[0], 'name': row[1], 'description': row[2],
                    'status': row[3], 'efficiency': float(row[4]) if row[4] else None,
                    'created_at': str(row[5]), 'updated_at': str(row[6])
                }
                return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'project': data})}
            else:
                cur.execute(
                    f"SELECT id, name, description, status, efficiency, created_at, updated_at FROM {SCHEMA}.projects ORDER BY updated_at DESC"
                )
                rows = cur.fetchall()
                projects = [
                    {'id': r[0], 'name': r[1], 'description': r[2], 'status': r[3],
                     'efficiency': float(r[4]) if r[4] else None,
                     'created_at': str(r[5]), 'updated_at': str(r[6])}
                    for r in rows
                ]
                return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'projects': projects})}

        elif method == 'POST':
            name = body.get('name', 'Новый проект')
            description = body.get('description', '')
            cur.execute(
                f"INSERT INTO {SCHEMA}.projects (name, description, status) VALUES (%s, %s, 'draft') RETURNING id",
                (name, description)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return {'statusCode': 201, 'headers': CORS, 'body': json.dumps({'id': new_id, 'message': 'Проект создан'})}

        elif method == 'PUT':
            project_id = body.get('id')
            if not project_id:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Не указан id'})}
            fields = []
            values = []
            for field in ['name', 'description', 'status', 'efficiency']:
                if field in body:
                    fields.append(f"{field} = %s")
                    values.append(body[field])
            if not fields:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Нет полей для обновления'})}
            fields.append("updated_at = NOW()")
            values.append(int(project_id))
            cur.execute(
                f"UPDATE {SCHEMA}.projects SET {', '.join(fields)} WHERE id = %s",
                values
            )
            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'message': 'Проект обновлён'})}

        return {'statusCode': 405, 'headers': CORS, 'body': json.dumps({'error': 'Метод не поддерживается'})}

    finally:
        cur.close()
        conn.close()
