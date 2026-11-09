from pathlib import Path
import tomllib


def _read_streamlit_secret(key: str):
    """Read a secret from Streamlit's runtime configuration."""
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def load_secret(key: str, local_secrets_file: Path) -> str:
    """Load a secret locally or from Streamlit Community Cloud."""
    value = None

    if local_secrets_file.exists():
        with local_secrets_file.open("rb") as file:
            secrets = tomllib.load(file)
        value = secrets.get(key)
    else:
        value = _read_streamlit_secret(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is missing from Streamlit secrets.")

    return value.strip()
