import pytest
from unittest.mock import MagicMock, patch
from src.cover_letter import CoverLetterGenerator
from src.tracker import Job

RESUME = "Bilal Aslam Sales Engineer ACET Engineering. EEE graduate. Python, automation."

JOB = Job(id="linkedin:1", portal="linkedin", title="Automation Engineer",
          company="Schneider Electric", location="Paris, France", country="France",
          url="https://example.com/1",
          description="Automation Engineer needed. Visa sponsorship available.",
          visa_sponsorship=True)


@pytest.fixture
def gen():
    with patch("src.cover_letter.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        resp = MagicMock()
        resp.content = [MagicMock(text="Dear Hiring Manager,\n\nExcited to apply...")]
        client.messages.create.return_value = resp
        g = CoverLetterGenerator(api_key="sk-ant-test", resume_text=RESUME)
        g._client = client
        yield g, client


def test_generate_returns_string(gen):
    g, _ = gen
    result = g.generate(JOB)
    assert isinstance(result, str) and len(result) > 5


def test_uses_haiku_model(gen):
    g, client = gen
    g.generate(JOB)
    assert "haiku" in client.messages.create.call_args.kwargs["model"]


def test_job_details_in_prompt(gen):
    g, client = gen
    g.generate(JOB)
    content = str(client.messages.create.call_args.kwargs["messages"])
    assert "Schneider Electric" in content


def test_fallback_on_error():
    with patch("src.cover_letter.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.side_effect = Exception("API down")
        g = CoverLetterGenerator(api_key="sk-ant-test", resume_text=RESUME)
        g._client = client
        result = g.generate_with_fallback(JOB)
        assert "Bilal Aslam" in result
        assert "Schneider Electric" in result


def test_save_creates_file(gen, tmp_path):
    g, _ = gen
    path = g.save(JOB, "Dear Hiring Manager...", output_dir=str(tmp_path))
    assert path.exists()
    assert "Schneider_Electric" in path.name


def test_load_resume_strips_html(tmp_path):
    f = tmp_path / "resume.html"
    f.write_text("<html><body><p>Bilal Aslam Sales Engineer</p></body></html>")
    text = CoverLetterGenerator.load_resume(str(f))
    assert "Bilal Aslam" in text
    assert "<html>" not in text
