# GameVault Data Dictionary

**Status:** Initial MVP design  
**Last updated:** October 15, 2026

## 1. Overview

GameVault is a multi-user game collection management platform. Each user can maintain a personal collection of games across different platforms, track ownership, record play progress, and rate games.

The initial database consists of three entities:

- **User:** Stores account information.
- **Game:** Stores shared information about a game for a particular platform.
- **CollectionEntry:** Connects a user to a game and stores that user's collection-specific information.

### Design Principles

- Separate shared game information from personal collection information.
- Use primary keys and foreign keys to identify and connect records.
- Prevent duplicate entries for the same user and game.
- Keep optional information optional.
- Protect user data so each user can access only their own collection entries.
- Design the MVP to allow future expansion without unnecessary complexity.

---

## 2. User Entity

Stores account information for each GameVault user.

| Field | Data Type | Required | Constraints and Description |
|---|---|---|---|
| id | Integer | Yes | Primary key; generated automatically |
| email | String | Yes | Must be unique and nonblank; normalized before storage |
| password_hash | String | Yes | Stores a secure password hash, never a plaintext password |
| created_at | Timestamp | Yes | Automatically records account creation time |

### Relationships

- One user can have many collection entries.
- Each collection entry belongs to exactly one user.

---

## 3. Game Entity

Stores shared information about a game released for a particular platform.

| Field | Data Type | Required | Constraints and Description |
|---|---|---|---|
| id | Integer | Yes | Primary key; generated automatically |
| title | String | Yes | Game title; must not be blank |
| platform | String | Yes | Platform name; must not be blank |
| release_year | Integer | No | Release year; must be plausible if provided |
| genre | String | No | One optional genre |

### Design Notes

- A game record represents a title for a particular platform.
- The same title may have separate records for different platforms.
- Title and platform will not have a strict unique constraint initially because alternate editions, remasters, and naming differences may exist.
- External game metadata and cover art may be integrated in a future phase.

### Relationships

- One game can appear in many users' collection entries.
- Each collection entry references exactly one game.

---

## 4. CollectionEntry Entity

Stores a user's relationship with a game, including ownership, play progress, rating, and personal notes.

| Field | Data Type | Required | Constraints and Description |
|---|---|---|---|
| id | Integer | Yes | Primary key; generated automatically |
| user_id | Integer | Yes | Foreign key referencing User.id |
| game_id | Integer | Yes | Foreign key referencing Game.id |
| ownership_type | String or Enum | Conditional | `physical` or `digital`; absent for wishlist entries |
| collection_status | String or Enum | Yes | `owned` or `wishlist` |
| play_status | String or Enum | Yes | `unplayed`, `in_progress`, `completed`, or `abandoned` |
| personal_rating | Numeric | No | Rating from 1.0 to 10.0 in increments of 0.5 |
| notes | Text | No | Optional personal notes |
| created_at | Timestamp | Yes | Automatically records entry creation time |
| updated_at | Timestamp | Yes | Records the most recent entry update |

### Validation Rules

1. `user_id` must reference an existing user.
2. `game_id` must reference an existing game.
3. The combination of `user_id` and `game_id` must be unique.
4. `collection_status` must be either `owned` or `wishlist`.
5. `ownership_type` must be `physical` or `digital` for owned games.
6. `ownership_type` must be absent for wishlist entries.
7. `play_status` is required for all entries, including wishlist entries.
8. `personal_rating` is optional but must be between 1.0 and 10.0, inclusive, in increments of 0.5.
9. `notes` may be empty or absent.
10. `created_at` is set automatically when an entry is created.
11. `updated_at` is refreshed when an entry is modified.

### Relationships

- Each collection entry belongs to one user.
- Each collection entry references one game.

---

## 5. Relationships Summary

| Relationship | Cardinality | Explanation |
|---|---|---|
| User → CollectionEntry | One-to-many | A user can have many collection entries |
| Game → CollectionEntry | One-to-many | A game can appear in many users' collections |

The CollectionEntry entity connects users and games while storing personal information separately from shared game metadata.

### Example

Two users can both track Pokémon X for Nintendo 3DS.

- The Game table contains one record for that game and platform.
- The CollectionEntry table contains one record for each user.
- Each user can have their own play status, rating, ownership type, and notes.

This avoids duplicating shared game information for every user.

---

## 6. Initial Technology Decisions

| Area | Technology |
|---|---|
| Backend API | Python and Fast