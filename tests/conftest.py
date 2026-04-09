import os

from evaluator.config import get_settings


os.environ["LANGSMITH_TRACING"] = "false"
os.environ["DB_PATH"] = ""
os.environ["BEDROCK_MODEL_ID"] = ""

get_settings.cache_clear()
