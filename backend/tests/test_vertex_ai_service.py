"""Unit tests for the Vertex AI adapter without making a network call."""

import asyncio

from app.services.vertex_ai_service import VertexAiService


class FakeResponse:
    text = "先去華山看展，再避開松菸尖峰。"


class FakeModels:
    def __init__(self):
        self.last_prompt = ""

    def generate_content(self, *, model, contents, config):
        self.last_prompt = contents
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def test_vertex_adapter_sends_catalog_context():
    service = VertexAiService()
    service._client = FakeClient()

    reply = asyncio.run(
        service.recommend(
            "今天下午想看室內展覽，不想太熱",
            [
                {
                    "name": "華山 1914",
                    "category": "展覽",
                    "description": "室內展覽",
                    "internal_only_field": "should not be sent",
                }
            ],
        )
    )

    assert reply == "先去華山看展，再避開松菸尖峰。"
    assert "華山 1914" in service._client.models.last_prompt
    assert "should not be sent" not in service._client.models.last_prompt
