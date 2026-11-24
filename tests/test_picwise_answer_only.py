"""Shorter deployments: the functions the search runs only when it answers are left out of the
prepared file's fingerprint (`picwise_providers.answer_only`; owner, 2026-11-24: «Είναι καλό να
περιορίσουμε το χρόνο εφόσον υπάρχει ασφάλεια ότι θα βγει σωστό»).

Pinned here:
- a change inside a function marked `@answer_only` leaves the fingerprint as it was, so a
  deployment of it does not prepare the catalogue again; a change anywhere else changes it;
- the repository's marks: the functions of the answer the preparation never runs, and a
  change to one of them (the rule of a price forty times the next) or to one the preparation
  runs (a product's search fields), read on a copy of the code;
- a preparation records the marked functions it calls: none on the fixture's catalogue,
  so the file is frozen without them; one that calls one is written with the whole
  fingerprint, and still read by the code that wrote it: a wrong mark makes deployments
  slower, never the site wrong;
- the deployment's own reading of the file (`prepared_state`) follows the file's mode.

Every product is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import prepared_state  # noqa: E402
from picwise_providers import answer_only, prepared_catalogue, search_selection, variant_families, variant_names  # noqa: E402
from picwise_providers.prepared_catalogue import check_prepared_catalogue, code_fingerprint  # noqa: E402
from test_picwise_prepared_catalogue import _feed_rows, _PreparedMixin  # noqa: E402


def _copy_of_the_code() -> Path:
    root = Path(tempfile.mkdtemp())
    for package in prepared_catalogue._FROZEN_PACKAGES:
        shutil.copytree(ROOT / package, root / package)
    for name in prepared_catalogue._FROZEN_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, target)
    return root


def _edit(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


class FingerprintTests(unittest.TestCase):
    def test_a_change_inside_a_marked_function_leaves_the_fingerprint(self) -> None:
        root = _copy_of_the_code()
        self.addCleanup(shutil.rmtree, root, True)
        before, before_full = code_fingerprint(repo_root=root), code_fingerprint(repo_root=root, full=True)
        _edit(root, "src/picwise_providers/search_selection.py", "FAR_LEFT_OUT_MOST):", "FAR_LEFT_OUT_MOST + 0):")
        self.assertEqual(code_fingerprint(repo_root=root), before)
        self.assertNotEqual(code_fingerprint(repo_root=root, full=True), before_full)

    def test_a_change_the_preparation_runs_changes_it(self) -> None:
        root = _copy_of_the_code()
        self.addCleanup(shutil.rmtree, root, True)
        before = code_fingerprint(repo_root=root)
        source = (root / "src/picwise_providers/search_selection.py").read_text(encoding="utf-8")
        start = source.index("def _product_search_fields(")
        body = source.index('"""', source.index('"""', start) + 3) + 3
        _edit(root, "src/picwise_providers/search_selection.py", source[start:body], source[start:body] + "\n    pass")
        self.assertNotEqual(code_fingerprint(repo_root=root), before)

    def test_a_change_to_a_frozen_data_file_changes_it(self) -> None:
        root = _copy_of_the_code()
        self.addCleanup(shutil.rmtree, root, True)
        before = code_fingerprint(repo_root=root)
        _edit(root, "data/category_switches.json", '"min": 120', '"min": 130')
        self.assertNotEqual(code_fingerprint(repo_root=root), before)

    def test_the_marked_functions(self) -> None:
        def marked(module) -> list[str]:
            return sorted(name for name, value in vars(module).items()
                          if getattr(value, "__answer_only__", False) and value.__module__ == module.__name__)

        self.assertEqual(marked(search_selection), sorted([
            "_cheaper_elsewhere", "_fitting_first", "_join_variants", "_median_recommendation", "_own_offers",
            "_price_bar", "_price_first_answer", "_price_first_products", "_price_first_result", "_price_from",
            "_shop_options", "_variant_members", "_variant_titles", "_without_far_dearer",
        ]))
        self.assertEqual(marked(variant_names), sorted([
            "merged_variants", "names_a_colour", "option_kind", "shop_option_values", "variant_values",
        ]))
        self.assertEqual(marked(variant_families), ["doubtful_sets", "families_of"])


class PreparationTests(_PreparedMixin, unittest.TestCase):
    def test_the_fixtures_preparation_calls_no_marked_function(self) -> None:
        self._write_feed(_feed_rows())
        self._prepare()
        self.assertEqual(answer_only.used_while_preparing(), frozenset())
        head = prepared_state.read_head(self.prepared_path)
        self.assertEqual(head["code_mode"], "answer_only_left_out")
        self.assertEqual(head["code"], code_fingerprint())
        self.assertEqual(check_prepared_catalogue(self.prepared_path).state, "fresh")
        self.assertEqual(prepared_state.state_of(self.prepared_path)[0], "fresh")

    def test_a_preparation_that_calls_one_is_frozen_whole_and_still_read(self) -> None:
        self._write_feed(_feed_rows())
        from picwise_providers import state

        original = state._catalogue_kind_choices

        def calling(*args, **kwargs):
            search_selection._price_bar([1.0, 2.0])
            return original(*args, **kwargs)

        with mock.patch.object(state, "_catalogue_kind_choices", calling):
            self._prepare()
        self.assertEqual(answer_only.used_while_preparing(), frozenset({"picwise_providers.search_selection._price_bar"}))
        head = prepared_state.read_head(self.prepared_path)
        self.assertEqual(head["code_mode"], "full")
        self.assertEqual(head["code"], code_fingerprint(full=True))
        self.assertEqual(check_prepared_catalogue(self.prepared_path).state, "fresh")
        self.assertEqual(prepared_state.state_of(self.prepared_path)[0], "fresh")

    def test_a_search_outside_a_preparation_records_nothing(self) -> None:
        with answer_only.preparing():
            pass
        search_selection._price_bar([1.0, 5.0])
        self.assertEqual(answer_only.used_while_preparing(), frozenset())


if __name__ == "__main__":
    unittest.main()
