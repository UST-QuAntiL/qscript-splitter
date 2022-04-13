# ******************************************************************************
#  Copyright (c) 2022 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************

import threading
import base64
import os
import pickle

import requests
from urllib.request import urlopen
import app


def poll():
    print('Polling for new external tasks at the Camunda engine with URL: ', pollingEndpoint)

    body = {
        "workerId": "$ServiceNamePlaceholder",
        "maxTasks": 1,
        "topics":
            [{"topicName": topic,
              "lockDuration": 100000000
              }]
    }

    try:
        response = requests.post(pollingEndpoint + '/fetchAndLock', json=body)

        if response.status_code == 200:
            for externalTask in response.json():
                print('External task with ID for topic ' + str(externalTask.get('topicName')) + ': ' + str(externalTask.get('id')))
                variables = externalTask.get('variables')
                if externalTask.get('topicName') == topic:
                    ### LOAD INPUT DATA ###
                    ### CALL SCRIPT PART ###
                    ### STORE OUTPUT DATA SECTION ###

                    # send response
                    response = requests.post(pollingEndpoint + '/' + externalTask.get('id') + '/complete', json=body)
                    print('Status code of response message: ' + str(response.status_code))

    except Exception as err:
        print('Exception during polling: ', err)

    threading.Timer(8, poll).start()


def download_data(url):
    response = urlopen(url)
    data = response.read().decode('utf-8')
    return str(data)

# start polling for requests
camundaEndpoint = os.environ['CAMUNDA_ENDPOINT']
pollingEndpoint = camundaEndpoint + '/external-task'
topic = os.environ['CAMUNDA_TOPIC']
poll()
