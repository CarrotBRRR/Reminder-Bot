import json
import base64

test_obj = {
    "id": None,
    "issuer_id": 123456789012345678,
}

with open("test.json", "w") as f:
    json.dump(test_obj, f, indent=4)

with open("test.json", "r") as f:
    data = json.load(f)
    print(data["id"])
    print(data["issuer_id"])