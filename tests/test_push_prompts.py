"""
Testes offline do push de prompts (leitura, validação, montagem e chamada ao Hub).
"""
import sys
from pathlib import Path

import pytest
import yaml

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langsmith.utils import LangSmithConflictError

import push_prompts
from push_prompts import (
    PROMPT_KEY,
    build_prompt_template,
    build_tags,
    load_prompt_data,
    push_prompt_to_langsmith,
    technique_warnings,
    validate_prompt,
)

SYSTEM = "Você é um Product Manager.\n\nTransforme o bug em user story."
USER = "Relato:\n{bug_report}"


def make_prompt(**overrides):
    data = {
        "description": "Prompt de teste",
        "system_prompt": SYSTEM,
        "user_prompt": USER,
        "version": "v2",
        "tags": ["user-story"],
        "techniques_applied": ["few-shot", "role-prompting"],
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


# --- load_prompt_data ---------------------------------------------------------

class TestLoadPromptData:
    def test_reads_root_key(self, tmp_path):
        path = tmp_path / "p.yml"
        path.write_text(yaml.safe_dump({PROMPT_KEY: make_prompt()}), encoding="utf-8")
        assert load_prompt_data(path)["system_prompt"] == SYSTEM

    def test_wrong_root_key(self, tmp_path, capsys):
        path = tmp_path / "p.yml"
        path.write_text(
            yaml.safe_dump({"bug_to_user_story_v1": make_prompt()}), encoding="utf-8"
        )
        assert load_prompt_data(path) is None
        out = capsys.readouterr().out
        assert PROMPT_KEY in out
        assert "bug_to_user_story_v1" in out

    def test_missing_file(self, tmp_path):
        assert load_prompt_data(tmp_path / "nao_existe.yml") is None

    def test_invalid_yaml(self, tmp_path):
        path = tmp_path / "p.yml"
        path.write_text("a: [b", encoding="utf-8")
        assert load_prompt_data(path) is None

    def test_input_path_anchored_at_repo_root(self):
        repo_root = Path(__file__).resolve().parent.parent
        assert push_prompts.INPUT_PATH == repo_root / "prompts" / f"{PROMPT_KEY}.yml"


# --- build_prompt_template / build_tags --------------------------------------

class TestBuildPromptTemplate:
    def test_system_then_user_with_same_text(self):
        prompt = build_prompt_template(make_prompt())
        assert len(prompt.messages) == 2
        system, user = prompt.messages
        assert isinstance(system, SystemMessagePromptTemplate)
        assert isinstance(user, HumanMessagePromptTemplate)
        assert system.prompt.template == SYSTEM
        assert user.prompt.template == USER

    @pytest.mark.parametrize("user_prompt", [None, "", "   "])
    def test_only_system_when_user_empty(self, user_prompt):
        prompt = build_prompt_template(
            make_prompt(system_prompt="Bug: {bug_report}", user_prompt=user_prompt)
        )
        assert len(prompt.messages) == 1
        assert isinstance(prompt.messages[0], SystemMessagePromptTemplate)


class TestBuildTags:
    def test_tags_plus_techniques_without_duplicates(self):
        data = make_prompt(
            tags=["user-story", "few-shot"],
            techniques_applied=["few-shot", "role-prompting"],
        )
        assert build_tags(data) == ["user-story", "few-shot", "role-prompting"]

    def test_missing_tags_and_techniques(self):
        assert build_tags(make_prompt(tags=None, techniques_applied=None)) == []


# --- validate_prompt / technique_warnings -------------------------------------

class TestValidatePrompt:
    def test_valid_prompt(self):
        assert validate_prompt(make_prompt()) == (True, [])

    @pytest.mark.parametrize("field", ["description", "system_prompt", "version"])
    def test_missing_required_field(self, field):
        is_valid, errors = validate_prompt(make_prompt(**{field: None}))
        assert not is_valid
        assert any(field in e for e in errors)

    def test_empty_system_prompt(self):
        is_valid, errors = validate_prompt(make_prompt(system_prompt="   "))
        assert not is_valid
        assert any("system_prompt está vazio" in e for e in errors)

    @pytest.mark.parametrize("field", ["system_prompt", "user_prompt"])
    def test_todo(self, field):
        data = make_prompt()
        data[field] = data[field] + "\n[TODO] revisar"
        is_valid, errors = validate_prompt(data)
        assert not is_valid
        assert any(field in e and "TODO" in e for e in errors)

    def test_missing_bug_report(self):
        is_valid, errors = validate_prompt(make_prompt(user_prompt="Sem variável"))
        assert not is_valid
        assert any("{bug_report}" in e for e in errors)

    def test_bug_report_only_in_system(self):
        data = make_prompt(system_prompt="Bug: {bug_report}", user_prompt=None)
        assert validate_prompt(data) == (True, [])

    def test_unknown_variable(self):
        data = make_prompt(user_prompt="{bug_report}\n{contexto}")
        is_valid, errors = validate_prompt(data)
        assert not is_valid
        assert any("{contexto}" in e for e in errors)

    def test_escaped_braces_are_not_variables(self):
        data = make_prompt(system_prompt=SYSTEM + '\nFormato: {{"titulo": "..."}}')
        assert validate_prompt(data) == (True, [])

    def test_reports_all_errors_at_once(self):
        data = make_prompt(description=None, system_prompt="", user_prompt="TODO")
        is_valid, errors = validate_prompt(data)
        assert not is_valid
        assert len(errors) >= 4  # description, vazio, TODO, {bug_report}

    def test_few_techniques_is_not_an_error(self):
        assert validate_prompt(make_prompt(techniques_applied=None)) == (True, [])


class TestTechniqueWarnings:
    def test_warns_without_techniques(self):
        warnings = technique_warnings(make_prompt(techniques_applied=None))
        assert len(warnings) == 1
        assert "2" in warnings[0]

    def test_warns_with_one_technique(self):
        assert technique_warnings(make_prompt(techniques_applied=["few-shot"]))

    def test_no_warning_with_two(self):
        assert technique_warnings(make_prompt()) == []


# --- push_prompt_to_langsmith -------------------------------------------------

class FakeClient:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def push_prompt(self, identifier, **kwargs):
        self.calls.append((identifier, kwargs))
        if self.error:
            raise self.error
        return f"https://smith.langchain.com/prompts/{identifier}"


@pytest.fixture
def fake_client(monkeypatch):
    def install(error=None):
        client = FakeClient(error)
        monkeypatch.setattr(push_prompts, "Client", lambda: client)
        return client
    return install


class TestPushPromptToLangsmith:
    def test_sends_public_prompt_with_metadata(self, fake_client):
        client = fake_client()
        assert push_prompt_to_langsmith("handle/bug_to_user_story_v2", make_prompt())

        identifier, kwargs = client.calls[0]
        assert identifier == "handle/bug_to_user_story_v2"
        assert kwargs["is_public"] is True
        assert kwargs["description"] == "Prompt de teste"
        assert kwargs["tags"] == ["user-story", "few-shot", "role-prompting"]
        assert "few-shot" in kwargs["readme"]
        assert kwargs["commit_description"].startswith("v2:")
        assert len(kwargs["commit_description"]) <= 1000
        assert kwargs["object"].messages[0].prompt.template == SYSTEM

    def test_baseline_commit_description(self, fake_client):
        client = fake_client()
        push_prompt_to_langsmith("h/p", make_prompt(techniques_applied=None))
        kwargs = client.calls[0][1]
        assert "linha de base" in kwargs["commit_description"]
        assert "linha de base" in kwargs["readme"]

    def test_conflict_means_no_changes(self, fake_client, capsys):
        fake_client(LangSmithConflictError("Nothing to commit"))
        assert push_prompt_to_langsmith("h/p", make_prompt()) is True
        out = capsys.readouterr().out
        assert "Nenhuma mudança" in out
        assert "h/p" in out

    def test_generic_error(self, fake_client, capsys):
        fake_client(RuntimeError("403 Forbidden"))
        assert push_prompt_to_langsmith("h/p", make_prompt()) is False
        out = capsys.readouterr().out
        assert "403 Forbidden" in out
        assert "USERNAME_LANGSMITH_HUB" in out


# --- main ---------------------------------------------------------------------

class TestMain:
    def test_missing_env_vars(self, monkeypatch, fake_client, capsys):
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("USERNAME_LANGSMITH_HUB", raising=False)
        client = fake_client()
        assert push_prompts.main() == 1
        out = capsys.readouterr().out
        assert "LANGSMITH_API_KEY" in out and "USERNAME_LANGSMITH_HUB" in out
        assert client.calls == []

    def test_invalid_prompt_is_not_pushed(self, monkeypatch, fake_client, tmp_path):
        monkeypatch.setenv("LANGSMITH_API_KEY", "x")
        monkeypatch.setenv("USERNAME_LANGSMITH_HUB", "handle")
        path = tmp_path / "p.yml"
        path.write_text(
            yaml.safe_dump({PROMPT_KEY: make_prompt(system_prompt="")}), encoding="utf-8"
        )
        monkeypatch.setattr(push_prompts, "INPUT_PATH", path)
        client = fake_client()
        assert push_prompts.main() == 1
        assert client.calls == []

    def test_baseline_warns_and_pushes(self, monkeypatch, fake_client, tmp_path, capsys):
        monkeypatch.setenv("LANGSMITH_API_KEY", "x")
        monkeypatch.setenv("USERNAME_LANGSMITH_HUB", "handle")
        path = tmp_path / "p.yml"
        path.write_text(
            yaml.safe_dump({PROMPT_KEY: make_prompt(techniques_applied=None)}),
            encoding="utf-8",
        )
        monkeypatch.setattr(push_prompts, "INPUT_PATH", path)
        client = fake_client()
        assert push_prompts.main() == 0
        assert "⚠️" in capsys.readouterr().out
        assert client.calls[0][0] == "handle/bug_to_user_story_v2"
