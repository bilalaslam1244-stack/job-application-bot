from telegram import Bot
from src.tracker import Job, Event


class Notifier:
    def __init__(self, token: str, chat_id: str):
        self._bot = Bot(token=token)
        self._chat_id = chat_id

    async def _send(self, text: str):
        await self._bot.send_message(chat_id=self._chat_id, text=text, parse_mode="HTML")

    async def notify_new_job(self, job: Job):
        await self._send(
            f"🔍 <b>New Job Found</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location}\n"
            f"🌐 {job.portal.title()}\n"
            f"🔗 {job.url}"
        )

    async def notify_applied(self, job: Job, cover_letter_excerpt: str = ""):
        excerpt = cover_letter_excerpt[:200] + "..." if len(cover_letter_excerpt) > 200 else cover_letter_excerpt
        await self._send(
            f"✅ <b>Applied</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location} | 🌐 {job.portal.title()}\n"
            f"🔗 {job.url}\n\n"
            f"<i>{excerpt}</i>"
        )

    async def notify_status_change(self, job: Job, event: Event):
        emoji = {"viewed": "👀", "in_review": "📋", "interview": "🎉", "rejected": "❌", "message": "💬"}.get(
            event.new_status, "📌"
        )
        text = (
            f"{emoji} <b>Status Update</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"{event.old_status} → <b>{event.new_status}</b>\n"
            f"🔗 {job.url}"
        )
        if event.detail:
            text += f"\n\n<i>{event.detail[:300]}</i>"
        await self._send(text)

    async def send_daily_digest(self, stats: dict[str, int]):
        labels = {
            "found": "🔍 Found", "applied": "✅ Applied", "viewed": "👀 Viewed",
            "in_review": "📋 In Review", "interview": "🎉 Interview", "rejected": "❌ Rejected",
        }
        lines = ["📊 <b>Daily Digest</b>\n"]
        for key, label in labels.items():
            if key in stats:
                lines.append(f"{label}: {stats[key]}")
        await self._send("\n".join(lines))

    async def notify_captcha(self, portal: str):
        await self._send(
            f"⚠️ <b>CAPTCHA Required</b>\n\n"
            f"Portal: <b>{portal.title()}</b>\n"
            f"Open the browser and solve the CAPTCHA manually.\n"
            f"Bot resumes automatically once session is restored."
        )

    async def notify_manual_apply(self, job: Job, cover_letter: str):
        excerpt = cover_letter[:300] + "..." if len(cover_letter) > 300 else cover_letter
        await self._send(
            f"👆 <b>Manual Apply Needed</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location}\n"
            f"🔗 {job.url}\n\n"
            f"Cover letter ready:\n<i>{excerpt}</i>"
        )

    async def notify_linkedin_job(self, job: Job):
        await self._send(
            f"🔵 <b>LinkedIn — Apply Manually</b>\n\n"
            f"<b>{job.title}</b> at <b>{job.company}</b>\n"
            f"📍 {job.location}\n"
            f"🔗 {job.url}"
        )

    async def notify_error(self, portal: str, error: str):
        await self._send(f"🚨 <b>Error — {portal.title()}</b>\n\n<code>{error[:500]}</code>")
