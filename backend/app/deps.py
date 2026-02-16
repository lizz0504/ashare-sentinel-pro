"""
Dependency functions for FastAPI
包含认证相关的依赖注入函数
"""
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    获取当前用户ID的依赖函数

    Args:
        credentials: HTTP认证凭证

    Returns:
        str: 用户ID

    Raises:
        HTTPException: 认证失败时抛出异常
    """
    token = credentials.credentials

    try:
        # 这里是一个简化的验证过程
        try:
            # 验证 JWT token
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET.encode(),
                algorithms=["HS256"],
                audience="authenticated"
            )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user_id

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_optional(request: Request):
    """
    获取当前用户ID的可选依赖函数（允许未认证访问）

    Args:
        request: HTTP请求对象

    Returns:
        Optional[str]: 用户ID，如果未认证则返回 None
    """
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET.encode(),
            algorithms=["HS256"],
            audience="authenticated"
        )

        return payload.get("sub")

    except Exception:
        # 认证失败时不抛出异常，而是返回 None
        return None