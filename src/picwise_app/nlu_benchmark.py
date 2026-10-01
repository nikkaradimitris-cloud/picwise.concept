"""End-to-end misspelling benchmark: does PicWise understand what the buyer typed?

The question this answers is the product's own promise: a buyer types a product the way
people really type -- in Greek without accents, in greeklish, with a wrong vowel, with
the wrong keyboard layout on, in English with a slipped key -- and PicWise must still
return four suitable products of the right kind, with one recommended.

Each case is run through the real resolver and the real render gate, then classified:

- ``pass``: four cards render, one is recommended, and every card is the expected kind
  of product
- ``wrong_family``: cards render but at least one is the wrong kind of product. This is
  the worst outcome -- a confident wrong answer -- and must stay at zero
- ``ambiguous``: PicWise refused because the words pointed at two kinds of product
- ``empty``: nothing rendered; PicWise did not understand

Two sources of cases, kept apart on purpose:

- ``generated``: clean English and Greek names for each product type, run through the
  deterministic error generators in ``picwise_nlu.misspelling_variants``
- ``held_out``: realistic queries written by hand, with qualifiers, specs, mixed
  languages and the kind of misspellings people make. They are not derived from any
  lexicon PicWise uses, so the system is not grading its own vocabulary.

``negative`` cases must be refused: they are not retail product searches.

The inventory is the local coverage fixture feed. This benchmark measures understanding
given inventory; it says nothing about what a real provider feed contains.
"""
from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from picwise_nlu.misspelling_variants import (
    GREEKLISH_SCHEME_NAMES,
    doubled_letter,
    english_keyboard_slip,
    greek_final_sigma_error,
    greek_typed_on_english_layout,
    greek_vowel_confusion_variants,
    joined_words,
    missing_letter,
    strip_greek_accents,
    swapped_letters,
    transliterate_greek,
)
from picwise_nlu.query_variant_generator import generate_noisy_variants_for_term

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_FEED = ROOT / "tests" / "fixtures" / "provider_feed_coverage_matrix_fixture.csv"


@dataclass(frozen=True)
class BenchmarkProduct:
    product_type: str
    mega_category_id: str
    english: str
    greek: str


# The clean name a buyer would type for each product type stocked in the benchmark feed.
BENCHMARK_PRODUCTS: tuple[BenchmarkProduct, ...] = (
    BenchmarkProduct("Washing Machines", "home_appliances_laundry_climate", "washing machine", "πλυντήριο ρούχων"),
    BenchmarkProduct("Air Conditioners", "home_appliances_laundry_climate", "air conditioner", "κλιματιστικό"),
    BenchmarkProduct("Refrigerators", "home_appliances_laundry_climate", "fridge", "ψυγείο"),
    BenchmarkProduct("Vacuum Cleaners", "home_appliances_laundry_climate", "vacuum cleaner", "ηλεκτρική σκούπα"),
    BenchmarkProduct("Coffee Machines", "kitchen_cooking_household", "coffee machine", "καφετιέρα"),
    BenchmarkProduct("Microwave Ovens", "kitchen_cooking_household", "microwave", "φούρνος μικροκυμάτων"),
    BenchmarkProduct("Air Fryers", "kitchen_cooking_household", "air fryer", "φριτέζα αέρος"),
    BenchmarkProduct("Office & Computer Chairs", "furniture_living_storage_smart_home", "office chair", "καρέκλα γραφείου"),
    BenchmarkProduct("Desks", "furniture_living_storage_smart_home", "desk", "γραφείο υπολογιστή"),
    BenchmarkProduct("Mobile Phones", "phones_mobile_accessories", "smartphone", "κινητό τηλέφωνο"),
    BenchmarkProduct("Power Banks", "phones_mobile_accessories", "power bank", "εξωτερική μπαταρία"),
    BenchmarkProduct("Laptops", "computers_office_peripherals", "laptop", "φορητός υπολογιστής"),
    BenchmarkProduct("Mice", "computers_office_peripherals", "mouse", "ποντίκι"),
    BenchmarkProduct("Computer Monitors", "computers_office_peripherals", "monitor", "οθόνη υπολογιστή"),
    BenchmarkProduct("Keyboards", "computers_office_peripherals", "keyboard", "πληκτρολόγιο"),
    BenchmarkProduct("Webcams", "computers_office_peripherals", "webcam", "κάμερα υπολογιστή"),
    BenchmarkProduct("Toner Cartridges", "computers_office_peripherals", "toner cartridge", "τόνερ"),
    BenchmarkProduct("Ink Cartridges", "computers_office_peripherals", "ink cartridge", "μελάνια εκτυπωτή"),
    BenchmarkProduct("Multifunction Printers", "computers_office_peripherals", "printer", "εκτυπωτής"),
    BenchmarkProduct("Headphones & Headsets", "audio_video_gaming_cameras", "headphones", "ακουστικά"),
    BenchmarkProduct("Televisions", "audio_video_gaming_cameras", "tv", "τηλεόραση"),
    BenchmarkProduct("Car Batteries", "car_parts_service_maintenance", "car battery", "μπαταρία αυτοκινήτου"),
    BenchmarkProduct("Tyres", "tyres_wheels_car_accessories", "tyres", "λάστιχα αυτοκινήτου"),
    BenchmarkProduct("Bicycle Helmets", "moto_bicycle_mobility_gear", "bicycle helmet", "κράνος ποδηλάτου"),
    BenchmarkProduct("Power Drills", "power_tools_workshop", "drill", "δράπανο"),
    BenchmarkProduct("Screwdriver Sets", "hand_tools_consumables_measuring", "screwdriver set", "σετ κατσαβίδια"),
    BenchmarkProduct("Lawn Mowers", "garden_outdoor_repair_building", "lawn mower", "χλοοκοπτικό"),
    BenchmarkProduct("Blood Pressure Monitors", "health_wellness_safety_devices", "blood pressure monitor", "πιεσόμετρο"),
    BenchmarkProduct("Electric Shavers", "beauty_grooming_personal_care", "electric shaver", "ξυριστική μηχανή"),
    BenchmarkProduct("Baby Strollers", "baby_kids_pets_sports_outdoor", "stroller", "καρότσι μωρού"),
    BenchmarkProduct("Work Trousers", "clothing_apparel_workwear", "work trousers", "παντελόνι εργασίας"),
    BenchmarkProduct("Athletic Shoes", "footwear_shoes_sneakers_boots", "running shoes", "αθλητικά παπούτσια"),
    BenchmarkProduct("Wristwatches", "jewelry_watches_bags_fashion_accessories", "watch", "ρολόι χειρός"),
)


# Written by hand, not generated: how buyers actually phrase a search. Specs, needs,
# brands, mixed Greek and English, and the misspellings people really make.
HELD_OUT_QUERIES: tuple[tuple[str, str], ...] = (
    ("πλυντηριο ρουχων 8 κιλα", "Washing Machines"),
    ("plintirio 9 kila", "Washing Machines"),
    ("πλυντήριο ρούχον", "Washing Machines"),
    ("wasing machine 8kg", "Washing Machines"),
    ("κλιματηστικο 12000 btu", "Air Conditioners"),
    ("klimatistiko inverter", "Air Conditioners"),
    ("φθηνο κλιματιστικο", "Air Conditioners"),
    ("air condisioner", "Air Conditioners"),
    ("ψυγειο", "Refrigerators"),
    ("ψιγείο", "Refrigerators"),
    ("psygeio", "Refrigerators"),
    ("ψυγειοκαταψυκτης", "Refrigerators"),
    ("fridge freezer", "Refrigerators"),
    ("ηλεκτρικη σκουπα", "Vacuum Cleaners"),
    ("σκουπα ρομποτ", "Vacuum Cleaners"),
    ("skoupa", "Vacuum Cleaners"),
    ("vacum cleaner", "Vacuum Cleaners"),
    ("καφετιερα φιλτρου", "Coffee Machines"),
    ("μηχανη καφε espresso", "Coffee Machines"),
    ("kafetiera", "Coffee Machines"),
    ("coffe machine", "Coffee Machines"),
    ("καφετηέρα", "Coffee Machines"),
    ("φουρνος μικροκυματων", "Microwave Ovens"),
    ("μικροκυματα", "Microwave Ovens"),
    ("microwve", "Microwave Ovens"),
    ("φριτεζα αερος", "Air Fryers"),
    ("air fryer 5 λιτρα", "Air Fryers"),
    ("fritieza aeros", "Air Fryers"),
    ("φριτέζα χωρίς λάδι", "Air Fryers"),
    ("καρεκλα γραφειου εργονομικη", "Office & Computer Chairs"),
    ("karekla grafeiou", "Office & Computer Chairs"),
    ("ofice chair", "Office & Computer Chairs"),
    ("γραφειο υπολογιστη", "Desks"),
    ("grafeio ypologisti", "Desks"),
    ("κινητο τηλεφωνο", "Mobile Phones"),
    ("κινητο με καλη καμερα", "Mobile Phones"),
    ("kinito", "Mobile Phones"),
    ("smarphone", "Mobile Phones"),
    ("pawer bank 20000 gia iphone", "Power Banks"),
    ("εξωτερικη μπαταρια κινητου", "Power Banks"),
    ("powerbank 10000mah", "Power Banks"),
    ("λαπτοπ για φοιτητη", "Laptops"),
    ("laptop 16gb ram", "Laptops"),
    ("φορητος υπολογιστης", "Laptops"),
    ("lapotp", "Laptops"),
    ("ποντικι ασυρματο", "Mice"),
    ("pontiki", "Mice"),
    ("mause", "Mice"),
    ("οθονη υπολογιστη 27", "Computer Monitors"),
    ("othoni 24", "Computer Monitors"),
    ("monitr", "Computer Monitors"),
    ("πληκτρολογιο ασυρματο", "Keyboards"),
    ("pliktrologio", "Keyboards"),
    ("keybord", "Keyboards"),
    ("καμερα υπολογιστη για zoom", "Webcams"),
    ("webcam για laptop", "Webcams"),
    ("τονερ εκτυπωτη", "Toner Cartridges"),
    ("τόνερ για εκτυπωτή laser", "Toner Cartridges"),
    ("μελανια εκτυπωτη", "Ink Cartridges"),
    ("melania ektypoti", "Ink Cartridges"),
    ("εκτυπωτης", "Multifunction Printers"),
    ("εκτυπωτης πολυμηχανημα", "Multifunction Printers"),
    ("ektypotis laser", "Multifunction Printers"),
    ("printr", "Multifunction Printers"),
    ("ακουστικα bluetooth", "Headphones & Headsets"),
    ("akoustika", "Headphones & Headsets"),
    ("ασυρματα ακουστικα", "Headphones & Headsets"),
    ("headfones", "Headphones & Headsets"),
    ("τηλεοραση 55 ιντσες", "Televisions"),
    ("tileorasi", "Televisions"),
    ("tv 43", "Televisions"),
    ("τηλαιοραση", "Televisions"),
    ("μπαταρια αυτοκινητου 70ah", "Car Batteries"),
    ("bataria aftokinitou", "Car Batteries"),
    ("λαστιχα αυτοκινητου", "Tyres"),
    ("ελαστικα 205/55 r16", "Tyres"),
    ("lastixa", "Tyres"),
    ("κρανος ποδηλατου", "Bicycle Helmets"),
    ("kranos podilatou", "Bicycle Helmets"),
    ("κρανοσ ποδηλατου παιδικο", "Bicycle Helmets"),
    ("δραπανο μπαταριας", "Power Drills"),
    ("drapano", "Power Drills"),
    ("κρουστικο δραπανο", "Power Drills"),
    ("σετ κατσαβιδια", "Screwdriver Sets"),
    ("katsavidia", "Screwdriver Sets"),
    ("χλοοκοπτικο", "Lawn Mowers"),
    ("xlookoptiko", "Lawn Mowers"),
    ("χλοοκοπτικο ηλεκτρικο", "Lawn Mowers"),
    ("πιεσομετρο", "Blood Pressure Monitors"),
    ("piesometro", "Blood Pressure Monitors"),
    ("πιεσόμετρο μπράτσου", "Blood Pressure Monitors"),
    ("ξυριστικη μηχανη", "Electric Shavers"),
    ("ksiristiki mixani", "Electric Shavers"),
    ("καροτσι μωρου", "Baby Strollers"),
    ("karotsi", "Baby Strollers"),
    ("καρότσι για μωρό", "Baby Strollers"),
    ("παντελονι εργασιας", "Work Trousers"),
    ("panteloni ergasias", "Work Trousers"),
    ("αθλητικα παπουτσια για τρεξιμο", "Athletic Shoes"),
    ("athlitika papoutsia", "Athletic Shoes"),
    ("παπουτσια τρεξιματος", "Athletic Shoes"),
    ("ρολοι χειρος", "Wristwatches"),
    ("roloi", "Wristwatches"),
    ("ρολόι ανδρικό", "Wristwatches"),
)

# Not retail product searches. PicWise must render nothing for them.
NEGATIVE_QUERIES: tuple[str, ...] = (
    "δανειο",
    "ασφαλεια αυτοκινητου",
    "τραπεζα",
    "asdfgh",
    "καιρος αυριο",
    "loan",
    "insurance",
)


@dataclass(frozen=True)
class BenchmarkCase:
    query: str
    expected_product_type: str
    error_class: str
    language: str
    source: str


@dataclass
class BenchmarkOutcome:
    case: BenchmarkCase
    outcome: str
    rendered_product_types: tuple[str, ...] = field(default_factory=tuple)
    unmatched_terms: tuple[str, ...] = field(default_factory=tuple)
    resolver_state: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["case"] = asdict(self.case)
        return payload


def _dedupe_cases(cases: Iterable[BenchmarkCase]) -> list[BenchmarkCase]:
    seen: set[tuple[str, str]] = set()
    output: list[BenchmarkCase] = []
    for case in cases:
        key = (" ".join(case.query.lower().split()), case.expected_product_type)
        if not case.query.strip() or key in seen:
            continue
        seen.add(key)
        output.append(case)
    return output


def _generated_cases(product: BenchmarkProduct) -> list[BenchmarkCase]:
    expected = product.product_type
    cases: list[BenchmarkCase] = []

    def add(query: str, error_class: str, language: str) -> None:
        if query:
            cases.append(BenchmarkCase(query, expected, error_class, language, "generated"))

    add(product.english, "clean", "en")
    for row in generate_noisy_variants_for_term(product.english, product.mega_category_id):
        add(row["variant"], f"en_{row['variant_type']}", "en")
    add(english_keyboard_slip(product.english), "en_keyboard_slip", "en")

    greek = product.greek
    bare = strip_greek_accents(greek).lower()
    add(greek, "clean", "el")
    add(bare, "el_no_accents", "el")
    for variant in greek_vowel_confusion_variants(greek):
        add(variant, "el_vowel_confusion", "el")
    final_sigma = greek_final_sigma_error(greek)
    if final_sigma != bare:
        add(final_sigma, "el_final_sigma", "el")
    add(missing_letter(bare), "el_missing_letter", "el")
    add(swapped_letters(bare), "el_swapped_letters", "el")
    add(doubled_letter(bare), "el_doubled_letter", "el")
    add(joined_words(bare), "el_joined_words", "el")

    for scheme in GREEKLISH_SCHEME_NAMES:
        add(transliterate_greek(greek, scheme), scheme, "greeklish")
    add(missing_letter(transliterate_greek(greek, "greeklish_standard")), "greeklish_missing_letter", "greeklish")
    add(greek_typed_on_english_layout(greek), "el_wrong_keyboard_layout", "el")
    return cases


def build_misspelling_benchmark(
    products: Iterable[BenchmarkProduct] = BENCHMARK_PRODUCTS,
    *,
    include_held_out: bool = True,
    include_negatives: bool = True,
) -> list[BenchmarkCase]:
    """The deterministic benchmark case list."""
    cases: list[BenchmarkCase] = []
    # Held-out cases go first so a hand-written query that happens to equal a generated
    # variant keeps its held-out label: that set is the independent check.
    if include_held_out:
        cases.extend(
            BenchmarkCase(query, expected, "held_out", "mixed", "held_out")
            for query, expected in HELD_OUT_QUERIES
        )
    for product in products:
        cases.extend(_generated_cases(product))
    if include_negatives:
        cases.extend(
            BenchmarkCase(query, "", "negative", "mixed", "negative")
            for query in NEGATIVE_QUERIES
        )
    return _dedupe_cases(cases)


def _resolve(query: str):
    # Imported here so this module can be loaded by tooling without starting the search
    # runtime until a benchmark actually runs.
    from picwise_search.live_search_resolver import resolve_live_search
    from picwise_surface import provider_feed_cards_will_render

    resolution = resolve_live_search(query)
    return resolution, provider_feed_cards_will_render(resolution)


def evaluate_benchmark_case(
    case: BenchmarkCase,
    *,
    resolve: Callable[[str], Any] | None = None,
) -> BenchmarkOutcome:
    started = time.perf_counter()
    resolution, rendered = (resolve or _resolve)(case.query)
    latency_ms = (time.perf_counter() - started) * 1000
    products = tuple(resolution.provider_feed_selected_products) if rendered else tuple()
    rendered_types = tuple(str(p.get("product_type") or "") for p in products)
    unmatched = tuple(getattr(resolution, "provider_feed_unmatched_query_terms", ()) or ())
    state = str(getattr(resolution, "resolver_state", "") or "")

    if case.source == "negative":
        outcome = "pass" if not rendered else "wrong_family"
    elif rendered and len(products) == 4 and resolution.provider_feed_recommended_product_id:
        outcome = (
            "pass"
            if all(kind == case.expected_product_type for kind in rendered_types)
            else "wrong_family"
        )
    elif rendered:
        outcome = "wrong_family"
    elif getattr(resolution, "provider_feed_selection_status", "") == "ambiguous_product_family":
        outcome = "ambiguous"
    else:
        outcome = "empty"
    return BenchmarkOutcome(
        case=case,
        outcome=outcome,
        rendered_product_types=rendered_types,
        unmatched_terms=unmatched,
        resolver_state=state,
        latency_ms=round(latency_ms, 1),
    )


def _rate(outcomes: list[BenchmarkOutcome], outcome: str) -> float:
    return round(sum(1 for o in outcomes if o.outcome == outcome) / len(outcomes), 4) if outcomes else 0.0


def summarize_benchmark(outcomes: list[BenchmarkOutcome]) -> dict[str, Any]:
    def group(key: Callable[[BenchmarkOutcome], str]) -> dict[str, dict[str, Any]]:
        buckets: dict[str, list[BenchmarkOutcome]] = {}
        for outcome in outcomes:
            buckets.setdefault(key(outcome), []).append(outcome)
        return {
            name: {
                "cases": len(rows),
                "pass_rate": _rate(rows, "pass"),
                "wrong_family": sum(1 for o in rows if o.outcome == "wrong_family"),
                "empty": sum(1 for o in rows if o.outcome == "empty"),
                "ambiguous": sum(1 for o in rows if o.outcome == "ambiguous"),
            }
            for name, rows in sorted(buckets.items())
        }

    latencies = sorted(o.latency_ms for o in outcomes)
    return {
        "cases": len(outcomes),
        "pass_rate": _rate(outcomes, "pass"),
        "wrong_family": sum(1 for o in outcomes if o.outcome == "wrong_family"),
        "empty": sum(1 for o in outcomes if o.outcome == "empty"),
        "ambiguous": sum(1 for o in outcomes if o.outcome == "ambiguous"),
        "latency_ms_median": latencies[len(latencies) // 2] if latencies else 0.0,
        "latency_ms_p95": latencies[int(len(latencies) * 0.95)] if latencies else 0.0,
        "by_source": group(lambda o: o.case.source),
        "by_language": group(lambda o: o.case.language),
        "by_error_class": group(lambda o: o.case.error_class),
        "by_product_type": group(lambda o: o.case.expected_product_type or "(negative)"),
    }


def run_misspelling_benchmark(
    cases: list[BenchmarkCase] | None = None,
    *,
    feed_file: str | os.PathLike[str] | None = None,
) -> tuple[list[BenchmarkOutcome], dict[str, Any]]:
    """Run the benchmark against a feed file, restoring the environment afterwards."""
    from picwise_providers.awin_adapter import clear_awin_feed_parse_cache
    from picwise_providers.state import clear_provider_feed_pipeline_cache

    selected = cases if cases is not None else build_misspelling_benchmark()
    previous = os.environ.get("AWIN_FEED_FILE")
    os.environ["AWIN_FEED_FILE"] = str(feed_file or DEFAULT_BENCHMARK_FEED)
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()
    try:
        outcomes = [evaluate_benchmark_case(case) for case in selected]
    finally:
        if previous is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
    return outcomes, summarize_benchmark(outcomes)
