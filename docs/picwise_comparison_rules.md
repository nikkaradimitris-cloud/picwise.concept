# Comparison rules: where "better" exists, and where it does not

Owner instruction (2026-10-12): make rules for the subcategories that cannot be
compared with each other; find the ones that do not support the notions of
**comparison** and **best**, because those get a "see more" button; and find which
ones have criteria such as bytes, megabytes or kilos, for the grouping and the
comparison logic. Get the engine's logic clear first, and only then connect more feeds
and databases.

The rules are in `src/picwise_taxonomy/comparison_rules.py`, pinned by
`tests/test_picwise_comparison_rules.py` (16 tests). Nothing in the locked specs was
changed.

## The distinction the rules rest on

A measurable characteristic does two different jobs, and mixing them is what produced
"Lowest price of these four" on every card:

- **A ranking criterion** decides which is **better**, because more of it is better
  for every buyer: storage, battery, runtime, warranty length, an energy efficiency
  class. 64 GB really is more than 32 GB, for anyone.
- **A matching criterion** decides which one **fits**, and ranking by it would be a
  lie: the kilos of a washing machine, the litres of a fridge, the metres of a cable,
  the inches of a television, a shoe size, a tyre size. A 10 kg washing machine is not
  better than a 7 kg one -- it is bigger, and the buyer who wants 7 kg is not served
  by being shown 10.

No criterion is ever both, for any kind of product. That is a test, not a convention.

## The three classes, over the 278 kinds PicWise recognises

| Class | Kinds | What PicWise may claim |
| --- | --- | --- |
| `spec` | 34 (12%) | one is better, argued from a number |
| `rating` | 168 (60%) | one is better, but **only a rating can say so** |
| `fit` | 76 (27%) | **no best** -- four different answers and "see more" |

The middle row is the whole argument for the owner's "comparison starts with the
product's rating": for 168 of 278 kinds, a rating is not one signal among
several. It is the **only** signal that can honestly separate them.

## `fit` -- no best, only different. These get the "see more" button

Taste, style, or matching one specific requirement. The owner's own examples are here.

  `air_filter`, `alloy_wheels`, `aquarium`, `bag`, `bed_linen`, `belt`, `board_game`, `boots`
  `bracelet`, `brake_pads`, `cabin_filter`, `car_charger`, `car_phone_holder`, `charging_cable`, `curtains`, `dinnerware`
  `doll`, `dress`, `drill_bits`, `duvet`, `earrings`, `flower_pot`, `food_storage`, `garden_furniture`
  `glassware`, `gloves`, `handbag`, `hat`, `hoodie`, `ink_cartridge`, `insoles`, `jacket`
  `jeans`, `leggings`, `lego`, `makeup`, `mirror`, `nail_polish`, `nappies`, `necklace`
  `oil_filter`, `parasol`, `perfume`, `phone_case`, `pillow`, `pool`, `printer_paper`, `pyjamas`
  `raincoat`, `razor_blades`, `ring`, `rug`, `sandals`, `screen_protector`, `shirt`, `shoes`
  `shorts`, `skirt`, `slippers`, `snow_chains`, `socks`, `spark_plugs`, `suit`, `sunglasses`
  `sweater`, `swimwear`, `t_shirt`, `toner`, `towels`, `toy`, `trousers`, `underwear`
  `wall_clock`, `wallet`, `watch`, `wiper_blades`

Three families, and the reason each is here:

- **Style and size**: clothing, fashion footwear, jewellery, worn accessories, home
  textiles and decoration. A dress, a ring, a tablecloth. Better does not apply.
- **Must match one thing**: an ink cartridge for one printer, a filter for one engine,
  a case for one phone, chains for one tyre size. The right one is the one that fits,
  so "best" is meaningless and a wrong pick is worse than a dear one.
- **Taste goods**: a scent, a shade, a colour, a toy. Not better or worse.

## `spec` -- a number decides, once a source supplies it

| Kind | Ranks on | Fits on | Why |
| --- | --- | --- | --- |
| `air_conditioner` | efficiency_class | power | efficiency decides; power must match the room |
| `car_battery` | battery | fitment | capacity decides; it must still fit |
| `dishwasher` | efficiency_class | capacity_l | efficiency decides |
| `e_bike` | playtime, battery | weight | range decides |
| `e_reader` | storage, battery | screen | storage and battery decide |
| `e_scooter` | playtime, battery | weight | range decides |
| `freezer` | efficiency_class | capacity_l | efficiency decides; litres are a choice |
| `game_console` | storage | — | storage decides |
| `headphones` | playtime, battery | frequency, impedance, weight | playtime decides |
| `heat_pump` | efficiency_class | power | efficiency decides |
| `laptop` | storage, battery | screen, weight | storage and battery decide; screen size is a choice |
| `lawn_mower` | playtime | width, power | runtime decides where it is cordless; cut width is a choice |
| `light_bulb` | efficiency_class | power | efficiency decides |
| `monitor` | efficiency_class | screen, resolution, frequency | inches are a choice |
| `power_bank` | battery | weight | mAh decides |
| `ram_memory` | storage | frequency | capacity decides |
| `refrigerator` | efficiency_class | capacity_l | efficiency decides; litres are a choice |
| `robot_mower` | playtime | size | runtime and the area it covers decide |
| `robot_vacuum` | playtime, battery | — | runtime decides |
| `smart_speaker` | playtime | power | playtime decides where it is portable |
| `smartphone` | storage, battery | screen | storage and battery decide; screen size is a choice |
| `storage_drive` | storage | size | capacity decides |
| `summer_tyres` | efficiency_class | fitment | the EU label decides; size must match |
| `tablet` | storage, battery | screen | storage and battery decide; screen size is a choice |
| `television` | efficiency_class | screen, resolution | inches are a choice, not a merit |
| `tumble_dryer` | efficiency_class | capacity_kg | efficiency decides; kilos are a choice |
| `tv_box` | storage | resolution | storage decides |
| `tyres` | efficiency_class | fitment | the EU label's wet grip and efficiency decide; size must match |
| `ups` | battery | power | backup time decides |
| `vacuum_cleaner` | playtime, efficiency_class | power | runtime decides where it is cordless |
| `washer_dryer` | efficiency_class | capacity_kg | efficiency decides; kilos are a choice |
| `washing_machine` | efficiency_class | capacity_kg | efficiency decides; kilos are a choice |
| `water_heater` | efficiency_class | capacity_l | efficiency decides |
| `winter_tyres` | efficiency_class | fitment | the EU label decides; size must match |

Note what is deliberately **not** a ranking criterion anywhere above: inches, kilos,
litres, metres, watts and resolution. Every one of them is a size or a fit.

## `rating` -- quality is real, no feed number measures it

Tools, appliances, cookware, cosmetics with a function, baby equipment, performance
footwear, bags built for a job, audio and camera gear. A drill really can be better
than another drill; nothing in any product feed says which.

  `action_camera`, `air_compressor`, `air_fryer`, `air_purifier`, `amplifier`, `angle_grinder`, `athletic_shoes`, `baby_bottle`
  `baby_carrier`, `baby_monitor`, `baby_stroller`, `backpack`, `bathroom_scale`, `bed`, `bicycle`, `bicycle_helmet`
  `bike_lock`, `blender`, `blood_pressure_monitor`, `breast_pump`, `brush_cutter`, `camera`, `car_audio`, `cat_food`
  `cat_litter`, `chainsaw`, `chair`, `child_car_seat`, `circular_saw`, `coffee_machine`, `cooker`, `cookware`
  `coolant`, `cot`, `cutlery`, `dash_cam`, `deep_fryer`, `dehumidifier`, `deodorant`, `desk`
  `desktop_pc`, `dishwasher_tablets`, `docking_station`, `dog_food`, `drill`, `drone`, `dumbbells`, `electric_shaver`
  `electric_toothbrush`, `engine_oil`, `epilator`, `exercise_bike`, `face_cream`, `face_mask`, `fan`, `food_processor`
  `football`, `game_controller`, `garden_hose`, `garden_sprayer`, `glucose_meter`, `gps_navigator`, `graphics_card`, `grill`
  `hair_brush`, `hair_clipper`, `hair_dryer`, `hair_straightener`, `hammer`, `hand_blender`, `hand_saw`, `hearing_aid`
  `heat_gun`, `heater`, `hedge_trimmer`, `helmet`, `high_chair`, `hiking_boots`, `hob`, `impact_driver`
  `iron`, `jigsaw`, `juicer`, `kettle`, `kettlebell`, `keyboard`, `kitchen_scale`, `knife_set`
  `ladder`, `lamp`, `laptop_bag`, `laundry_detergent`, `leaf_blower`, `massager`, `mattress`, `microphone`
  `microwave`, `mitre_saw`, `mixer`, `motherboard`, `moto_helmet`, `mouse`, `multi_tool`, `multimeter`
  `nail_gun`, `office_chair`, `oven`, `paint`, `pc_case`, `pet_carrier`, `phone_charger`, `pliers`
  `power_supply`, `pressure_cooker`, `pressure_washer`, `printer`, `processor`, `projector`, `pulse_oximeter`, `rotary_hammer`
  `router`, `running_shoes`, `safety_shoes`, `safety_vest`, `sander`, `scanner`, `scooter`, `screwdriver`
  `screwdriver_set`, `selfie_stick`, `shampoo`, `shelving`, `sleeping_bag`, `smart_plug`, `smartwatch`, `smoke_detector`
  `socket_set`, `sofa`, `soldering_iron`, `soundbar`, `spanner`, `speaker`, `spirit_level`, `steam_mop`
  `suitcase`, `sunscreen`, `table`, `tap`, `tape_measure`, `tent`, `thermometer`, `tiller`
  `toaster`, `tool_box`, `treadmill`, `utility_knife`, `vr_headset`, `wardrobe`, `water_filter_jug`, `water_pump`
  `webcam`, `weight_bench`, `welder`, `wheelchair`, `wireless_charger`, `work_gloves`, `work_trousers`, `yoga_mat`

## Borderline, and the owner's call

These are the ones where the judgement could go either way. They are listed so they
can be moved with one word, rather than defended:

- **Furniture**: `bed`, `mattress`, `sofa`, `chair`, `desk`, `table`, `wardrobe`,
  `shelving`. Placed in `rating`, because a mattress and a chair have real quality.
  But much of the choice is size and taste, so they may belong in `fit`.
- **`lamp`, `paint`**: placed in `rating` for build quality and coverage, but a lamp is
  mostly design and paint is mostly colour.
- **Performance footwear and bags**: `running_shoes`, `athletic_shoes`, `hiking_boots`,
  `safety_shoes`, `backpack`, `laptop_bag`, `suitcase` are in `rating`, separated from
  their fashion twins `shoes`, `boots`, `sandals`, `bag`, `handbag` in `fit`. The
  owner said there is no best pair of shoes; this keeps that true for fashion footwear
  while letting a safety boot be judged on the standard it meets.
- **`watch`** is in `fit` as jewellery, while `smartwatch` is in `rating`.

## What is missing from the taxonomy itself

The owner's fourth example was wine, and it has no place to go: **wine, food and drink
are not among the eighteen mega-categories**, and neither are home textiles as a
department. The first real feed is full of both -- 899 table runners and placemats,
and whole shops of wine and flowers from the earlier feed. A kind PicWise does not
recognise falls to `rating` by default, which would let it claim a best on a
tablecloth. The eighteen mega-categories are locked architecture, so extending them is
the owner's decision, not this module's.
