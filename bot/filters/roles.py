from models.user import User

ROLE_LEVELS = {
    "guest": 0,
    "user": 1,
    "admin": 2,
    "owner": 3,
}


def has_role(user: User, min_role: str) -> bool:
    return ROLE_LEVELS.get(user.role, 0) >= ROLE_LEVELS.get(min_role, 0)
