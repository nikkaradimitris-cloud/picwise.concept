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
    # Names marked "~" in the table: read when a buyer types them, never trusted to
    # say what a feed product is. See `weak_forms` below.
    weak: tuple[str, ...] = ()

    @property
    def primary_english(self) -> str:
        return self.english[0] if self.english else ""


# A name written "~word" is a **weak form**: a real name of the product that is also
# an ordinary word in other products' names. A buyer who types it means the product
# ("cap" is a hat), but feed text that contains it usually does not ("Lens Cap 67mm" is
# not headwear, "Mirror Ball" is not a football, "Carplay Screen" is not a monitor).
# Weak forms are read from a query and ignored when classifying a feed product, where
# a wrong kind of product is the worst thing PicWise can do. A feed that really sells
# these kinds names them in its product type with the full word.
#
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
fire_pit|GA||fire pit,fire pits,firepit,firepits,fire bowl,fire bowls,chiminea,chimineas|εστία φωτιάς,εστίες φωτιάς
sauna|GA||sauna,saunas,outdoor sauna,outdoor saunas,infrared sauna,infrared saunas,sauna cabin,sauna cabins|σάουνα,σάουνες
heater|HA||heater,heaters,electric heater,electric heaters,radiator heater,electric fire,electric fires,electric fireplace,electric fireplaces,fireplace,fireplaces,fireplace stove,fireplace stoves,log burner,log burners,wood burner,wood burners|θερμάστρα,θερμάστρες,καλοριφέρ λαδιού,αερόθερμο,τζάκι,ηλεκτρικό τζάκι
fan|HA||fan,fans,electric fan|ανεμιστήρας,ανεμιστήρες
heat_pump|HA||heat pump,heat pumps|αντλία θερμότητας,αντλίες θερμότητας
water_heater|HA||water heater,water heaters,boiler,immersion heater|θερμοσίφωνας,θερμοσίφωνες,ηλιακός θερμοσίφωνας,λέβητας
vacuum_cleaner|HA||vacuum cleaner,vacuum cleaners,vacuum,vacuums,hoover|ηλεκτρική σκούπα,ηλεκτρικές σκούπες,σκούπα,σκούπες
robot_vacuum|HA|vacuum_cleaner|robot vacuum,robot vacuums,robot vacuum cleaner,robot vacuum cleaners,robotic vacuum|σκούπα ρομπότ,σκούπες ρομπότ,ρομπότ σκούπα
steam_mop|HA||steam mop,steam cleaner,steam cleaners|ατμοκαθαριστής,σφουγγαρίστρα ατμού
iron|HA||iron,steam iron,clothes iron,steam generator iron|σίδερο,σίδερα,σίδερο ατμού,σύστημα σιδερώματος
coffee_machine|KI||coffee machine,coffee machines,coffee maker,coffee makers,espresso machine,espresso machines|καφετιέρα,καφετιέρες,μηχανή καφέ,μηχανές καφέ,μηχανή εσπρέσο,καφετιέρα φίλτρου
microwave|KI||microwave,microwaves,microwave oven,microwave ovens|φούρνος μικροκυμάτων,φούρνοι μικροκυμάτων,μικροκύματα
oven|KI||oven,ovens,built in oven|φούρνος,φούρνοι,εντοιχιζόμενος φούρνος
cooker|KI||cooker,cookers,~stove,range cooker|κουζίνα,κουζίνες,ηλεκτρική κουζίνα,ηλεκτρικές κουζίνες
hob|KI||hob,hobs,cooktop,induction hob|εστία,εστίες,επαγωγική εστία
air_fryer|KI||air fryer,air fryers,air fryer oven,air fryer ovens|φριτέζα αέρος,φριτέζες αέρος,φριτέζα αέρα,φριτέζα χωρίς λάδι
deep_fryer|KI||deep fryer,deep fryers|φριτέζα,φριτέζες
mixer|KI||~mixer,~mixers,stand mixer,hand mixer,food mixer|μίξερ,κουζινομηχανή,κουζινομηχανές
hand_blender|KI||hand blender,immersion blender,stick blender|μίνι πίμερ,ραβδομπλέντερ
blender|KI||blender,blenders|μπλέντερ
food_processor|KI||food processor,food processors|πολυμίξερ,~multi
toaster|KI||toaster,toasters,sandwich maker,sandwich toaster|τοστιέρα,τοστιέρες,φρυγανιέρα
kettle|KI||kettle,kettles,electric kettle|βραστήρας,βραστήρες
juicer|KI||juicer,juicers,citrus press|αποχυμωτής,αποχυμωτές,στίφτης
cookware|KI||frying pan,frying pans,pan,pans,~pot,~pots,cooking pot,cooking pots,stock pot,stock pots,saucepan,saucepans,cookware set|τηγάνι,τηγάνια,κατσαρόλα,κατσαρόλες,σετ μαγειρικών σκευών
pressure_cooker|KI||pressure cooker,pressure cookers|χύτρα ταχύτητας,χύτρες ταχύτητας,χύτρα
kitchen_scale|KI||kitchen scale,kitchen scales|ζυγαριά κουζίνας
office_chair|FU|chair|office chair,office chairs,computer chair,computer chairs,desk chair|καρέκλα γραφείου,καρέκλες γραφείου,καρέκλα υπολογιστή,πολυθρόνα γραφείου
chair|FU||chair,chairs,armchair,armchairs,recliner,recliners,accent chair,accent chairs|καρέκλα,καρέκλες
desk|FU||desk,desks,computer desk,office desk|γραφείο υπολογιστή,γραφεία υπολογιστή,γραφείο,γραφεία
sofa|FU||sofa,sofas,couch,settee|καναπές,καναπέδες
sofa_bed|FU|sofa|sofa bed,sofa beds|καναπές κρεβάτι,καναπέδες κρεβάτι
bed|FU||bed,beds,bed frame|κρεβάτι,κρεβάτια
mattress|FU||mattress,mattresses|στρώμα,στρώματα
wardrobe|FU||wardrobe,wardrobes|ντουλάπα,ντουλάπες
shelving|FU||shelving unit,shelving units,shelf,shelves,shelving|ραφιέρα,ραφιέρες,ράφι,ράφια
bookcase|FU|shelving|bookcase,bookcases,~bookshelf,~bookshelves|βιβλιοθήκη,βιβλιοθήκες
table|FU||table,tables|τραπέζι,τραπέζια,τραπεζάκι,τραπεζαρία
bedside_table|FU||bedside table,bedside tables,bedside cabinet,bedside cabinets,bedside,bedsides,nightstand,nightstands,night stand,night stands|κομοδίνο,κομοδίνα
lamp|FU||lamp,lamps,desk lamp,ceiling light,ceiling lights,pendant light,pendant lights,wall light,wall lights,chandelier,chandeliers,light fitting,light fittings|φωτιστικό,φωτιστικά,πορτατίφ,φωτιστικό οροφής
light_bulb|FU||light bulb,light bulbs,led bulb,smart bulb|λάμπα,λάμπες,λαμπτήρας,λαμπτήρες
smart_plug|FU||smart plug,smart plugs|έξυπνη πρίζα,έξυπνες πρίζες
smartphone|PH||smartphone,smartphones,smart phone,smart phones,android phone,android phones,galaxy phone,galaxy phones|σμαρτφόν,έξυπνο κινητό,έξυπνα κινητά
mobile_phone|PH||mobile phone,mobile phones,cell phone,cell phones,phone,phones,basic phone,basic phones,feature phone,feature phones,flip phone,flip phones,big button phone,big button phones,senior phone,senior phones|κινητό,κινητά,κινητό τηλέφωνο,κινητά τηλέφωνα,τηλέφωνο,απλό κινητό,απλά κινητά
desk_phone|PH||ip phone,ip phones,voip phone,voip phones,sip phone,sip phones,conference phone,conference phones,desk phone,desk phones,office phone,office phones,landline phone,landline phones,cordless phone,cordless phones,dect phone,dect phones|σταθερό τηλέφωνο,σταθερά τηλέφωνα,ασύρματο τηλέφωνο,ασύρματα τηλέφωνα,τηλέφωνο γραφείου
power_bank|PH||power bank,power banks,powerbank,portable charger,external battery|εξωτερική μπαταρία,εξωτερικές μπαταρίες,φορητή μπαταρία,φορητός φορτιστής,πάουερ μπανκ
phone_charger|PH||charger,chargers,phone charger,wall charger,usb charger,power adapter,power adapters,ac adapter,ac adapters|φορτιστής,φορτιστές,φορτιστής κινητού
wireless_charger|PH|phone_charger|wireless charger,wireless chargers,charging pad|ασύρματος φορτιστής,ασύρματοι φορτιστές
charging_cable|PH||charging cable,usb cable,cable,cables,usb c cable,lightning cable|καλώδιο φόρτισης,καλώδιο,καλώδια
phone_case|PH||phone case,phone cases,mobile phone case,mobile phone cases,cell phone case,cell phone cases,smartphone case,smartphone cases,case,~cover,phone cover|θήκη κινητού,θήκες κινητού,θήκη,θήκες
screen_protector|PH||screen protector,screen protectors,screen back protector,screen back protectors,tempered glass|προστασία οθόνης,προστατευτικό οθόνης,τζαμάκι
car_phone_holder|PH||car phone holder,car phone mount,phone holder|βάση κινητού αυτοκινήτου,βάση κινητού
smartwatch|PH|watch|smartwatch,smartwatches,smart watch,fitness tracker,fitness trackers|έξυπνο ρολόι,έξυπνα ρολόγια
laptop|CO||laptop,laptops,notebook computer,notebook computers|λάπτοπ,φορητός υπολογιστής,φορητοί υπολογιστές,φορητό
desktop_pc|CO||desktop pc,desktop pcs,desktop computer,desktop computers,workstation,workstations,~desktop,~pc|υπολογιστής,υπολογιστές,σταθερός υπολογιστής,κομπιούτερ,σταθμός εργασίας,σταθμοί εργασίας
monitor|CO||monitor,monitors,computer monitor,computer monitors,pc monitor,pc monitors,pc screen,pc screens,computer screen,computer screens,~screen|οθόνη υπολογιστή,οθόνες υπολογιστή,οθόνη,οθόνες,μόνιτορ
printer|CO||printer,printers,multifunction printer,multifunction printers,all in one printer|εκτυπωτής,εκτυπωτές,πολυμηχάνημα,πολυμηχανήματα
label_printer|CO||label printer,label printers,label maker,label makers|ετικετογράφος,ετικετογράφοι,εκτυπωτής ετικετών
toner|CO||toner,toners,toner cartridge,toner cartridges|τόνερ
ink_cartridge|CO||ink cartridge,ink cartridges,printer ink,ink|μελάνι,μελάνια,μελάνι εκτυπωτή,μελάνια εκτυπωτή,φυσίγγιο μελανιού,αμπούλα,αμπούλες
router|CO||router,routers,wifi router,network router,network routers,modem,modems|ρούτερ,μόντεμ
access_point|CO||access point,access points,wireless access point,wireless access points,wifi access point,wifi access points|σημείο πρόσβασης,σημεία πρόσβασης
firewall|CO||firewall,firewalls,hardware firewall,hardware firewalls,network firewall,network firewalls|τείχος προστασίας
server|CO||server,servers,rack server,rack servers,tower server,tower servers,console server,console servers|διακομιστής,διακομιστές
memory_card|CO||memory card,memory cards,sd card,sd cards,micro sd card,micro sd cards,microsd card,microsd cards,compactflash card,compactflash cards|κάρτα μνήμης,κάρτες μνήμης
battery|CO||household battery,household batteries,rechargeable battery,rechargeable batteries,alkaline battery,alkaline batteries,aa battery,aa batteries,aaa battery,aaa batteries,~battery,~batteries|επαναφορτιζόμενη μπαταρία,επαναφορτιζόμενες μπαταρίες,αλκαλική μπαταρία,αλκαλικές μπαταρίες
pen|CO||ballpoint pen,ballpoint pens,ballpoint,ballpoints,gel pen,gel pens,rollerball pen,rollerball pens,fountain pen,fountain pens,~pen,~pens|στυλό,στιλό
marker|CO||marker,markers,marker pen,marker pens,permanent marker,permanent markers,whiteboard marker,whiteboard markers,highlighter,highlighters|μαρκαδόρος,μαρκαδόροι,υπογραμμιστής,υπογραμμιστές
folder|CO||folder,folders,ring binder,ring binders,lever arch file,lever arch files,document folder,document folders|ντοσιέ,φάκελος εγγράφων,φάκελοι εγγράφων,κλασέρ
network_switch|CO||network switch,network switches,ethernet switch,ethernet switches|μεταγωγέας δικτύου,μεταγωγείς δικτύου,switch δικτύου
media_converter|CO||media converter,media converters,fibre media converter,fibre media converters,fiber media converter,fiber media converters|μετατροπέας μέσων,μετατροπείς μέσων
network_card|CO||network card,network cards,network interface card,network interface cards|κάρτα δικτύου,κάρτες δικτύου
software|CO||security software,antivirus software,antivirus,networking software,office software,operating system,operating systems|λογισμικό προστασίας,αντιικό πρόγραμμα,λειτουργικό σύστημα
keyboard|CO||keyboard,keyboards|πληκτρολόγιο,πληκτρολόγια
mouse|CO||mouse,mice,computer mouse|ποντίκι,ποντίκια
webcam|CO||webcam,webcams,web camera,web cam|κάμερα υπολογιστή,κάμερες υπολογιστή,κάμερα web
scanner|CO||scanner,scanners,document scanner|σαρωτής,σαρωτές,σκάνερ
storage_drive|CO||external hard drive,external hard drives,hard drive,hard drives,internal hard drive,internal hard drives,ssd,ssds,solid state drive,solid state drives|σκληρός δίσκος,εξωτερικός σκληρός δίσκος
usb_flash_drive|CO||usb stick,usb sticks,usb flash drive,usb flash drives,flash drive,flash drives,pen drive,pen drives,memory stick,memory sticks|στικάκι,στικάκια,φλασάκι,φλασάκια
docking_station|CO||docking station,docking stations,dock,docks,laptop dock,laptop docks,port replicator,port replicators,usb hub|βάση σύνδεσης
television|AV||tv,tvs,television,televisions,smart tv|τηλεόραση,τηλεοράσεις
speaker|AV||speaker,speakers,bluetooth speaker,portable speaker|ηχείο,ηχεία
soundbar|AV||soundbar,soundbars,sound bar|μπάρα ήχου
headphones|AV||headphones,headphone,headset,headsets,earphones,earbuds|ακουστικά,ακουστικό,ακουστικά κεφαλής,ψείρες
game_console|AV||games console,game console,gaming console,games consoles,game consoles|κονσόλα,κονσόλες,κονσόλα παιχνιδιών
game_controller|AV||~controller,~controllers,gamepad,joystick,game controller,game controllers,gaming controller,gaming controllers|χειριστήριο,χειριστήρια
video_game|AV||video game,video games,pc game,pc games,console game,console games|βιντεοπαιχνίδι,βιντεοπαιχνίδια,ηλεκτρονικό παιχνίδι,ηλεκτρονικά παιχνίδια
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
punching_bag|BK||punching bag,punching bags,punch bag,punch bags,punchbag,punchbags,boxing bag,boxing bags|σάκος πυγμαχίας,σάκοι πυγμαχίας
dog_food|BK||dog food|τροφή σκύλου,τροφή για σκύλους
cat_food|BK||cat food|τροφή γάτας,τροφή για γάτες
treadmill|BK||treadmill,treadmills|διάδρομος γυμναστικής,διάδρομος
exercise_bike|BK||exercise bike,exercise bikes|στατικό ποδήλατο
dumbbells|BK||dumbbells,dumbbell|αλτήρες,βαράκια
barbell|BK||barbell,barbells,barbell set,barbell sets,barbell bar,curl bar,weight plate,weight plates,olympic plates|μπάρα,μπάρες,δίσκοι βαρών,δίσκος βαρών
yoga_mat|BK||yoga mat,exercise mat|στρώμα γιόγκα,στρωματάκι γυμναστικής
tent|BK||tent,tents|σκηνή,σκηνές
play_tent|BK|toy|play tent,play tents,kids tent,kids tents,kids play tent,kids play tents,play teepee,play teepees,kids teepee,kids teepees|σκηνή παιχνιδιού,σκηνές παιχνιδιού,παιδική σκηνή,παιδικές σκηνές
sleeping_bag|BK||sleeping bag,sleeping bags|υπνόσακος,υπνόσακοι
trousers|CL||trousers,pants,chinos,cargo trousers|παντελόνι,παντελόνια
work_trousers|CL|trousers|work trousers,work pants|παντελόνι εργασίας,παντελόνια εργασίας
jeans|CL||jeans|τζιν
jacket|CL||jacket,jackets,coat,coats|μπουφάν,παλτό,μπουφάν χειμερινό
t_shirt|CL||t shirt,t shirts,tshirt,tee|μπλουζάκι,μπλουζάκια,κοντομάνικο,μπλούζα
shirt|CL||shirt,shirts|πουκάμισο,πουκάμισα
hoodie|CL||hoodie,hoodies,sweatshirt,sweatshirts|φούτερ
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
ring|JW||~ring,~rings,gold ring,silver ring,engagement ring|δαχτυλίδι,δαχτυλίδια
necklace|JW||necklace,necklaces,~pendant|κολιέ,μενταγιόν
bracelet|JW||bracelet,bracelets|βραχιόλι,βραχιόλια
earrings|JW||earrings|σκουλαρίκια,σκουλαρίκι
sunglasses|JW||sunglasses|γυαλιά ηλίου
bag|JW||bag,bags|τσάντα,τσάντες
backpack|JW|bag|backpack,backpacks,rucksack|σακίδιο,σακίδιο πλάτης,τσάντα πλάτης
laptop_bag|JW|bag|laptop bag,laptop bags,laptop case,laptop cases,laptop sleeve,laptop sleeves|τσάντα laptop,τσάντα λάπτοπ,θήκη laptop,θήκη λάπτοπ
handbag|JW|bag|handbag,handbags,shoulder bag,crossbody bag,tote bag|τσάντα χειρός,τσάντα ώμου
suitcase|JW||suitcase,suitcases,luggage|βαλίτσα,βαλίτσες
wallet|JW||wallet,wallets,purse|πορτοφόλι,πορτοφόλια
belt|JW||belt,belts|ζώνη,ζώνες
hat|JW||hat,hats,~cap,~caps,beanie|καπέλο,καπέλα,σκούφος
gloves|JW||gloves|γάντια
tablet|CO||tablet,tablets,android tablet,ipad|τάμπλετ,ταμπλέτα υπολογιστή
e_reader|CO||e reader,ebook reader,kindle|ηλεκτρονικός αναγνώστης βιβλίων
graphics_card|CO||graphics card,graphics cards,video card,gpu|κάρτα γραφικών,κάρτες γραφικών
processor|CO||processor,processors,cpu|επεξεργαστής,επεξεργαστές
ram_memory|CO||ram memory,ram module,ram modules,memory module,memory modules,ddr4 ram,ddr5 ram,dimm,dimms|μνήμη ram,μνήμες ram
motherboard|CO||motherboard,motherboards|μητρική,μητρική κάρτα,μητρικές
power_supply|CO||power supply unit,power supply units,psu,psus,pc power supply|τροφοδοτικό,τροφοδοτικά
pc_case|CO||pc case,pc cases,computer case,computer cases,tower case|κουτί υπολογιστή
pc_cooling|CO||case fan,case fans,pc fan,pc fans,cpu cooler,cpu coolers,computer cooling system,computer cooling systems,liquid cooler|ανεμιστήρας υπολογιστή,ψύκτρα,ψύξη υπολογιστή
printer_paper|CO||printer paper,copy paper,a4 paper|χαρτί εκτυπωτή,χαρτί φωτοτυπικού,χαρτί a4
ups|CO||ups,uninterruptible power supply|ups αδιάλειπτης παροχής
smart_speaker|AV||smart speaker,smart speakers|έξυπνο ηχείο
drone|AV||drone,drones|ντρόουν
vr_headset|AV||vr headset,vr headsets,virtual reality headset|γυαλιά εικονικής πραγματικότητας
tv_box|AV||tv box,tv boxes,android tv box,android tv boxes,streaming device,tv stick,tv sticks,streaming stick|tv box,tv stick
car_charger|PH|phone_charger|car charger,car chargers|φορτιστής αυτοκινήτου
selfie_stick|PH||selfie stick,~tripod|μπαστούνι selfie,τρίποδο
car_audio|TY||car stereo,car radio,car speakers|ηχοσύστημα αυτοκινήτου,ράδιο αυτοκινήτου
gps_navigator|TY||gps navigator,sat nav,gps|πλοηγός gps,πλοηγός
dishwasher_tablets|KI||dishwasher tablets,dishwasher pods|ταμπλέτες πλυντηρίου πιάτων,κάψουλες πλυντηρίου πιάτων
laundry_detergent|KI||laundry detergent,washing powder,washing liquid|απορρυπαντικό ρούχων,σκόνη πλυντηρίου,απορρυπαντικό
knife_set|KI||knife set,kitchen knives,chef knife|σετ μαχαιριών,μαχαίρια κουζίνας,μαχαίρι κουζίνας
cutlery|KI||cutlery,cutlery set|μαχαιροπίρουνα,σετ μαχαιροπίρουνα
dinnerware|KI||dinner set,dinner sets,dinner plates,~plates,dinnerware|σερβίτσιο,πιάτα
glassware|KI||glasses set,drinking glasses,wine glasses|ποτήρια,σετ ποτηριών
water_filter_jug|KI||water filter jug,filter jug|κανάτα φίλτρου νερού
food_storage|KI||food containers,lunch box,food storage containers|δοχεία φαγητού,φαγητοδοχείο,τάπερ
grill|GA||bbq,bbqs,barbecue,barbecues,barbeque,barbeques,grill,grills,gas grill,gas grills,gas bbq,gas bbqs,charcoal grill,charcoal grills,charcoal bbq,charcoal bbqs|ψησταριά,ψησταριές,μπάρμπεκιου,ψησταριά υγραερίου
garden_furniture|GA||garden furniture,patio furniture,outdoor furniture,garden chairs,~patio|έπιπλα κήπου,καρέκλες κήπου,τραπέζι κήπου
parasol|GA||parasol,patio umbrella,sun umbrella|ομπρέλα βεράντας,ομπρέλα κήπου,ομπρέλα παραλίας
pool|GA||swimming pool,above ground pool,paddling pool|πισίνα,φουσκωτή πισίνα
flower_pot|GA||flower pot,flower pots,plant pot,plant pots,planter,planters,planter box,planter boxes,planter bed,planter beds,raised garden bed,raised garden beds,raised bed,raised beds,garden bed,garden beds,flower bed,flower beds,raised flower bed,raised flower beds|γλάστρα,γλάστρες,ζαρντινιέρα,ζαρντινιέρες
greenhouse|GA||greenhouse,greenhouses,grow tent,grow tents,polytunnel,polytunnels,cold frame,cold frames|θερμοκήπιο,θερμοκήπια
towels|FU||towel,towels,bath towel,beach towel|πετσέτα,πετσέτες,πετσέτα μπάνιου,πετσέτα θαλάσσης
bedding|FU||bedding,bedding set,bedding sets|κλινοσκεπάσματα,είδη κρεβατιού
bed_linen|FU|bedding|bed sheets,bed linen,duvet cover,~sheets|σεντόνια,σετ σεντόνια,παπλωματοθήκη
pillow|FU|bedding|pillow,pillows|μαξιλάρι,μαξιλάρια
duvet|FU|bedding|duvet,duvets,quilt,comforter|πάπλωμα,παπλώματα,κουβέρτα
bedspread|FU|bedding|bedspread,bedspreads,coverlet,coverlets|κουβερλί
curtains|FU||curtains,curtain,blinds|κουρτίνες,κουρτίνα,στόρια
rug|FU||rug,rugs,carpet|χαλί,χαλιά
bath_mat|FU||bath mat,bath mats,bathmat,bathmats,bath rug,bath rugs,shower mat,shower mats|πατάκι μπάνιου,πατάκια μπάνιου
mirror|FU||mirror,mirrors,wall mirror|καθρέφτης,καθρέφτες
wall_clock|FU||wall clock,alarm clock|ρολόι τοίχου,ξυπνητήρι
baby_bottle|BK||baby bottle,baby bottles,feeding bottle|μπιμπερό
breast_pump|BK||breast pump|θήλαστρο
pet_carrier|BK||pet carrier,dog carrier,cat carrier|τσάντα μεταφοράς κατοικιδίου,κλουβί μεταφοράς
cat_litter|BK||cat litter,litter box|άμμος γάτας,τουαλέτα γάτας
aquarium|BK||aquarium,fish tank|ενυδρείο
lego|BK||lego,building blocks|τουβλάκια
board_game|BK||board game,board games|επιτραπέζιο,επιτραπέζια,επιτραπέζιο παιχνίδι
doll|BK||doll,dolls|κούκλα,κούκλες
kettlebell|BK||kettlebell,kettlebells|kettlebell
weight_bench|BK||weight bench,gym bench|πάγκος γυμναστικής
football|BK||football,soccer ball,basketball,~ball|μπάλα,μπάλες,μπάλα ποδοσφαίρου,μπάλα μπάσκετ
game_table|BK||game table,game tables,games table,games tables,football table,football tables,foosball table,foosball tables,table football,pool table,pool tables,snooker table,snooker tables,billiard table,billiard tables,air hockey table,air hockey tables,table tennis table,table tennis tables,ping pong table,ping pong tables,poker table,poker tables,card table,card tables,casino table,casino tables,blackjack table,blackjack tables|ποδοσφαιράκι,τραπέζι ποδοσφαιράκι,μπιλιάρδο,τραπέζι μπιλιάρδου,τραπέζι πινγκ πονγκ,τραπέζι πόκερ
makeup|BE||makeup,foundation,mascara,lipstick|μακιγιάζ,μέικαπ,κραγιόν,μάσκαρα
nail_polish|BE||nail polish|βερνίκι νυχιών,μανό
hair_brush|BE||hair brush,hairbrush,comb|βούρτσα μαλλιών,χτένα
razor_blades|BE||razor blades,razor cartridges|ξυραφάκια,λεπίδες ξυρίσματος
deodorant|BE||deodorant,antiperspirant|αποσμητικό,αποσμητικά
hearing_aid|HE||hearing aid,hearing amplifier|ακουστικό βαρηκοΐας,ακουστικά βαρηκοΐας
wheelchair|HE||wheelchair,rollator,walking frame|αναπηρικό αμαξίδιο,περιπατητήρας
shower_seat|HE||shower seat,shower seats,shower chair,shower chairs,shower stool,shower stools,bath seat,bath seats,bath chair,bath chairs|κάθισμα μπάνιου,καρέκλα μπάνιου,κάθισμα ντουζιέρας
face_mask|HE||face mask,face masks|μάσκα προσώπου,μάσκες προσώπου
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


# Words a buyer uses to ask for an item that is not new. PicWise shows refurbished and
# used products only when they are asked for (owner decision, 2026-10-10), so these
# words are read as a request about the item's condition and are never matched against
# feed text: the feed states a condition in its own column, in its own wording, which
# `picwise_providers.product_condition` reads. Written here, next to the other words
# that are not the product itself, so one file holds the query vocabulary.
_CONDITION_REQUEST_ENGLISH = (
    "refurbished,refurb,refurbs,reconditioned,renewed,used,second hand,secondhand,"
    "pre owned,preowned,open box,openbox,ex display,ex demo"
)
_CONDITION_REQUEST_GREEK = (
    "μεταχειρισμένο,μεταχειρισμένα,μεταχειρισμένος,μεταχειρισμένη,μεταχειρισμένες,"
    "μεταχειρισμένοι,μεταχειρισμένου,ανακατασκευασμένο,ανακατασκευασμένα,"
    "ανακατασκευασμένος,ανακατασκευασμένη,ανακαινισμένο,ανακαινισμένα,ανακαινισμένος,"
    "ανακαινισμένη,σεκοντ χαντ"
)


@dataclass(frozen=True)
class ConditionRequestWords:
    """The words that ask for a non-new item, in each language the buyer may type."""

    english: tuple[str, ...]
    greek: tuple[str, ...]


@lru_cache(maxsize=1)
def get_condition_request_words() -> ConditionRequestWords:
    def forms(table: str) -> tuple[str, ...]:
        return tuple(form.strip() for form in table.split(",") if form.strip())

    return ConditionRequestWords(
        english=forms(_CONDITION_REQUEST_ENGLISH),
        greek=forms(_CONDITION_REQUEST_GREEK),
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
        english_forms = tuple(form.strip() for form in english.split(",") if form.strip())
        greek_forms = tuple(form.strip() for form in greek.split(",") if form.strip())
        concepts.append(
            ProductConcept(
                concept_id=concept_id,
                mega_category_id=_MEGA[mega],
                english=tuple(form.lstrip("~") for form in english_forms),
                greek=tuple(form.lstrip("~") for form in greek_forms),
                broader=tuple(b for b in broader.split(",") if b),
                weak=tuple(
                    form[1:] for form in english_forms + greek_forms if form.startswith("~")
                ),
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
