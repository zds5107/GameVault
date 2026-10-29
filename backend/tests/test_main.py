from sqlalchemy import select, func
from app.models import CollectionEntry

def test_root_returns_welcome_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to GameVault"
    }


def test_create_game_rejects_blank_title(client):
    response = client.post(
        "/games",
        json={
            "title": "   ",
            "platform": "Nintendo 64",
        },
    )

    assert response.status_code == 422


def test_create_game_persists_game(client):
    response = client.post(
        "/games",
        json={
            "title": "Metroid Prime",
            "platform": "Nintendo GameCube",
        },
    )

    assert response.status_code == 201

    created_game = response.json()

    assert created_game["id"] is not None
    assert created_game["title"] == "Metroid Prime"
    assert created_game["platform"] == "Nintendo GameCube"

    game_id = created_game["id"]
    get_response = client.get(f"/games/{game_id}")

    assert get_response.status_code == 200
    assert get_response.json() == created_game

def test_update_game_persists_changes(client):
    # Create a game to update.
    create_response = client.post(
        "/games",
        json={
            "title": "Metroid Prime",
            "platform": "Nintendo GameCube",
        },
    )
    game_id = create_response.json()["id"]

    # Update the game's details.
    update_response = client.put(
        f"/games/{game_id}",
        json={
            "title": "Metroid Prime Remastered",
            "platform": "Nintendo Switch",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Metroid Prime Remastered"
    assert update_response.json()["platform"] == "Nintendo Switch"

    # Retrieve the game again to verify persistence.
    get_response = client.get(f"/games/{game_id}")

    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Metroid Prime Remastered"
    assert get_response.json()["platform"] == "Nintendo Switch"

def test_delete_game_removes_game(client):
    # Create a game to delete.
    create_response = client.post(
        "/games",
        json={
            "title": "Super Mario Galaxy",
            "platform": "Nintendo Wii",
        },
    )
    game_id = create_response.json()["id"]

    # Delete the game.

    delete_response = client.delete(f"/games/{game_id}")

    assert delete_response.status_code == 204


    # Verify the game no longer exists.
    get_response = client.get(f"/games/{game_id}")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Game not found"}


def test_get_missing_game_returns_404(client):
    response = client.get("/games/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Game not found"}


def test_update_missing_game_returns_404(client):
    response = client.put(
        "/games/999999",
        json={
            "title": "Metroid Prime",
            "platform": "Nintendo GameCube",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Game not found"}


def test_delete_missing_game_returns_404(client):
    response = client.delete("/games/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Game not found"}

    
def test_list_games_returns_empty_list_when_no_games_exist(client):
    response = client.get("/games")

    assert response.status_code == 200
    assert response.json() == []



def test_list_games_returns_all_games(client):
    # Create two games.
    client.post(
        "/games",
        json={
            "title": "Metroid Prime",
            "platform": "Nintendo GameCube",
        },
    )
    client.post(
        "/games",
        json={
            "title": "Super Mario Galaxy",
            "platform": "Nintendo Wii",
        },
    )

    # Retrieve the full collection.
    response = client.get("/games")

    assert response.status_code == 200

    games = response.json()

    assert len(games) == 2

    titles = {game["title"] for game in games}
    assert titles == {"Metroid Prime", "Super Mario Galaxy"}

    
def test_create_game_rejects_title_over_200_characters(client):
    response = client.post(
        "/games",
        json={
            "title": "A" * 201,
            "platform": "Nintendo 64",
        },
    )

    assert response.status_code == 422

def test_create_game_rejects_missing_title(client):
    response = client.post(
        "/games",
        json={"platform": "Nintendo 64"},
    )

    assert response.status_code == 422


def test_create_game_rejects_missing_platform(client):
    response = client.post(
        "/games",
        json={"title": "Super Mario 64"},
    )

    assert response.status_code == 422


def test_create_user(client):
    response = client.post(
        "/users",
        json={
            "email": "newuser@example.com",
            "password": "GameVaultTest123!",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["email"] == "newuser@example.com"
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data

def test_create_user_duplicate_email_returns_409(client):
    user_data = {
        "email": "duplicate@example.com",
        "password": "GameVaultTest123!",
    }

    first_response = client.post("/users", json=user_data)
    second_response = client.post("/users", json=user_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "A user with this email already exists"
    )

def test_create_user_rejects_short_password(client):
    response = client.post(
        "/users",
        json={
            "email": "shortpass@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422

#collectionEntry Tests

def test_create_collection_entry(authenticated_client, user_and_game):
    user, game = user_and_game

    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "unplayed",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == user.id
    assert data["game_id"] == game.id
    assert data["collection_status"] == "owned"
    assert data["ownership_type"] == "physical"
    assert data["play_status"] == "unplayed"
    assert "id" in data

def test_create_wishlist_entry(authenticated_client, user_and_game):
    user, game = user_and_game

    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "wishlist",
            "play_status": "unplayed",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["collection_status"] == "wishlist"
    assert data["ownership_type"] is None
    assert data["play_status"] == "unplayed"

def test_owned_entry_without_ownership_type_returns_400(authenticated_client, user_and_game):
    user, game = user_and_game

    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "play_status": "unplayed",  
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Owned entries must have an ownership type"

def test_wishlist_entry_with_ownership_type_returns_400(authenticated_client, user_and_game):
    user, game = user_and_game
    
    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "wishlist",
            "ownership_type": "physical",
            "play_status": "unplayed",  
        },
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Wishlist entries cannot have an ownership type"

def test_create_collection_entry_without_authentication_returns_401(
    client, user_and_game
):
    user, game = user_and_game

    response = client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "unplayed",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_create_collection_entry_with_missing_game_returns_404(authenticated_client, user_and_game):
    user, game = user_and_game
    
    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": 999999,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "unplayed",  
        },
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_duplicate_collection_entry_returns_409(authenticated_client, user_and_game, db_session):
    user, game = user_and_game
    
    response1 = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "unplayed",  
        },
    )

    response2 = authenticated_client.post(
            "/collection-entries",
            json={
                "game_id": game.id,
                "collection_status": "owned",
                "ownership_type": "physical",
                "play_status": "unplayed",  
            },
        )
    assert response1.status_code == 201
    assert response2.status_code == 409
    assert response2.json()["detail"] == "This game is already in the user's collection"

    entry_count = db_session.scalar(
        select(func.count())
        .select_from(CollectionEntry)
        .where(
            CollectionEntry.user_id == user.id,
            CollectionEntry.game_id == game.id,
        )
    )

    assert entry_count == 1
    
def test_create_collection_entry_with_invalid_status_returns_422(authenticated_client, user_and_game):
    user, game = user_and_game

    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "borrowed",
            "ownership_type": "physical",
            "play_status": "unplayed",  
        },
    )

    assert response.status_code == 422

def test_create_collection_entry_with_invalid_ownership_type_returns_422(authenticated_client, user_and_game):
    user, game = user_and_game
    
    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owened",
            "ownership_type": "streaming",
            "play_status": "unplayed",  
        },
    )

    assert response.status_code == 422

def test_create_collection_entry_with_invalid_play_status_returns_422(authenticated_client, user_and_game):
    user, game = user_and_game
        
    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "not_started_yet",  
        },
    )

    assert response.status_code == 422

def test_create_collection_entry_uses_authenticated_user_id(authenticated_client, user_and_game, second_user):
    user1, game = user_and_game
    user2 = second_user

    response = authenticated_client.post(
        "/collection-entries",
        json={
            "game_id": game.id,
            "collection_status": "owned",
            "ownership_type": "physical",
            "play_status": "unplayed",  
            "user_id": user2.id
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == user1.id
    assert response.json()["user_id"] != user2.id

