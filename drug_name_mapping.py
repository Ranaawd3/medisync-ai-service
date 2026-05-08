import psycopg2
 
# =====================================================
# DB CONFIG — غيّر الـ password والـ port حسب بيئتك
# لو على Railway: استخدم DATABASE_URL من environment
# =====================================================
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "medisync_db",
    "user": "postgres",
    "password": "123456789",
    "port": "5432"
}
 
# =====================================================
# Schema المتفق عليه في الـ Contract:
# Id           → UUID      (الباك بتولده)
# LocalName    → string    الاسم المحلي بالعربي أو التجاري
# GenericName  → string    الاسم العلمي (Capitalized)
# ActiveIngredient → string  lowercase
# Country      → string    "EG"
# Source       → string    "manual" | "EDA" | "DrugBank"
#
# الأعمدة في الـ INSERT:
#   local_name, generic_name, active_ingredient, country, source
# =====================================================
 
# (local_name, generic_name, active_ingredient, country, source)
drug_mapping = [
 
    # ===== مسكنات الألم =====
    ("بروفين",       "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("Brufen",        "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("ادفيل",        "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("Advil",         "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("نيوروفين",     "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("Nurofen",       "Ibuprofen",    "ibuprofen",    "EG", "manual"),
    ("بنادول",       "Paracetamol",  "paracetamol",  "EG", "manual"),
    ("Panadol",       "Paracetamol",  "paracetamol",  "EG", "manual"),
    ("تايلينول",     "Paracetamol",  "paracetamol",  "EG", "manual"),
    ("Tylenol",       "Paracetamol",  "paracetamol",  "EG", "manual"),
    ("أسبرين",       "Aspirin",      "aspirin",       "EG", "manual"),
    ("Aspirin",       "Aspirin",      "aspirin",       "EG", "manual"),
    ("كتوفان",       "Ketoprofen",   "ketoprofen",    "EG", "manual"),
    ("Ketofan",       "Ketoprofen",   "ketoprofen",    "EG", "manual"),
    ("فولتارين",     "Diclofenac",   "diclofenac",   "EG", "manual"),
    ("Voltaren",      "Diclofenac",   "diclofenac",   "EG", "manual"),
    ("كتالجين",      "Diclofenac",   "diclofenac",   "EG", "manual"),
    ("Cataflam",      "Diclofenac",   "diclofenac",   "EG", "manual"),
    ("بروكسين",      "Piroxicam",    "piroxicam",     "EG", "manual"),
    ("Proxen",        "Piroxicam",    "piroxicam",     "EG", "manual"),
    ("أنالجين",      "Metamizole",   "metamizole",    "EG", "manual"),
    ("Analgin",       "Metamizole",   "metamizole",    "EG", "manual"),
 
    # ===== المضادات الحيوية =====
    ("أموكسيل",          "Amoxicillin",              "amoxicillin",      "EG", "manual"),
    ("Amoxil",            "Amoxicillin",              "amoxicillin",      "EG", "manual"),
    ("فلوموكس",          "Amoxicillin",              "amoxicillin",      "EG", "manual"),
    ("Flumox",            "Amoxicillin",              "amoxicillin",      "EG", "manual"),
    ("أوجمنتين",         "Amoxicillin/Clavulanate",  "amoxicillin",      "EG", "manual"),
    ("Augmentin",         "Amoxicillin/Clavulanate",  "amoxicillin",      "EG", "manual"),
    ("زيثروماكس",        "Azithromycin",             "azithromycin",     "EG", "manual"),
    ("Zithromax",         "Azithromycin",             "azithromycin",     "EG", "manual"),
    ("أزيثرال",          "Azithromycin",             "azithromycin",     "EG", "manual"),
    ("Azithral",          "Azithromycin",             "azithromycin",     "EG", "manual"),
    ("سيبروفلوكساسين",   "Ciprofloxacin",            "ciprofloxacin",    "EG", "manual"),
    ("Ciprofloxacin",     "Ciprofloxacin",            "ciprofloxacin",    "EG", "manual"),
    ("سيبروسين",         "Ciprofloxacin",            "ciprofloxacin",    "EG", "manual"),
    ("Ciprocin",          "Ciprofloxacin",            "ciprofloxacin",    "EG", "manual"),
    ("فلاجيل",           "Metronidazole",            "metronidazole",    "EG", "manual"),
    ("Flagyl",            "Metronidazole",            "metronidazole",    "EG", "manual"),
    ("كلاريثروميسين",    "Clarithromycin",           "clarithromycin",   "EG", "manual"),
    ("Klacid",            "Clarithromycin",           "clarithromycin",   "EG", "manual"),
    ("دوكسيسيكلين",      "Doxycycline",              "doxycycline",      "EG", "manual"),
    ("Doxycycline",       "Doxycycline",              "doxycycline",      "EG", "manual"),
    ("تتراسيكلين",       "Tetracycline",             "tetracycline",     "EG", "manual"),
    ("Tetracycline",      "Tetracycline",             "tetracycline",     "EG", "manual"),
    ("ليفوفلوكساسين",    "Levofloxacin",             "levofloxacin",     "EG", "manual"),
    ("Tavanic",           "Levofloxacin",             "levofloxacin",     "EG", "manual"),
    ("سيفيكسيم",         "Cefixime",                 "cefixime",         "EG", "manual"),
    ("Cefixime",          "Cefixime",                 "cefixime",         "EG", "manual"),
    ("سيفادروكسيل",      "Cefadroxil",               "cefadroxil",       "EG", "manual"),
    ("Cefadroxil",        "Cefadroxil",               "cefadroxil",       "EG", "manual"),
 
    # ===== أدوية القلب والضغط =====
    ("كونكور",           "Bisoprolol",       "bisoprolol",           "EG", "manual"),
    ("Concor",            "Bisoprolol",       "bisoprolol",           "EG", "manual"),
    ("كونكور كور",       "Bisoprolol",       "bisoprolol",           "EG", "manual"),
    ("Concor Cor",        "Bisoprolol",       "bisoprolol",           "EG", "manual"),
    ("تنورمين",          "Atenolol",         "atenolol",             "EG", "manual"),
    ("Tenormin",          "Atenolol",         "atenolol",             "EG", "manual"),
    ("أتينول",           "Atenolol",         "atenolol",             "EG", "manual"),
    ("Atenolol",          "Atenolol",         "atenolol",             "EG", "manual"),
    ("نورفاسك",          "Amlodipine",       "amlodipine",           "EG", "manual"),
    ("Norvasc",           "Amlodipine",       "amlodipine",           "EG", "manual"),
    ("كوزار",            "Losartan",         "losartan",             "EG", "manual"),
    ("Cozaar",            "Losartan",         "losartan",             "EG", "manual"),
    ("ديوفان",           "Valsartan",        "valsartan",            "EG", "manual"),
    ("Diovan",            "Valsartan",        "valsartan",            "EG", "manual"),
    ("كابوتين",          "Captopril",        "captopril",            "EG", "manual"),
    ("Capoten",           "Captopril",        "captopril",            "EG", "manual"),
    ("ريني تيك",         "Enalapril",        "enalapril",            "EG", "manual"),
    ("Renitec",           "Enalapril",        "enalapril",            "EG", "manual"),
    ("زيستريل",          "Lisinopril",       "lisinopril",           "EG", "manual"),
    ("Zestril",           "Lisinopril",       "lisinopril",           "EG", "manual"),
    ("فيلودبين",         "Felodipine",       "felodipine",           "EG", "manual"),
    ("Plendil",           "Felodipine",       "felodipine",           "EG", "manual"),
    ("ديلتيازيم",        "Diltiazem",        "diltiazem",            "EG", "manual"),
    ("Diltiazem",         "Diltiazem",        "diltiazem",            "EG", "manual"),
    ("أميودارون",        "Amiodarone",       "amiodarone",           "EG", "manual"),
    ("Cordarone",         "Amiodarone",       "amiodarone",           "EG", "manual"),
    ("ديجوكسين",         "Digoxin",          "digoxin",              "EG", "manual"),
    ("Digoxin",           "Digoxin",          "digoxin",              "EG", "manual"),
    ("فيراباميل",        "Verapamil",        "verapamil",            "EG", "manual"),
    ("Isoptin",           "Verapamil",        "verapamil",            "EG", "manual"),
    ("هيدروكلوروثيازيد", "Hydrochlorothiazide", "hydrochlorothiazide", "EG", "manual"),
    ("Hydrochlorothiazide","Hydrochlorothiazide", "hydrochlorothiazide", "EG", "manual"),
    ("لازيكس",           "Furosemide",       "furosemide",           "EG", "manual"),
    ("Lasix",             "Furosemide",       "furosemide",           "EG", "manual"),
    ("ألدكتون",          "Spironolactone",   "spironolactone",       "EG", "manual"),
    ("Aldactone",         "Spironolactone",   "spironolactone",       "EG", "manual"),
 
    # ===== أدوية السكر =====
    ("ديابيكون",    "Metformin",              "metformin",     "EG", "manual"),
    ("Diabicon",     "Metformin",              "metformin",     "EG", "manual"),
    ("جلوكوفاج",    "Metformin",              "metformin",     "EG", "manual"),
    ("Glucophage",   "Metformin",              "metformin",     "EG", "manual"),
    ("انتوبرال",    "Metformin",              "metformin",     "EG", "manual"),
    ("Metformin",    "Metformin",              "metformin",     "EG", "manual"),
    ("أماريل",      "Glimepiride",            "glimepiride",   "EG", "manual"),
    ("Amaryl",       "Glimepiride",            "glimepiride",   "EG", "manual"),
    ("جلوريل",      "Glimepiride",            "glimepiride",   "EG", "manual"),
    ("Gluril",       "Glimepiride",            "glimepiride",   "EG", "manual"),
    ("جانوميت",     "Sitagliptin/Metformin",  "sitagliptin",   "EG", "manual"),
    ("Janumet",      "Sitagliptin/Metformin",  "sitagliptin",   "EG", "manual"),
    ("جانوفيا",     "Sitagliptin",            "sitagliptin",   "EG", "manual"),
    ("Januvia",      "Sitagliptin",            "sitagliptin",   "EG", "manual"),
    ("فورسيجا",     "Dapagliflozin",          "dapagliflozin", "EG", "manual"),
    ("Forxiga",      "Dapagliflozin",          "dapagliflozin", "EG", "manual"),
    ("جارديانس",    "Empagliflozin",          "empagliflozin", "EG", "manual"),
    ("Jardiance",    "Empagliflozin",          "empagliflozin", "EG", "manual"),
    ("انسولين",     "Insulin",                "insulin",       "EG", "manual"),
    ("Insulin",      "Insulin",                "insulin",       "EG", "manual"),
    ("نوفوميكس",    "Insulin",                "insulin",       "EG", "manual"),
    ("Novomix",      "Insulin",                "insulin",       "EG", "manual"),
    ("ميكستارد",    "Insulin",                "insulin",       "EG", "manual"),
    ("Mixtard",      "Insulin",                "insulin",       "EG", "manual"),
 
    # ===== أدوية الكوليسترول =====
    ("كريستور",  "Rosuvastatin", "rosuvastatin", "EG", "manual"),
    ("Crestor",   "Rosuvastatin", "rosuvastatin", "EG", "manual"),
    ("ليبيتور",  "Atorvastatin", "atorvastatin", "EG", "manual"),
    ("Lipitor",   "Atorvastatin", "atorvastatin", "EG", "manual"),
    ("زوكور",    "Simvastatin",  "simvastatin",  "EG", "manual"),
    ("Zocor",     "Simvastatin",  "simvastatin",  "EG", "manual"),
    ("لوكول",    "Fluvastatin",  "fluvastatin",  "EG", "manual"),
    ("Lescol",    "Fluvastatin",  "fluvastatin",  "EG", "manual"),
    ("برافاكول", "Pravastatin",  "pravastatin",  "EG", "manual"),
    ("Pravachol", "Pravastatin",  "pravastatin",  "EG", "manual"),
 
    # ===== أدوية المعدة =====
    ("أوميز",       "Omeprazole",    "omeprazole",    "EG", "manual"),
    ("Omez",         "Omeprazole",    "omeprazole",    "EG", "manual"),
    ("لوسيك",       "Omeprazole",    "omeprazole",    "EG", "manual"),
    ("Losec",        "Omeprazole",    "omeprazole",    "EG", "manual"),
    ("نيكسيوم",     "Esomeprazole",  "esomeprazole",  "EG", "manual"),
    ("Nexium",       "Esomeprazole",  "esomeprazole",  "EG", "manual"),
    ("بانتوبرازول", "Pantoprazole",  "pantoprazole",  "EG", "manual"),
    ("Pantoprazole", "Pantoprazole",  "pantoprazole",  "EG", "manual"),
    ("كونترولوك",   "Pantoprazole",  "pantoprazole",  "EG", "manual"),
    ("Controloc",    "Pantoprazole",  "pantoprazole",  "EG", "manual"),
    ("زانتاك",      "Ranitidine",    "ranitidine",    "EG", "manual"),
    ("Zantac",       "Ranitidine",    "ranitidine",    "EG", "manual"),
    ("موتيليوم",    "Domperidone",   "domperidone",   "EG", "manual"),
    ("Motilium",     "Domperidone",   "domperidone",   "EG", "manual"),
    ("بريمبيران",   "Metoclopramide","metoclopramide","EG", "manual"),
    ("Primperan",    "Metoclopramide","metoclopramide","EG", "manual"),
 
    # ===== أدوية الغدة الدرقية =====
    ("سينثرويد",   "Levothyroxine", "levothyroxine", "EG", "manual"),
    ("Synthroid",   "Levothyroxine", "levothyroxine", "EG", "manual"),
    ("إلتروكسين",  "Levothyroxine", "levothyroxine", "EG", "manual"),
    ("Eltroxin",    "Levothyroxine", "levothyroxine", "EG", "manual"),
    ("كاربيمازول", "Carbimazole",   "carbimazole",   "EG", "manual"),
    ("Carbimazole", "Carbimazole",   "carbimazole",   "EG", "manual"),
    ("نيومركازول", "Carbimazole",   "carbimazole",   "EG", "manual"),
    ("Neomercazole","Carbimazole",   "carbimazole",   "EG", "manual"),
 
    # ===== أدوية الربو والتنفس =====
    ("فينتولين",         "Salbutamol",              "salbutamol",  "EG", "manual"),
    ("Ventolin",          "Salbutamol",              "salbutamol",  "EG", "manual"),
    ("سيريتيد",          "Fluticasone/Salmeterol",  "fluticasone", "EG", "manual"),
    ("Seretide",          "Fluticasone/Salmeterol",  "fluticasone", "EG", "manual"),
    ("بيكوتيد",          "Fluticasone",             "fluticasone", "EG", "manual"),
    ("Becotide",          "Fluticasone",             "fluticasone", "EG", "manual"),
    ("ثيوفيلين",         "Theophylline",            "theophylline","EG", "manual"),
    ("Theophylline",      "Theophylline",            "theophylline","EG", "manual"),
    ("مونتيلوكاست",      "Montelukast",             "montelukast", "EG", "manual"),
    ("Singulair",         "Montelukast",             "montelukast", "EG", "manual"),
 
    # ===== أدوية الأعصاب والنوم =====
    ("ريفوتريل",  "Clonazepam",   "clonazepam",   "EG", "manual"),
    ("Rivotril",   "Clonazepam",   "clonazepam",   "EG", "manual"),
    ("زاناكس",    "Alprazolam",   "alprazolam",   "EG", "manual"),
    ("Xanax",      "Alprazolam",   "alprazolam",   "EG", "manual"),
    ("فاليوم",    "Diazepam",     "diazepam",     "EG", "manual"),
    ("Valium",     "Diazepam",     "diazepam",     "EG", "manual"),
    ("تيجريتول",  "Carbamazepine","carbamazepine","EG", "manual"),
    ("Tegretol",   "Carbamazepine","carbamazepine","EG", "manual"),
    ("ديباكين",   "Valproate",    "valproate",    "EG", "manual"),
    ("Depakine",   "Valproate",    "valproate",    "EG", "manual"),
    ("نيوروتين",  "Gabapentin",   "gabapentin",   "EG", "manual"),
    ("Neurontin",  "Gabapentin",   "gabapentin",   "EG", "manual"),
    ("ليريكا",    "Pregabalin",   "pregabalin",   "EG", "manual"),
    ("Lyrica",     "Pregabalin",   "pregabalin",   "EG", "manual"),
 
    # ===== مضادات التخثر =====
    ("وارفارين",    "Warfarin",     "warfarin",     "EG", "manual"),
    ("Warfarin",     "Warfarin",     "warfarin",     "EG", "manual"),
    ("كلوبيدوجريل", "Clopidogrel",  "clopidogrel",  "EG", "manual"),
    ("Plavix",       "Clopidogrel",  "clopidogrel",  "EG", "manual"),
    ("بلافيكس",     "Clopidogrel",  "clopidogrel",  "EG", "manual"),
    ("Xarelto",      "Rivaroxaban",  "rivaroxaban",  "EG", "manual"),
    ("زاريلتو",     "Rivaroxaban",  "rivaroxaban",  "EG", "manual"),
 
    # ===== مضادات الاكتئاب =====
    ("بروزاك",  "Fluoxetine",  "fluoxetine",  "EG", "manual"),
    ("Prozac",   "Fluoxetine",  "fluoxetine",  "EG", "manual"),
    ("زولوفت",  "Sertraline",  "sertraline",  "EG", "manual"),
    ("Zoloft",   "Sertraline",  "sertraline",  "EG", "manual"),
    ("سيبرالكس","Escitalopram","escitalopram","EG", "manual"),
    ("Cipralex", "Escitalopram","escitalopram","EG", "manual"),
    ("إيفكسور", "Venlafaxine", "venlafaxine", "EG", "manual"),
    ("Effexor",  "Venlafaxine", "venlafaxine", "EG", "manual"),
 
    # ===== الكورتيزون =====
    ("بريدنيزون",   "Prednisone",    "prednisone",    "EG", "manual"),
    ("Prednisone",   "Prednisone",    "prednisone",    "EG", "manual"),
    ("بريدنيزولون", "Prednisolone",  "prednisolone",  "EG", "manual"),
    ("Prednisolone", "Prednisolone",  "prednisolone",  "EG", "manual"),
    ("ديكساميثازون","Dexamethasone", "dexamethasone", "EG", "manual"),
    ("Dexamethasone","Dexamethasone", "dexamethasone", "EG", "manual"),
 
    # ===== مضادات الهيستامين =====
    ("زيرتيك",  "Cetirizine",   "cetirizine",   "EG", "manual"),
    ("Zyrtec",   "Cetirizine",   "cetirizine",   "EG", "manual"),
    ("كلاريتين","Loratadine",   "loratadine",   "EG", "manual"),
    ("Claritin", "Loratadine",   "loratadine",   "EG", "manual"),
    ("تيلفاست", "Fexofenadine", "fexofenadine", "EG", "manual"),
    ("Telfast",  "Fexofenadine", "fexofenadine", "EG", "manual"),
 
    # ===== فيتامينات ومكملات =====
    ("نيوروبيون",    "Vitamin B Complex","vitamin b", "EG", "manual"),
    ("Neurobion",     "Vitamin B Complex","vitamin b", "EG", "manual"),
    ("كالسيوم",      "Calcium",          "calcium",   "EG", "manual"),
    ("Calcium",       "Calcium",          "calcium",   "EG", "manual"),
    ("فيتامين د",    "Vitamin D",         "vitamin d", "EG", "manual"),
    ("Vitamin D",     "Vitamin D",         "vitamin d", "EG", "manual"),
    ("فيروجلوبين",   "Iron",              "iron",      "EG", "manual"),
    ("Ferrogradumet", "Iron",              "iron",      "EG", "manual"),
 
    # ===== أدوية العيون =====
    ("زانتن",     "Tobramycin",              "tobramycin", "EG", "manual"),
    ("Tobradex",   "Tobramycin/Dexamethasone","tobramycin", "EG", "manual"),
    ("جانتاميسين","Gentamicin",              "gentamicin", "EG", "manual"),
    ("Gentamicin", "Gentamicin",              "gentamicin", "EG", "manual"),
 
    # ===== أدوية النقرس =====
    ("زيلوريك",  "Allopurinol", "allopurinol", "EG", "manual"),
    ("Zyloric",   "Allopurinol", "allopurinol", "EG", "manual"),
    ("كولشيسين", "Colchicine",  "colchicine",  "EG", "manual"),
    ("Colchicine","Colchicine",  "colchicine",  "EG", "manual"),
]
 
 
def add_mapping():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
 
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
 
    for local_name, generic_name, active_ingredient, country, source in drug_mapping:
        try:
            cursor.execute("""
                INSERT INTO "DrugNameMappings"
                    ("LocalName", "GenericName", "ActiveIngredient", "Country", "Source")
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (local_name, generic_name, active_ingredient, country, source))
 
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
 
        except Exception as e:
            print(f"❌ Error inserting '{local_name}': {e}")
            skipped += 1
 
    conn.commit()
    cursor.close()
    conn.close()
 
    print(f"\n✅ Done!")
    print(f"   Inserted : {inserted}")
    print(f"   Skipped  : {skipped}")
    print(f"   Total    : {len(drug_mapping)}")
 
 
if __name__ == "__main__":
    add_mapping()