"""One call of the deployed function through the Modal SDK: the inputs as
JSON on stdin, the result as JSON on stdout. The SDK reads its own
credentials (`modal token new`, or MODAL_TOKEN_ID and MODAL_TOKEN_SECRET)."""

import json
import os
import sys

import modal

function = modal.Function.from_name(os.environ["KAPSO_VALUE_APP"], "predict")
print(json.dumps(function.remote(json.load(sys.stdin))))
