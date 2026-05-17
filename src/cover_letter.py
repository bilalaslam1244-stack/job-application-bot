import re
from pathlib import Path
from datetime import datetime
import anthropic
from src.tracker import Job

SYSTEM_PROMPT = """You write concise, professional cover letters for engineering job applications.
Output ONLY the cover letter text — no subject line, no metadata, no explanations.
Maximum 250 words. Three paragraphs."""

USER_TEMPLATE = """Write a cover letter for {name} applying to the role below.

RESUME:
{resume}

JOB:
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

INSTRUCTIONS:
- Para 1: Why this specific role and company (reference something concrete from the description)
- Para 2: 2-3 specific achievements from the resume that directly match the job requirements
- Para 3: Mention visa sponsorship requirement (Sri Lankan citizen, currently based in Malaysia, requires work visa sponsorship), availability to relocate immediately, and a call to action
- Tone: professional and direct. No clichés. No "I am writing to express my interest."
- Max 250 words."""

FALLBACK_TEMPLATE = """Dear Hiring Manager,

Having reviewed the {title} role at {company}, I am confident my background in industrial automation and project coordination makes me a strong fit. My experience coordinating AI-driven automation projects and managing multi-stakeholder deliverables from scoping through commissioning aligns directly with what you are looking for.

At ACET Engineering, I delivered a RM 600,000 automation project for Kim Loong Palm Oil Mill, managing all stakeholder communication, milestone tracking, and on-site acceptance testing through to successful handover. At MAN Energy Solutions, I deployed IIoT remote monitoring protocols for a live industrial plant in Vietnam, maintaining uptime across borders. My fluency in English and French gives me a practical edge in multilingual engineering environments.

I am a Sri Lankan citizen currently based in Malaysia and require work visa sponsorship to join your team — I am ready to relocate immediately and am fully committed to contributing long-term. I would welcome the opportunity to discuss how my background fits your needs.

Best regards,
Bilal Aslam"""


class CoverLetterGenerator:
    def __init__(self, api_key: str, resume_text: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._resume_text = resume_text

    def generate(self, job: Job) -> str:
        prompt = USER_TEMPLATE.format(
            name="Bilal Aslam",
            resume=self._resume_text,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description[:3000],
        )
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self._resume_text, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.content[0].text.strip()

    def generate_with_fallback(self, job: Job) -> str:
        try:
            return self.generate(job)
        except Exception:
            return FALLBACK_TEMPLATE.format(title=job.title, company=job.company)

    def save(self, job: Job, letter: str, output_dir: str = "output/cover_letters") -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        safe_company = re.sub(r"[^\w]", "_", job.company)
        path = out / f"{job.portal}_{safe_company}_{datetime.now().strftime('%Y-%m-%d')}.txt"
        path.write_text(letter, encoding="utf-8")
        return path

    @staticmethod
    def load_resume(path: str) -> str:
        content = Path(path).read_text(encoding="utf-8")
        if path.endswith(".html"):
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
        return content
