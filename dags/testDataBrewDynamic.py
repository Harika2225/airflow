from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
import json
# pip install boto3
import boto3

dag = DAG('testDataBrew_dynamic_dag', start_date=datetime(2024,1,30))

# Create a DataBrew client
databrew_client = boto3.client('databrew')
# client object acts as a gateway for you to perform DataBrew operations programmatically

def create_dataset(dataset_name, bucket, key, format_type, format_options):
    response = databrew_client.create_dataset(
        Name=dataset_name,
        Format=format_type,
        FormatOptions=format_options,
        Input={
            'S3InputDefinition': {
                'Bucket': bucket,
                'Key': key
            }
        }
    )
    print(f"Dataset created: {response['Name']}")

def create_recipe(recipe_name):
    response = databrew_client.create_recipe(
        Description='recipe created for testing',
        Name=recipe_name,
        Steps=[
            {
                'Action': {
                    'Operation': 'MOVE_TO_START',
                    'Parameters': {
                        'sourceColumn': 'name', 
                    }
                },
            },
            {
                'Action': {
                    'Operation' : 'MOVE_AFTER',
                    'Parameters': {
                        'sourceColumn': 'phone',
                        'targetColumn': 'name',
                    }
                }
            },
            {
                'Action': {
                    'Operation' : 'MOVE_TO_INDEX',
                    'Parameters': {
                        'sourceColumn': 'region',
                        'targetIndex': '3',
                    }
                }
            },
            {
                'Action': {
                    'Operation' : 'MERGE',
                    'Parameters': {
                        'delimiter': ', ',
                        'sourceColumns': '["region","country"]',
                        'targetColumn': 'Area'
                    }
                }
            }
        ],
    )
    print(f"Recipe created: {response['Name']}")

def create_project(dataset_name, project_name, recipe_name, role_arn):
    response = databrew_client.create_project(
        DatasetName=dataset_name,
        Name=project_name,
        RecipeName=recipe_name,
        RoleArn=role_arn
    )
    print(f"Project created: {response['Name']}")

def create_job(job_name, project_name, bucket, key, format_type):
    response = databrew_client.create_recipe_job(
        Name=job_name,
        RoleArn='arn:aws:iam::379605592402:role/service-role/AWSGlueDataBrewServiceRole-test',
        ProjectName=project_name,
        Outputs=[
            {
                'Location': {
                    'Bucket': bucket,
                    'Key': key
                },
                'Format': format_type,
            }
        ]
    )
    print(f"Job created: {response['Name']}")

def start_job(job_name):
    response = databrew_client.start_job_run(Name=job_name)
    print(f"Job run started: {response['RunId']}")

bucket_name = 'databrewbuckettest'
file_key = 'persons_data.json'
file_format = file_key.split(".")[-1].upper()
file_key_output = 'outputtest1.csv'
file_format_output = file_key_output.split(".")[-1].upper()
# format_options = '{"Json": {"MultiLine": true}}' if file_format == 'JSON' else ''
format_options_str = '{"Json": {"MultiLine": true}}' if file_format == 'JSON' else ''
format_options = json.loads(format_options_str) if format_options_str else None

dataset_name = 'my-dataset1'
recipe_name = 'my-recipe1'
project_name = 'my-project1'
job_name = 'my-job1'
role_arn_key = 'arn:aws:iam::379605592402:role/service-role/AWSGlueDataBrewServiceRole-test'

create_dataset_task = PythonOperator(
    task_id='create_dataset',
    python_callable=create_dataset,
    op_kwargs={
        'dataset_name' : dataset_name,
        'bucket': bucket_name,
        'key': file_key,
        'format_type': file_format,
        'format_options': format_options
    }
)

create_recipe_task = PythonOperator(
    task_id='create_recipe',
    python_callable=create_recipe,
     op_kwargs={
        'recipe_name' : recipe_name,
    }
)

create_project_task = PythonOperator(
    task_id='create_project',
    python_callable=create_project,
    op_kwargs={
        'dataset_name': dataset_name,
        'recipe_name': recipe_name,
        'project_name': project_name,
        'role_arn': role_arn_key
    }
)

create_job_task = PythonOperator(
    task_id='create_job',
    python_callable=create_job,
    op_kwargs={
        'job_name': job_name,
        'project_name': project_name,
        'bucket': bucket_name,
        'key': file_key_output,
        'format_type': file_format_output
    }
)

start_job_task = PythonOperator(
    task_id='start_job',
    python_callable=start_job,
    op_kwargs={
        'job_name': job_name
    }
)

start = DummyOperator(task_id='start', dag=dag)
end = DummyOperator(task_id='end', dag=dag)

start >> create_dataset_task >> create_recipe_task >> create_project_task >> create_job_task >> start_job_task >> end