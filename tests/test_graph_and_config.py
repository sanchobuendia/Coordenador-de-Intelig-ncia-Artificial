from evaluator import config as config_module
from evaluator.graph import ALLOWED_MSGPACK_MODULES, build_checkpoint_serde, compile_graph, persistent_graph, route_to_evaluators
from evaluator.nodes.evaluators import CRITERIA


def test_route_to_evaluators_creates_one_send_per_criterion():
    sends = route_to_evaluators({"extracted_facts": object()})
    assert len(sends) == len(CRITERIA)
    assert {send.node for send in sends} == {"evaluator"}


def test_compile_graph_and_persistent_graph_without_db(monkeypatch):
    config_module.get_settings.cache_clear()
    monkeypatch.setenv("DB_PATH", "")
    compiled = compile_graph()
    assert compiled is not None
    with persistent_graph() as graph:
        assert graph is not None
    config_module.get_settings.cache_clear()


def test_build_checkpoint_serde_allows_expected_modules():
    serde = build_checkpoint_serde()
    assert serde is not None
    assert ALLOWED_MSGPACK_MODULES == [
        ("evaluator.schemas", "EvaluationReport"),
        ("evaluator.schemas", "ExtractedFacts"),
        ("evaluator.schemas", "CriterionScore"),
    ]


def test_get_settings_reads_env(monkeypatch):
    config_module.get_settings.cache_clear()
    monkeypatch.setenv("MODEL_PROVIDER", "provider_x")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "model_y")
    monkeypatch.setenv("MODEL_TEMPERATURE", "0.7")
    monkeypatch.setenv("AWS_REGION", "us-test-1")
    monkeypatch.setenv("DB_PATH", "postgres://example")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    settings = config_module.get_settings()
    assert settings.MODEL_PROVIDER == "provider_x"
    assert settings.BEDROCK_MODEL_ID == "model_y"
    assert settings.MODEL_TEMPERATURE == 0.7
    assert settings.AWS_REGION == "us-test-1"
    assert settings.DB_PATH == "postgres://example"
    assert settings.LOG_LEVEL == "DEBUG"
    config_module.get_settings.cache_clear()


def test_build_chat_model_with_fallback_uses_primary_model(monkeypatch):
    class DummyModel:
        def with_structured_output(self, schema):
            return self

        def invoke(self, *args, **kwargs):
            return {"ok": True, "args": args, "kwargs": kwargs}

    monkeypatch.setattr(config_module, "get_chat_model", lambda: DummyModel())
    wrapper = config_module.build_chat_model_with_fallback()
    assert wrapper.invoke("prompt")["ok"] is True


def test_fallback_chat_model_uses_secondary_when_primary_identifier_is_invalid():
    class BrokenPrimary:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("The provided model identifier is invalid")

    class Secondary:
        def invoke(self, *args, **kwargs):
            return "fallback-ok"

    wrapper = config_module.FallbackChatModel(BrokenPrimary(), Secondary())
    assert wrapper.invoke("prompt") == "fallback-ok"
