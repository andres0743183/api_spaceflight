from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime
from airflow.models import Variable
import os
# from dags.scripts.mi_script import lambda_handler

# Ruta al script de Python que deseas ejecutar


os.environ['AWS_ACCESS_KEY_ID'] = Variable.get('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = Variable.get('AWS_SECRET_ACCESS_KEY')
os.environ['AWS_DEFAULT_REGION'] = Variable.get('AWS_DEFAULT_REGION')


# Función que ejecutará el script de Python
def ejecutar_script():
    print("AQUI ************************************************************************************************")
    print(os.getcwd())
    contenido = os.listdir('./dags/scripts')
    print(contenido)

# Definir el DAG
with DAG(
    dag_id="mi_dag",
    start_date=datetime(2023, 10, 1),
    schedule_interval="@daily",  # Ejecutar diariamente
    catchup=False,  # No ejecutar tareas pasadas
) as dag:

    # Tarea que ejecuta el script de Python
    ejecutar_script_task = PythonOperator(
        task_id="ejecutar_script",
        python_callable=ejecutar_script,
    )

    ejecutar_blogs = BashOperator(
        task_id="descarga_blogs",
        bash_command="python3 /opt/airflow/dags/scripts/download_data.py /blogs",  # Comando para ejecutar el script
    )

    ejecutar_reports = BashOperator(
        task_id="descarga_reports",
        bash_command="python3 /opt/airflow/dags/scripts/download_data.py /reports",  # Comando para ejecutar el script
    )

    ejecutar_articles = BashOperator(
        task_id="descarga_articles",
        bash_command="python3 /opt/airflow/dags/scripts/download_data.py /articles",  # Comando para ejecutar el script
    )

    fin = DummyOperator(
        task_id='fin',
        dag=dag,
    )
    # Definir el flujo de tareas (en este caso, solo una tarea)

    ejecutar_script_task>>[ejecutar_blogs, ejecutar_reports, ejecutar_articles]>>fin