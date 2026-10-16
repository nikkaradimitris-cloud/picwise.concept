"""Which kinds of product support the idea of "better", and on what.

Owner instruction (2026-10-12): take the subcategories and make rules for the ones
that cannot be compared with each other. Find which ones do not support the notions
of **comparison** and **best** -- those get a "see more" button. Find which ones have
criteria such as bytes, megabytes, kilos or any other characteristic, for grouping and
for the logic of comparing characteristics. Get the engine's logic clear first, and
only then connect more feeds and databases.

Their examples were exact: there is no best pair of shoes, no best bag, no best
tablecloth, no best wine. The project already answers this in `concept.picwise.txt`
-- «Τα 4 προϊόντα είναι 4 διαφορετικές απαντήσεις», four answers whose roles change
per category -- and this module is the missing piece: **which** answer shape a kind of
product gets.

## The distinction that makes the rules work

A measurable characteristic does two completely different jobs, and conflating them is
what produced "Lowest price of these four" on every card:

- **A ranking criterion** decides which is better, because more of it is better for
  every buyer. Storage, battery capacity, runtime, warranty length, an efficiency
  class. 64 GB really is more than 32 GB for anyone.
- **A matching criterion** decides which one fits, and ranking by it would be a lie.
  Kilos of a washing machine, litres of a fridge, metres of a cable, inches of a
  television, a shoe size, a tyre size. A 10 kg washing machine is not better than a
  7 kg one, it is bigger; the buyer who wants 7 kg is not served by being shown 10.

So a kind of product carries a list of each, and the two are never mixed.

## The three comparison classes

- **`spec`** -- a ranking criterion exists, so "better" can be argued from the feed's
  own numbers once a database supplies them. A storage drive, a power bank, a TV box.
- **`rating`** -- quality is real and differs between products, but no number in any
  feed captures it. A drill, a frying pan, a shampoo, a child's car seat. Only a
  rating can separate these, which is why the owner's "comparison starts with the
  product's rating" is not a preference but the only honest route for most of the
  catalogue.
- **`fit`** -- there is no better, only different. The choice is taste, style, or
  matching a specific requirement: a dress, a ring, a tablecloth, a printer cartridge
  for one printer model, a 2 m cable. Here PicWise must not claim a best, and the
  honest control is the one the owner named: **four different answers and a "see more"
  button**, because the engine cannot narrow a taste for the buyer.

`fit` is also the **default**, by the owner's decision of 2026-10-12: a kind of
product PicWise does not recognise claims no best. Claiming one requires knowing what
makes that kind of thing better, and an unrecognised kind is exactly the case where
PicWise does not know. So the three sets below are all explicit, and nothing reaches
`rating` or `spec` by omission.

`fit` is not a weaker class. It is the class where PicWise's promise changes shape, and
saying so is what keeps the other two honest.

## What this module does not decide

The class of each kind of product below is a judgement, written to be read and moved:
one line per kind, grouped by family. The owner approves or moves any of them. What is
**not** a judgement is the rule that follows from a class, and that is the point of
having them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ComparisonClass = Literal["spec", "rating", "fit"]

# Ranking criteria: more is better for every buyer. Kept identical to
# `picwise_providers.product_specs.RANKING_PROPERTIES` plus the two that no current
# feed carries but a product database does.
RANKING_CRITERIA = ("storage", "battery", "playtime", "warranty", "efficiency_class")

# Matching criteria: the buyer chooses a value, and ranking by it would be a lie.
MATCHING_CRITERIA = (
    "capacity_kg", "capacity_l", "length", "screen", "size", "width", "power",
    "resolution", "weight", "frequency", "impedance", "fitment", "compatibility",
)


@dataclass(frozen=True)
class ComparisonRule:
    """How a kind of product may be compared, and on what."""

    concept_id: str
    comparison_class: ComparisonClass
    ranking_criteria: tuple[str, ...] = tuple()
    matching_criteria: tuple[str, ...] = tuple()
    note: str = ""

    @property
    def supports_best(self) -> bool:
        """May PicWise claim one of the four is better than the others?"""
        return self.comparison_class in ("spec", "rating")

    @property
    def shows_see_more(self) -> bool:
        """Does the page offer a second four instead of a recommendation?

        Owner rule: in the kinds that do not support "best", the four are four
        different answers and the buyer gets a "see more" button.
        """
        return self.comparison_class == "fit"


# --- fit: no better, only different -------------------------------------------------
# Taste, style, or matching one specific requirement. The owner's own examples are
# here: shoes, bags, tablecloths. Nothing in this class may carry a "best" claim.
_FIT: dict[str, tuple[tuple[str, ...], str]] = {
    # Clothing: the choice is size, cut and style.
    "trousers": (("size",), "size and cut"),
    "jeans": (("size",), "size and cut"),
    "jacket": (("size",), "size and style"),
    "t_shirt": (("size",), "size and style"),
    "shirt": (("size",), "size and style"),
    "hoodie": (("size",), "size and style"),
    "sweater": (("size",), "size and style"),
    "dress": (("size",), "size and style"),
    "skirt": (("size",), "size and style"),
    "shorts": (("size",), "size and style"),
    "leggings": (("size",), "size and style"),
    "underwear": (("size",), "size and style"),
    "socks": (("size",), "size and style"),
    "swimwear": (("size",), "size and style"),
    "pyjamas": (("size",), "size and style"),
    "suit": (("size",), "size and cut"),
    "raincoat": (("size",), "size and style"),
    # Footwear worn for style rather than performance.
    "shoes": (("size",), "size and style -- the owner's own example of no best"),
    "sandals": (("size",), "size and style"),
    "slippers": (("size",), "size and style"),
    "boots": (("size",), "size and style"),
    # Jewellery and worn accessories: taste, and sometimes a size.
    "ring": (("size",), "taste, and a ring size"),
    "necklace": (tuple(), "taste"),
    "bracelet": (tuple(), "taste"),
    "earrings": (tuple(), "taste"),
    "sunglasses": (tuple(), "taste and face fit"),
    "watch": (tuple(), "taste -- a watch is jewellery before it is an instrument"),
    "hat": (("size",), "taste and head size"),
    "gloves": (("size",), "size and style"),
    "belt": (("size",), "size and style"),
    "wallet": (tuple(), "taste"),
    "bag": (tuple(), "taste -- the owner's own example of no best"),
    "handbag": (tuple(), "taste"),
    # Home textiles and decoration: the owner's tablecloth case.
    "towels": (("size",), "taste and size"),
    "bed_linen": (("size",), "bed size and taste"),
    "pillow": (tuple(), "sleeping preference"),
    "duvet": (("size",), "bed size and warmth preference"),
    "curtains": (("size",), "window size and taste"),
    "rug": (("size",), "room size and taste"),
    "mirror": (("size",), "size and taste"),
    "wall_clock": (tuple(), "taste"),
    "flower_pot": (("size",), "size and taste"),
    "parasol": (("size",), "size and taste"),
    "dinnerware": (tuple(), "taste"),
    "glassware": (tuple(), "taste"),
    # Consumables and parts that must match one specific thing. "Best" is meaningless:
    # the right one is the one that fits.
    "ink_cartridge": (("compatibility",), "must match the printer model"),
    "toner": (("compatibility",), "must match the printer model"),
    "phone_case": (("compatibility",), "must match the phone model"),
    "screen_protector": (("compatibility",), "must match the screen"),
    "charging_cable": (("length", "compatibility"), "length is a choice, not a merit"),
    "car_charger": (("compatibility", "power"), "must match the socket and device"),
    "car_phone_holder": (("compatibility",), "must match the car and phone"),
    "drill_bits": (("size", "compatibility"), "must match the material and chuck"),
    "razor_blades": (("compatibility",), "must match the handle"),
    "insoles": (("size",), "must match the shoe"),
    "snow_chains": (("fitment",), "must match the tyre size"),
    "oil_filter": (("fitment",), "must match the engine"),
    "air_filter": (("fitment",), "must match the engine"),
    "cabin_filter": (("fitment",), "must match the car"),
    "spark_plugs": (("fitment",), "must match the engine"),
    "wiper_blades": (("fitment", "length"), "must match the windscreen"),
    "brake_pads": (("fitment",), "must match the car"),
    "alloy_wheels": (("fitment", "size"), "must match the car, then taste"),
    "printer_paper": (("size",), "paper size and weight are a choice"),
    "nappies": (("size",), "baby size"),
    "food_storage": (("capacity_l",), "size and taste"),
    # Taste goods: a scent or a colour is not better or worse.
    "perfume": (tuple(), "scent is taste"),
    "nail_polish": (tuple(), "colour is taste"),
    "makeup": (tuple(), "shade is taste"),
    "lego": (tuple(), "the set is the choice"),
    "doll": (tuple(), "taste"),
    "board_game": (tuple(), "taste"),
    "toy": (tuple(), "taste and age fit"),
    "aquarium": (("capacity_l",), "size and taste"),
    "pool": (("capacity_l", "size"), "size and taste"),
    "garden_furniture": (("size",), "size and taste"),
    "flower_pot_saucer": (("size",), "size"),
    # Furniture, moved here by the owner on 2026-10-12. A mattress and a chair do have
    # real quality, but the choice is led by the size of the room and by taste, and
    # nobody asks for the best table.
    "bed": (("size",), "bed size and taste"),
    "mattress": (("size",), "bed size and firmness preference"),
    "sofa": (("size",), "room size and taste"),
    "chair": (("size",), "taste"),
    "desk": (("size",), "room size and taste"),
    "table": (("size",), "room size and taste"),
    "wardrobe": (("size",), "room size and taste"),
    "shelving": (("size",), "room size and taste"),
}

# --- spec: a ranking criterion exists ------------------------------------------------
# More of the named criterion is better for every buyer. Everything else about these
# products is still a matching criterion.
_SPEC: dict[str, tuple[tuple[str, ...], tuple[str, ...], str]] = {
    "storage_drive": (("storage",), ("size",), "capacity decides"),
    "ram_memory": (("storage",), ("frequency",), "capacity decides"),
    "power_bank": (("battery",), ("weight",), "mAh decides"),
    "tv_box": (("storage",), ("resolution",), "storage decides"),
    "tablet": (("storage", "battery"), ("screen",), "storage and battery decide; screen size is a choice"),
    "e_reader": (("storage", "battery"), ("screen",), "storage and battery decide"),
    "smartphone": (("storage", "battery"), ("screen",), "storage and battery decide; screen size is a choice"),
    "mobile_phone": (("battery",), ("screen",), "battery decides; screen size is a choice"),
    "laptop": (("storage", "battery"), ("screen", "weight"), "storage and battery decide; screen size is a choice"),
    "game_console": (("storage",), tuple(), "storage decides"),
    "headphones": (("playtime", "battery"), ("frequency", "impedance", "weight"), "playtime decides"),
    "smart_speaker": (("playtime",), ("power",), "playtime decides where it is portable"),
    "e_scooter": (("playtime", "battery"), ("weight",), "range decides"),
    "e_bike": (("playtime", "battery"), ("weight",), "range decides"),
    "ups": (("battery",), ("power",), "backup time decides"),
    "washing_machine": (("efficiency_class",), ("capacity_kg",), "efficiency decides; kilos are a choice"),
    "tumble_dryer": (("efficiency_class",), ("capacity_kg",), "efficiency decides; kilos are a choice"),
    "washer_dryer": (("efficiency_class",), ("capacity_kg",), "efficiency decides; kilos are a choice"),
    "dishwasher": (("efficiency_class",), ("capacity_l",), "efficiency decides"),
    "refrigerator": (("efficiency_class",), ("capacity_l",), "efficiency decides; litres are a choice"),
    "freezer": (("efficiency_class",), ("capacity_l",), "efficiency decides; litres are a choice"),
    "air_conditioner": (("efficiency_class",), ("power",), "efficiency decides; power must match the room"),
    "heat_pump": (("efficiency_class",), ("power",), "efficiency decides"),
    "water_heater": (("efficiency_class",), ("capacity_l",), "efficiency decides"),
    "television": (("efficiency_class",), ("screen", "resolution"), "inches are a choice, not a merit"),
    "monitor": (("efficiency_class",), ("screen", "resolution", "frequency"), "inches are a choice"),
    "light_bulb": (("efficiency_class",), ("power",), "efficiency decides"),
    "tyres": (("efficiency_class",), ("fitment",), "the EU label's wet grip and efficiency decide; size must match"),
    "winter_tyres": (("efficiency_class",), ("fitment",), "the EU label decides; size must match"),
    "summer_tyres": (("efficiency_class",), ("fitment",), "the EU label decides; size must match"),
    "car_battery": (("battery",), ("fitment",), "capacity decides; it must still fit"),
    "vacuum_cleaner": (("playtime", "efficiency_class"), ("power",), "runtime decides where it is cordless"),
    "robot_vacuum": (("playtime", "battery"), tuple(), "runtime decides"),
    "lawn_mower": (("playtime",), ("width", "power"), "runtime decides where it is cordless; cut width is a choice"),
    "robot_mower": (("playtime",), ("size",), "runtime and the area it covers decide"),
}


# --- rating: quality is real, no feed number measures it ---------------------------
# A drill really can be better than another drill, and nothing in any product feed
# says which. Only a rating can separate these, which is why the owner's rule that
# the comparison starts from the product's rating is not a preference: for most of
# the catalogue it is the only honest route. Listed explicitly rather than left as a
# default, because the default is `fit` (see `_rule_for`).
_RATING: frozenset[str] = frozenset(
    {
        # Appliances, kitchen machines and cookware: a kettle really can be better than
    # another kettle, and nothing in a feed says which.
        "dehumidifier", "air_purifier", "heater", "fan", "steam_mop",
        "iron", "coffee_machine", "microwave", "oven", "cooker",
        "hob", "air_fryer", "deep_fryer", "mixer", "hand_blender",
        "blender", "food_processor", "toaster", "kettle", "juicer",
        "cookware", "pressure_cooker", "kitchen_scale", "knife_set", "cutlery",
        "water_filter_jug", "grill",
        # Computing, networking, office and PC hardware.
        "office_chair", "lamp", "smart_plug", "phone_charger", "wireless_charger",
        "smartwatch", "desktop_pc", "printer", "router", "keyboard",
        "mouse", "webcam", "scanner", "docking_station", "graphics_card",
        "processor", "motherboard", "power_supply", "pc_case",
        # Audio, camera and video gear, where build and sound quality are real and
    # unmeasured by any feed number.
        "speaker", "soundbar", "game_controller", "camera", "action_camera",
        "microphone", "projector", "amplifier", "drone", "vr_headset",
        "selfie_stick", "car_audio", "gps_navigator", "dash_cam",
        # Car care, child safety and mobility, where a standard or a build decides.
        "engine_oil", "coolant", "child_car_seat", "bicycle", "helmet",
        "bicycle_helmet", "moto_helmet", "scooter", "bike_lock",
        # Power tools, hand tools and garden machines.
        "drill", "rotary_hammer", "impact_driver", "angle_grinder", "circular_saw",
        "jigsaw", "mitre_saw", "sander", "heat_gun", "air_compressor",
        "multi_tool", "nail_gun", "welder", "screwdriver", "screwdriver_set",
        "socket_set", "spanner", "pliers", "hammer", "tape_measure",
        "spirit_level", "utility_knife", "tool_box", "multimeter", "soldering_iron",
        "hand_saw", "work_gloves", "brush_cutter", "hedge_trimmer", "chainsaw",
        "leaf_blower", "pressure_washer", "garden_hose", "water_pump", "tiller",
        "ladder", "garden_sprayer", "paint", "tap", "blood_pressure_monitor",
        "thermometer",
        # Health, measuring and mobility devices.
        "pulse_oximeter", "smoke_detector", "bathroom_scale", "massager", "glucose_meter",
        "hearing_aid", "wheelchair", "face_mask",
        # Personal care and cosmetics with a function rather than a shade.
        "electric_shaver", "hair_clipper", "hair_dryer", "hair_straightener", "electric_toothbrush",
        "epilator", "hair_brush", "shampoo", "face_cream", "sunscreen",
        "deodorant", "baby_stroller", "baby_carrier",
        # Baby, child and pet equipment, where safety and durability are the question.
        "high_chair", "baby_monitor", "cot", "baby_bottle", "breast_pump",
        "dog_food", "cat_food", "pet_carrier", "cat_litter", "treadmill",
        "exercise_bike",
        # Sport, fitness and outdoor gear built for a job.
        "dumbbells", "kettlebell", "weight_bench", "yoga_mat", "football",
        "tent", "sleeping_bag", "work_trousers", "safety_vest", "athletic_shoes",
        # Workwear, performance footwear and bags built for a job -- deliberately apart
    # from their fashion twins `shoes`, `boots`, `bag` and `handbag`, which are `fit`.
        "running_shoes", "hiking_boots", "safety_shoes", "backpack", "laptop_bag",
        "suitcase", "dishwasher_tablets", "laundry_detergent",
    }
)

def _rule_for(concept_id: str) -> ComparisonRule:
    if concept_id in _FIT:
        matching, note = _FIT[concept_id]
        return ComparisonRule(
            concept_id=concept_id,
            comparison_class="fit",
            matching_criteria=matching,
            note=note,
        )
    if concept_id in _SPEC:
        ranking, matching, note = _SPEC[concept_id]
        return ComparisonRule(
            concept_id=concept_id,
            comparison_class="spec",
            ranking_criteria=ranking,
            matching_criteria=matching,
            note=note,
        )
    if concept_id in _RATING:
        return ComparisonRule(
            concept_id=concept_id,
            comparison_class="rating",
            note="quality is real but no feed number measures it",
        )
    # Anything PicWise does not recognise is `fit`, by the owner's decision of
    # 2026-10-12. This is the safe direction and the only honest one: claiming a best
    # requires knowing what makes this kind of thing better, and an unknown kind is
    # exactly the case where PicWise does not know. The default used to be `rating`,
    # which would have let the engine claim a best tablecloth or a best wine -- both
    # kinds the taxonomy does not carry. A kind that belongs in `rating` or `spec` is
    # added to the sets above, deliberately, rather than arriving there by omission.
    return ComparisonRule(
        concept_id=concept_id,
        comparison_class="fit",
        note="not a kind PicWise recognises, so no best is claimed",
    )


def comparison_rule(concept_id: str) -> ComparisonRule:
    """How this kind of product may be compared. Unknown kinds fall to `rating`."""
    return _rule_for(" ".join(str(concept_id or "").strip().lower().split()))


def kinds_without_a_best() -> tuple[str, ...]:
    """The kinds listed as having no best, where PicWise offers "see more" instead.

    An unrecognised kind is treated the same way but is not listed here: this is the
    vocabulary, not the behaviour.
    """
    return tuple(sorted(_FIT))


def kinds_judged_by_rating() -> tuple[str, ...]:
    """The kinds where quality is real and only a rating can separate them."""
    return tuple(sorted(_RATING))


def kinds_with_a_ranking_criterion() -> tuple[str, ...]:
    """The kinds a feed's own numbers could rank, once a source supplies them."""
    return tuple(sorted(_SPEC))
