from typing import Annotated

from fastapi import Depends
from secure_knowledge_core.database.session import get_session
from sqlalchemy.orm import Session

DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
