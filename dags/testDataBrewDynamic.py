from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
import json
import uuid
# pip install boto3
import boto3
#pip install botocore
import botocore

dag = DAG('testDataBrew_dynamic_dag', start_date=datetime(2024,1,30))

# Create a DataBrew client
databrew_client = boto3.client('databrew')
# client object acts as a gateway for you to perform DataBrew operations programmatically

bucket_name = 'databrewbuckettest'
file_key = 'persons_data.json'
file_format = file_key.split(".")[-1].upper()
file_key_output = 'outputtest1.csv'
file_format_output = file_key_output.split(".")[-1].upper()
format_options_str = '{"Json": {"MultiLine": true}}' if file_format == 'JSON' else ''
format_options = json.loads(format_options_str) if format_options_str else None

dataset_name = 'my-dataset1'
recipe_name = 'my-recipe1'
project_name = 'my-project1'
job_name = 'my-job1'
role_arn_key = 'arn:aws:iam::379605592402:role/service-role/AWSGlueDataBrewServiceRole-test'


def check_dataset_exists(dataset_name):
    response = databrew_client.list_datasets()
    existing_datasets = response.get('Datasets', [])
    return any(dataset['Name'] == dataset_name for dataset in existing_datasets)

def create_dataset(dataset_name, bucket, key, format_type, format_options):
    if check_dataset_exists(dataset_name):
        print(f"Dataset '{dataset_name}' already exists. Skipping creation.")
        return

    dataset_params = {
        'Name': dataset_name,
        'Format': format_type,
        'Input': {
            'S3InputDefinition': {
                'Bucket': bucket,
                'Key': key
            }
        }
    }
    if format_type == 'JSON':
        dataset_params['FormatOptions'] = format_options

    response = databrew_client.create_dataset(**dataset_params)
    print(f"Dataset created: {response['Name']}")


def check_recipe_exists(recipe_name):
    response = databrew_client.list_recipes()
    existing_recipes = response.get('Recipes', [])
    return any(recipe['Name'] == recipe_name for recipe in existing_recipes)

def create_recipe(recipe_name):
    try:
        if check_recipe_exists(recipe_name):
            print(f"Recipe '{recipe_name}' already exists. Skipping creation.")
            return

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

    except botocore.exceptions.ClientError as e:
        # Handle the case where an exception occurs
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"Error: {e}")
            print(f"Recipe '{recipe_name}' already exists. Skipping creation.")
        else:
            raise  # Re-raise the exception if it's not a ConflictException


def check_project_exists(project_name):
    response = databrew_client.list_projects()
    existing_projects = response.get('Projects', [])
    return any(project['Name'] == project_name for project in existing_projects)

def create_project(dataset_name, project_name, recipe_name, role_arn):
    if check_project_exists(project_name):
        print(f"Project '{project_name}' already exists. Skipping creation.")
        return

    print(f"Creating project with dataset: {dataset_name}")
    print(f"Creating project with recipe: {recipe_name}")
    response = databrew_client.create_project(
        DatasetName=dataset_name,
        Name=project_name,
        RecipeName=recipe_name,
        RoleArn=role_arn
    )
    print(f"Project created: {response['Name']}")


def check_job_exists(job_name):
    response = databrew_client.list_jobs()
    existing_jobs = response.get('Jobs', [])
    return any(job['Name'] == job_name for job in existing_jobs)

def create_job(job_name, project_name, bucket, key, format_type, role_arn):
    if check_job_exists(job_name):
        print(f"Job '{job_name}' already exists. Skipping creation.")
        return

    response = databrew_client.create_recipe_job(
        Name=job_name,
        RoleArn=role_arn,
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
        'format_type': file_format_output,
        'role_arn': role_arn_key
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