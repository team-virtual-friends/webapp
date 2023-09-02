import json

from custom_error import CustomError

class WebSocketMessage():
    def __init__(self, action:str, message:str, data:str, err:CustomError):
        self.action = action
        self.message = message
        self.data = data
        self.err = err

    def __str__(self):
        return f"WebSocketMessage: {self.action}, {self.message}, {self.data}, {self.err}"

    def to_json(self):
        json_obj = {"action": self.action, "message": self.message, "data": self.data, "err": str(self.err)}
        return json.dumps(json_obj)
