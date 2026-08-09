import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mirror how SAM assembles the deployment package: the Lambda Layer's
# python/ directory and the function's own CodeUri directory both end up
# on sys.path at runtime.
sys.path.insert(0, os.path.join(ROOT, "layers", "common_layer", "python"))
sys.path.insert(0, os.path.join(ROOT, "src", "register"))
sys.path.insert(0, os.path.join(ROOT, "src", "list_events"))
sys.path.insert(0, os.path.join(ROOT, "src", "get_registrations"))
sys.path.insert(0, os.path.join(ROOT, "src", "cancel_registration"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
