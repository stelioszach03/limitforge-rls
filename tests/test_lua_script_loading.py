from app.rl.strategies import token_bucket as tb, fixed_window as fw


def test_token_bucket_loads_lua_script_text():
    # Ensure the Lua file is readable (covers code path)
    s = tb._get_script_text()
    assert isinstance(s, str) and "redis.call" in s


def test_fixed_window_loads_lua_script_text():
    s = fw._get_script_text()
    assert isinstance(s, str) and "redis.call" in s
