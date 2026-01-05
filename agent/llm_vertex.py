# agent/llm_vertex.py

import vertexai
from vertexai.generative_models import GenerativeModel
import os

# Initialize Vertex AI ONCE
def init_vertex():
    project = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION")

    if not project or not region:
        raise RuntimeError("GCP_PROJECT_ID or GCP_REGION not set")

    vertexai.init(project=project, location=region)


# Shared Gemini model
MODEL_NAME = "gemini-2.5-flash"
_model = None


def get_llm():
    global _model
    if _model is None:
        _model = GenerativeModel(MODEL_NAME)
    return _model


def llm_generate(prompt: str) -> str:
    model = get_llm()
    response = model.generate_content(prompt)
    return response.text
