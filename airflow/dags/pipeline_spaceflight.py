from airflow import DAG
from airflow.providers.amazon.aws.operators.lambda_function import LambdaInvokeFunctionOperator
from airflow.providers.amazon.aws.hooks.glue import GlueJobHook
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator

from airflow.operators.dummy import DummyOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import os, json
import boto3

os.environ['AWS_ACCESS_KEY_ID'] = Variable.get('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = Variable.get('AWS_SECRET_ACCESS_KEY')
os.environ['AWS_DEFAULT_REGION'] = Variable.get('AWS_DEFAULT_REGION')

# Configuración inicial del DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'pipeline_spaceflight',
    default_args=default_args,
    description='DAG para descarga de datos y ejecución de Glue Crawlers',
    schedule_interval=None,
    tags=['data_pipeline'],
) as dag:

    # Nodo inicial y final
    start = DummyOperator(task_id='inicio_pipeline')


    # Configuración de endpoints y crawlers
    endpoints_config = [
        ('/articles', 'articles_crawler'),
        ('/blogs', 'blogs-crawler'),
        ('/reports', 'reports-crawler')
    ]

    lambda_articles = LambdaInvokeFunctionOperator(
        task_id='descarga_articles',
        function_name=Variable.get('lambda_descarga'),
        payload=json.dumps({"endpoints": ["/articles"]})
    )
    #
    lambda_blogs = LambdaInvokeFunctionOperator(
        task_id='descarga_blogs',
        function_name=Variable.get('lambda_descarga'),
        payload=json.dumps({"endpoints": ["/blogs"]})
    )
    #
    lambda_reports = LambdaInvokeFunctionOperator(
        task_id='descarga_reports',
        function_name=Variable.get('lambda_descarga'),
        payload=json.dumps({"endpoints": ["/reports"]})
    )

    crawler_articles = GlueCrawlerOperator(
        task_id='crawler_articles',
        config={
            'Name': Variable.get("crawler_articles"),  # Cambia esto por el nombre de tu Glue Crawler
        },
        aws_conn_id='aws_default',  # Cambia si tienes una conexión diferente en Airflow
        wait_for_completion=True,  # Espera a que el crawler termine antes de continuar
        poll_interval=10,  # Intervalo en segundos para revisar el estado
    )

    crawler_blogs = GlueCrawlerOperator(
        task_id='crawler_blogs',
        config={
            'Name': Variable.get("crawler_blogs"),  # Cambia esto por el nombre de tu Glue Crawler
        },
        aws_conn_id='aws_default',  # Cambia si tienes una conexión diferente en Airflow
        wait_for_completion=True,  # Espera a que el crawler termine antes de continuar
        poll_interval=10,  # Intervalo en segundos para revisar el estado
    )

    crawler_reports = GlueCrawlerOperator(
        task_id='crawler_reports',
        config={
            'Name': Variable.get("crawler_reports"),  # Cambia esto por el nombre de tu Glue Crawler
        },
        aws_conn_id='aws_default',  # Cambia si tienes una conexión diferente en Airflow
        wait_for_completion=True,  # Espera a que el crawler termine antes de continuar
        poll_interval=10,  # Intervalo en segundos para revisar el estado
    )

    # run_s3 = DummyOperator(task_id='run_s3')

    create_dwh = DummyOperator(task_id='creando_data_warehouse')
    # Estructura de dependencias
    start>>lambda_articles >> crawler_articles>>create_dwh
    start>>lambda_blogs>> crawler_blogs>>create_dwh
    start>>lambda_reports >> crawler_reports>>create_dwh

    # start >> [crawler_articles, crawler_blogs, crawler_reports]

