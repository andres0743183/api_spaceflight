import os, sys
import json
import requests
from datetime import datetime, timedelta
import boto3
import time
from botocore.exceptions import ClientError


# Configuración de clientes AWS
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Variables de entorno
os.environ['RAW_BUCKET'] = 'spaceflight-raw-data-test'
os.environ['DLQ_URL'] = 'https://sqs.us-east-2.amazonaws.com/120569625886/errorspaceflightnewsapi'
os.environ['STATE_TABLE'] = 'pipeline-state'


RAW_BUCKET = os.environ['RAW_BUCKET']
DLQ_URL = os.environ['DLQ_URL']
STATE_TABLE = os.environ['STATE_TABLE']
API_BASE_URL = "https://api.spaceflightnewsapi.net/v4"



def lambda_handler(event=None, context=None, endpoints=None):
    print("Iniciando extracción...")
    try:
        # Si no se proporcionan endpoints, usar los predeterminados
        if endpoints is None:
            endpoints = ['/articles', '/blogs', '/reports']

        # Procesar todos los endpoints
        for endpoint in endpoints:
            print(f"Procesando endpoint: {endpoint}")
            # Obtener última fecha procesada para este endpoint
            last_processed = get_last_processed_date(endpoint) or get_default_start_date()
            print(f"Iniciando extracción desde: {last_processed}")

            # Procesar el endpoint
            process_endpoint(endpoint, last_processed)

            # Actualizar estado para este endpoint
            update_last_processed_date(endpoint)

        return {
            'statusCode': 200,
            'body': "Extracción completada."
        }

    except Exception as e:
        handle_error(e)
        raise


def process_endpoint(endpoint, last_date):
    next_url = build_initial_url(endpoint, last_date)

    while next_url:
        try:
            response = make_api_request(next_url)
            data = response.json()

            process_results(data['results'], endpoint)
            print(next_url)
            next_url = data.get('next')
            handle_rate_limit(response.headers)

        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 429:
                handle_rate_limit(err.response.headers, force_retry=True)
            else:
                log_error(f"HTTP Error {err.response.status_code}: {err.response.text}")
                raise


def make_api_request(url):
    response = requests.get(
        url,
        headers={
            'User-Agent': 'SpaceflightDataPipeline/1.0',
            'Accept': 'application/json'
        },
        timeout=30
    )
    response.raise_for_status()
    return response


def process_results(results, endpoint):
    for item in results:
        try:
            if should_process_item(item):
                s3_key = generate_s3_key(item, endpoint)
                if not object_exists(RAW_BUCKET, s3_key):
                    save_to_s3(item, s3_key)
        except Exception as e:
            log_error(f"Error procesando item {item.get('id')}: {str(e)}")
            continue


def generate_s3_key(item, endpoint):
    publish_date = datetime.strptime(
        item['published_at'], '%Y-%m-%dT%H:%M:%SZ'
    )
    return (
        f"{endpoint[1:]}/"
        f"year={publish_date.year}/"
        f"month={publish_date.month:02d}/"
        f"day={publish_date.day:02d}/"
        f"{item['id']}.json"
    )


def save_to_s3(item, key):
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(item),
        ContentType='application/json',
        Metadata={
            'source': 'spaceflight-news-api',
            'processed': 'false'
        }
    )


def should_process_item(item):
    # Validación adicional si es necesaria
    return all([
        item.get('id'),
        item.get('published_at'),
        item.get('title')
    ])


def handle_rate_limit(headers, force_retry=False):
    limit = int(headers.get('X-RateLimit-Limit', 10))
    remaining = int(headers.get('X-RateLimit-Remaining', 1))

    if remaining <= 2 or force_retry:
        reset_time = int(headers.get('X-RateLimit-Reset', 5))
        sleep_time = max(reset_time, 5)
        print(f"Rate limit alcanzado. Esperando {sleep_time} segundos")
        time.sleep(sleep_time)


def get_last_processed_date(endpoint):
    try:
        table = dynamodb.Table(STATE_TABLE)
        # Usar el endpoint como clave primaria
        response = table.get_item(Key={'id': f'last_processed_{endpoint[1:]}'})
        return response['Item']['timestamp'] if 'Item' in response else None
    except ClientError as e:
        log_error(f"Error DynamoDB: {str(e)}")
        return None


def update_last_processed_date(endpoint):
    try:
        table = dynamodb.Table(STATE_TABLE)
        # Usar el endpoint como clave primaria
        table.put_item(
            Item={
                'id': f'last_processed_{endpoint[1:]}',  # Ejemplo: last_processed_articles
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'updated_at': datetime.utcnow().isoformat()
            },
            ConditionExpression='attribute_not_exists(id) OR updated_at <= :now',
            ExpressionAttributeValues={':now': datetime.utcnow().isoformat()}
        )
    except ClientError as e:
        log_error(f"Error actualizando estado: {str(e)}")


def get_default_start_date():
    return (datetime.utcnow() - timedelta(days=1*10)).isoformat() + "Z"


def build_initial_url(endpoint, last_date):
    return (
        f"{API_BASE_URL}{endpoint}"
        f"?published_at_gt={last_date}"
        f"&ordering=published_at"
        f"&limit=100"
    )

def object_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False

def handle_error(error):
    error_message = f"{datetime.utcnow()} - {str(error)}"
    sqs.send_message(
        QueueUrl=DLQ_URL,
        MessageBody=error_message,
        MessageAttributes={
            'Service': {'DataType': 'String', 'StringValue': 'SpaceflightIngestor'},
            'Severity': {'DataType': 'String', 'StringValue': 'HIGH'}
        }
    )
    log_error(error_message)

def log_error(message):
    print(f"ERROR: {message}")


# Handler para pruebas locales
# Handler para pruebas locales
if __name__ == "__main__":
    # Obtener los endpoints desde los argumentos de la línea de comandos
    if len(sys.argv) > 1:
        endpoints = sys.argv[1:]  # Todos los argumentos después del nombre del script
    else:
        endpoints = ['/articles', '/blogs', '/reports']  # Valores predeterminados

    print(f"Endpoints a procesar: {endpoints}")
    lambda_handler(endpoints=endpoints)
    time.sleep(20)
