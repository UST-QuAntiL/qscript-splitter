[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# qscript splitter

This service takes a Python-based quantum implementation (i.e., a Python file and a requirements.txt file) as input and splits it into its quantum and classical parts.
It further generates a workflow.
Additionally, an agent is generated which handles the transfer of input/output parameters between the script parts and the workflow.

The qscript-splitter can be used in conjunction with the [QuantME Transformation Framework](https://github.com/UST-QuAntiL/QuantME-TransformationFramework).
Furthermore, a use case showing the analysis and rewrite of quantum workflows using the qiskit-runtime-handler is available [here](https://github.com/UST-QuAntiL/QuantME-UseCases/tree/master/2022-edoc).

## Docker Setup

* Clone the repository:
```
git clone https://github.com/UST-QuAntiL/qscript-splitter.git
```

* Start the containers using the [docker-compose file](docker-compose.yml):
```
docker-compose pull
docker-compose up
```

Now the qscript-splitter is available on http://localhost:8889/.

## Local Setup

### Start Redis

Start Redis, e.g., using Docker:

```
docker run -p 5040:5040 redis --port 5040
```

### Configure the qscript-splitter

Before starting the qscript-splitter, define the following environment variables:

```
FLASK_RUN_PORT=8889
REDIS_URL=redis://$DOCKER_ENGINE_IP:5040
```

Thereby, please replace $DOCKER_ENGINE_IP with the actual IP of the Docker engine you started the Redis container.

### Configure the Database

* Install SQLite DB, e.g., as described [here](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database)
* Create a `data` folder in the `app` folder
* Setup the results table with the following commands:

```
flask db migrate -m "results table"
flask db upgrade
```

### Start the Application

Start a worker for the request queue:

```
rq worker --url redis://$DOCKER_ENGINE_IP:5040 script-splitting-handler
```

Finally, start the Flask application, e.g., using PyCharm or the command line.
