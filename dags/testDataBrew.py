from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.operators.glue_databrew import GlueDataBrewStartJobOperator
# pip install boto3
import boto3
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook

dag = DAG('testDataBrew_dag', start_date=datetime(2024,1,29))

# Create a DataBrew client
databrew_client = boto3.client('databrew')
# client object acts as a gateway for you to perform DataBrew operations programmatically

def create_dataset():
    response = databrew_client.create_dataset(
        Name='my-dataset',
        Format='JSON',
        FormatOptions={
            'Json': {
                'MultiLine': True
            },
        },
        Input={
            'S3InputDefinition': {
                'Bucket': 'databrewbuckettest',
                'Key': 'persons_data.json'
            }
        }
    )
    print(f"Dataset created: {response['Name']}")

def create_recipe():
    response = databrew_client.create_recipe(
        Description='recipe created for testing',
        Name='my-recipe',
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

def create_project():
    response = databrew_client.create_project(
        DatasetName = 'my-dataset',
        Name = 'my-project',
        RecipeName = 'my-recipe',
        RoleArn = 'arn:aws:iam::379605592402:role/service-role/AWSGlueDataBrewServiceRole-test'
    )
    print(f"Project created: {response['Name']}")

def create_job():
    response = databrew_client.create_recipe_job(
        Name='my-job',
        RoleArn = 'arn:aws:iam::379605592402:role/service-role/AWSGlueDataBrewServiceRole-test',
        ProjectName='my-project',
        Outputs=[
            {
                'Location': {
                    'Bucket': 'databrewbuckettest',
                    'Key': 'outputtest.csv'
                },
                'Format':'CSV',
            }
        ]
    )
    print(f"Job created: {response['Name']}")

  
def start_job():
    response = databrew_client.start_job_run(Name='my-job')
    print(f"Job run started: {response['RunId']}")

create_dataset_task = PythonOperator(
    task_id='create_dataset',
    python_callable=create_dataset
)
create_recipe_task = PythonOperator(
    task_id='create_recipe',
    python_callable=create_recipe
)
create_project_task = PythonOperator(
    task_id='create_project',
    python_callable=create_project
)
create_job_task = PythonOperator(
    task_id='create_job',
    python_callable=create_job
)
start_job_task = PythonOperator(
    task_id='start_job',
    python_callable=start_job
)


start = DummyOperator(task_id='start', dag=dag)
end = DummyOperator(task_id='end', dag=dag)

start >> create_dataset_task >> create_recipe_task >> create_project_task >> create_job_task >> start_job_task >> end