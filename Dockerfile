# Use the official AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Set the working directory to the Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the requirements file into the image
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy the Lambda function script to the task root
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py

# Set the command to invoke the Lambda handler
CMD ["lambda_function.lambda_handler"]
