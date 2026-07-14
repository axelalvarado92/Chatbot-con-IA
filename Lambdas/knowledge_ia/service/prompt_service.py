import boto3
import json

s3 = boto3.client("s3")
_prompt_cache = None
_knowledge_cache = None

def obtener_prompt(bucket, prompt_file):

    global _prompt_cache

    if _prompt_cache is None:

        response = s3.get_object(
            Bucket=bucket,
            Key=prompt_file
        )

        _prompt_cache = json.loads(
            response["Body"].read().decode("utf-8")
        )

    return _prompt_cache

