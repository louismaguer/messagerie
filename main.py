from sqlmodel import SQLModel, Field, Relationship, select, col, func
from typing import List, Dict
from datetime import datetime

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str

    sent_messages: List["Message"] = Relationship(back_populates="sender", sa_relationship_kwargs={"foreign_keys": "Message.sender_id"})
    received_messages: List["Message"] = Relationship(back_populates="receiver", sa_relationship_kwargs={"foreign_keys": "Message.receiver_id"})

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject: str
    body: str
    date: datetime = Field(default_factory=datetime.now)
    is_read: bool = Field(default=False)

    sender_id: int = Field(foreign_key="user.id")
    sender: User = Relationship(back_populates="sent_messages", sa_relationship_kwargs={"foreign_keys": "Message.sender_id"})

    receiver_id: int = Field(foreign_key="user.id")
    receiver: User = Relationship(back_populates="received_messages", sa_relationship_kwargs={"foreign_keys": "Message.receiver_id"})

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

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_json_message(self, data: dict, user_id: int):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(data)

manager = ConnectionManager()

@app.post("/users/", response_model=User)
def create_user(user: User, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.name == user.name)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà existant")
    session.add(user)
    session.commit()
    session.refresh(user)  # reload the object with the generated ID
    return user

from typing import List

@app.get("/users/", response_model=List[User])
def list_users(limit: int | None = None, offset: int = 0, session: Session = Depends(get_session)):
    query = select(User).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    users = session.exec(query).all()
    return users

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur inexistant")
    return user

@app.post("/messages/", response_model=Message)
async def create_message(message: Message, session: Session = Depends(get_session)):
    
    sender = session.get(User, message.sender_id)
    if not sender:
        raise HTTPException(status_code=404, detail="Expéditeur inexistant")
    
    receiver = session.get(User, message.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Destinataire inexistant")

    if not message.subject:
        raise HTTPException(status_code=400, detail="Sujet vide")
    if not message.body:
        raise HTTPException(status_code=400, detail="Corps du message vide")
    if message.sender_id == message.receiver_id:
        raise HTTPException(status_code=400, detail="Même expéditeur et destinataire")

    session.add(message)
    session.commit()
    session.refresh(message)  # reload the object with the generated ID

    message_data = {"id": message.id, "subject": message.subject, "body": message.body, "date": message.date, "is_read": message.is_read, "sender_id": message.sender_id, "receiver_id": message.receiver_id}
    await manager.send_json_message(message_data, message.receiver_id)

    return message

@app.get("/messages/", response_model=List[Message])
def list_messages(limit: int | None = None, offset: int = 0, session: Session = Depends(get_session)):
    query = select(Message).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    messages = session.exec(query).all()
    return messages

@app.get("/users/{user_id}/inbox", response_model=List[Message])
def get_inbox(user_id: int, unread_only: bool = False, limit: int | None = None, offset: int = 0, search: str | None = None, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur inexistant")
    
    query = select(Message).where(Message.receiver_id == user_id)
    if unread_only:
        query = query.where(Message.is_read == False)
    if search:
        query = query.where(col(Message.subject).contains(search))
    
    query = query.order_by(col(Message.date).desc()).offset(offset)
    if limit is not None:
        query = query.limit(limit)

    messages = session.exec(query).all()
    return messages

@app.get("/users/{user_id}/sent", response_model=List[Message])
def get_sent_messages(user_id: int, limit: int | None = None, offset: int = 0, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur inexistant")
    query = select(Message).where(Message.sender_id == user_id).order_by(col(Message.date).desc()).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    messages = session.exec(query).all()
    return messages

@app.get("/messages/{message_id}", response_model=Message)
def get_message(message_id: int, session: Session = Depends(get_session)):
    message = session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message inexistant")
    return message

@app.patch("/messages/{message_id}/read", response_model=Message)
def mark_message_as_read(message_id: int, session: Session = Depends(get_session)):
    message = session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message inexistant")
    message.is_read = True
    session.add(message)
    session.commit()
    session.refresh(message)
    return message

@app.delete("/messages/{message_id}")
def delete_message(message_id: int, session: Session = Depends(get_session)):
    message = session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message inexistant")
    session.delete(message)
    session.commit()
    return {"detail": "Message supprimé"}

@app.get("/users/{user_id}/unread_count")
def get_unread_count(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur inexistant")
    count = session.exec(select(func.count(col(Message.id))).where(Message.receiver_id == user_id, Message.is_read == False)).one()
    return {"unread_count": count}

@app.websocket("/ws/users/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        await websocket.close()
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(user_id)