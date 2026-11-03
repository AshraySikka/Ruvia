"""
Curated content. Everything the app suggests comes from these tables, not from a model.
Review this file yourself and edit freely. Keep wording plain and never add doses.
"""

# Symptom keys, display labels and words people actually use.
SYMPTOMS = {
    "headache": {"label": "Headache", "words": ["headache", "head ache", "migraine", "head hurts", "head is pounding", "head pounding", "throbbing head"]},
    "acidity": {"label": "Acidity", "words": ["acidity", "acidic", "acid reflux", "reflux", "heartburn", "gerd", "burning in my chest after", "sour burps"]},
    "nausea": {"label": "Nausea", "words": ["nausea", "nauseous", "queasy", "feel like throwing up", "want to throw up", "vomit", "threw up"]},
    "bloating": {"label": "Bloating", "words": ["bloated", "bloating", "gassy"]},
    "stomach_ache": {"label": "Stomach ache", "words": ["stomach ache", "stomachache", "stomach hurts", "tummy", "stomach pain", "abdominal cramp"]},
    "constipation": {"label": "Constipation", "words": ["constipated", "constipation", "can't poop", "cannot poop"]},
    "diarrhea": {"label": "Diarrhea", "words": ["diarrhea", "diarrhoea", "loose motion", "loose stool"]},
    "cramps": {"label": "Cramps", "words": ["period cramps", "cramps", "cramping", "period pain", "menstrual pain"]},
    "back_pain": {"label": "Back pain", "words": ["back pain", "backache", "back ache", "lower back", "back hurts"]},
    "neck_pain": {"label": "Neck pain", "words": ["neck pain", "stiff neck from", "neck hurts", "neck is sore"]},
    "muscle_soreness": {"label": "Sore muscles", "words": ["sore muscles", "muscle pain", "body ache", "body aches", "sore from"]},
    "cold": {"label": "Cold", "words": ["a cold", "caught a cold", "have a cold", "runny nose", "stuffy nose", "blocked nose", "congested", "congestion", "sneezing"]},
    "sore_throat": {"label": "Sore throat", "words": ["sore throat", "throat hurts", "scratchy throat", "throat pain"]},
    "cough": {"label": "Cough", "words": ["cough", "coughing"]},
    "fever": {"label": "Fever", "words": ["fever", "feverish", "high temperature", "chills"]},
    "allergies": {"label": "Allergies", "words": ["allergies", "allergy", "hay fever", "itchy eyes", "watery eyes", "pollen"]},
    "insomnia": {"label": "Poor sleep", "words": ["insomnia", "can't sleep", "cannot sleep", "couldn't sleep", "could not sleep", "slept badly", "barely slept", "woke up a lot"]},
    "fatigue": {"label": "Tired", "words": ["tired", "fatigue", "fatigued", "drained", "no energy", "low energy", "wiped out"]},
    "stress": {"label": "Stress", "words": ["stressed", "stress", "anxious", "anxiety", "overwhelmed", "on edge", "panicky", "worried"]},
    "low_mood": {"label": "Low mood", "words": ["sad", "feeling down", "feeling low", "feel low", "depressed", "feeling blue", "crying", "empty"]},
    "dizziness": {"label": "Dizzy", "words": ["dizzy", "lightheaded", "light headed", "vertigo"]},
    "toothache": {"label": "Toothache", "words": ["toothache", "tooth hurts", "tooth pain"]},
    "skin_rash": {"label": "Rash", "words": ["rash", "hives", "itchy skin"]},
}

TRIGGER_WORDS = {
    "Late dinner": ["late dinner", "ate late", "late meal", "eating late", "dinner at 11", "midnight snack"],
    "Spicy food": ["spicy", "chili", "chilli", "biryani", "curry"],
    "Coffee": ["coffee", "espresso", "too much caffeine", "caffeine"],
    "Skipped meal": ["skipped lunch", "skipped breakfast", "skipped dinner", "skipped a meal", "didn't eat", "did not eat"],
    "Poor sleep": ["no sleep", "slept badly", "barely slept", "didn't sleep", "did not sleep", "up all night"],
    "Screen time": ["screen", "laptop all day", "staring at my screen"],
    "Alcohol": ["alcohol", "drinks last night", "wine", "beer", "hangover"],
    "Long workday": ["long day at work", "work was crazy", "deadline", "back to back meetings", "long shift"],
    "Dehydrated": ["didn't drink water", "not enough water", "dehydrated", "forgot to drink"],
}

SEVERITY_WORDS = [
    ("extreme", ["extreme", "extremely", "unbearable", "excruciating", "can't function", "cannot function", "10/10", "10 out of 10"]),
    ("severe", ["severe", "really bad", "very bad", "awful", "terrible", "horrible", "intense", "killing me", "8/10", "9/10"]),
    ("mild", ["mild", "slight", "slightly", "a little", "a bit", "minor", "little", "1/10", "2/10", "3/10"]),
    ("moderate", ["moderate", "pretty bad", "quite", "annoying", "4/10", "5/10", "6/10", "7/10"]),
]

# Follow up timing is set here, never by a model.
FOLLOWUP_MINUTES = {"mild": 120, "moderate": 60, "severe": 30, "extreme": 20}

# Over the counter options. No doses on purpose: the label and a pharmacist decide that.
OTC = {
    "famotidine": {"name": "Famotidine", "brands": ["Pepcid"], "class": "H2 blocker"},
    "calcium_carbonate": {"name": "Calcium carbonate antacid", "brands": ["Tums", "Rolaids"], "class": "antacid"},
    "omeprazole": {"name": "Omeprazole", "brands": ["Olex", "Prilosec"], "class": "PPI"},
    "acetaminophen": {"name": "Acetaminophen", "brands": ["Tylenol"], "class": "analgesic"},
    "ibuprofen": {"name": "Ibuprofen", "brands": ["Advil", "Motrin"], "class": "NSAID"},
    "naproxen": {"name": "Naproxen", "brands": ["Aleve"], "class": "NSAID"},
    "loratadine": {"name": "Loratadine", "brands": ["Claritin"], "class": "antihistamine"},
    "cetirizine": {"name": "Cetirizine", "brands": ["Reactine", "Zyrtec"], "class": "antihistamine"},
    "diphenhydramine": {"name": "Diphenhydramine", "brands": ["Benadryl"], "class": "sedating antihistamine"},
    "dimenhydrinate": {"name": "Dimenhydrinate", "brands": ["Gravol"], "class": "sedating antihistamine"},
    "dextromethorphan": {"name": "Dextromethorphan cough syrup", "brands": ["Benylin DM", "Robitussin DM"], "class": "cough suppressant"},
    "pseudoephedrine": {"name": "Pseudoephedrine", "brands": ["Sudafed"], "class": "decongestant"},
    "saline_spray": {"name": "Saline nasal spray", "brands": ["Hydrasense"], "class": "saline"},
    "lozenges": {"name": "Throat lozenges", "brands": ["Strepsils", "Halls"], "class": "lozenge"},
    "loperamide": {"name": "Loperamide", "brands": ["Imodium"], "class": "antidiarrheal"},
    "bismuth": {"name": "Bismuth subsalicylate", "brands": ["Pepto-Bismol"], "class": "salicylate"},
    "ors": {"name": "Oral rehydration salts", "brands": ["Gastrolyte", "Pedialyte"], "class": "rehydration"},
    "simethicone": {"name": "Simethicone", "brands": ["Ovol", "Gas-X"], "class": "anti gas"},
    "peg": {"name": "Polyethylene glycol", "brands": ["RestoraLAX", "MiraLAX"], "class": "laxative"},
    "melatonin": {"name": "Melatonin", "brands": [], "class": "sleep aid"},
    "hydrocortisone": {"name": "Hydrocortisone cream", "brands": ["Cortate"], "class": "topical steroid"},
}

REMEDIES = {
    "headache": {
        "home": ["Drink a full glass of water now", "Rest in a quiet, dim room for 20 minutes", "Cold compress on your forehead or the back of your neck", "Step away from screens for a bit", "Eat something if you have skipped a meal"],
        "otc": ["acetaminophen", "ibuprofen", "naproxen"],
        "doctor_if": "it is sudden and the worst you have had, comes with a stiff neck, fever, confusion or vision changes, or follows a head injury",
    },
    "acidity": {
        "home": ["Sip warm water slowly", "Stay upright for at least 2 hours, no lying down", "Skip spicy, fried and acidic food for the rest of the day", "A small bowl of plain yogurt or a banana can settle things", "Ginger or fennel tea, weak and warm", "Raise the head of your bed if it hits at night"],
        "otc": ["calcium_carbonate", "famotidine", "omeprazole"],
        "doctor_if": "it happens most weeks, wakes you up often, makes swallowing hard, or comes with weight loss or black stools",
    },
    "nausea": {
        "home": ["Small sips of water or ginger ale, often", "Ginger tea or ginger candy", "Plain crackers or toast", "Fresh air and slow breathing", "Avoid strong smells for a while"],
        "otc": ["dimenhydrinate", "bismuth"],
        "doctor_if": "you cannot keep fluids down for a day, see blood, or have strong belly pain",
    },
    "bloating": {
        "home": ["A slow 10 minute walk", "Peppermint or fennel tea", "Skip fizzy drinks and gum today", "Eat slowly and smaller portions"],
        "otc": ["simethicone"],
        "doctor_if": "it lasts more than a couple of weeks or comes with weight loss or bleeding",
    },
    "stomach_ache": {
        "home": ["Warm water bottle on your belly", "Peppermint or ginger tea", "Bland food like rice, toast or banana", "Rest and small sips of water"],
        "otc": ["calcium_carbonate", "simethicone", "bismuth"],
        "doctor_if": "the pain is severe, keeps getting worse, sits low on the right side, or comes with fever or vomiting",
    },
    "constipation": {
        "home": ["Two extra glasses of water today", "Fibre: oats, prunes, kiwi, lentils", "A 15 minute walk", "Warm drink first thing in the morning"],
        "otc": ["peg"],
        "doctor_if": "it lasts more than a week, or there is blood or strong pain",
    },
    "diarrhea": {
        "home": ["Replace fluids: water, broth, diluted juice", "Bland food: rice, banana, toast, applesauce", "Skip dairy, coffee and alcohol for a day"],
        "otc": ["ors", "loperamide", "bismuth"],
        "doctor_if": "there is blood, a high fever, signs of dehydration, or it lasts more than 2 days",
    },
    "cramps": {
        "home": ["Heating pad or hot water bottle on your lower belly", "A gentle walk or light stretching", "Warm shower", "Ginger tea", "Magnesium rich food: dark chocolate, nuts, leafy greens"],
        "otc": ["ibuprofen", "naproxen", "acetaminophen"],
        "doctor_if": "the pain stops you from normal life most months, bleeding is very heavy, or pain is new and severe",
    },
    "back_pain": {
        "home": ["Keep moving gently, short walks help more than bed rest", "Heat for 15 to 20 minutes", "Gentle stretches like knee to chest", "Check your chair and screen height"],
        "otc": ["acetaminophen", "ibuprofen", "naproxen"],
        "doctor_if": "you have numbness, weakness in your legs, trouble peeing, or pain after a fall",
    },
    "neck_pain": {
        "home": ["Heat on the sore area", "Slow neck rolls and shoulder shrugs", "Raise your screen to eye level", "Take breaks from looking down at your phone"],
        "otc": ["acetaminophen", "ibuprofen"],
        "doctor_if": "it comes with fever and a headache, or numbness down your arm",
    },
    "muscle_soreness": {
        "home": ["Gentle movement and stretching", "Warm bath or shower", "Protein and water today", "Ice for fresh strains, heat for stiffness"],
        "otc": ["acetaminophen", "ibuprofen"],
        "doctor_if": "there is swelling you cannot explain, or the pain is sharp and does not ease",
    },
    "cold": {
        "home": ["Rest and plenty of warm fluids", "Steam from a hot shower", "Honey in warm water or tea", "Saltwater gargle"],
        "otc": ["saline_spray", "acetaminophen", "pseudoephedrine"],
        "doctor_if": "it lasts more than 10 days, you have trouble breathing, or a fever over 3 days",
    },
    "sore_throat": {
        "home": ["Warm saltwater gargle", "Honey in warm water or tea", "Cold drinks or popsicles", "Rest your voice"],
        "otc": ["lozenges", "acetaminophen", "ibuprofen"],
        "doctor_if": "swallowing is very hard, you have a high fever, or white patches on your tonsils",
    },
    "cough": {
        "home": ["Honey in warm water", "Steam or a humidifier", "Prop yourself up with an extra pillow at night", "Stay hydrated"],
        "otc": ["dextromethorphan", "lozenges"],
        "doctor_if": "it lasts more than 3 weeks, you cough up blood, or you are short of breath",
    },
    "fever": {
        "home": ["Rest", "Drink more than usual", "Light clothing and a cool cloth", "Check your temperature again in a few hours"],
        "otc": ["acetaminophen", "ibuprofen"],
        "doctor_if": "it is over 39.5 C, lasts more than 3 days, or comes with a rash, stiff neck or confusion",
    },
    "allergies": {
        "home": ["Rinse your face and change clothes after being outside", "Keep windows closed on high pollen days", "Saline rinse"],
        "otc": ["cetirizine", "loratadine", "saline_spray"],
        "doctor_if": "you have wheezing, swelling of the face or throat, or nothing helps",
    },
    "insomnia": {
        "home": ["Same wake up time tomorrow, even if tired", "No screens for the last 30 minutes", "Cool, dark room", "If awake for 20 minutes, get up and do something calm, then try again", "Skip caffeine after noon"],
        "otc": ["melatonin"],
        "doctor_if": "poor sleep lasts more than a few weeks or affects your days",
    },
    "fatigue": {
        "home": ["Drink a glass of water", "Eat something with protein", "10 minutes outside in daylight", "A 20 minute nap before 3 PM", "Earlier bedtime tonight"],
        "otc": [],
        "doctor_if": "you are tired most days for weeks without a clear reason",
    },
    "stress": {
        "home": ["Breathe in for 4, hold for 4, out for 6, five times", "Write down the 3 things on your mind", "A 10 minute walk without your phone", "Text someone you like"],
        "otc": [],
        "doctor_if": "it is constant, affects sleep or eating, or you feel unable to cope",
    },
    "low_mood": {
        "home": ["Step outside for 10 minutes", "Eat something warm", "Message one person", "Shower and change into fresh clothes", "Do one small thing you can finish"],
        "otc": [],
        "doctor_if": "low mood lasts most days for 2 weeks or more",
    },
    "dizziness": {
        "home": ["Sit or lie down until it passes", "Drink water", "Eat something small", "Stand up slowly"],
        "otc": ["dimenhydrinate"],
        "doctor_if": "you faint, have chest pain, a racing heart, or trouble speaking",
    },
    "toothache": {
        "home": ["Warm saltwater rinse", "Cold compress on the cheek", "Avoid very hot, cold or sweet food"],
        "otc": ["ibuprofen", "acetaminophen"],
        "doctor_if": "there is swelling in your face or jaw, or fever. Book a dentist either way",
    },
    "skin_rash": {
        "home": ["Cool compress", "Fragrance free moisturizer", "Loose cotton clothing", "Think about anything new you used or ate"],
        "otc": ["hydrocortisone", "cetirizine"],
        "doctor_if": "it spreads fast, blisters, or comes with swelling of the face or trouble breathing",
    },
}

# Medication groups used for interaction checks. Lowercase substrings.
MED_GROUPS = {
    "anticoagulant": ["warfarin", "coumadin", "apixaban", "eliquis", "rivaroxaban", "xarelto", "dabigatran", "pradaxa", "edoxaban", "lixiana", "clopidogrel", "plavix", "ticagrelor", "brilinta", "heparin", "enoxaparin"],
    "nsaid": ["ibuprofen", "advil", "motrin", "naproxen", "aleve", "diclofenac", "voltaren", "celecoxib", "celebrex", "meloxicam", "mobicox", "ketorolac", "aspirin", "asa"],
    "ssri_snri": ["sertraline", "zoloft", "escitalopram", "cipralex", "lexapro", "citalopram", "celexa", "fluoxetine", "prozac", "paroxetine", "paxil", "fluvoxamine", "venlafaxine", "effexor", "desvenlafaxine", "pristiq", "duloxetine", "cymbalta", "vortioxetine", "trintellix"],
    "maoi": ["phenelzine", "nardil", "tranylcypromine", "parnate", "selegiline", "moclobemide", "rasagiline", "linezolid"],
    "ace_arb": ["lisinopril", "ramipril", "altace", "enalapril", "perindopril", "coversyl", "losartan", "cozaar", "valsartan", "diovan", "candesartan", "atacand", "irbesartan", "telmisartan", "micardis", "olmesartan"],
    "diuretic": ["hydrochlorothiazide", "hctz", "furosemide", "lasix", "spironolactone", "chlorthalidone", "indapamide"],
    "bp_other": ["amlodipine", "norvasc", "metoprolol", "atenolol", "bisoprolol", "propranolol", "nifedipine", "diltiazem"],
    "lithium": ["lithium"],
    "methotrexate": ["methotrexate"],
    "thyroid": ["levothyroxine", "synthroid", "eltroxin", "euthyrox"],
    "antibiotic_chelating": ["ciprofloxacin", "cipro", "levofloxacin", "moxifloxacin", "doxycycline", "minocycline", "tetracycline"],
    "sedative": ["lorazepam", "ativan", "alprazolam", "xanax", "clonazepam", "rivotril", "diazepam", "valium", "zopiclone", "imovane", "zolpidem", "gabapentin", "pregabalin", "lyrica", "oxycodone", "percocet", "hydromorphone", "morphine", "codeine", "tramadol", "quetiapine", "seroquel", "trazodone", "mirtazapine", "cyclobenzaprine"],
    "acetaminophen_combo": ["tylenol", "acetaminophen", "paracetamol", "percocet", "nyquil", "dayquil", "tylenol 3", "neocitran", "buckley's complete"],
    "clopidogrel": ["clopidogrel", "plavix"],
    "tizanidine": ["tizanidine", "zanaflex"],
    "stimulant": ["methylphenidate", "concerta", "ritalin", "lisdexamfetamine", "vyvanse", "adderall"],
}

# Rules: OTC key -> list of (group, level, reason). Level "avoid" removes the option, "caution" keeps it with a note.
INTERACTIONS = {
    "ibuprofen": [
        ("anticoagulant", "avoid", "raises bleeding risk with your blood thinner"),
        ("nsaid", "avoid", "doubles up with another anti-inflammatory you take"),
        ("ssri_snri", "caution", "together with your antidepressant this can raise bleeding risk"),
        ("ace_arb", "caution", "can affect kidneys and blood pressure with your blood pressure medicine"),
        ("diuretic", "caution", "can strain the kidneys with your water pill"),
        ("lithium", "avoid", "can raise lithium levels"),
        ("methotrexate", "avoid", "can raise methotrexate levels"),
    ],
    "naproxen": [
        ("anticoagulant", "avoid", "raises bleeding risk with your blood thinner"),
        ("nsaid", "avoid", "doubles up with another anti-inflammatory you take"),
        ("ssri_snri", "caution", "together with your antidepressant this can raise bleeding risk"),
        ("ace_arb", "caution", "can affect kidneys and blood pressure with your blood pressure medicine"),
        ("diuretic", "caution", "can strain the kidneys with your water pill"),
        ("lithium", "avoid", "can raise lithium levels"),
        ("methotrexate", "avoid", "can raise methotrexate levels"),
    ],
    "acetaminophen": [
        ("acetaminophen_combo", "caution", "one of your medicines already contains acetaminophen, so watch the total"),
        ("anticoagulant", "caution", "regular use can affect blood thinner levels"),
    ],
    "bismuth": [
        ("anticoagulant", "avoid", "contains a salicylate, which adds to bleeding risk"),
        ("nsaid", "caution", "contains a salicylate, similar to aspirin"),
        ("methotrexate", "avoid", "salicylates can raise methotrexate levels"),
    ],
    "calcium_carbonate": [
        ("thyroid", "caution", "take it at least 4 hours apart from your thyroid medicine"),
        ("antibiotic_chelating", "caution", "space it a few hours from your antibiotic"),
    ],
    "famotidine": [
        ("tizanidine", "caution", "may raise tizanidine levels"),
    ],
    "omeprazole": [
        ("clopidogrel", "avoid", "can make clopidogrel work less well"),
        ("methotrexate", "caution", "may raise methotrexate levels"),
    ],
    "diphenhydramine": [
        ("sedative", "avoid", "adds to drowsiness with your other medicine"),
        ("maoi", "avoid", "not a safe mix with your antidepressant"),
    ],
    "dimenhydrinate": [
        ("sedative", "avoid", "adds to drowsiness with your other medicine"),
        ("maoi", "avoid", "not a safe mix with your antidepressant"),
    ],
    "dextromethorphan": [
        ("maoi", "avoid", "can cause a serious reaction with MAO inhibitors"),
        ("ssri_snri", "caution", "can add to serotonin effects with your antidepressant"),
    ],
    "pseudoephedrine": [
        ("maoi", "avoid", "can cause dangerous blood pressure spikes"),
        ("ace_arb", "caution", "can raise blood pressure"),
        ("bp_other", "caution", "can raise blood pressure"),
        ("stimulant", "caution", "adds to stimulant effects"),
    ],
    "melatonin": [
        ("sedative", "caution", "adds to drowsiness"),
        ("anticoagulant", "caution", "may affect blood thinners"),
    ],
}

# Allergy words that rule out a whole family of options.
ALLERGY_FAMILIES = {
    "nsaid": ["ibuprofen", "naproxen", "bismuth"],
    "aspirin": ["ibuprofen", "naproxen", "bismuth"],
    "asa": ["ibuprofen", "naproxen", "bismuth"],
    "salicylate": ["bismuth"],
    "ibuprofen": ["ibuprofen", "naproxen"],
    "naproxen": ["naproxen", "ibuprofen"],
    "acetaminophen": ["acetaminophen"],
    "paracetamol": ["acetaminophen"],
    "tylenol": ["acetaminophen"],
    "antihistamine": ["loratadine", "cetirizine", "diphenhydramine", "dimenhydrinate"],
    "calcium": ["calcium_carbonate"],
}

# Mood suggestions. The first three come straight from the internet rule people swear by.
MOODS = {
    "everyone_hates_me": {
        "label": "Feeling like everyone hates you",
        "words": ["everyone hates me", "nobody likes me", "no one likes me", "everybody hates me", "people hate me"],
        "do": "Sleep",
        "why": "A tired brain turns small things into big ones. A nap or an early night often makes this feeling shrink.",
        "more": ["20 minute nap", "Early night, phone in another room", "Lie down with a calm playlist"],
    },
    "hate_everyone": {
        "label": "Feeling like you hate everyone",
        "words": ["hate everyone", "everyone is annoying", "everyone annoys me", "people are annoying", "irritated", "irritable", "snappy", "cranky"],
        "do": "Eat something",
        "why": "Hunger shows up as irritation more often than we think. Get some food with protein in it.",
        "more": ["Snack with protein", "A proper meal", "Glass of water too"],
    },
    "hate_myself": {
        "label": "Feeling like you hate yourself",
        "words": ["hate myself", "i'm useless", "i am useless", "i'm a failure", "i am a failure", "i'm disgusting", "feel gross"],
        "do": "Take a shower",
        "why": "Warm water and clean clothes reset more than you would expect. If this feeling is heavy or keeps coming back, please talk to someone.",
        "more": ["Shower and fresh clothes", "Open a window", "Text someone who likes you"],
    },
    "overwhelmed": {
        "label": "Overwhelmed",
        "words": ["overwhelmed", "too much", "drowning", "so much to do", "can't cope"],
        "do": "Write it down and pick one thing",
        "why": "Getting it out of your head and onto paper makes it smaller. Then do the easiest item first.",
        "more": ["List everything for 3 minutes", "Do one 10 minute task", "Say no to one thing"],
    },
    "anxious": {
        "label": "Anxious",
        "words": ["anxious", "anxiety", "panicky", "nervous", "on edge", "worried", "racing thoughts"],
        "do": "Slow your breathing",
        "why": "Long exhales tell your body it is safe. Try 4 in, 6 out, for a minute or two.",
        "more": ["Name 5 things you can see", "Cold water on your wrists", "Short walk outside"],
    },
    "lonely": {
        "label": "Lonely",
        "words": ["lonely", "alone", "isolated", "no one to talk to"],
        "do": "Reach out to one person",
        "why": "One short message is enough. Most people are glad to hear from you.",
        "more": ["Send a voice note", "Call family", "Go somewhere with people around"],
    },
    "sad": {
        "label": "Sad",
        "words": ["sad", "feeling down", "feeling blue", "crying", "heartbroken", "feeling low"],
        "do": "Gentle movement",
        "why": "A slow walk or stretching lifts mood a little, and a little is enough for today.",
        "more": ["10 minute walk", "Comfort show or music", "Something warm to eat or drink"],
    },
    "exhausted": {
        "label": "Mentally drained",
        "words": ["drained", "burnt out", "burned out", "exhausted", "fried", "brain is mush"],
        "do": "Screen break",
        "why": "Ten minutes away from every screen gives your attention a real rest.",
        "more": ["Look out a window", "Stretch", "Lie down with eyes closed"],
    },
    "cant_focus": {
        "label": "Can't focus",
        "words": ["can't focus", "cannot focus", "distracted", "foggy", "brain fog", "scattered"],
        "do": "Water and a 25 minute timer",
        "why": "Mild dehydration hurts focus. Then work in one short block with your phone away.",
        "more": ["Glass of water", "Close extra tabs", "Walk around the block"],
    },
    "restless": {
        "label": "Restless",
        "words": ["restless", "bored", "antsy", "fidgety"],
        "do": "Move your body",
        "why": "Restless energy wants to go somewhere. Use it.",
        "more": ["Quick workout", "Dance to one song", "Tidy one area"],
    },
    "cant_sleep": {
        "label": "Can't sleep",
        "words": ["can't sleep", "cannot sleep", "wide awake", "mind won't stop"],
        "do": "Wind down routine",
        "why": "Dim lights, no screens, and something boring to read work better than trying hard to sleep.",
        "more": ["Dim the lights", "Write down tomorrow's to do list", "Warm non caffeine drink"],
    },
    "good": {
        "label": "Feeling good",
        "words": ["happy", "great", "good day", "amazing", "energized", "motivated", "calm", "grateful"],
        "do": "Notice what helped",
        "why": "Write down what went right today. It is useful data for a harder day.",
        "more": ["Save a note about today", "Share it with someone", "Keep the routine going"],
    },
}

# Cycle phase tips. Plain, gentle, no promises of pain free periods.
CYCLE_TIPS = {
    "menstrual": {
        "title": "Period days",
        "tips": ["Heat on your lower belly", "Gentle walk or stretching", "Iron rich food like lentils, spinach and eggs", "Drink plenty of water", "Rest when you can"],
    },
    "follicular": {
        "title": "Energy building",
        "tips": ["Good week for harder workouts", "Protein with each meal", "Get morning daylight", "Plan the bigger tasks now"],
    },
    "ovulation": {
        "title": "Around ovulation",
        "tips": ["Stay hydrated", "Keep moving every day", "Some people notice a slight twinge, which is common"],
    },
    "luteal": {
        "title": "Before your period",
        "tips": ["Protein and fibre with each meal to keep energy steady", "Daily 20 to 30 minute walk, which may ease cramps later", "Magnesium rich food: nuts, seeds, leafy greens, dark chocolate", "Go easy on salt and caffeine to cut bloating", "Protect your sleep"],
    },
    "pre_period": {
        "title": "Period is close",
        "tips": ["Walk today, even 20 minutes", "Eat protein at breakfast", "Keep a heating pad and pads handy", "Warm ginger tea in the evening", "Lighter, earlier dinner"],
    },
}

DOCTOR_LINE = "Check with your doctor or pharmacist before taking anything new, especially with your other medicines."
