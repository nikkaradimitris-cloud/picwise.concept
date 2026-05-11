# PickWise Stage 23A: 18 Mega-Category Coverage Blueprint

This document defines the Stage 23A coverage planning layer for PickWise.

It is a **coverage blueprint**, not completed deep taxonomy population.

## Locked architecture context

- Architecture lock from Stage 22B remains unchanged.
- PickWise structure is fixed at **6 engines** and **18 mega-categories**.
- Stage 23A describes what must exist next so each mega-category can behave like a full vertical search universe.

## Expansion model (future deep packs)

Each mega-category will later expand through:

`engine -> mega-category -> departments -> subcategories -> product families -> aliases/Greeklish/typos -> specs/priorities/intent patterns`

Stage 23A provides deterministic seeds for each layer, but does not claim that deep packs are complete.

## Current Local NLU limitation (explicit)

Current Local NLU has deep-ish proof only for:

- `car_tyres`
- `calculators`
- `power_banks`
- `chargers`
- `ambiguous`
- `unknown`

This must **not** be interpreted as full taxonomy depth across all mega-categories.

## 18 mega-categories and expansion direction

### Home / Living / Appliances engine

- `home_appliances_laundry_climate`: expand to major appliances, laundry systems, climate control, floor care, appliance specs, and lifecycle priorities.
- `kitchen_cooking_household`: expand to small appliances, cookware workflows, food-prep ecosystems, household care, and routine intent patterns.
- `furniture_living_storage_smart_home`: expand to room systems, storage architecture, smart-home interoperability, and living-space optimization intents.

### Tech / Electronics / Office engine

- `phones_mobile_accessories`: expand to mobile compute, charging ecosystems, accessory compatibility, and mobility-first decision patterns.
- `computers_office_peripherals`: expand to workstation stacks, printing/networking layers, office calculators, and productivity fit priorities.
- `audio_video_gaming_cameras`: expand to media systems, gaming setups, creator capture workflows, and compatibility-heavy specs.

### Auto / Moto / Mobility engine

- `car_parts_service_maintenance`: expand to service timelines, fitment-sensitive parts, maintenance schemas, and safety-critical priorities.
- `tyres_wheels_car_accessories`: expand to tyre fitment, wheel standards, seasonal driving contexts, and accessory utility layers.
- `moto_bicycle_mobility_gear`: expand to rider safety gear, bike/moto components, commute workflows, and mobility support patterns.

### Tools / DIY / Garden / Repair engine

- `power_tools_workshop`: expand to cordless platforms, workshop machines, dust/safety systems, and trade workflow intents.
- `hand_tools_consumables_measuring`: expand to manual tooling depth, consumable chains, precision measurement schemas, and repair sequencing.
- `garden_outdoor_repair_building`: expand to outdoor maintenance, irrigation, building repair materials, and seasonal property-care planning.

### Health / Beauty / Family / Lifestyle engine

- `health_wellness_safety_devices`: expand to home wellness devices, preventive monitoring, safety detectors, and responsible support intents.
- `beauty_grooming_personal_care`: expand to skincare/haircare/grooming routines, compatibility schemas, and daily routine optimization.
- `baby_kids_pets_sports_outdoor`: expand to family lifecycle needs, pet care systems, sports/outdoor workflows, and active lifestyle bundles.

### Fashion / Footwear / Jewelry / Accessories engine

- `clothing_apparel_workwear`: expand to full apparel systems, workwear compliance paths, fit taxonomies, and seasonal wardrobe planning.
- `footwear_shoes_sneakers_boots`: expand to activity-based footwear depth, fit/traction schema layers, and weather/use-case priorities.
- `jewelry_watches_bags_fashion_accessories`: expand to complete accessory ecosystems, style/utility balancing, and occasion-driven intent maps.

## Stage 23A boundary

- This stage adds planning coverage only.
- It does not generate inventory, offers, prices, or affiliate links.
- It does not add live LLM/API calls.
- It does not modify app/router/Decision Machine behavior.

## Next step after Stage 23A

The next milestone should be **deep expansion packs per mega-category**, not UI work.
