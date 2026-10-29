import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import database_url, get_db
from app.main import app, password_hash
from app.models import Base, Game, User


# Point the test engine at the separate test database.
test_database_url = database_url.set(database="gamevault_test")
test_engine = create_engine(test_database_url)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_and_game(db_session):
    user = User(
        email="fixture@example.com",
        password_hash=password_hash.hash("test-password"),
    )

    game = Game(
        title="The Legend of Zelda",
        platform="Nintendo 3DS",
    )

    db_session.add_all([user, game])
    db_session.commit()

    db_session.refresh(user)
    db_session.refresh(game)

    return user, game


@pytest.fixture
def second_user(db_session):
    user = User(
        email="fixture2@example.com",
        password_hash=password_hash.hash("test-password2"),
    )


    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user

@pytest.fixture
def authenticated_client(client, user_and_game):
    user, game = user_and_game
    
    response = client.post(
        "/login",
        json={
            "email": user.email,
            "password": "test-password",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    return client
