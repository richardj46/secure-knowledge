from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from secure_knowledge_core.database.session import get_session

DatabaseSession = Annotated[Session, Depends(get_session)]