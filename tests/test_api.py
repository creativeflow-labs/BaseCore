from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.core.router import choose_model_source
from apps.api.core.schemas import GenerateRequest
from apps.api.core.settings import get_settings


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_builder_with_mocked_provider() -> None:
    client = TestClient(app)
    content = (
        '{"product_one_liner":"AI 영어회화 MVP","primary_user_segment":"초급 영어 학습자",'
        '"user_pain_points":["말하기 시작이 어렵다"],'
        '"user_flow_steps":[{"step":"start","user_action":"학습 시작","system_response":"스크립트 추천"}],'
        '"screens":[{"name":"script_tab","purpose":"대화 스크립트 학습","inputs":["level"],"outputs":["script_list"]}],'
        '"system_actions":[{"trigger":"학습 시작","action":"레벨별 스크립트 조회","output":"추천 스크립트"}],'
        '"mvp_in_scope":["스크립트 탭","단어 탭","문화 탭"],'
        '"mvp_out_scope":["실시간 음성 평가"],'
        '"operational_metrics":[{"name":"주간 재방문율","measurement_method":"7일 내 재방문 사용자 / 전체 사용자","signal":"학습 지속성"}],'
        '"acceptance_criteria":[{"scenario":"사용자가 레벨을 선택한다","expected_result":"적절한 스크립트 목록이 표시된다"}],'
        '"risks":["콘텐츠 품질 편차"]'
        '}'
    )

    with patch("apps.api.core.rewrite_loop.chat_completion", return_value=_Response(content)):
        response = client.post(
            "/generate",
            json={
                "mode": "builder",
                "user_input": "영어회화앱 MVP를 4주 로드맵으로 설계해줘. 3탭 구조(스크립트/단어/문화).",
                "goal": "새 앱 기획",
                "tone": "professional",
                "length": "medium",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["validation_status"] == "passed"
    assert body["result"]["product_one_liner"] == "AI 영어회화 MVP"


def test_generate_requires_api_key_when_enabled() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.enable_auth = True
        settings.service_api_key = "secret-key"
        settings.rate_limit_enabled = False
        return settings

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    response = client.post(
        "/generate",
        json={
            "mode": "builder",
            "user_input": "테스트",
        },
    )

    assert response.status_code == 401
    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_restricted_data_forces_internal_routing() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    settings.external_base_url = "https://example.com/v1"
    settings.external_api_key = "external-key"
    settings.external_model_name = "external-model"

    decision = choose_model_source(
        GenerateRequest(
            mode="reviewer",
            user_input="검토해줘",
            data_classification="restricted",
        ),
        settings,
    )

    assert decision.source == "internal"
    assert decision.reason == "restricted_data_internal_only"
    get_settings.cache_clear()


def test_reviewer_prefers_external_when_available() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    settings.reviewer_default_source = "external"
    settings.external_base_url = "https://example.com/v1"
    settings.external_api_key = "external-key"
    settings.external_model_name = "external-model"

    decision = choose_model_source(
        GenerateRequest(
            mode="reviewer",
            user_input="검토해줘",
        ),
        settings,
    )

    assert decision.source == "external"
    assert decision.reason == "reviewer_prefers_external"
    get_settings.cache_clear()


def test_generate_falls_back_to_external_after_internal_failure() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.rate_limit_enabled = False
        settings.external_api_key = "external-key"
        settings.external_model_name = "gpt-test"
        settings.external_base_url = "https://api.openai.com/v1"
        settings.external_fallback_enabled = True
        settings.max_attempts = 1
        return settings

    invalid_internal = _Response("not json")
    valid_external = _Response(
        '{"product_one_liner":"외부 폴백 성공","primary_user_segment":"초급 영어 학습자",'
        '"user_pain_points":["빠른 학습 시작이 어렵다"],'
        '"user_flow_steps":[{"step":"start","user_action":"학습 시작","system_response":"스크립트 추천"}],'
        '"screens":[{"name":"script_tab","purpose":"스크립트 학습","inputs":["level"],"outputs":["script_list"]}],'
        '"system_actions":[{"trigger":"학습 시작","action":"스크립트 조회","output":"추천 스크립트"}],'
        '"mvp_in_scope":["스크립트 탭"],'
        '"mvp_out_scope":["실시간 음성 평가"],'
        '"operational_metrics":[{"name":"주간 재방문율","measurement_method":"7일 내 재방문 사용자 / 전체 사용자","signal":"학습 지속성"}],'
        '"acceptance_criteria":[{"scenario":"사용자가 학습 시작","expected_result":"스크립트가 표시된다"}],'
        '"risks":["콘텐츠 품질 편차"]'
        '}'
    )

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    with patch(
        "apps.api.core.rewrite_loop.chat_completion",
        side_effect=[invalid_internal, valid_external],
    ):
        response = client.post(
            "/generate",
            json={
                "mode": "builder",
                "user_input": "영어회화앱 MVP를 설계해줘.",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["validation_status"] == "passed"
    assert body["model_source"] == "external"
    assert body["fallback_used"] is True
    assert body["routing_reason"].startswith("fallback_after_internal_failure:")

    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_generate_falls_back_to_external_after_internal_provider_error() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.rate_limit_enabled = False
        settings.external_api_key = "external-key"
        settings.external_model_name = "gpt-test"
        settings.external_base_url = "https://api.openai.com/v1"
        settings.external_fallback_enabled = True
        settings.max_attempts = 1
        return settings

    valid_external = _Response(
        '{"product_one_liner":"외부 폴백 성공","primary_user_segment":"초급 영어 학습자",'
        '"user_pain_points":["빠른 학습 시작이 어렵다"],'
        '"user_flow_steps":[{"step":"start","user_action":"학습 시작","system_response":"스크립트 추천"}],'
        '"screens":[{"name":"script_tab","purpose":"스크립트 학습","inputs":["level"],"outputs":["script_list"]}],'
        '"system_actions":[{"trigger":"학습 시작","action":"스크립트 조회","output":"추천 스크립트"}],'
        '"mvp_in_scope":["스크립트 탭"],'
        '"mvp_out_scope":["실시간 음성 평가"],'
        '"operational_metrics":[{"name":"주간 재방문율","measurement_method":"7일 내 재방문 사용자 / 전체 사용자","signal":"학습 지속성"}],'
        '"acceptance_criteria":[{"scenario":"사용자가 학습 시작","expected_result":"스크립트가 표시된다"}],'
        '"risks":["콘텐츠 품질 편차"]'
        '}'
    )

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    with patch(
        "apps.api.core.rewrite_loop.chat_completion",
        side_effect=[RuntimeError("internal down"), valid_external],
    ):
        response = client.post(
            "/generate",
            json={
                "mode": "builder",
                "user_input": "영어회화앱 MVP를 설계해줘.",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["validation_status"] == "passed"
    assert body["model_source"] == "external"
    assert body["fallback_used"] is True
    assert body["routing_reason"].startswith("fallback_after_internal_failure:PROVIDER_ERROR:")

    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_provider_health_reports_configuration() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.external_api_key = "external-key"
        settings.external_model_name = "gpt-test"
        settings.external_base_url = "https://api.openai.com/v1"
        return settings

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    with patch("apps.api.routes.health.probe_provider", return_value={"status": "ok", "detail": "reachable"}):
        response = client.get("/health/providers")

    body = response.json()
    assert response.status_code == 200
    assert body["providers"]["internal"]["status"] == "ok"
    assert body["providers"]["external"]["configured"] is True
    assert body["providers"]["external"]["status"] == "ok"

    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_mock_internal_provider_health_is_ok() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.internal_provider = "mock"
        settings.external_api_key = None
        settings.external_model_name = None
        return settings

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    response = client.get("/health/providers")
    body = response.json()

    assert response.status_code == 200
    assert body["providers"]["internal"]["status"] == "ok"
    assert body["providers"]["internal"]["detail"] == "mock_provider"

    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_generate_with_mock_internal_provider() -> None:
    get_settings.cache_clear()
    app.dependency_overrides = {}

    def override_settings():
        settings = get_settings()
        settings.internal_provider = "mock"
        settings.rate_limit_enabled = False
        settings.external_api_key = None
        settings.external_model_name = None
        return settings

    app.dependency_overrides[get_settings] = override_settings
    client = TestClient(app)

    response = client.post(
        "/generate",
        json={
            "mode": "writer",
            "user_input": "카페에서 디카페인 라떼를 주문하는 영어 문장 2개",
            "tone": "casual",
            "length": "short",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["validation_status"] == "passed"
    assert body["model_source"] == "internal"
    assert body["result"]["warnings"] == ["mock provider output is for local development only"]

    app.dependency_overrides = {}
    get_settings.cache_clear()
