import time
import os
import boto3
import json
import logging
from datetime import datetime
from sagemaker.huggingface import HuggingFaceModel, get_huggingface_llm_image_uri

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("INFO: Loading environment variables.")
ENDPOINT_NAME = os.getenv('ENDPOINT_NAME')
MODEL_LOCATION = os.getenv('LOCATION')
SAGEMAKER_ROLE = os.getenv('ROLE')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')

# Initialize AWS clients
sns_client = boto3.client('sns')
s3_client = boto3.resource('s3')
sns_failure_topic_arn = f'arn:aws:sns:us-west-3:{AWS_ACCOUNT_ID}:your-failure-topic-name'

def get_current_timestamp():
    """Returns the current timestamp as a string."""
    return str(datetime.now())

def lambda_handler(event, context):
    start_time = time.time()

    try:
        logger.info("INFO: Creating Hugging Face Model Configuration")
        hub_config = {
            'HF_MODEL_ID': '/opt/ml/model',
            'SM_NUM_GPUS': json.dumps(1),
            'MAX_INPUT_LENGTH': json.dumps(12287),
            'MAX_TOTAL_TOKENS': json.dumps(12288),
            'MAX_BATCH_PREFILL_TOKENS': json.dumps(12288)
        }

        logger.info("INFO: Creating Hugging Face Model Class")
        huggingface_model = HuggingFaceModel(
            model_data=MODEL_LOCATION,
            env=hub_config,
            role=SAGEMAKER_ROLE,
            image_uri=get_huggingface_llm_image_uri("huggingface", version="1.3.3")
        )

        logger.info("INFO: Deploying Model to SageMaker Inference")
        predictor = huggingface_model.deploy(
            initial_instance_count=1,
            instance_type="ml.g5.4xlarge",
            endpoint_name=ENDPOINT_NAME,
            container_startup_health_check_timeout=1200
        )

        logger.info("INFO: SageMaker Endpoint Created Successfully")
        elapsed_time = time.time() - start_time
        logger.info(f"Elapsed Time for Endpoint Creation: {int(elapsed_time) // 60}m {int(elapsed_time) % 60}s")
        return "Successfully created endpoint."

    except Exception as error:
        logger.error("ERROR: Unable to Deploy Endpoint")
        logger.error(f"Exception: {error}")

        error_message = {
            "timestamp": get_current_timestamp(),
            "aws_request_id": context.aws_request_id,
            "error": str(error),
            "service": "lambda/sagemaker-endpoint-init"
        }

        # Publish error notification to SNS
        sns_client.publish(
            TargetArn=sns_failure_topic_arn,
            Message=json.dumps({"default": json.dumps(error_message)}),
            MessageStructure='json'
        )

        # Log error details to S3
        error_date = datetime.utcnow().strftime("%Y-%m-%d")
        error_timestamp = get_current_timestamp()
        s3_error_path = f'error/endpoint_init/{error_date}/{error_timestamp}/error.json'
        bucket_name = os.getenv('ERROR_BUCKET_NAME')  # Ensure bucket name is available in environment variables

        s3_client.Bucket(bucket_name).put_object(Key=s3_error_path, Body=json.dumps(error_message))
        raise error
