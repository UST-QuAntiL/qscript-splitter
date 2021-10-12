import sys
import threading
import requests
import postPart


def send_error(error_code, external_task_id):
    body = {
        "workerId": "PreprocessingPollingAgent",
        "errorCode": error_code
    }
    response = requests.post(pollingEndpoint + '/' + external_task_id + '/bpmnError', json=body)
    print(response.status_code)


def poll():
    """
    Poll at the camunda engine to retrieve the task for the preprocessing step
    :return:
    """
    print('Polling for new external tasks at the Camunda engine with URL: ', pollingEndpoint)

    body = {
        "workerId": "PreprocessingPollingAgent",
        "maxTasks": 1,
        "topics":
            [{"topicName": topic,
              "lockDuration": 100000000
              }]
    }

    response = requests.post(pollingEndpoint + '/fetchAndLock', json=body)
    #print(response)
    if response.status_code == 200:
        for externalTask in response.json():
            variables = externalTask.get('variables')
            values = []
            for var in variables.values():
                values.append(var["value"])

            # call the wrapper function of the pre part
            result = postPart.post(*values)

            # provided variables
            prov_variables = dict()
            for var in result:
                prov_variables[var] = {"value": var}

            body = {
                "workerId": "PostprocessingPollingAgent",
                "variables": prov_variables
            }
            response = requests.post(pollingEndpoint + '/' + externalTask.get('id') + '/complete', json=body)
            #print(response.status_code)

    threading.Timer(20, poll).start()


# maybe get the endpoint from a parameter
# check if there are suitable inputs given via command line
if sys.argv[1] is not None:
    pollingEndpoint = sys.argv[1]
else:
    pollingEndpoint = "http://localhost:8080/engine-rest"
if sys.argv[2] is not None:
    topic = sys.argv[2]
else:
    topic = "RandomPost"
poll()
