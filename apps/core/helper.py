import os
import tomllib

from django.contrib.auth import get_user_model


def get_superuser_from_config() -> tuple[str | None, str | None]:
    try:
        with open("settings.toml", "rb") as fh:
            data = tomllib.load(fh)
            return data["general"]["admin_username"], data["general"]["admin_password"]
    except Exception as err:
        print(f"Error reading settings.toml: {err}")
        return None, None


def get_superuser_from_env() -> tuple[str | None, str | None]:
    username = os.environ.get("ADMIN_USERNAME", None)
    password = os.environ.get("ADMIN_PASSWORD", None)
    return username, password


def create_superuser_on_startup() -> None:
    admin_username, admin_password = get_superuser_from_env()
    if None in (admin_username, admin_password):
        admin_username, admin_password = get_superuser_from_config()

    if all((admin_username, admin_password)):
        User = get_user_model()  # pylint: disable=invalid-name
        admin, _ = User.objects.get_or_create(username=admin_username, is_superuser=True)
        admin.set_password(admin_password)
        admin.save()
