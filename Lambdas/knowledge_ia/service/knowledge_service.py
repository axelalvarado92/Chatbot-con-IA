import boto3

s3 = boto3.client("s3")

_knowledge_cache = None


def obtener_knowledge(
    bucket,
    knowledge_file
):

    global _knowledge_cache

    if _knowledge_cache is None:

        response = s3.get_object(
            Bucket=bucket,
            Key=knowledge_file
        )

        _knowledge_cache = (
            response["Body"]
            .read()
            .decode("utf-8")
        )

    return _knowledge_cache


def limpiar_cache_knowledge():

    global _knowledge_cache
    _knowledge_cache = None