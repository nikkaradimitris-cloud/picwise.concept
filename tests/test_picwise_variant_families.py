"""The AI's part in one card per product: the sets asked about, and their answers.

Owner, 2026-11-19: a shop listing each variant of a product as a product of its own still
shows as one card, «εκεί εμπλέκεται και το σύστημα ai»; «Το όριο του ai μπορεί να ανέβει
... δεν θα περιμένω τη νύχτα για να κάνει το σκανάρισμα θα το κάνουμε τώρα». Pinned here:

- the sets: per shop, brand and own words, each page once, only when a colour or a number
  tells some apart; the same set, the same id; too many, none;
- the jobs: those not answered yet, the night before's unclaimed ones taken away;
- the service: one call a job; an answer used only when every listing is in exactly one
  group; each product's family kept in the small file the site reads, each set's answer
  with its titles in another; written at most once a minute and when it stops; past the
  day's cap, nothing asked; a job claimed by a run that stopped, given back;
- the units: under the AI's own user and key, at most $5.00 a day, the site's user writing
  the sets, the site reading the file.

Every product is local test data: fictional brands and shops, `.invalid` URLs. No call
leaves the machine: the model's answers are written here.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_ai.client import Asked  # noqa: E402
from picwise_ai.families import (  # noqa: E402
    DAILY_CAP_USD,
    FamilyService,
    FamilyStore,
    checked_groups,
    request_kwargs,
)
from picwise_ai.service import MinuteLimit, SpendLedger  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.variant_families import (  # noqa: E402
    SET_MOST,
    answered_set_ids,
    doubtful_sets,
    write_jobs,
)

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _product(pid: str, title: str, price: float, *, page: str = "", shop: str = "Fixture Shop",
             brand: str = "Fixturon") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=title, brand=brand, category_text="Glassware",
        product_url=f"https://track.example.invalid/{pid}", image_url=f"https://cdn.example.invalid/{pid}.jpg",
        price_text=f"{price:.2f}", availability_text="in stock", currency="GBP",
        raw={"merchant_name": shop, "link": page or f"https://shop.example.invalid/products/{pid}"},
    )


def _asked(answer: dict | None, *, cost: float = 0.001, error: str = "") -> Asked:
    return Asked(answer, "end_turn", "claude-haiku-5-5", 100, 20, 0, 0, cost, 0.5, error)


class SetsTests(unittest.TestCase):
    def test_a_colour_apart_makes_a_set_each_page_once(self) -> None:
        page = "https://shop.example.invalid/products/runner-black"
        sets = doubtful_sets(
            [
                _product("b8", "Fixturon Runner Black Size 8", 40.0, page=f"{page}?variant=8"),
                _product("b9", "Fixturon Runner Black Size 9", 38.0, page=f"{page}?variant=9"),
                _product("w8", "Fixturon Runner White Size 8", 41.0),
                # Sizes apart only: joined by the rule, no set.
                _product("t1", "Fixturon Tracksuit - S", 20.0),
                _product("t2", "Fixturon Tracksuit - 2XL", 22.0),
            ]
        )
        self.assertEqual(len(sets), 1)
        listings = sets[0]["listings"]
        self.assertEqual([listing["title"] for listing in listings],
                         ["Fixturon Runner Black Size 9", "Fixturon Runner White Size 8"])
        self.assertEqual(listings[0]["price"], "38.00")
        self.assertEqual(listings[0]["products"], ["fixture shop\x1fb8", "fixture shop\x1fb9"])
        # The same products and titles, the same id.
        again = doubtful_sets([
            _product("w8", "Fixturon Runner White Size 8", 41.0),
            _product("b9", "Fixturon Runner Black Size 9", 38.0, page=f"{page}?variant=9"),
            _product("b8", "Fixturon Runner Black Size 8", 40.0, page=f"{page}?variant=8"),
        ])
        self.assertEqual(again[0]["id"], sets[0]["id"])

    def test_prints_named_after_the_name_make_a_set_another_name_does_not(self) -> None:
        # The live search for "satin sleep mask" (2026-11-19): one shop's prints, each a
        # card, while its black and pink were already one.
        sets = doubtful_sets([
            _product("snake", "Satin Sleep Mask - Snake Print - Sleep Mask Only", 10.0),
            _product("cheetah", "Satin Sleep Mask - Cheetah Print - Sleep Mask Only", 15.0),
            _product("black", "Satin Sleep Mask - Black - Sleep Mask Only", 15.0),
            _product("cherry", "Satin Sleep Mask - Frosted Cherry Print", 10.0),
            _product("caramel", "Cloud Padded Satin Sleep Mask - Caramel", 15.0),
            _product("fern", "Cloud Padded Satin Sleep Mask - Pink Fern Print", 15.0),
            # A head of one word of its own: the whole title is the key.
            _product("p1", "Platinum - Lola's Leads Fabric Extension Cable - 1m / Black 2 Gang", 20.0),
            _product("m1", "Malachite - Lola's Leads Fabric Extension Cable - 1m / Black 2 Gang", 20.0),
        ])
        self.assertEqual(
            [[listing["title"] for listing in found["listings"]] for found in sets],
            sorted(
                [
                    ["Satin Sleep Mask - Frosted Cherry Print", "Satin Sleep Mask - Snake Print - Sleep Mask Only",
                     "Satin Sleep Mask - Black - Sleep Mask Only", "Satin Sleep Mask - Cheetah Print - Sleep Mask Only"],
                    ["Cloud Padded Satin Sleep Mask - Caramel", "Cloud Padded Satin Sleep Mask - Pink Fern Print"],
                ],
                key=lambda titles: next(found["id"] for found in sets if found["listings"][0]["title"] == titles[0]),
            ),
        )

    def test_sizes_apart_are_one_listing_so_colours_in_sizes_make_a_small_set(self) -> None:
        products = [
            _product(f"{colour}-{size}", f"Fixturon Tee {colour.title()} {size}", 12.0 + index)
            for index, (colour, size) in enumerate(
                (colour, size) for colour in ("black", "white", "navy") for size in ("S", "M", "L", "XL", "2XL", "3XL")
            )
        ]
        sets = doubtful_sets(products)
        self.assertEqual(len(sets), 1)
        listings = sets[0]["listings"]
        self.assertEqual([listing["title"] for listing in listings],
                         ["Fixturon Tee Black S", "Fixturon Tee White S", "Fixturon Tee Navy S"])
        self.assertEqual(len(listings[0]["products"]), 6)
        self.assertIn("fixture shop\x1fblack-3XL", listings[0]["products"])
        # More colours of one shirt than a set holds: none asked.
        from picwise_providers.product_variants import _COLOURS

        colours = sorted(_COLOURS)[:SET_MOST + 1]
        self.assertEqual(len(colours), SET_MOST + 1)
        many = [_product(f"{colour}-{size}", f"Fixturon Tee {colour.title()} {size}", 12.0)
                for colour in colours for size in ("S", "M")]
        self.assertEqual(doubtful_sets(many), [])
        self.assertEqual(len(doubtful_sets(many[:2 * SET_MOST])[0]["listings"]), SET_MOST)

    def test_other_shops_brands_or_too_many_make_no_set(self) -> None:
        self.assertEqual(doubtful_sets([
            _product("a", "Fixturon Wine Glass Red", 10.0, shop="Fixture One"),
            _product("b", "Fixturon Wine Glass White", 10.0, shop="Fixture Two"),
            _product("c", "Fixturon Wine Glass Red", 10.0, brand="Otherbrand"),
        ]), [])
        many = [_product(f"p{number}", f"Fixturon Mug {number}", 5.0) for number in range(SET_MOST + 1)]
        self.assertEqual(doubtful_sets(many), [])

    def test_a_job_holds_so_many_listings_at_most(self) -> None:
        from picwise_providers.variant_families import LISTINGS_PER_JOB

        folder = Path(tempfile.mkdtemp())
        listing = {"title": "Fixturon Mug Black", "price": "5.00", "products": ["fixture shop\x1fm"]}
        sets = [{"id": f"s{number:03d}", "brand": "", "listings": [listing] * SET_MOST} for number in range(10)]
        written = write_jobs(sets, folder, answered=set())
        per_job = LISTINGS_PER_JOB // SET_MOST
        self.assertEqual(written, -(-10 // per_job))
        for job in folder.glob("family-*.json"):
            held = json.loads(job.read_text(encoding="utf-8"))["sets"]
            self.assertLessEqual(sum(len(found["listings"]) for found in held), LISTINGS_PER_JOB)

    def test_the_jobs_are_the_sets_not_answered_the_night_before_s_gone(self) -> None:
        folder = Path(tempfile.mkdtemp())
        (folder / "family-old.json").write_text("{}", encoding="utf-8")
        sets = [{"id": f"s{number:03d}", "brand": "", "listings": []} for number in range(30)]
        written = write_jobs(sets, folder, answered={"s000", "s001"})
        names = sorted(path.name for path in folder.glob("family-*.json"))
        self.assertEqual(written, 2)
        self.assertNotIn("family-old.json", names)
        held = [found["id"] for name in names for found in json.loads((folder / name).read_text())["sets"]]
        self.assertEqual(len(held), 28)
        self.assertNotIn("s000", held)


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.sets = [
            {"id": "set-a", "brand": "Fixturon", "listings": [
                {"title": "Fixturon Runner Black", "price": "38.00", "products": ["fixture shop\x1fb8", "fixture shop\x1fb9"]},
                {"title": "Fixturon Runner White", "price": "41.00", "products": ["fixture shop\x1fw8"]},
            ]},
            {"id": "set-b", "brand": "Fixturon", "listings": [
                {"title": "Fixturon Red Wine Glass", "price": "10.00", "products": ["fixture shop\x1fr"]},
                {"title": "Fixturon White Wine Glass", "price": "10.00", "products": ["fixture shop\x1fw"]},
            ]},
        ]
        write_jobs(self.sets, self.folder / "jobs", answered=set())

    def _service(self, answers: list[Asked], *, cap: float = DAILY_CAP_USD) -> FamilyService:
        asked = iter(answers)
        return FamilyService(
            self.folder, client=None, ask_fn=lambda request, client: next(asked),
            ledger=SpendLedger(self.folder, cap_usd=cap), limit=MinuteLimit(per_minute=1000),
            now=lambda: NOW, sleep=lambda seconds: None,
        )

    def _read(self, name: str) -> dict:
        return json.loads((self.folder / "answers" / name).read_text(encoding="utf-8"))

    def test_the_answers_give_each_product_its_family(self) -> None:
        service = self._service([_asked({"sets": [
            {"set": 1, "groups": [[1, 2]]},
            {"set": 2, "groups": [[1], [2]]},
        ]})])
        service.run(once=True)
        # The site's file: the products' families alone.
        self.assertEqual(self._read("families.json")["families"], {
            "fixture shop\x1fb8": "set-a-0", "fixture shop\x1fb9": "set-a-0", "fixture shop\x1fw8": "set-a-0",
        })
        sets = self._read("sets.json")
        self.assertEqual(sets["sets"], {
            "set-a": {"groups": [[1, 2]], "titles": ["Fixturon Runner Black", "Fixturon Runner White"]},
            "set-b": {"groups": [[1], [2]], "titles": ["Fixturon Red Wine Glass", "Fixturon White Wine Glass"]},
        })
        self.assertEqual(sets["families_count"], 3)
        self.assertEqual(list((self.folder / "jobs").glob("*.json*")), [])
        self.assertEqual(answered_set_ids(self.folder / "answers" / "sets.json"), {"set-a", "set-b"})

    def test_an_answer_that_does_not_check_out_is_left_out(self) -> None:
        self.assertEqual(checked_groups({"sets": [{"set": 1, "groups": [[1]]}]}, self.sets), {})  # 2 missing
        self.assertEqual(checked_groups({"sets": [{"set": 1, "groups": [[1, 2], [2]]}]}, self.sets), {})  # twice
        self.assertEqual(checked_groups({"sets": [{"set": 3, "groups": [[1]]}]}, self.sets), {})  # no such set
        self.assertEqual(checked_groups(None, self.sets), {})
        service = self._service([_asked(None, error="an answer that is not JSON")])
        service.run(once=True)
        # Nothing answered, nothing written: both sets are asked again the next night.
        self.assertFalse((self.folder / "answers" / "families.json").exists())
        self.assertEqual(answered_set_ids(self.folder / "answers" / "sets.json"), set())

    def test_past_the_day_s_cap_nothing_is_asked(self) -> None:
        ledger = SpendLedger(self.folder, cap_usd=0.001)
        ledger.add(NOW, 0.002)
        service = self._service([], cap=0.001)
        service.run(once=True)
        self.assertEqual(len(list((self.folder / "jobs").glob("family-*.json"))), 1)
        self.assertFalse((self.folder / "answers" / "families.json").exists())

    def test_a_job_a_stopped_run_had_claimed_is_given_back(self) -> None:
        job = next((self.folder / "jobs").glob("family-*.json"))
        job.replace(job.with_name(f".{job.name}.taken"))
        service = self._service([_asked({"sets": [{"set": 1, "groups": [[1, 2]]}, {"set": 2, "groups": [[1, 2]]}]})])
        service.run(once=True)
        self.assertEqual(answered_set_ids(self.folder / "answers" / "sets.json"), {"set-a", "set-b"})

    def test_a_stop_writes_the_answers_kept_so_far(self) -> None:
        (self.folder / "jobs" / "family-zzz.json").write_text(
            json.dumps({"sets": [{"id": "set-c", "brand": "", "listings": self.sets[0]["listings"]}]}), encoding="utf-8"
        )
        answers = iter([_asked({"sets": [{"set": 1, "groups": [[1, 2]]}, {"set": 2, "groups": [[1], [2]]}]})])

        def ask_then_stop(request, client):
            for found in answers:
                return found
            raise SystemExit(0)  # systemd's stop, as family_service.py turns it

        service = FamilyService(
            self.folder, client=None, ask_fn=ask_then_stop, ledger=SpendLedger(self.folder),
            limit=MinuteLimit(per_minute=1000), now=lambda: NOW, sleep=lambda seconds: None,
        )
        with self.assertRaises(SystemExit):
            service.run()
        self.assertEqual(answered_set_ids(self.folder / "answers" / "sets.json"), {"set-a", "set-b"})
        self.assertTrue((self.folder / "jobs" / ".family-zzz.json.taken").exists())

    def test_the_files_are_written_at_most_once_a_minute(self) -> None:
        clock = [100.0]
        answers = FamilyStore(self.folder / "answers", clock=lambda: clock[0])
        clock[0] = 110.0
        answers.add(self.sets[:1], {"set-a": [[1, 2]]}, now=NOW)
        self.assertFalse((self.folder / "answers" / "families.json").exists())
        clock[0] = 161.0
        answers.add(self.sets[1:], {"set-b": [[1, 2]]}, now=NOW)
        self.assertEqual(set(self._read("sets.json")["sets"]), {"set-a", "set-b"})
        self.assertEqual(len(self._read("families.json")["families"]), 5)
        # Read back by the next run, as it left them.
        again = FamilyStore(self.folder / "answers")
        self.assertEqual((set(again.sets), len(again.families)), ({"set-a", "set-b"}, 5))

    def test_the_request_names_no_shop_link_and_asks_for_groups(self) -> None:
        request = request_kwargs(self.sets)
        text = request["messages"][0]["content"]
        self.assertIn("Set 1 (brand Fixturon):", text)
        self.assertIn("1. Fixturon Runner Black | £38.00", text)
        self.assertNotIn("http", text)
        self.assertNotIn("fixture shop", text)
        self.assertEqual(request["model"], "claude-haiku-5-5")
        self.assertIn("When unsure, keep the listings apart.", request["system"][0]["text"])


class SampleTests(unittest.TestCase):
    def test_the_sample_prints_joined_titles_and_counts(self) -> None:
        import contextlib
        import importlib.util
        import io

        spec = importlib.util.spec_from_file_location(
            "print_families", ROOT / "deployment" / "server" / "print_families.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = {
            "sets": {
                "set-a": {"groups": [[1, 2]], "titles": ["Fixturon Runner Black", "Fixturon Runner White"]},
                "set-b": {"groups": [[1], [2]], "titles": ["Fixturon Red Wine Glass", "Fixturon White Wine Glass"]},
            },
            "families_count": 2,
            "updated_at": "2026-11-19T12:00:00+00:00",
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            module.print_families(payload, sample=10)
        text = out.getvalue()
        self.assertIn("sets answered: 2; with listings joined: 1; kept all apart: 1; products given a family: 2", text)
        self.assertIn("Fixturon Runner Black  +  Fixturon Runner White", text)
        self.assertIn("apart: Fixturon Red Wine Glass  |  Fixturon White Wine Glass", text)


class FamilyJobsTests(unittest.TestCase):
    def test_the_jobs_are_written_from_the_prepared_catalogue(self) -> None:
        import subprocess

        from picwise_providers.contracts import ProviderFeedStatus
        from picwise_providers.offer_health import build_feed_availability_context
        from picwise_providers.prepared_catalogue import PreparedCatalogue, write_prepared_catalogue
        from picwise_providers.search_selection import _product_search_fields

        products = tuple(
            _product(pid, title, price)
            for pid, title, price in (
                ("b", "Fixturon Runner Black", 38.0),
                ("w", "Fixturon Runner White", 41.0),
                ("k", "Fixturon Electric Kettle", 20.0),
            )
        )
        folder = Path(tempfile.mkdtemp())
        catalogue = folder / "catalogue.json.gz"
        write_prepared_catalogue(
            PreparedCatalogue(
                prepared_at=NOW,
                feed_status=ProviderFeedStatus(
                    status="provider_feed_ready", provider_key="awin", product_count=3, eligible_count=3
                ),
                availability_context=build_feed_availability_context(products),
                products=products,
                non_new=("", "", ""),
                kinds=(frozenset(), frozenset(), frozenset()),
                eligible_count=3,
                shop_count=1,
                suggestions=(),
                search_fields=tuple(_product_search_fields(product) for product in products),
            ),
            catalogue,
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "family_jobs.py"), "--catalogue", str(catalogue),
             "--jobs", str(folder / "jobs"), "--answers", str(folder / "answers" / "sets.json")],
            capture_output=True, text=True, check=False, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("family_jobs: 3 products; 1 sets a colour or a number tells apart, 0 answered before; "
                      "1 asked now, in 1 jobs", result.stdout)
        job = json.loads(next((folder / "jobs").glob("family-*.json")).read_text(encoding="utf-8"))
        self.assertEqual([listing["title"] for listing in job["sets"][0]["listings"]],
                         ["Fixturon Runner Black", "Fixturon Runner White"])
        missing = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "family_jobs.py"), "--catalogue",
             str(folder / "none.json.gz"), "--jobs", str(folder / "jobs"), "--answers", str(folder / "sets.json")],
            capture_output=True, text=True, check=False, timeout=300,
        )
        self.assertEqual(missing.returncode, 1)
        self.assertIn("the prepared catalogue cannot be read", missing.stdout)


class UnitsTests(unittest.TestCase):
    def test_the_services_and_the_deployment(self) -> None:
        server = ROOT / "deployment" / "server"
        families = (server / "picwise-families.service").read_text(encoding="utf-8")
        self.assertIn("User=picwise-assist", families)
        self.assertIn("EnvironmentFile=-/etc/picwise/assist.env", families)
        self.assertIn("ReadWritePaths=/srv/picwise/assist/families\n", families)
        jobs = (server / "picwise-family-jobs.service").read_text(encoding="utf-8")
        self.assertIn("User=picwise\n", jobs)
        self.assertNotIn("assist.env", jobs)
        self.assertIn("ReadWritePaths=-/srv/picwise/assist/families/jobs", jobs)
        self.assertIn("--answers /srv/picwise/assist/families/answers/sets.json", jobs)
        self.assertIn("OOMScoreAdjust=500", jobs)
        web = (server / "picwise-web.service").read_text(encoding="utf-8")
        self.assertIn("Environment=PICWISE_FAMILIES_FILE=/srv/picwise/assist/families/answers/families.json", web)
        deploy = (server / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("systemctl start --no-block picwise-family-jobs.service", deploy)
        self.assertIn('install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/families/jobs"', deploy)
        self.assertEqual(DAILY_CAP_USD, 5.00)


if __name__ == "__main__":
    unittest.main()
