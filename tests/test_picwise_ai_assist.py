"""The AI layer's jobs, answers and service on the server (`docs/PICWISE_AI_LAYER_SPEC.md`,
4.5 to 4.7), with the API faked: no test reaches the network.

Pinned here:

- a job is written once for a search and its products, and not again while its answer
  stands (24 hours; a failed call 15 minutes) or while it waits or is being answered;
- the key names the search (its spaces and letter case do not count) and the products
  read, and a key from a URL names no other file;
- the service answers the newest job first, writes what the page may do (the sentence and
  the products that fit, with their own words as they write them; the shops' words;
  nothing; withheld; failed), and removes the job;
- it asks nothing past the day's cap, one euro kept as $1.00 (owner, 2026-11-06), nor more
  than 30 times a minute; a job older than an hour is dropped;
- the site reads only the products a shown answer read as fitting.

Every brand and shop is fictional.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_ai import store  # noqa: E402
from picwise_ai.client import Asked  # noqa: E402
from picwise_ai.complex_search import Candidate, ComplexSearch  # noqa: E402
from picwise_ai.service import AssistService, MinuteLimit, SpendLedger, answer_job  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
SIGNATURE = "a" * 32
PRODUCTS = (
    ("Fixturon WM1045 10kg 1400rpm Washing Machine", "279.00 GBP", ""),
    ("Testline Series 6 9kg Quiet Mark Approved Washing Machine", "549.00 GBP", ""),
    ("Fixturon EcoWash 9kg Washing Machine", "429.99 GBP", "Inverter motor, Low Noise: 49 dB when washing."),
)


def _search(text: str = "quiet washing machine") -> ComplexSearch:
    return ComplexSearch(
        search=text,
        words=("quiet",),
        kind_name="washing machine",
        fell_back=False,
        candidates=tuple(
            Candidate(number, f"wm{number}", title, title.split()[0], price, "GBP", "Fictional Appliances", description)
            for number, (title, price, description) in enumerate(PRODUCTS, start=1)
        ),
        total=3,
        kind_id="washing_machine",
    )


def _asked(answer, *, stop_reason="end_turn", cost=0.001, error="") -> Asked:
    return Asked(answer, stop_reason, "claude-haiku-5-5", 1000, 200, 0, 0, cost, 4.2, error)


def _verdicts(*rows) -> list[dict]:
    return [{"n": n, "fits": fits, "words": words} for n, fits, words in rows]


SHOWN = {
    "verdicts": _verdicts((1, "unclear", ""), (2, "yes", "Quiet Mark Approved"), (3, "yes", "low noise: 49 dB")),
    "sentence": "2 of these 3 washing machines say they are quiet, from 429.99 GBP.",
    "shop_words": [],
}


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())

    def test_the_key_names_the_search_and_the_products_read(self) -> None:
        key = store.job_key("Quiet  Washing Machine ", SIGNATURE)
        self.assertEqual(key, store.job_key("quiet washing machine", SIGNATURE))
        self.assertNotEqual(key, store.job_key("quiet washing machine", "b" * 32))
        self.assertNotEqual(key, store.job_key("quiet dishwasher", SIGNATURE))
        self.assertTrue(store.valid_key(key))
        for bad in ("../results/x", "A" * 32, "a" * 31, "", None, "a" * 32 + "/"):
            self.assertFalse(store.valid_key(bad), bad)
        self.assertIsNone(store.read_result(self.directory, "../../etc/passwd"))

    def test_a_job_is_written_once_and_read_back_whole(self) -> None:
        key = store.write_job(self.directory, _search(), SIGNATURE, now=NOW)
        path = self.directory / "jobs" / f"{key}.json"
        self.assertTrue(path.is_file())
        self.assertTrue(store.job_pending(self.directory, key))
        first = path.read_text(encoding="utf-8")
        self.assertEqual(store.write_job(self.directory, _search(), SIGNATURE, now=NOW + timedelta(minutes=1)), key)
        self.assertEqual(path.read_text(encoding="utf-8"), first)
        read_key, signature, written, complex_search = store.read_job(path)
        self.assertEqual((read_key, signature, written), (key, SIGNATURE, NOW))
        self.assertEqual(complex_search, _search())
        # Being answered still counts as waiting.
        path.rename(path.with_name(f".{key}.taken"))
        self.assertTrue(store.job_pending(self.directory, key))
        self.assertFalse(list(self.directory.glob("jobs/*.partial")))

    def test_an_answer_stands_a_day_a_failure_a_quarter_of_an_hour(self) -> None:
        key = store.job_key("quiet washing machine", SIGNATURE)
        store.write_result(self.directory, key, {"status": "nothing"}, now=NOW)
        self.assertEqual(store.read_result(self.directory, key, now=NOW + timedelta(hours=23))["status"], "nothing")
        self.assertIsNone(store.read_result(self.directory, key, now=NOW + timedelta(hours=25)))
        # While it stands, no job is written.
        store.write_job(self.directory, _search(), SIGNATURE, now=NOW + timedelta(hours=1))
        self.assertFalse(store.job_pending(self.directory, key))
        store.write_result(self.directory, key, {"status": "failed", "reason": "timeout"}, now=NOW)
        self.assertIsNotNone(store.read_result(self.directory, key, now=NOW + timedelta(minutes=14)))
        self.assertIsNone(store.read_result(self.directory, key, now=NOW + timedelta(minutes=16)))
        # A file that is not an answer is none.
        (self.directory / "results" / f"{key}.json").write_text("{not json", encoding="utf-8")
        self.assertIsNone(store.read_result(self.directory, key, now=NOW))

    def test_the_site_reads_the_fitting_only_from_a_shown_answer(self) -> None:
        key = store.job_key("quiet washing machine", SIGNATURE)
        fitting = [{"product_id": "wm2", "words": "Quiet Mark Approved"}, {"product_id": "wm3", "words": "Low Noise"}]
        lookup = store.AssistLookup(self.directory, "quiet washing machine", now=NOW)
        self.assertEqual(lookup(SIGNATURE), ())
        self.assertIsNone(lookup.result)
        self.assertEqual(lookup.key, key)
        store.write_result(self.directory, key, {"status": "shown", "sentence": "s", "fitting": fitting}, now=NOW)
        self.assertEqual(lookup(SIGNATURE), ("wm2", "wm3"))
        self.assertEqual(store.fitting_words(lookup.result), {"wm2": "Quiet Mark Approved", "wm3": "Low Noise"})
        store.write_result(self.directory, key, {"status": "withheld", "fitting": fitting}, now=NOW)
        self.assertEqual(lookup(SIGNATURE), ())
        self.assertEqual(store.fitting_words(lookup.result), {})

    def test_a_draft_becomes_a_job_only_when_asked_for(self) -> None:
        key = store.write_draft(self.directory, _search(), SIGNATURE, now=NOW - timedelta(hours=3))
        self.assertTrue(store.draft_waits(self.directory, key))
        self.assertFalse(store.job_pending(self.directory, key))
        # Written again: still the one draft.
        first = (self.directory / "drafts" / f"{key}.json").read_text(encoding="utf-8")
        store.write_draft(self.directory, _search(), SIGNATURE, now=NOW)
        self.assertEqual((self.directory / "drafts" / f"{key}.json").read_text(encoding="utf-8"), first)
        # Asked for: a job dated now, so that the service does not drop it as old.
        self.assertTrue(store.activate_draft(self.directory, key, now=NOW))
        self.assertFalse(store.draft_waits(self.directory, key))
        _key, signature, written, complex_search = store.read_job(self.directory / "jobs" / f"{key}.json")
        self.assertEqual((signature, written, complex_search), (SIGNATURE, NOW, _search()))
        self.assertFalse(store.activate_draft(self.directory, key, now=NOW))
        self.assertFalse(store.activate_draft(self.directory, "../jobs/" + key, now=NOW))
        # While a job waits, or an answer stands, no draft is written.
        store.write_draft(self.directory, _search(), SIGNATURE, now=NOW)
        self.assertFalse(store.draft_waits(self.directory, key))

    def test_old_files_are_removed_at_most_once_an_hour(self) -> None:
        folder = self.directory / "drafts"
        folder.mkdir()
        old, new = folder / ("a" * 32 + ".json"), folder / ("b" * 32 + ".json")
        old.write_text("{}", encoding="utf-8")
        new.write_text("{}", encoding="utf-8")
        day_ago = NOW.timestamp() - 25 * 3600
        os.utime(old, (day_ago, day_ago))
        os.utime(new, (NOW.timestamp(), NOW.timestamp()))
        self.assertEqual(store.prune(self.directory, "drafts", older_than=timedelta(hours=24), now=NOW), 1)
        self.assertEqual(sorted(path.name for path in folder.iterdir()), [new.name])
        os.utime(new, (day_ago, day_ago))
        # Within the hour: nothing is looked at again.
        self.assertEqual(store.prune(self.directory, "drafts", older_than=timedelta(hours=24), now=NOW), 0)
        self.assertEqual(store.prune(self.directory, "drafts", older_than=timedelta(hours=24), now=NOW,
                                     every_seconds=0), 1)
        self.assertEqual(store.prune(self.directory, "nothing-here", older_than=timedelta(hours=1), now=NOW,
                                     every_seconds=0), 0)

    def test_the_shops_words_counted_once(self) -> None:
        key = store.job_key("smartwatch for swimming", SIGNATURE)
        self.assertIsNone(store.read_served(self.directory, key))
        store.write_served(self.directory, key, [{"word": "5ATM", "search": "5ATM smartwatch", "count": 2}])
        self.assertEqual(store.read_served(self.directory, key), [{"word": "5ATM", "search": "5ATM smartwatch", "count": 2}])


class AnswerTests(unittest.TestCase):
    def test_a_shown_answer_with_the_fitting_in_their_own_words(self) -> None:
        result = answer_job(_search(), _asked(SHOWN))
        self.assertEqual(result["status"], "shown")
        self.assertEqual(result["sentence"], SHOWN["sentence"])
        # The words as the product writes them, not as the check lower-cased them.
        self.assertEqual(result["fitting"], [{"product_id": "wm2", "words": "Quiet Mark Approved"},
                                             {"product_id": "wm3", "words": "Low Noise: 49 dB"}])
        self.assertEqual((result["cost_usd"], result["seconds"], result["kind_name"]), (0.001, 4.2, "washing machine"))

    def test_the_other_outcomes(self) -> None:
        buttons = {"verdicts": _verdicts((1, "unclear", ""), (2, "unclear", ""), (3, "unclear", "")),
                   "sentence": "", "shop_words": ["EcoWash"]}
        self.assertEqual(answer_job(_search(), _asked(buttons))["shop_words"], ["EcoWash"])
        self.assertEqual(answer_job(_search(), _asked({**buttons, "shop_words": []}))["status"], "nothing")
        wrong_price = {**SHOWN, "sentence": "2 of these 3 washing machines say they are quiet, from 279.00 GBP."}
        withheld = answer_job(_search(), _asked(wrong_price))
        self.assertEqual(withheld["status"], "withheld")
        self.assertIn("a price not of a product answered yes", withheld["reason"])
        failed = answer_job(_search(), _asked(None, stop_reason="", error="APITimeoutError"))
        self.assertEqual((failed["status"], failed["reason"]), ("failed", "APITimeoutError"))


class LimitTests(unittest.TestCase):
    def test_the_days_cap(self) -> None:
        directory = Path(tempfile.mkdtemp())
        ledger = SpendLedger(directory, cap_usd=1.00)
        self.assertTrue(ledger.reserve(NOW))
        self.assertAlmostEqual(ledger.add(NOW, 0.6), 0.6)
        self.assertAlmostEqual(ledger.add(NOW, 0.5), 1.1)
        self.assertFalse(ledger.reserve(NOW))
        # A new UTC day starts again, and a restart remembers the day.
        self.assertTrue(ledger.reserve(NOW + timedelta(hours=13)))
        self.assertFalse(SpendLedger(directory, cap_usd=1.00).reserve(NOW))

    def test_thirty_calls_a_minute(self) -> None:
        clock = [1000.0]
        limit = MinuteLimit(per_minute=30, clock=lambda: clock[0])
        self.assertEqual([limit.wait_time() for _ in range(30)], [0.0] * 30)
        self.assertAlmostEqual(limit.wait_time(), 60.0)
        clock[0] += 60.0
        self.assertEqual(limit.wait_time(), 0.0)


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.asked: list[str] = []

    def _service(self, *, answer=SHOWN, cap=1.00, now=NOW) -> AssistService:
        def fake_ask(request, *, client):
            self.asked.append(request["messages"][0]["content"].splitlines()[0])
            return _asked(answer)

        return AssistService(self.directory, client=object(), ask_fn=fake_ask,
                             ledger=SpendLedger(self.directory, cap_usd=cap), now=lambda: now, sleep=lambda _s: None)

    def test_jobs_are_answered_the_newest_first_and_removed(self) -> None:
        old = store.write_job(self.directory, _search("quiet washing machine"), SIGNATURE, now=NOW)
        new = store.write_job(self.directory, _search("silent washing machine"), SIGNATURE, now=NOW)
        os.utime(self.directory / "jobs" / f"{old}.json", (1, 1))
        service = self._service()
        self.assertEqual([path.stem for path in service.waiting_jobs()], [new, old])
        service.run(once=True, workers=1)
        self.assertEqual(self.asked, ["Search, as typed: silent washing machine", "Search, as typed: quiet washing machine"])
        self.assertEqual(list((self.directory / "jobs").iterdir()), [])
        for key in (old, new):
            self.assertEqual(store.read_result(self.directory, key, now=NOW)["status"], "shown")
        spend = json.loads(next((self.directory / "spend").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(spend, {"spent_usd": 0.002, "calls": 2})

    def test_nothing_is_asked_past_the_days_cap(self) -> None:
        SpendLedger(self.directory).add(NOW, 1.00)
        key = store.write_job(self.directory, _search(), SIGNATURE, now=NOW)
        self._service().run(once=True)
        self.assertEqual(self.asked, [])
        self.assertIsNone(store.read_result(self.directory, key, now=NOW))
        self.assertFalse(store.job_pending(self.directory, key))

    def test_a_job_taken_by_a_service_that_stopped_is_answered_after_all(self) -> None:
        key = store.write_job(self.directory, _search(), SIGNATURE, now=NOW)
        job = self.directory / "jobs" / f"{key}.json"
        job.rename(job.with_name(f".{key}.taken"))
        self._service().run(once=True)
        self.assertEqual(self.asked, ["Search, as typed: quiet washing machine"])
        self.assertEqual(store.read_result(self.directory, key, now=NOW)["status"], "shown")
        self.assertEqual(list((self.directory / "jobs").iterdir()), [])

    def test_an_old_job_and_one_already_answered_are_not_asked(self) -> None:
        old = store.write_job(self.directory, _search("quiet washing machine"), SIGNATURE, now=NOW - timedelta(hours=2))
        done = store.write_job(self.directory, _search("silent washing machine"), SIGNATURE, now=NOW)
        store.write_result(self.directory, done, {"status": "nothing"}, now=NOW)
        self._service().run(once=True)
        self.assertEqual(self.asked, [])
        self.assertIsNone(store.read_result(self.directory, old, now=NOW))
        self.assertEqual(list((self.directory / "jobs").iterdir()), [])


class DeploymentTests(unittest.TestCase):
    """The service on the server: its own user and key, nothing of the site's."""

    SERVER = ROOT / "deployment" / "server"

    def test_the_service_has_its_own_user_key_and_folder_only(self) -> None:
        unit = (self.SERVER / "picwise-assist.service").read_text(encoding="utf-8")
        for line in ("User=picwise-assist", "Group=picwise-assist", "EnvironmentFile=-/etc/picwise/assist.env",
                     "ReadWritePaths=/srv/picwise/assist", "ProtectSystem=strict", "NoNewPrivileges=yes",
                     "MemoryMax=384M", "Restart=on-failure", "/srv/picwise/venv-ai/bin/python",
                     '"$$release/deployment/server/assist_service.py" --dir /srv/picwise/assist'):
            self.assertIn(line, unit)
        settings = "\n".join(line for line in unit.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn("/srv/picwise/shared", settings)
        self.assertNotIn("picwise.env", settings)

    def test_the_site_never_has_the_key(self) -> None:
        web = (self.SERVER / "picwise-web.service").read_text(encoding="utf-8")
        self.assertIn("Environment=PICWISE_ASSIST_DIR=/srv/picwise/assist", web)
        self.assertIn("ReadWritePaths=/srv/picwise/shared -/srv/picwise/assist", web)
        self.assertNotIn("EnvironmentFile", web)
        self.assertNotIn("ANTHROPIC", web)
        workflow = (ROOT / ".github" / "workflows" / "server-deploy.yml").read_text(encoding="utf-8")
        site_file = workflow[workflow.index('echo "# The site\'s secrets'):workflow.index('> "$RUNNER_TEMP/picwise.env"')]
        self.assertNotIn("ANTHROPIC", site_file)
        self.assertIn("ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}", workflow)
        self.assertIn("""printf "ANTHROPIC_API_KEY='%s'\\n" "$ai_key\"""", workflow)
        self.assertIn("ssh picwise 'umask 077; cat > ~/picwise-assist.env' < \"$RUNNER_TEMP/assist.env\"", workflow)
        self.assertIn("~/picwise.env ~/picwise-assist.env;", workflow)
        self.assertNotIn('echo "$ai_key"', workflow)
        self.assertNotIn("echo $ai_key", workflow)

    def test_the_deployment_makes_the_jobs_folder_only_with_the_key(self) -> None:
        deploy = (self.SERVER / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("ASSIST_ENV_FILE=${4:-}", deploy)
        self.assertIn("useradd --system --user-group", deploy)
        self.assertIn("usermod -a -G picwise-assist picwise", deploy)
        with_key = deploy[deploy.index("grep -q '^ANTHROPIC_API_KEY=' \"$ASSIST_ENV_FILE\"; then"):deploy.index('echo "Anthropic key: not set')]
        self.assertIn('install -o root -g root -m 600 "$ASSIST_ENV_FILE" /etc/picwise/assist.env', with_key)
        self.assertIn('install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/jobs"', with_key)
        self.assertIn('install -d -o picwise -g picwise-assist -m 2750 "$ASSIST/drafts"', with_key)
        self.assertIn('rm -rf -- "${ASSIST:?}/jobs" "${ASSIST:?}/drafts"', deploy)
        self.assertIn('install -m 644 "$RELEASE/deployment/server/picwise-assist.service" /etc/systemd/system/', deploy)
        self.assertIn("systemctl disable --now picwise-assist.service", deploy)
        self.assertIn('! -path "$VENV" ! -path "$AI_VENV" -exec rm -rf {} +', deploy)
        self.assertIn('--require-hashes \\\n    -r "$AI_REQUIREMENTS"', deploy)


class PrivacyPageTests(unittest.TestCase):
    def test_the_privacy_page_says_it_as_the_owner_accepted_naming_no_company(self) -> None:
        from picwise_surface.legal import render_privacy_page

        page = render_privacy_page()
        self.assertIn("<h2>Complex searches</h2>", page)
        self.assertIn("PicWise may send the words of the search and the details of the products found to a "
                      "service provider", page)
        self.assertIn("Nothing that identifies you is sent with them: no IP address and no browser or device "
                      "details.", page)
        self.assertIn("outside the United Kingdom and the European Economic Area", page)
        self.assertIn("Complex searches: PicWise's legitimate interest in matching products to searches.", page)
        self.assertIn("Last updated: 6 November 2026", page)
        for name in ("Anthropic", "Claude", "Haiku", "OpenAI", " AI "):
            self.assertNotIn(name, page)


class EntryTests(unittest.TestCase):
    def test_without_a_key_it_asks_nothing_and_stops(self) -> None:
        import assist_service

        previous = os.environ.pop("ANTHROPIC_API_KEY", None)
        self.addCleanup(lambda: os.environ.__setitem__("ANTHROPIC_API_KEY", previous) if previous else None)
        self.assertEqual(assist_service.main(["--dir", tempfile.mkdtemp(), "--once"]), 0)

    def test_the_site_never_imports_the_service_nor_the_sdk(self) -> None:
        sources = [ROOT / "api" / "index.py", *sorted((ROOT / "src" / "picwise_app").glob("*.py")),
                   *sorted((ROOT / "src" / "picwise_surface").glob("*.py"))]
        for path in sources:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("picwise_ai.service", text)
                self.assertNotIn("import anthropic", text)
                self.assertNotIn("picwise_ai.client", text)


if __name__ == "__main__":
    unittest.main()
