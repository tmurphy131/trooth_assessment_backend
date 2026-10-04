from fastapi import HTTPException, status

class UnauthorizedException(HTTPException):
    def __init__(self, detail="Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    def __init__(self, detail="Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(HTTPException):
    def __init__(self, detail="Not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ValidationException(HTTPException):
    # 400, not 422: released apps already receive 400 from the handler in app/main.py.
    def __init__(self, detail="Invalid input"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
