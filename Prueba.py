

import boto3
import json


def ejecutar_lambda(endpoints="/blogs"):
    # Crear un cliente de Lambda
    lambda_client = boto3.client('lambda')

    # Parámetros que se enviarán a la función Lambda
    payload = {
        "endpoints": [endpoints]
    }

    # Convertir el payload a JSON
    payload_json = json.dumps(payload)

    # Invocar la función Lambda
    response = lambda_client.invoke(
        FunctionName='api-data-ingestor-88990484',  # Reemplaza con el nombre de tu función Lambda
        InvocationType='RequestResponse',
        Payload=payload_json
    )

    # Leer la respuesta
    response_payload = json.loads(response['Payload'].read())

    # Imprimir la respuesta

    return response_payload