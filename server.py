from flask import Flask, request
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api, reqparse
from json import dumps
from flask_jsonpify import jsonify
import boto3
import sys
import configparser
import socket
import requests
import time

app = Flask(__name__)
api = Api(app)
access_key = ''
secret_key = ''

CORS(app)

parser = reqparse.RequestParser()

def get_client(ak, sk):
    client = boto3.client(
        'ec2',
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name='us-east-2'
    )

    return client

class InstanceTypes(Resource):
    def post(self):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])
        return client._service_model.shape_for('InstanceType').enum

api.add_resource(InstanceTypes, '/instance_types')

class GetInstances(Resource):
    def post(self):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])
        response = client.describe_instances()

        if(response['Reservations']):
            response['Reservations'][0]['Instances'][0]['LaunchTime'] = str(response['Reservations'][0]['Instances'][0]['LaunchTime'])
        else:
            response = 'Nao existem instancias'
        return response

api.add_resource(GetInstances, '/get_instances')

class Regions(Resource):
    def post(self):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])
        response = client.describe_regions()
        return response['Regions']

api.add_resource(Regions, '/listar_regioes')


class SpotInstance(Resource):
    def post(self):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])

        response = client.request_spot_instances(
            InstanceCount = 1,
            SpotPrice = args['SpotPrice'],
            LaunchSpecification =  {
                "ImageId": args['ImageId'],
                "InstanceType": args['InstanceType'],
                "BlockDeviceMappings": [
                    {
                        "DeviceName": args['DeviceName'],
                        "Ebs": {
                            "DeleteOnTermination": True,
                            "VolumeType": args['VolumeType'],
                            "VolumeSize": int(args['VolumeSize'])
                        }
                    }
                ],
            },
            Type="one-time"
        )

        response["SpotInstanceRequests"][0]["CreateTime"] = str(response["SpotInstanceRequests"][0]["CreateTime"])
        response["SpotInstanceRequests"][0]["Status"]["UpdateTime"] = str(response["SpotInstanceRequests"][0]["Status"]["UpdateTime"])

        return response

api.add_resource(SpotInstance, '/request_spot_instance')

class SendCommand(Resource):
    def post(self):
        # args = request.get_json(force=True)

        ssm = boto3.client('ssm',
                                region_name='us-east-2',
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key)

        testCommand = ssm.send_command(InstanceIds=['i-0cddfadf629ec95c8'], DocumentName='AWS-RunShellScript', Parameters={ "commands":[ "ps aux" ] } )

        time.sleep(5)
        response = ssm.get_command_invocation(
            CommandId = testCommand['Command']['CommandId'],
            InstanceId = testCommand['Command']['InstanceIds'][0]
        )
        return response

api.add_resource(SendCommand, '/send_command')

if __name__ == '__main__':
    app.run(port=5002, debug=True)