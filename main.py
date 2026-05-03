from sqlmodel import SQLModel, Field, Relationship
from typing import List

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str

    messages_envoyes: List["Message"] = Relationship(
        back_populates="expediteur",
        sa_relationship_kwargs={"foreign_keys": "Message.expediteur_id"}
    )
    messages_recus: List["Message"] = Relationship(
        back_populates="destinataire",
        sa_relationship_kwargs={"foreign_keys": "Message.destinataire_id"}
    )

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject: str
    content: str

    expediteur_id: int = Field(foreign_key="user.id")
    expediteur: User = Relationship(
        back_populates="messages_envoyes",
        sa_relationship_kwargs={"foreign_keys": "Message.expediteur_id"}
    )

    destinataire_id: int = Field(foreign_key="user.id")
    destinataire: User = Relationship(
        back_populates="messages_recus",
        sa_relationship_kwargs={"foreign_keys": "Message.destinataire_id"}
    )

# typical boilerplate code

from sqlmodel import create_engine, Session

# local SQLite file
database_url = "sqlite:///./users.db"
engine = create_engine(database_url, echo=True)

# create tables
# of course this needs to come AFTER all model definitions...
SQLModel.metadata.create_all(engine)

# utility function to get a session
def get_session():
    with Session(engine) as session:
        yield session

# this uses so-called "dependency injection"
# meaning the session is (re-)created on demand by FastAPI

from fastapi import FastAPI, Depends

app = FastAPI()

@app.post("/users/", response_model=User)
def create_user(user: User, session: Session = Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)  # reload the object with the generated ID
    return user

from typing import List

@app.get("/users/", response_model=List[User])
def list_users(session: Session = Depends(get_session)):
    users = session.query(User).all()
    return users
