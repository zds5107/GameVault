import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, exists
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
import jwt

from app.database import get_db
from app.models import (
    CollectionEntry,
    CollectionStatus,
    Game,
    OwnershipType,
    PlayStatus,
    User
)

password_hash = PasswordHash.recommended()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not isinstance(user_id, str) or not user_id.isdigit():
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, int(user_id))

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

app = FastAPI(title="GameVault API")

class GameResponse(BaseModel):
    id: int
    title: str
    platform: str


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

class GameCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    platform: str = Field(min_length=1, max_length=100)

    @field_validator("title", "platform")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        return clean_nonblank_string(value)


class GameUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    platform: str = Field(min_length=1, max_length=100)

    @field_validator("title", "platform")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        return clean_nonblank_string(value)

class CollectionEntryCreate(BaseModel):
    game_id: int
    collection_status: CollectionStatus
    ownership_type: OwnershipType | None = None
    play_status: PlayStatus

class CollectionEntryUpdate(BaseModel):
    collection_status: CollectionStatus = None
    ownership_type: OwnershipType | None = None
    play_status: PlayStatus = None

class CollectionEntryResponse(BaseModel):
    id: int
    game_id: int
    user_id: int
    collection_status: CollectionStatus
    ownership_type: OwnershipType | None
    play_status: PlayStatus
    game: GameResponse
    


def clean_nonblank_string(value: str) -> str:
    if not value.strip():
        raise ValueError("This field cannot be blank")

    return value.strip()


@app.get("/")
def root():
    return {"message" : "Welcome to GameVault"}

@app.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user




@app.get("/games", response_model=list[GameResponse])
def get_games(db: Session = Depends(get_db)):
    result = db.scalars(select(Game)).all()
    return result

@app.get("/games/{game_id}", response_model=GameResponse)
def get_game(
    game_id: int,
    db: Session = Depends(get_db),
):
    game = db.get(Game, game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return game 

@app.post("/games", response_model=GameResponse, status_code=201)
def create_game(
    game_data: GameCreate,
    db: Session = Depends(get_db),
):
    new_game = Game(
        title=game_data.title,
        platform=game_data.platform,
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return new_game

@app.put("/games/{game_id}", response_model=GameResponse)
def update_game(
    game_id: int,
    game_data: GameUpdate,
    db: Session = Depends(get_db),
):

    game = db.get(Game, game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    game.title = game_data.title
    game.platform = game_data.platform

    db.commit()
    db.refresh(game)

    return game

@app.delete("/games/{game_id}", status_code=204)
def delete_game(
    game_id:int,
    db: Session = Depends(get_db),
):

    game = db.get(Game, game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    game_is_referenced = db.scalar(
        select(
            exists().where(CollectionEntry.game_id == game_id)
        )
    )

    if game_is_referenced:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a game that appears in a collection",
        )

    db.delete(game)
    db.commit()
    return

@app.post(
    "/collection-entries",
    response_model=CollectionEntryResponse,
    status_code=201,
)
def create_collection_entry(
    entry: CollectionEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    game = db.get(Game, entry.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if (
        entry.collection_status == CollectionStatus.OWNED
        and entry.ownership_type is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Owned entries must have an ownership type",
        )

    if (
        entry.collection_status == CollectionStatus.WISHLIST
        and entry.ownership_type is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Wishlist entries cannot have an ownership type",
        )

    new_entry = CollectionEntry(
        user_id=current_user.id,
        game_id=entry.game_id,
        collection_status=entry.collection_status,
        ownership_type=entry.ownership_type,
        play_status=entry.play_status,
    )

    db.add(new_entry)

    #catches all integrity errors, meh code make specific when more integrity errors can occur
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This game is already in the user's collection",
        )

    db.refresh(new_entry)
    return new_entry

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = User(
        email=user.email.strip().lower(),
        password_hash=password_hash.hash(user.password),
    )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists",
        )

    db.refresh(new_user)
    return new_user


@app.get("/collection-entries", response_model=list[CollectionEntryResponse])
def get_collection_entries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = db.scalars(select(CollectionEntry).where(CollectionEntry.user_id == current_user.id)).all()

    return results


@app.get("/collection-entries/{entry_id}", response_model=CollectionEntryResponse)
def get_collection_entry(entry_id: int, current_user: User = Depends(get_current_user), db:Session = Depends(get_db)):

    entry = db.scalar(
        select(CollectionEntry)
        .where(CollectionEntry.user_id == current_user.id)
        .where(CollectionEntry.id == entry_id)
    )
    
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    return entry 

@app.patch("/collection-entries/{entry_id}", response_model=CollectionEntryResponse)
def update_collection_entry(entry_id: int, update_data:CollectionEntryUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    entry = db.scalar(
        select(CollectionEntry)
        .where(CollectionEntry.user_id == current_user.id)
        .where(CollectionEntry.id == entry_id)
    )
    
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    changes = update_data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
                    status_code=400,
                    detail="Changes must be supplied",
    )


    final_status = changes.get(
        "collection_status", entry.collection_status
    )
    final_ownership = changes.get(
        "ownership_type", entry.ownership_type
    )


    if (
        final_status == CollectionStatus.OWNED
        and final_ownership is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Owned entries must have an ownership type",
        )

    if (
        final_status == CollectionStatus.WISHLIST
        and final_ownership is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Wishlist entries cannot have an ownership type",
        )


    for field, value in changes.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry

@app.delete("/collection-entries/{entry_id}", status_code=204)
def delete_collection_entry(entry_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    entry = db.scalar(
        select(CollectionEntry)
        .where(CollectionEntry.user_id == current_user.id)
        .where(CollectionEntry.id == entry_id)
    )

    if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(entry)
    db.commit()
    return






@app.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    email = credentials.email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None or not password_hash.verify(
        credentials.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    

    return {
    "access_token": access_token,
    "token_type": "bearer",
    }

