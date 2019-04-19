from flask import Flask, request
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
import boto3, sys, configparser, socket

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
        return {'status': 'ok'}

api.add_resource(Keys, '/aws_keys')

class Regions(Resource):
    def get(self):
        client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        response = client.describe_regions()
        return response['Regions']

api.add_resource(Regions, '/listar_regioes')

if __name__ == '__main__':
    app.run(port=5002, debug=True)