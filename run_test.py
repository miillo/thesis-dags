import requests
from datetime import datetime
import time

dag_uuids_file = 'result_uuids.txt'
prometheus_api_url = "http://localhost:8080/api/v1/"
headers = {'Content-type': 'application/json'}
credentials = ("admin", "admin")

with open(dag_uuids_file, newline='') as dag_uuids:
    lines = dag_uuids.readlines()
    for line in lines:
        r = requests.get(url=prometheus_api_url + "dags", auth=credentials)

        payload = f'{{ "execution_date": "{datetime.utcnow().isoformat() + "Z"}", "conf": {{ }} }}'
        response = requests.post(url=prometheus_api_url + "dags/" + "ngs-pipeline-" + line.rstrip() + "/dagRuns",
                                 auth=credentials, data=payload, headers=headers)
        print(response.json())

        while True:
            dag_run_response = requests.get(url=prometheus_api_url + "dags/" + "ngs-pipeline-" + line.rstrip() +
                                                "/dagRuns", auth=credentials).json()
            if dag_run_response['dag_runs'][0]['state'] != "running":
                print("DAG " + "ngs-pipeline-" + line + " just ended. State: " + dag_run_response['dag_runs'][0]['state'])
                break
            print("DAG " + "ngs-pipeline-" + line + " is still running...")
            time.sleep(10)

