import json
import boto3
import email
from sms_spam_classifier_utilities import one_hot_encode
from sms_spam_classifier_utilities import vectorize_sequences
import os

def lambda_handler(event, context):
    vocabulary_length = 9013
    # TODO implement
    s3_client = boto3.client('s3', region_name='us-east-1')

    s3_info = event['Records'][0]['s3']
    bucket = s3_info['bucket']['name']
    name = s3_info['object']['key'].replace("%40","@")
    
    response = s3_client.get_object(Bucket=bucket, Key=name)
    e = response['Body'].read()
    message = email.message_from_string(e.decode("utf-8"))
    msg_boday = message.get_payload()[0].get_payload().replace("\n"," ").replace("\r", " ") 
    
    ENDPOINT_NAME = os.environ['ENDPOINT']
    one_hot_test_messages = one_hot_encode(msg_boday, vocabulary_length)
    encoded_test_messages = vectorize_sequences(one_hot_test_messages, vocabulary_length)
    encoded_json_msg = json.dumps(encoded_test_messages)
    
    runtime= boto3.client('runtime.sagemaker', region_name='us-east-1')
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                   ContentType='text/csv',
                                   Body=encoded_json_msg)
    
    result = response['Body'].read()
    print(result)
    
    SENDER = message['To']
    RECIPIENT = message['From']
    
    AWS_REGION = "us-east-1"
    
    SUBJECT = "Spam Filter Analysis"
    result = json.loads(result)
    
    classification = ["HAM", "SPAM"][int(result['predicted_label'][0][0])]
    prob = result["predicted_probability"][0][1]
    
    BODY_TEXT = "We received your email sent at {} with the subject {}.\r\n".format(message['Date'], message['SUBJECT'])
    BODY_TEXT += "\r\nHere is a 240 character sample of the email body:\r\n"
    BODY_TEXT += "\r\n" + msg_boday[:240] + "\r\n"
    BODY_TEXT += "\r\nThe email was categorized as {} ".format(classification)
    BODY_TEXT += "with a {:.1%} confidence.".format(prob)

    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)
    
    response = client.send_email(
        Destination={
            'ToAddresses': [
                RECIPIENT,
            ],
        },
        Message={
            'Body': {
                'Text': {
                    'Charset': CHARSET,
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
        Source=SENDER,
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
