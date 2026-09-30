"""Product concept lexicon: what kind of product a buyer means, in English and Greek.

A concept is one kind of product -- "washing machine" -- with every ordinary name a
buyer or a feed uses for it, in English and in Greek, singular and plural. Each concept
belongs to exactly one mega category of the taxonomy deep packs, so the product rules
of that category (its `spec_fields` and `buying_priorities`) apply to it.

The lexicon holds only correctly spelled dictionary names. Misspellings, greeklish and
wrong-keyboard-layout text are recognised by `picwise_nlu.concept_understanding`, which
compares what the buyer typed against these names by sound and by edit distance. Listing
typo forms here would mean the system can only understand the mistakes someone thought
to write down.

`broader` links a narrower concept to the more general one it is a kind of: a robot
vacuum is a vacuum cleaner, a bicycle helmet is a helmet. A buyer who asks for a helmet
can be answered with bicycle helmets; a buyer who asks for a bicycle helmet cannot be
answered with motorcycle helmets.

Forms that carry a buyer's preference ("wireless mouse", "cordless drill") are left out
on purpose: the preference must stay a filter the inventory is checked against, not be
absorbed into the product name.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

_MEGA = {
    "HA": "home_appliances_laundry_climate",
    "KI": "kitchen_cooking_household",
    "FU": "furniture_living_storage_smart_home",
    "PH": "phones_mobile_accessories",
    "CO": "computers_office_peripherals",
    "AV": "audio_video_gaming_cameras",
    "CP": "car_parts_service_maintenance",
    "TY": "tyres_wheels_car_accessories",
    "MO": "moto_bicycle_mobility_gear",
    "PT": "power_tools_workshop",
    "HT": "hand_tools_consumables_measuring",
    "GA": "garden_outdoor_repair_building",
    "HE": "health_wellness_safety_devices",
    "BE": "beauty_grooming_personal_care",
    "BK": "baby_kids_pets_sports_outdoor",
    "CL": "clothing_apparel_workwear",
    "FO": "footwear_shoes_sneakers_boots",
    "JW": "jewelry_watches_bags_fashion_accessories",
}


@dataclass(frozen=True)
class ProductConcept:
    concept_id: str
    mega_category_id: str
    english: tuple[str, ...]
    greek: tuple[str, ...]
    broader: tuple[str, ...] = ()

    @property
    def primary_english(self) -> str:
        return self.english[0] if self.english else ""


# concept id | mega | broader | English names | Greek names
_CONCEPT_TABLE = """
washing_machine|HA||washing machine,washing machines,washer,washers|πλυντήριο ρούχων,πλυντήρια ρούχων,πλυντήριο,πλυντήρια
tumble_dryer|HA||tumble dryer,tumble dryers,clothes dryer,clothes dryers|στεγνωτήριο,στεγνωτήρια,στεγνωτήριο ρούχων,στεγνωτήρια ρούχων
washer_dryer|HA||washer dryer,washer dryers|πλυντήριο στεγνωτήριο,πλυντήρια στεγνωτήρια,πλυντηριοστεγνωτήριο
dishwasher|HA||dishwasher,dishwashers|πλυντήριο πιάτων,πλυντήρια πιάτων
refrigerator|HA||fridge,fridges,refrigerator,refrigerators,fridge freezer,fridge freezers|ψυγείο,ψυγεία,ψυγειοκαταψύκτης,ψυγειοκαταψύκτες
freezer|HA||freezer,freezers,chest freezer,chest freezers|καταψύκτης,καταψύκτες
air_conditioner|HA||air conditioner,air conditioners,air conditioning unit,aircon|κλιματιστικό,κλιματιστικά
dehumidifier|HA||dehumidifier,dehumidifiers|αφυγραντήρας,αφυγραντήρες
air_purifier|HA||air purifier,air purifiers|καθαριστής αέρα,καθαριστές αέρα,ιονιστής
heater|HA||heater,heaters,electric heater,radiator heater|θερμάστρα,θερμάστρες,καλοριφέρ λαδιού,αερόθερμο
fan|HA||fan,fans,electric fan,tower fan,ceiling fan|ανεμιστήρας,ανεμιστήρες
heat_pump|HA||heat pump,heat pumps|αντλία θερμότητας,αντλίες θερμότητας
water_heater|HA||water heater,water heaters,boiler,immersion heater|θερμοσίφωνας,θερμοσίφωνες,ηλιακός θερμοσίφωνας,λέβητας
vacuum_cleaner|HA||vacuum cleaner,vacuum cleaners,vacuum,vacuums,hoover|ηλεκτρική σκούπα,ηλεκτρικές σκούπες,σκούπα,σκούπες
robot_vacuum|HA|vacuum_cleaner|robot vacuum,robot vacuums,robot vacuum cleaner,robot vacuum cleaners,robotic vacuum|σκούπα ρομπότ,σκούπες ρομπότ,ρομπότ σκούπα
steam_mop|HA||steam mop,steam cleaner,steam cleaners|ατμοκαθαριστής,σφουγγαρίστρα ατμού
iron|HA||iron,steam iron,clothes iron,steam generator iron|σίδερο,σίδερα,σίδερο ατμού,σύστημα σιδερώματος
coffee_machine|KI||coffee machine,coffee machines,coffee maker,coffee makers,espresso machine,espresso machines|καφετιέρα,καφετιέρες,μηχανή καφέ,μηχανές καφέ,μηχανή εσπρέσο,καφετιέρα φίλτρου
microwave|KI||microwave,microwaves,microwave oven,microwave ovens|φούρνος μικροκυμάτων,φούρνοι μικροκυμάτων,μικροκύματα
oven|KI||oven,ovens,built in oven|φούρνος,φούρνοι,εντοιχιζόμενος φούρνος
cooker|KI||cooker,cookers,stove,range cooker|κουζίνα,κουζίνες,ηλεκτρική κουζίνα,ηλεκτρικές κουζίνες
hob|KI||hob,hobs,cooktop,induction hob|εστία,εστίες,επαγωγική εστία
air_fryer|KI||air fryer,air fryers|φριτέζα αέρος,φριτέζες αέρος,φριτέζα αέρα,φριτέζα χωρίς λάδι
deep_fryer|KI||deep fryer,deep fryers|φριτέζα,φριτέζες
mixer|KI||mixer,mixers,stand mixer,hand mixer|μίξερ,κουζινομηχανή,κουζινομηχανές
hand_blender|KI||hand blender,immersion blender,stick blender|μίνι πίμερ,ραβδομπλέντερ
blender|KI||blender,blenders|μπλέντερ
food_processor|KI||food processor,food processors|πολυμίξερ,multi
toaster|KI||toaster,toasters,sandwich maker,sandwich toaster|τοστιέρα,τοστιέρες,φρυγανιέρα
kettle|KI||kettle,kettles,electric kettle|βραστήρας,βραστήρες
juicer|KI||juicer,juicers,citrus press|αποχυμωτής,αποχυμωτές,στίφτης
cookware|KI||frying pan,frying pans,pan,pans,pot,pots,cookware set|τηγάνι,τηγάνια,κατσαρόλα,κατσαρόλες,σετ μαγειρικών σκευών
pressure_cooker|KI||pressure cooker,pressure cookers|χύτρα ταχύτητας,χύτρες ταχύτητας,χύτρα
kitchen_scale|KI||kitchen scale,kitchen scales|ζυγαριά κουζίνας
office_chair|FU|chair|office chair,office chairs,computer chair,computer chairs,desk chair,gaming chair,gaming chairs|καρέκλα γραφείου,καρέκλες γραφείου,καρέκλα υπολογιστή,πολυθρόνα γραφείου
chair|FU||chair,chairs|καρέκλα,καρέκλες
desk|FU||desk,desks,computer desk,office desk,standing desk|γραφείο υπολογιστή,γραφεία υπολογιστή,γραφείο,γραφεία
sofa|FU||sofa,sofas,couch,settee|καναπές,καναπέδες
bed|FU||bed,beds,bed frame|κρεβάτι,κρεβάτια
mattress|FU||mattress,mattresses|στρώμα,στρώματα
wardrobe|FU||wardrobe,wardrobes|ντουλάπα,ντουλάπες
shelving|FU||bookcase,bookcases,shelf,shelves,shelving unit|βιβλιοθήκη,βιβλιοθήκες,ραφιέρα,ράφι,ράφια
table|FU||table,tables,dining table,coffee table|τραπέζι,τραπέζια,τραπεζάκι,τραπεζαρία
lamp|FU||lamp,lamps,desk lamp,floor lamp,ceiling light,light fitting|φωτιστικό,φωτιστικά,πορτατίφ,φωτιστικό οροφής
light_bulb|FU||light bulb,light bulbs,led bulb,smart bulb|λάμπα,λάμπες,λαμπτήρας,λαμπτήρες
smart_plug|FU||smart plug,smart plugs|έξυπνη πρίζα,έξυπνες πρίζες
smartphone|PH||smartphone,smartphones,mobile phone,mobile phones,cell phone,phone,phones|κινητό,κινητά,κινητό τηλέφωνο,κινητά τηλέφωνα,τηλέφωνο
power_bank|PH||power bank,power banks,powerbank,portable charger,external battery|εξωτερική μπαταρία,εξωτερικές μπαταρίες,φορητή μπαταρία,φορητός φορτιστής,πάουερ μπανκ
phone_charger|PH||charger,chargers,phone charger,wall charger,usb charger|φορτιστής,φορτιστές,φορτιστής κινητού
wireless_charger|PH|phone_charger|wireless charger,wireless chargers,charging pad|ασύρματος φορτιστής,ασύρματοι φορτιστές
charging_cable|PH||charging cable,usb cable,cable,cables,usb c cable,lightning cable|καλώδιο φόρτισης,καλώδιο,καλώδια
phone_case|PH||phone case,phone cases,case,cover,phone cover|θήκη κινητού,θήκες κινητού,θήκη,θήκες
screen_protector|PH||screen protector,screen protectors,tempered glass|προστασία οθόνης,προστατευτικό οθόνης,τζαμάκι
car_phone_holder|PH||car phone holder,car phone mount,phone holder|βάση κινητού αυτοκινήτου,βάση κινητού
smartwatch|PH|watch|smartwatch,smartwatches,smart watch,fitness tracker,fitness trackers|έξυπνο ρολόι,έξυπνα ρολόγια
laptop|CO||laptop,laptops,notebook computer,notebook computers|λάπτοπ,φορητός υπολογιστής,φορητοί υπολογιστές,φορητό
desktop_pc|CO||desktop pc,desktop pcs,desktop computer,desktop computers,desktop,pc|υπολογιστής,υπολογιστές,σταθερός υπολογιστής,κομπιούτερ
monitor|CO||monitor,monitors,computer monitor,computer monitors,pc monitor,screen|οθόνη υπολογιστή,οθόνες υπολογιστή,οθόνη,οθόνες,μόνιτορ
printer|CO||printer,printers,multifunction printer,multifunction printers,all in one printer,laser printer,inkjet printer|εκτυπωτής,εκτυπωτές,πολυμηχάνημα,πολυμηχανήματα
toner|CO||toner,toners,toner cartridge,toner cartridges|τόνερ
ink_cartridge|CO||ink cartridge,ink cartridges,printer ink,ink|μελάνι,μελάνια,μελάνι εκτυπωτή,μελάνια εκτυπωτή,φυσίγγιο μελανιού,αμπούλα,αμπούλες
router|CO||router,routers,wifi router,modem|ρούτερ,μόντεμ
keyboard|CO||keyboard,keyboards|πληκτρολόγιο,πληκτρολόγια
mouse|CO||mouse,mice,computer mouse|ποντίκι,ποντίκια
webcam|CO||webcam,webcams,web camera,web cam|κάμερα υπολογιστή,κάμερες υπολογιστή,κάμερα web
scanner|CO||scanner,scanners,document scanner|σαρωτής,σαρωτές,σκάνερ
storage_drive|CO||external hard drive,hard drive,hard drives,ssd,usb stick,flash drive|σκληρός δίσκος,εξωτερικός σκληρός δίσκος,στικάκι,φλασάκι
docking_station|CO||docking station,usb hub|βάση σύνδεσης
television|AV||tv,tvs,television,televisions,smart tv|τηλεόραση,τηλεοράσεις
speaker|AV||speaker,speakers,bluetooth speaker,portable speaker|ηχείο,ηχεία
soundbar|AV||soundbar,soundbars,sound bar|μπάρα ήχου
headphones|AV||headphones,headphone,headset,headsets,earphones,earbuds|ακουστικά,ακουστικό,ακουστικά κεφαλής,ψείρες
game_console|AV||games console,game console,gaming console,games consoles,game consoles|κονσόλα,κονσόλες,κονσόλα παιχνιδιών
game_controller|AV||controller,controllers,gamepad,joystick|χειριστήριο,χειριστήρια
camera|AV||camera,cameras,digital camera,mirrorless camera,dslr|φωτογραφική μηχανή,φωτογραφικές μηχανές,κάμερα,κάμερες
action_camera|AV|camera|action camera,action cameras,action cam|κάμερα δράσης
microphone|AV||microphone,microphones,mic|μικρόφωνο,μικρόφωνα
projector|AV||projector,projectors|προτζέκτορας,βιντεοπροβολέας
amplifier|AV||amplifier,amplifiers,av receiver|ενισχυτής,ενισχυτές,ραδιοενισχυτής
engine_oil|CP||engine oil,motor oil,car oil|λάδι αυτοκινήτου,λάδια αυτοκινήτου,λάδι κινητήρα,λάδια κινητήρα
oil_filter|CP||oil filter,oil filters|φίλτρο λαδιού,φίλτρα λαδιού
air_filter|CP||engine air filter,air filter,air filters|φίλτρο αέρα,φίλτρα αέρα
cabin_filter|CP||cabin filter,cabin filters,pollen filter|φίλτρο καμπίνας,φίλτρα καμπίνας
car_battery|CP||car battery,car batteries,vehicle battery|μπαταρία αυτοκινήτου,μπαταρίες αυτοκινήτου
brake_pads|CP||brake pads,brake pad,brake discs,brake disc|τακάκια,τακάκια φρένων,δισκόπλακες,δισκόπλακα
wiper_blades|CP||wiper blades,wiper blade,wipers|υαλοκαθαριστήρες,υαλοκαθαριστήρας,μάκτρα
coolant|CP||coolant,antifreeze|αντιψυκτικό,ψυκτικό υγρό
spark_plugs|CP||spark plug,spark plugs|μπουζί
tyres|TY||tyre,tyres,tire,tires,car tyres|λάστιχα,λάστιχο,λάστιχα αυτοκινήτου,ελαστικά,ελαστικό,ελαστικά αυτοκινήτου
winter_tyres|TY|tyres|winter tyres,winter tires,snow tyres|χειμερινά λάστιχα,λάστιχα χειμερινά,χειμερινά ελαστικά,ελαστικά χειμερινά
summer_tyres|TY|tyres|summer tyres,summer tires|καλοκαιρινά λάστιχα,λάστιχα καλοκαιρινά,θερινά ελαστικά
alloy_wheels|TY||alloy wheels,alloy wheel,rims|ζάντες,ζάντα,ζάντες αλουμινίου
dash_cam|TY||dash cam,dash cams,dashcam,car camera|κάμερα αυτοκινήτου,κάμερες αυτοκινήτου
child_car_seat|TY||child car seat,child car seats,car seat,baby car seat,booster seat|παιδικό κάθισμα,παιδικά καθίσματα,κάθισμα αυτοκινήτου,παιδικό κάθισμα αυτοκινήτου
snow_chains|TY||snow chains,tyre chains|αλυσίδες χιονιού,αλυσίδες
bicycle|MO||bicycle,bicycles,bike,bikes,city bike,mountain bike,mountain bikes|ποδήλατο,ποδήλατα,ποδήλατο πόλης,ποδήλατο βουνού
e_bike|MO|bicycle|electric bike,electric bikes,electric bicycle,e bike,ebike|ηλεκτρικό ποδήλατο,ηλεκτρικά ποδήλατα
helmet|MO||helmet,helmets|κράνος,κράνη
bicycle_helmet|MO|helmet|bicycle helmet,bicycle helmets,bike helmet,bike helmets,cycling helmet|κράνος ποδηλάτου,κράνη ποδηλάτου
moto_helmet|MO|helmet|motorcycle helmet,motorcycle helmets,motorbike helmet,moto helmet|κράνος μηχανής,κράνη μηχανής,κράνος μοτοσυκλέτας
scooter|MO||scooter,scooters,kick scooter|πατίνι,πατίνια
e_scooter|MO|scooter|electric scooter,electric scooters,e scooter|ηλεκτρικό πατίνι,ηλεκτρικά πατίνια
bike_lock|MO||bike lock,bike locks,bicycle lock|κλειδαριά ποδηλάτου,λουκέτο ποδηλάτου
drill|PT||drill,drills,power drill,power drills,drill driver,combi drill,impact drill,hammer drill|δράπανο,δράπανα,δραπανοκατσάβιδο,κρουστικό δράπανο
rotary_hammer|PT||rotary hammer,rotary hammers,sds drill,demolition hammer|πιστολέτο,πιστολέτα,κατεδαφιστικό
impact_driver|PT||impact driver,impact drivers|παλμικό κατσαβίδι
angle_grinder|PT||angle grinder,angle grinders,grinder|τροχός,τροχοί,γωνιακός τροχός
circular_saw|PT||circular saw,circular saws|δισκοπρίονο,δισκοπρίονα
jigsaw|PT||jigsaw,jigsaws|σέγα,σέγες
mitre_saw|PT||mitre saw,miter saw,mitre saws|φαλτσοπρίονο
sander|PT||sander,sanders,orbital sander,belt sander|τριβείο,τριβεία
heat_gun|PT||heat gun,heat guns|πιστόλι θερμού αέρα
air_compressor|PT||air compressor,air compressors,compressor|αεροσυμπιεστής,αεροσυμπιεστές,κομπρεσέρ
multi_tool|PT||oscillating multi tool,multi tool,multitool|πολυεργαλείο
nail_gun|PT||nail gun,nailer,staple gun|καρφωτικό,καρφωτικά
welder|PT||welder,welding machine|ηλεκτροκόλληση,ηλεκτροκολλήσεις
screwdriver|HT||screwdriver,screwdrivers|κατσαβίδι
screwdriver_set|HT|screwdriver|screwdriver set,screwdriver sets|σετ κατσαβίδια,σετ κατσαβιδιών,κατσαβίδια
socket_set|HT||socket set,socket sets,ratchet set|καρυδάκια,σετ καρυδάκια,κασετίνα καρυδάκια
spanner|HT||spanner,spanners,wrench,wrenches,torque wrench|γερμανοπολύγωνο,γερμανοπολύγωνα,γαλλικό κλειδί,δυναμόκλειδο
pliers|HT||pliers|πένσα,πένσες,μυτοτσίμπιδο
hammer|HT||hammer,hammers|σφυρί,σφυριά
tape_measure|HT||tape measure,measuring tape|μετροταινία
spirit_level|HT||spirit level,laser level|αλφάδι,αλφάδια
utility_knife|HT||utility knife,cutter knife|κοπίδι,κοπίδια
drill_bits|HT||drill bits,drill bit set|τρυπάνια,τρυπάνι,μύτες δραπάνου
tool_box|HT||tool box,toolbox,tool case|εργαλειοθήκη,εργαλειοθήκες
multimeter|HT||multimeter,multimeters|πολύμετρο
soldering_iron|HT||soldering iron|κολλητήρι
hand_saw|HT||hand saw,hand saws|πριόνι,πριόνια
work_gloves|HT|gloves|work gloves|γάντια εργασίας
lawn_mower|GA||lawn mower,lawn mowers,lawnmower,mower|χλοοκοπτικό,χλοοκοπτικά,μηχανή γκαζόν
robot_mower|GA|lawn_mower|robotic lawn mower,robot mower,robot lawn mower|ρομποτικό χλοοκοπτικό
brush_cutter|GA||brush cutter,brush cutters,strimmer,grass trimmer,line trimmer|θαμνοκοπτικό,θαμνοκοπτικά,χορτοκοπτικό
hedge_trimmer|GA||hedge trimmer,hedge trimmers|μπορντουροψάλιδο
chainsaw|GA||chainsaw,chainsaws,chain saw|αλυσοπρίονο,αλυσοπρίονα
leaf_blower|GA||leaf blower,leaf blowers|φυσητήρας,φυσητήρες
pressure_washer|GA||pressure washer,pressure washers,jet washer|πλυστικό,πλυστικό μηχάνημα,πλυστικά
garden_hose|GA||garden hose,garden hoses,hose|λάστιχο ποτίσματος,λάστιχο κήπου
water_pump|GA||water pump,garden pump,submersible pump|αντλία νερού,αντλία,αντλίες
tiller|GA||tiller,tillers,cultivator|σκαπτικό,φρέζα,καλλιεργητής
ladder|GA||ladder,ladders,step ladder,telescopic ladder|σκάλα,σκάλες,τηλεσκοπική σκάλα
garden_sprayer|GA||garden sprayer,sprayer|ψεκαστήρας,ψεκαστήρες
paint|GA||paint,wall paint,primer|χρώμα τοίχου,μπογιά,αστάρι
tap|GA||tap,taps,faucet,mixer tap|βρύση,βρύσες,μπαταρία νιπτήρα,μπαταρία κουζίνας
blood_pressure_monitor|HE||blood pressure monitor,blood pressure monitors,bp monitor|πιεσόμετρο,πιεσόμετρα,μετρητής πίεσης
thermometer|HE||thermometer,thermometers|θερμόμετρο,θερμόμετρα
pulse_oximeter|HE||pulse oximeter,oximeter|οξύμετρο,παλμικό οξύμετρο
smoke_detector|HE||smoke detector,smoke alarm,carbon monoxide detector|ανιχνευτής καπνού,ανιχνευτής μονοξειδίου
bathroom_scale|HE||bathroom scale,bathroom scales,body scale|ζυγαριά μπάνιου,ζυγαριά
massager|HE||massager,massage gun|συσκευή μασάζ
glucose_meter|HE||glucose meter,blood glucose meter|μετρητής σακχάρου,σακχαρόμετρο
electric_shaver|BE||electric shaver,electric shavers,shaver,shavers,razor|ξυριστική μηχανή,ξυριστικές μηχανές,ξυριστική
hair_clipper|BE||hair clipper,hair clippers,beard trimmer,trimmer|κουρευτική μηχανή,κουρευτική
hair_dryer|BE||hair dryer,hair dryers,hairdryer|πιστολάκι,πιστολάκι μαλλιών,σεσουάρ
hair_straightener|BE||hair straightener,hair straighteners,flat iron|ισιωτική,ισιωτική μαλλιών,πρέσα μαλλιών
electric_toothbrush|BE||electric toothbrush,electric toothbrushes|ηλεκτρική οδοντόβουρτσα
epilator|BE||epilator,epilators|αποτριχωτική μηχανή
shampoo|BE||shampoo,shampoos|σαμπουάν
face_cream|BE||face cream,moisturiser,moisturizer|κρέμα προσώπου,ενυδατική κρέμα
perfume|BE||perfume,perfumes,fragrance|άρωμα,αρώματα
sunscreen|BE||sunscreen,sun cream|αντηλιακό,αντηλιακά
baby_stroller|BK||stroller,strollers,baby stroller,baby strollers,pushchair,pram,buggy|καρότσι μωρού,καροτσάκι μωρού,καρότσι,καροτσάκι
baby_carrier|BK||baby carrier,baby carriers|μάρσιπος
high_chair|BK||high chair,high chairs|καρεκλάκι φαγητού
baby_monitor|BK||baby monitor,baby monitors|ενδοεπικοινωνία μωρού
cot|BK||cot,cots,crib,travel cot|κούνια μωρού,κούνια,παρκοκρέβατο
nappies|BK||nappies,diapers|πάνες,πάνες μωρού
toy|BK||toy,toys|παιχνίδι,παιχνίδια
dog_food|BK||dog food|τροφή σκύλου,τροφή για σκύλους
cat_food|BK||cat food|τροφή γάτας,τροφή για γάτες
treadmill|BK||treadmill,treadmills|διάδρομος γυμναστικής,διάδρομος
exercise_bike|BK||exercise bike,exercise bikes|στατικό ποδήλατο
dumbbells|BK||dumbbells,dumbbell|αλτήρες,βαράκια
yoga_mat|BK||yoga mat,exercise mat|στρώμα γιόγκα,στρωματάκι γυμναστικής
tent|BK||tent,tents|σκηνή,σκηνές
sleeping_bag|BK||sleeping bag,sleeping bags|υπνόσακος,υπνόσακοι
trousers|CL||trousers,pants,chinos,cargo trousers|παντελόνι,παντελόνια
work_trousers|CL|trousers|work trousers,work pants|παντελόνι εργασίας,παντελόνια εργασίας
jeans|CL||jeans|τζιν
jacket|CL||jacket,jackets,coat,coats|μπουφάν,παλτό,μπουφάν χειμερινό
t_shirt|CL||t shirt,t shirts,tshirt,tee|μπλουζάκι,μπλουζάκια,κοντομάνικο,μπλούζα
shirt|CL||shirt,shirts|πουκάμισο,πουκάμισα
hoodie|CL||hoodie,hoodies,sweatshirt|φούτερ
sweater|CL||sweater,sweaters,jumper,cardigan|πουλόβερ,ζακέτα
dress|CL||dress,dresses|φόρεμα,φορέματα
skirt|CL||skirt,skirts|φούστα,φούστες
shorts|CL||shorts|σορτς,βερμούδα
leggings|CL||leggings|κολάν
underwear|CL||underwear,boxers,briefs|εσώρουχα,μπόξερ,σλιπ
socks|CL||socks|κάλτσες
swimwear|CL||swimwear,swimsuit,swim shorts,bikini|μαγιό
pyjamas|CL||pyjamas,pajamas|πιτζάμες
suit|CL||suit,suits|κοστούμι,κουστούμι
safety_vest|CL||hi vis vest,safety vest|γιλέκο ασφαλείας
raincoat|CL||raincoat,rain jacket|αδιάβροχο
shoes|FO||shoes,shoe|παπούτσια,παπούτσι
athletic_shoes|FO|shoes|athletic shoes,sneakers,trainers,sports shoes|αθλητικά παπούτσια,αθλητικά
running_shoes|FO|athletic_shoes|running shoes,running shoe,running trainers|παπούτσια τρεξίματος,παπούτσια για τρέξιμο,αθλητικά παπούτσια για τρέξιμο
boots|FO|shoes|boots,ankle boots|μπότες,μποτάκια
hiking_boots|FO|boots|hiking boots,hiking shoes|ορειβατικά παπούτσια,ορειβατικά μποτάκια,ορειβατικά
safety_shoes|FO|shoes|safety shoes,safety boots,work shoes,work boots|παπούτσια εργασίας,παπούτσια ασφαλείας
sandals|FO|shoes|sandals|σανδάλια,πέδιλα
slippers|FO|shoes|slippers,flip flops|παντόφλες,σαγιονάρες
insoles|FO||insoles|πάτοι,ανατομικοί πάτοι
watch|JW||watch,watches,wristwatch,wristwatches|ρολόι,ρολόγια,ρολόι χειρός,ρολόγια χειρός
ring|JW||ring,rings|δαχτυλίδι,δαχτυλίδια
necklace|JW||necklace,necklaces,pendant|κολιέ,μενταγιόν
bracelet|JW||bracelet,bracelets|βραχιόλι,βραχιόλια
earrings|JW||earrings|σκουλαρίκια,σκουλαρίκι
sunglasses|JW||sunglasses|γυαλιά ηλίου
bag|JW||bag,bags|τσάντα,τσάντες
backpack|JW|bag|backpack,backpacks,rucksack|σακίδιο,σακίδιο πλάτης,τσάντα πλάτης
laptop_bag|JW|bag|laptop bag,laptop bags,laptop case,laptop cases,laptop sleeve|τσάντα laptop,τσάντα λάπτοπ,θήκη laptop,θήκη λάπτοπ
handbag|JW|bag|handbag,handbags,shoulder bag,crossbody bag,tote bag|τσάντα χειρός,τσάντα ώμου
suitcase|JW||suitcase,suitcases,luggage|βαλίτσα,βαλίτσες
wallet|JW||wallet,wallets,purse|πορτοφόλι,πορτοφόλια
belt|JW||belt,belts|ζώνη,ζώνες
hat|JW||hat,hats,cap,caps,beanie|καπέλο,καπέλα,σκούφος
gloves|JW||gloves|γάντια
"""


# Words that describe what the buyer wants from the product rather than what the
# product is. Each maps to the English word a feed uses for it, so a Greek preference
# can still filter an English feed. `None` means the word is understood but no feed
# text can confirm it (price and comfort are judgements, not attributes).
_QUALIFIER_TABLE = """
wireless|ασύρματο,ασύρματα,ασύρματος,ασύρματη,ασύρματες,ασύρματοι
kids|παιδικό,παιδικά,παιδικός,παιδική,παιδικές,για παιδιά
men|ανδρικό,ανδρικά,ανδρικός,ανδρική,αντρικό,αντρικά
women|γυναικείο,γυναικεία,γυναικείος,γυναικεία
electric|ηλεκτρικό,ηλεκτρικά,ηλεκτρικός,ηλεκτρική
cordless|μπαταρίας,επαναφορτιζόμενο,επαναφορτιζόμενο
inverter|inverter
portable|φορητό,φορητή,φορητός,φορητά
digital|ψηφιακό,ψηφιακή,ψηφιακός
gaming|gaming,παιχνιδιών
mechanical|μηχανικό,μηχανικό
ergonomic|εργονομική,εργονομικό,εργονομικός
quiet|αθόρυβο,αθόρυβη,αθόρυβος,ήσυχο
compact|μικρό,μικρή,μικρός
large|μεγάλο,μεγάλη,μεγάλος
black|μαύρο,μαύρη,μαύρος
white|λευκό,λευκή,άσπρο,άσπρη
leather|δερμάτινο,δερμάτινη,δερμάτινα
waterproof|αδιάβροχο,αδιάβροχη,αδιάβροχα
smart|έξυπνο,έξυπνη
petrol|βενζίνης,βενζινοκίνητο
upper arm|μπράτσου
wrist|καρπού
espresso|εσπρέσο
filter|φίλτρου
laser|λέιζερ
red|κόκκινο,κόκκινη,κόκκινος,κόκκινα
blue|μπλε
green|πράσινο,πράσινη,πράσινος,πράσινα
yellow|κίτρινο,κίτρινη,κίτρινος,κίτρινα
orange|πορτοκαλί
pink|ροζ
grey|γκρι
purple|μωβ
silver|ασημί,ασημένιο,ασημένια
gold|χρυσό,χρυσή,χρυσός,χρυσά
""".strip()

_JUDGEMENT_QUALIFIERS = (
    "φθηνό,φθηνή,φθηνός,φθηνά,φτηνό,φτηνή,φτηνός,οικονομικό,οικονομική,καλό,καλή,καλός,"
    "καλύτερο,καλύτερη,άνετο,άνετη,ποιοτικό,δυνατό,γρήγορο"
)


@dataclass(frozen=True)
class Qualifier:
    english: str | None
    greek: tuple[str, ...]


@lru_cache(maxsize=1)
def get_product_concepts() -> tuple[ProductConcept, ...]:
    concepts: list[ProductConcept] = []
    for line in _CONCEPT_TABLE.strip().splitlines():
        concept_id, mega, broader, english, greek = line.split("|")
        concepts.append(
            ProductConcept(
                concept_id=concept_id,
                mega_category_id=_MEGA[mega],
                english=tuple(form.strip() for form in english.split(",") if form.strip()),
                greek=tuple(form.strip() for form in greek.split(",") if form.strip()),
                broader=tuple(b for b in broader.split(",") if b),
            )
        )
    return tuple(concepts)


@lru_cache(maxsize=1)
def get_product_concepts_by_id() -> dict[str, ProductConcept]:
    return {concept.concept_id: concept for concept in get_product_concepts()}


def broader_concepts(concept_id: str) -> tuple[str, ...]:
    """The concept itself followed by every concept it is a kind of."""
    by_id = get_product_concepts_by_id()
    ordered: list[str] = []
    pending = [concept_id]
    while pending:
        current = pending.pop(0)
        if current in ordered or current not in by_id:
            continue
        ordered.append(current)
        pending.extend(by_id[current].broader)
    return tuple(ordered)


@lru_cache(maxsize=1)
def get_qualifiers() -> tuple[Qualifier, ...]:
    qualifiers = [
        Qualifier(
            english=english.strip(),
            greek=tuple(form.strip() for form in greek.split(",") if form.strip()),
        )
        for english, greek in (line.split("|") for line in _QUALIFIER_TABLE.splitlines())
    ]
    qualifiers.append(
        Qualifier(
            english=None,
            greek=tuple(form.strip() for form in _JUDGEMENT_QUALIFIERS.split(",") if form.strip()),
        )
    )
    return tuple(qualifiers)


@lru_cache(maxsize=32)
def spec_fields_for_mega_category(mega_category_id: str) -> tuple[str, ...]:
    """The product rules' spec fields for a mega category, read from the deep packs."""
    import importlib

    for name in (
        "home_living_appliances",
        "tech_electronics_office",
        "auto_moto_mobility",
        "tools_diy_garden_repair",
        "health_beauty_family_lifestyle",
        "fashion_footwear_jewelry_accessories",
    ):
        try:
            module = importlib.import_module(f"picwise_taxonomy.deep_packs.{name}")
            pack = getattr(module, f"get_{name}_pack")()
        except (ImportError, AttributeError):
            continue
        for record in pack.get("mega_categories", []):
            if record.get("mega_category_id") == mega_category_id:
                return tuple(record.get("spec_fields") or ())
    return tuple()
