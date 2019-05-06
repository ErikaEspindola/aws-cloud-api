from flask import Flask, request
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
import boto3
import sys
import configparser
import socket
import requests

app = Flask(__name__)
api = Api(app)
access_key = ''
secret_key = ''

CORS(app)


class Keys(Resource):
    def get(self):
        global access_key
        access_key = request.args.get('access_key')
        global secret_key
        secret_key = request.args.get('secret_key')

        get_client()

        return {'status': 'ok'}


api.add_resource(Keys, '/aws_keys')

class InstanceTypes(Resource):
    def get(self):
        get_client()
        return client._service_model.shape_for('InstanceType').enum

api.add_resource(InstanceTypes, '/instace_types')


def get_client():
    global client
    client = boto3.client(
        'ec2',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-2'
    )


class Regions(Resource):
    def get(self):
  #      try:
        response = client.describe_regions()
        return response['Regions']
#        except Exception as e:
 #           return {"error": str(e)}

api.add_resource(Regions, '/listar_regioes')


class SpotInstance(Resource):
    def get(self):
        a = client.request_spot_instances(
            InstanceCount = 1,
            SpotPrice = "0.105",
            LaunchSpecification =  {
                "ImageId": "ami-0360d18a580e175cc",
                "InstanceType": "t2.micro",
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "/dev/xvda",
                        "Ebs": {
                            "DeleteOnTermination": True,
                            "VolumeType": "gp2",
                            "VolumeSize": 8
                        }
                    }
                ],
            },
            Type="one-time"
        )

        a["SpotInstanceRequests"][0]["CreateTime"] = str(a["SpotInstanceRequests"][0]["CreateTime"])
        a["SpotInstanceRequests"][0]["Status"]["UpdateTime"] = str(a["SpotInstanceRequests"][0]["Status"]["UpdateTime"])

        return a

api.add_resource(SpotInstance, '/request_spot_instance')

if __name__ == '__main__':
    app.run(port=5002, debug=True)