"""The searches `tools/price_first_eval.py` runs: the 118 English buyer searches PicWise
has been measured on since 2026-10-16, of the kinds the third feed sells, each as
(search, the kind it was written to ask for, how it is written).

The kinds are as written on 2026-10-16, and a kind that starts with "?" was one the
lexicon did not know then. Steps 1 to 3 gave some of these searches a kind of their own
(mobile phone, USB stick, bookcase, fire pit, sofa bed, greenhouse, RAM memory), so the
tool reports this column and does not judge by it. The style says what the search
tests: "clean", "typo", "synonym", "phrase", "sentence", "brand", "pet" or "unknown".
"""

CASES = [
    # laptop
    ("laptop", "laptop", "clean"), ("labtop", "laptop", "typo"), ("lapptop", "laptop", "typo"),
    ("cheap laptop for student", "laptop", "phrase"), ("lenovo thinkpad 16gb ram", "laptop", "brand"),
    ("i need a new laptop for work", "laptop", "sentence"), ("notebook computer 15 inch", "laptop", "synonym"),
    # smartphone
    ("smartphone", "smartphone", "clean"), ("smartfone", "smartphone", "typo"), ("mobile phone", "smartphone", "synonym"),
    ("samsung galaxy phone 128gb", "smartphone", "brand"), ("unlocked android phone", "smartphone", "phrase"),
    ("cell phone", "smartphone", "synonym"),
    # tablet
    ("tablet", "tablet", "clean"), ("tablit", "tablet", "typo"), ("ipad 11 inch", "tablet", "brand"),
    ("android tablet for kids", "tablet", "phrase"),
    # monitor
    ("computer monitor", "monitor", "clean"), ("moniter 27 inch", "monitor", "typo"), ("4k gaming monitor", "monitor", "phrase"),
    ("pc screen 24in", "monitor", "synonym"),
    # headphones
    ("headphones", "headphones", "clean"), ("headfones", "headphones", "typo"),
    ("wireless headphones noise cancelling", "headphones", "phrase"),
    ("bluetooth earbuds", "headphones", "synonym"), ("headset with mic for office", "headphones", "phrase"),
    # keyboard / mouse
    ("keyboard", "keyboard", "clean"), ("keybord", "keyboard", "typo"), ("mechanical gaming keyboard", "keyboard", "phrase"),
    ("wireless mouse", "mouse", "clean"), ("mosue", "mouse", "typo"), ("gaming mouse rgb", "mouse", "phrase"),
    # printer / toner / ink
    ("printer", "printer", "clean"), ("printor for home", "printer", "typo"), ("wireless all in one printer", "printer", "phrase"),
    ("laser printer for office", "printer", "phrase"),
    ("toner", "toner", "clean"), ("tonner cartridge hp", "toner", "typo"), ("hp 26a toner", "toner", "brand"),
    ("ink cartridges", "ink_cartridge", "clean"), ("inc cartridge epson", "ink_cartridge", "typo"),
    ("printer ink canon", "ink_cartridge", "phrase"),
    # storage / ups / power bank
    ("external hard drive 2tb", "storage_drive", "clean"), ("hardrive", "storage_drive", "typo"),
    ("portable ssd 1tb", "storage_drive", "synonym"), ("usb stick 64gb", "storage_drive", "synonym"),
    ("ups battery backup", "ups", "phrase"), ("uninterruptible power supply", "ups", "clean"),
    ("power bank", "power_bank", "clean"), ("powerbank 20000mah", "power_bank", "typo"),
    # webcam / router / speaker
    ("webcam", "webcam", "clean"), ("web cam for zoom calls", "webcam", "phrase"),
    ("wifi router", "router", "clean"), ("bluetooth speaker", "speaker", "clean"),
    # office chair / desk
    ("office chair", "office_chair", "clean"), ("ofice chair", "office_chair", "typo"),
    ("ergonomic desk chair", "office_chair", "phrase"), ("gaming chair", "office_chair", "synonym"),
    ("comfy chair for home office", "office_chair", "sentence"),
    ("desk", "desk", "clean"), ("computer desk", "desk", "clean"), ("standing desk", "desk", "phrase"),
    ("dsek for home office", "desk", "typo"),
    # tables / sofas / beds
    ("dining table", "table", "clean"), ("coffee table", "table", "clean"), ("tabel", "table", "typo"),
    ("sofa", "sofa", "clean"), ("soffa", "sofa", "typo"), ("3 seater sofa grey", "sofa", "phrase"), ("couch", "sofa", "synonym"),
    ("corner sofa bed", "sofa", "phrase"),
    ("double bed frame", "bed", "clean"), ("bunk bed for kids", "bed", "phrase"), ("dog bed", "bed", "pet"),
    # garden
    ("garden furniture", "garden_furniture", "clean"), ("garden furnature", "garden_furniture", "typo"),
    ("rattan garden furniture set", "garden_furniture", "phrase"), ("patio set", "garden_furniture", "synonym"),
    ("outdoor furniture", "garden_furniture", "synonym"),
    ("bbq", "grill", "clean"), ("barbeque grill", "grill", "typo"), ("gas bbq with 4 burners", "grill", "phrase"),
    ("charcoal barbecue", "grill", "synonym"),
    ("tent", "tent", "clean"), ("tnet", "tent", "typo"), ("4 person camping tent", "tent", "phrase"),
    # home
    ("floor lamp", "lamp", "clean"), ("table lamp", "lamp", "clean"), ("lamb for bedroom", "lamp", "typo"),
    ("kettle", "kettle", "clean"), ("kettel", "kettle", "typo"), ("electric kettle 1.7l", "kettle", "phrase"),
    ("electric heater", "heater", "clean"), ("heatr", "heater", "typo"), ("patio heater", "heater", "phrase"),
    ("fire pit", "heater", "synonym"),
    ("desk fan", "fan", "clean"), ("pedestal fan", "fan", "clean"), ("ceiling fan with light", "fan", "phrase"),
    ("full length mirror", "mirror", "clean"), ("mirrer", "mirror", "typo"), ("bathroom mirror with lights", "mirror", "phrase"),
    ("bookcase", "shelving", "clean"), ("bookshelf", "shelving", "synonym"), ("shelving unit", "shelving", "clean"),
    ("shelfs for garage", "shelving", "typo"),
    ("dumbbells", "dumbbells", "clean"), ("dumbells set", "dumbbells", "typo"),
    # toys
    ("toys for kids", "toy", "phrase"), ("kids ride on car", "toy", "phrase"), ("toy", "toy", "clean"),
    # kinds the lexicon does not know (real products in the third feed)
    ("greenhouse", "?greenhouse", "unknown"), ("cat tree", "?cat_tree", "unknown"), ("dog crate", "?dog_crate", "unknown"),
    ("rabbit hutch", "?rabbit_hutch", "unknown"), ("memory card 128gb", "?memory_card", "unknown"),
    ("network switch", "?network_switch", "unknown"), ("ram memory 16gb", "?ram_memory", "unknown"),
]
