"""One call of the BentoCloud deployment through the BentoML SDK, which
asks BentoCloud for the endpoint and sends its own credentials: the
inputs as JSON on stdin, the result as JSON on stdout."""

import json
import os
import sys

import bentoml

client = bentoml.deployment.get(os.environ["KAPSO_VALUE_DEPLOYMENT"]).get_client()
print(json.dumps(client.predict(inputs=json.load(sys.stdin))))
