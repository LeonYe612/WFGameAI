import jwt
import datetime
from django.conf import settings

JWT_SECRET = getattr(settings, "JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天
REFRESH_TOKEN_EXPIRE_DAYS = 30     # 30 天

def generate_access_token(user):
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "username": user.username,
        "roles": user.sso_permissions.get("roles", []),
        "exp": expire,
        "type": "access"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire

def generate_refresh_token(user):
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "username": user.username,
        "exp": expire,
        "type": "refresh"
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire

def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token已过期"
    except jwt.InvalidTokenError:
        return None, "无效的Token"