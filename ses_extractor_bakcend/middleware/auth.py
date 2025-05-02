
# 新建 middleware/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
# HTTPBearerのインスタンスを作成
security = HTTPBearer()
# JWT設定
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # デフォルト値HS256

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="无效的令牌格式")
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"无效凭证: {str(e)}")