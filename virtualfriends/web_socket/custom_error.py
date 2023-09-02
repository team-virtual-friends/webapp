class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"CustomError: {self.args[0]}"
    
    def NoError():
        return CustomError("")
    
    def IsError(self):
        return len(self.args[0]) > 0
