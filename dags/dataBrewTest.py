from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.amazon.aws.operators.glue_databrew import GlueDataBrewStartJobOperator
# pip install apache-airflow-providers-amazon

with DAG('dataBrew_dag', start_date = datetime(2024, 1, 23), schedule='@daily') as dag:
    dataBrew_task = GlueDataBrewStartJobOperator(
        task_id='dataBrew_task',
        job_name="test", 
        aws_conn_id='aws_conn_id',
    )
    #in connections-create a new connection named aws_conn_id and fill the aws credentials

start = DummyOperator(task_id='start', dag=dag)
end = DummyOperator(task_id='end', dag=dag)

start >> dataBrew_task >> end