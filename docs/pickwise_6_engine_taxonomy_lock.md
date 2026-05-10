# PickWise Stage 22B: 6-Engine Taxonomy Lock

This document defines the Stage 22B architecture lock for PickWise taxonomy.

## Scope

- This stage defines top-level taxonomy architecture only.
- This stage does not populate full product inventory or offer data.
- Registry shape is deterministic and JSON-serializable for downstream expansion.

## 6 Search Engines

1. `home_living_appliances_engine`
2. `tech_electronics_office_engine`
3. `auto_moto_mobility_engine`
4. `tools_diy_garden_repair_engine`
5. `health_beauty_family_lifestyle_engine`
6. `fashion_footwear_jewelry_accessories_engine`

## 18 Mega-Categories (3 per engine)

- `home_living_appliances_engine`
  - `home_appliances_laundry_climate`
  - `kitchen_cooking_household`
  - `furniture_living_storage_smart_home`
- `tech_electronics_office_engine`
  - `phones_mobile_accessories`
  - `computers_office_peripherals`
  - `audio_video_gaming_cameras`
- `auto_moto_mobility_engine`
  - `car_parts_service_maintenance`
  - `tyres_wheels_car_accessories`
  - `moto_bicycle_mobility_gear`
- `tools_diy_garden_repair_engine`
  - `power_tools_workshop`
  - `hand_tools_consumables_measuring`
  - `garden_outdoor_repair_building`
- `health_beauty_family_lifestyle_engine`
  - `health_wellness_safety_devices`
  - `beauty_grooming_personal_care`
  - `baby_kids_pets_sports_outdoor`
- `fashion_footwear_jewelry_accessories_engine`
  - `clothing_apparel_workwear`
  - `footwear_shoes_sneakers_boots`
  - `jewelry_watches_bags_fashion_accessories`

## Why fashion is a dedicated engine

Fashion has distinct discovery behavior, vocabulary, fit intents, style cycles, and accessory adjacency. Keeping it as a dedicated engine protects long-term taxonomy depth and avoids burying fashion under unrelated domains.

## Planned expansion path

Future stages can expand this stable top-level lock using:

`engine -> mega-category -> department -> subcategory -> product family -> aliases/specs/intents`
