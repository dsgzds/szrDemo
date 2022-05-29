import io
import boto3
import logging
import mimetypes

AWS_ACCESS_KEY_ID = 'AKIA56IU572O45QU5PCU'
AWS_SECRET_ACCESS_KEY = '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'


def get_file_mime_type(path):
    return mimetypes.MimeTypes().guess_type(path)[0]

class S3Client(object):

    def __init__(self, bucket_name, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY):
        self.bucket = bucket_name
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

    def upload_file_by_path(self, path, uri):
        try:
            mt = get_file_mime_type(path)
            self.s3.upload_file(path, self.bucket, uri, ExtraArgs={'ContentType': mt})
            return True
        except Exception as err:
            logging.exception(err)
            return False
        

    def upload_file_by_obj(self, fileobj, uri, mime_type='binary/octet-stream'):
        try:
            self.s3.upload_fileobj(fileobj, self.bucket, uri, ExtraArgs={'ContentType': mime_type})
            return True
        except Exception as err:
            logging.exception(err)
            return False

    def upload_file_by_data(self, data, uri, mime_type='binary/octet-stream'):
        try:
            self.s3.put_object(Bucket=self.bucket, Body=data, Key=uri, ExtraArgs={'ContentType': mime_type})
            return True
        except Exception as err:
            logging.exception(err)
            return False

    def read_file(self, uri):
        try:
            f = self.s3.get_object(Bucket=self.bucket, Key=uri)
            return f['Body'].read()
        except Exception as err:
            logging.exception(err)
            return

if __name__ == '__main__':
    c = S3Client('xfacee')
    with open('test.jpeg', 'rb') as f:
        data = f.read()

    # c.upload_fileobj(data, 'medias/zzz/test.jpeg')
    c.upload_file_by_data(data, 'medias/zzz/test.jpg')

