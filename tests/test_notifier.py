import pytest
from unittest.mock import AsyncMock, patch
from src.notifier import Notifier
from src.tracker import Job, Event

JOB = Job(id="linkedin:1", portal="linkedin", title="Sales Engineer",
          company="Siemens", location="Munich, Germany", country="Germany",
          url="https://example.com/1", description="", visa_sponsorship=True)


@pytest.fixture
def notifier():
    with patch("src.notifier.Bot") as MockBot:
        bot = AsyncMock()
        MockBot.return_value = bot
        n = Notifier(token="test-token", chat_id="123456")
        n._bot = bot
        yield n, bot


@pytest.mark.asyncio
async def test_notify_new_job(notifier):
    n, bot = notifier
    await n.notify_new_job(JOB)
    bot.send_message.assert_called_once()
    text = bot.send_message.call_args.kwargs["text"]
    assert "Sales Engineer" in text and "Siemens" in text


@pytest.mark.asyncio
async def test_notify_applied(notifier):
    n, bot = notifier
    await n.notify_applied(JOB, "Dear Hiring Manager...")
    text = bot.send_message.call_args.kwargs["text"]
    assert "Siemens" in text


@pytest.mark.asyncio
async def test_notify_status_change(notifier):
    n, bot = notifier
    event = Event(job_id="linkedin:1", event_type="status_change",
                  old_status="applied", new_status="viewed", detail="")
    await n.notify_status_change(JOB, event)
    text = bot.send_message.call_args.kwargs["text"]
    assert "viewed" in text.lower()


@pytest.mark.asyncio
async def test_daily_digest(notifier):
    n, bot = notifier
    await n.send_daily_digest({"found": 10, "applied": 5})
    text = bot.send_message.call_args.kwargs["text"]
    assert "10" in text and "5" in text


@pytest.mark.asyncio
async def test_notify_captcha(notifier):
    n, bot = notifier
    await n.notify_captcha("linkedin")
    text = bot.send_message.call_args.kwargs["text"]
    assert "captcha" in text.lower() and "linkedin" in text.lower()
