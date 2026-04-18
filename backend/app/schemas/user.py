from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
