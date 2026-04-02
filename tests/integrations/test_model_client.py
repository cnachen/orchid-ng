from pydantic import BaseModel

from orchid_ng.integrations import FakeModelClient


class Greeting(BaseModel):
    message: str


def test_fake_model_client_parses_structured_response() -> None:
    client = FakeModelClient([{"message": "hello"}])
    response = client.generate("ignored", Greeting)
    assert response.message == "hello"
    assert client.history == ["ignored"]


def test_fake_model_client_accepts_json_string() -> None:
    client = FakeModelClient(['{"message":"orchid"}'])
    response = client.generate("prompt", Greeting)
    assert response.message == "orchid"
