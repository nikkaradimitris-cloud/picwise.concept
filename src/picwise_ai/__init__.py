"""PicWise's AI layer for complex searches (`docs/PICWISE_AI_LAYER_SPEC.md`, part (c)).

Owner, 2026-11-05: «συμφωνώ με την αρχιτεκτονική και την εγκατάσταση Haiku», then «ΝΑΙ»
to building it first. Claude Haiku 5.5 reads up to 30 products the engine has already
verified, only when the page says "PicWise could not match" some words of a search for a
kind, and writes one sentence that code checks before anything is shown. It never changes
which products are shown; the products whose own words show they fit the need come first,
the Recommended chosen among them (owner, 2026-11-06), and nothing else of the order.

A layer of its own: `picwise_nlu` never imports it, and the site never imports the
Anthropic SDK; only `client.make_client` does, when it is called.
"""
