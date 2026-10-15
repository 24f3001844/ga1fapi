import os
from typing import List, Optional
import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for cross-origin requests from any page/browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def coerce_value(key: str, value: str):
  """Applies type coercion rules based on the key name."""
  if value is None:
    return None

  if key in ("port", "workers"):
    try:
      return int(value)
    except ValueError:
      return value

  if key == "debug":
    if isinstance(value, bool):
      return value
    return str(value).lower() in ("true", "1", "yes", "on")

  return str(value)


@app.get("/effective-config")
def get_effective_config(
    set: Optional[List[str]] = Query(
        None, description="CLI overrides in key=value format"
    )
):
  # Layer 1: Hardcoded defaults
  config = {
      "port": 8000,
      "workers": 1,
      "debug": False,
      "log_level": "info",
      "api_key": "default-secret-000",
  }

  # Layer 2: config.development.yaml (if present)
  yaml_path = "config.development.yaml"
  if os.path.exists(yaml_path):
    try:
      with open(yaml_path, "r") as f:
        yaml_data = yaml.safe_load(f) or {}
        for k, v in yaml_data.items():
          config[k] = coerce_value(k, v)
    except Exception:
      pass

  # Layer 3: .env file or environment variables simulation
  # Handling alias: NUM_WORKERS -> workers
  env_mapping = {
      "APP_PORT": "port",
      "APP_WORKERS": "workers",
      "NUM_WORKERS": "workers",
      "APP_DEBUG": "debug",
      "APP_LOG_LEVEL": "log_level",
      "APP_API_KEY": "api_key",
  }
  for env_key, cfg_key in env_mapping.items():
    val = os.getenv(env_key)
    if val is not None:
      config[cfg_key] = coerce_value(cfg_key, val)

  # Layer 4: OS env vars (APP_* prefix)
  for env_key, val in os.environ.items():
    if env_key.startswith("APP_"):
      cfg_key = env_key[4:].lower()
      if cfg_key in config or cfg_key in ("port", "workers", "debug", "log_level", "api_key"):
        config[cfg_key] = coerce_value(cfg_key, val)

  # Layer 5: CLI overrides via ?set=key=value query parameters (Highest Precedence)
  if set:
    for override in set:
      if "=" in override:
        k, v = override.split("=", 1)
        k = k.strip()
        v = v.strip()
        config[k] = coerce_value(k, v)

  # Ensure correct types on all baseline keys
  config["port"] = coerce_value("port", config.get("port", 8000))
  config["workers"] = coerce_value("workers", config.get("workers", 1))
  config["debug"] = coerce_value("debug", config.get("debug", False))
  config["log_level"] = str(config.get("log_level", "info"))

  # Secret masking: api_key must always appear as "****"
  config["api_key"] = "****"

  return config
