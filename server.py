from flask import Flask, request
import paramiko
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api, reqparse
import json
from flask_jsonpify import jsonify
import boto3
import sys
import configparser
import socket
import requests
import time
import os

app = Flask(__name__)
api = Api(app)
access_key = ''
secret_key = ''

CORS(app)

parser = reqparse.RequestParser()


def createSecurityGroup():
    print('dentro')
    args = request.get_json(force=True)
    ec2Client = get_client(args['ak'], args['sk'])

    try:
        res = ec2Client.create_security_group(
            GroupName='EC2INI-GrupoSegurancaSCP-SSH',
            Description='Autorizar SSH e SCP'
        )
        ec2Client.authorize_security_group_ingress(
            GroupId=res['GroupId'],
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 0,
                'ToPort': 65535,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }])
        ec2Client.authorize_security_group_egress(
            GroupId=res['GroupId'],
            IpPermissions=[{
                'IpProtocol': '-1',
                'FromPort': 0,
                'ToPort': 65535,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }])
    except:
        pass

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
    def sendFiles(self, hostname):
        clientSftp = paramiko.SSHClient()
        clientSftp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        directory = os.path.join('/tmp')
        for filename in os.listdir(directory):
            if (filename.endswith('.pem')):
                old_file = os.path.join(directory, filename)
                new_file = os.path.join(directory, "amazonKey.pem")
                os.rename(old_file, new_file)
                break

        ip = hostname
        print(ip)
        ip = ip.split('.')
        print(ip)
        ip = ip[0].replace('ec2-', '')
        print(ip)
        ip = ip.replace('-', '.')
        print(ip)
        clientSftp.connect(ip, username='ec2-user', key_filename=directory + '\\amazonKey.pem')
        sftp = clientSftp.open_sftp()

        for filename in os.listdir(directory):
            print("Copiando...")
            print(directory + '\\' + filename)
            print("Pronto")
            sftp.put(directory + '\\' + filename, '/home/ec2-user/' + filename)
        sftp.close()



    def getHostName(self, response):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])

        ec2Rsrc = boto3.resource('ec2')
        requestId = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        time.sleep(25)
        instanceId = client.describe_spot_instance_requests(SpotInstanceRequestIds=[requestId])
        instanceId = instanceId['SpotInstanceRequests'][0]['InstanceId']

        instancia = ec2Rsrc.Instance(instanceId)
        instancia.load()
        return instancia.public_dns_name

    def sendScript(self, host, script):
        print('chamou o post ein')
        response = requests.post('http://127.0.0.1:5002/sendCommand/'+script+'/'+host)
        print("voltou do post ein")
        return response.text

    def post(self):
        args = request.get_json(force=True)
        client = get_client(args['ak'], args['sk'])

        createSecurityGroup()
        response = client.request_spot_instances(
            InstanceCount = 1,
            SpotPrice = args['SpotPrice'],
            LaunchSpecification =  {
                "KeyName": "amazonKey",
                "SecurityGroups": ["EC2INI-GrupoSegurancaSCP-SSH"],
                "ImageId": "ami-013587c46717c510a",
                "InstanceType": args['InstanceType'],
            },
            Type="one-time"
        )

        response["SpotInstanceRequests"][0]["CreateTime"] = str(response["SpotInstanceRequests"][0]["CreateTime"])
        response["SpotInstanceRequests"][0]["Status"]["UpdateTime"] = str(response["SpotInstanceRequests"][0]["Status"]["UpdateTime"])
        self.sendFiles(self.getHostName(response))
        print('chamou o sendScript')
        res = self.sendScript(self.getHostName(response), args['VolumeType'])
        print ("Voltou pro comeco")
        return res

api.add_resource(SpotInstance, '/request_spot_instance')


class UploadFile(Resource):
    def post(self):
        target = os.path.join('/tmp')
        file = request.files['file']
        file_name = file.filename or ''
        destination = '/'.join([target, file_name])
        file.save(destination)

api.add_resource(UploadFile, '/upload_file')

class SendCommand(Resource):
    def post(self, script, host):
        print('entrou no post')
        ssh = paramiko.SSHClient()
        try:
            pemKey = paramiko.RSAKey.from_private_key_file("/tmp/amazonKey.pem")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(hostname=host, username="ec2-user", pkey=pemKey)

            stdin, stdout, stderr = ssh.exec_command(script)
            res = stdout.readlines()
            res = [i.replace('\n', '') for i in res]
            jsonRes = jsonify(saida=res)

            ssh.close()
            return jsonRes
        except Exception as e:
            return e


api.add_resource(SendCommand, '/sendCommand/<string:script>/<string:host>')


if __name__ == '__main__':
    app.run(port=5002, debug=True)