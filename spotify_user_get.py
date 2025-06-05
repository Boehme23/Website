from flask import session
from spotipy import Spotify
from spotipy.cache_handler import FlaskSessionCacheHandler  # Keep this import

from server import sp_oauth


def get_spotify_for_user_():
    # 'session' will be available because this function runs within a Flask request context.
    user_cache_handler = FlaskSessionCacheHandler(session)
    token_info = sp_oauth.validate_token(user_cache_handler.get_cached_token())
    if not token_info:
        # No valid token, redirect to login
        return None, None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        user_cache_handler.save_token_to_cache(token_info)  # Save refreshed token using this handler

    sp = Spotify(auth_manager=sp_oauth)  # Use auth_manager with the cached token
    return sp, token_info['access_token']
