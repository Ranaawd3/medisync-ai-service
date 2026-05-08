import psycopg2
import uuid
import json
 
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
# Id               → UUID
# Drug1Ingredient  → string  lowercase  "ibuprofen"
# Drug2Ingredient  → string  lowercase  "aspirin"
# Severity         → string  "HIGH" | "MODERATE" | "LOW"
# DescriptionAr    → string  شرح بالعربي للمريض
# DescriptionEn    → string  شرح بالإنجليزي
# Mechanism        → string? آلية التفاعل (nullable)
# Alternatives     → string[] قائمة بدائل آمنة (text[])
# Source           → string  "DrugBank" | "OpenFDA" | "Manual"
# LastReviewed     → string  "YYYY-MM-DD"
#
# الأعمدة في الـ INSERT:
#   drug1_ingredient, drug2_ingredient, severity,
#   description_ar, description_en, mechanism, alternatives, source, last_reviewed
# =====================================================
 
# (drug1, drug2, severity, description_ar, description_en, mechanism, alternatives, source)
interactions = [
 
    # ===== أسبرين =====
    ("aspirin", "heparin", "HIGH",
     "خطر نزيف شديد عند استخدامهما معاً",
     "Increased risk of bleeding when used together",
     "Additive antiplatelet and anticoagulant effects",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "warfarin", "HIGH",
     "خطر نزيف شديد جداً — يزيد من تأثير مميع الدم بشكل كبير",
     "Significantly increases bleeding risk",
     "Aspirin inhibits platelet aggregation while warfarin inhibits clotting factors",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "clopidogrel", "MODERATE",
     "زيادة خطر النزيف — استخدم بحذر",
     "Increased bleeding risk, use with caution",
     "Dual antiplatelet effect",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "ibuprofen", "MODERATE",
     "الإيبوبروفين قد يقلل من التأثير الوقائي للأسبرين على القلب",
     "Ibuprofen may reduce aspirin cardioprotective effect",
     "Ibuprofen competitively inhibits COX-1 binding site of aspirin",
     ["paracetamol", "diclofenac"], "Manual"),
 
    ("aspirin", "methotrexate", "HIGH",
     "الأسبرين يزيد من سمية الميثوتريكسات",
     "Aspirin increases methotrexate toxicity",
     "Aspirin reduces renal clearance of methotrexate",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "prednisolone", "HIGH",
     "زيادة خطر نزيف المعدة",
     "Increased risk of GI bleeding",
     "Both drugs cause gastric irritation independently",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "diclofenac", "MODERATE",
     "زيادة خطر نزيف المعدة",
     "Increased GI bleeding risk",
     "Additive GI irritation",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "enoxaparin", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive anticoagulant effect",
     ["paracetamol"], "Manual"),
 
    ("aspirin", "alcohol", "HIGH",
     "زيادة خطر نزيف المعدة بشكل كبير",
     "Increased risk of stomach bleeding",
     "Both irritate gastric mucosa",
     ["paracetamol"], "Manual"),
 
    # ===== هيبارين =====
    ("heparin", "warfarin", "HIGH",
     "تأثير مضاعف لمميع الدم — راقب المريض عن كثب",
     "Additive anticoagulant effect, monitor closely",
     "Both inhibit different steps of coagulation cascade",
     [], "Manual"),
 
    ("heparin", "clopidogrel", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive antiplatelet and anticoagulant effects",
     [], "Manual"),
 
    ("heparin", "ibuprofen", "HIGH",
     "مضادات الالتهاب تزيد خطر النزيف مع الهيبارين",
     "NSAIDs increase bleeding risk with heparin",
     "NSAIDs inhibit platelet aggregation",
     ["paracetamol"], "Manual"),
 
    ("heparin", "diclofenac", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "NSAIDs inhibit platelet aggregation",
     ["paracetamol"], "Manual"),
 
    # ===== وارفارين =====
    ("warfarin", "aspirin", "HIGH",
     "خطر نزيف كبير جداً",
     "Major bleeding risk",
     "Additive anticoagulant and antiplatelet effects",
     ["paracetamol"], "Manual"),
 
    ("warfarin", "ibuprofen", "HIGH",
     "زيادة تأثير مميع الدم وخطر النزيف",
     "Increased anticoagulant effect and bleeding",
     "NSAIDs displace warfarin from protein binding",
     ["paracetamol"], "Manual"),
 
    ("warfarin", "diclofenac", "HIGH",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "NSAIDs displace warfarin from protein binding",
     ["paracetamol"], "Manual"),
 
    ("warfarin", "amoxicillin", "MODERATE",
     "المضادات الحيوية قد تزيد من تأثير الوارفارين",
     "Antibiotics may increase warfarin effect",
     "Antibiotics reduce vitamin K producing gut bacteria",
     [], "Manual"),
 
    ("warfarin", "ciprofloxacin", "HIGH",
     "السيبروفلوكساسين يزيد من تأثير الوارفارين بشكل ملحوظ",
     "Ciprofloxacin significantly increases warfarin effect",
     "CYP1A2 and CYP2C9 inhibition",
     [], "Manual"),
 
    ("warfarin", "metronidazole", "HIGH",
     "زيادة كبيرة في تأثير مميع الدم",
     "Major increase in anticoagulant effect",
     "CYP2C9 inhibition by metronidazole",
     [], "Manual"),
 
    ("warfarin", "azithromycin", "MODERATE",
     "زيادة في تأثير مميع الدم",
     "Increased anticoagulant effect",
     "Possible CYP2C9 inhibition",
     [], "Manual"),
 
    ("warfarin", "fluconazole", "HIGH",
     "الفلوكونازول يضاعف تأثير الوارفارين",
     "Fluconazole doubles warfarin effect",
     "Strong CYP2C9 inhibition",
     [], "Manual"),
 
    ("warfarin", "omeprazole", "MODERATE",
     "قد يزيد من مستويات الوارفارين",
     "May increase warfarin levels",
     "CYP2C19 inhibition",
     [], "Manual"),
 
    ("warfarin", "simvastatin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("warfarin", "atorvastatin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("warfarin", "carbamazepine", "MODERATE",
     "الكاربامازيبين يقلل من فاعلية الوارفارين",
     "Carbamazepine reduces warfarin effectiveness",
     "CYP2C9 induction by carbamazepine",
     [], "Manual"),
 
    ("warfarin", "rifampicin", "HIGH",
     "الريفامبيسين يقلل من تأثير الوارفارين بشكل كبير",
     "Rifampicin significantly reduces warfarin effect",
     "Strong CYP2C9 and CYP3A4 induction",
     [], "Manual"),
 
    ("warfarin", "alcohol", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Alcohol affects warfarin metabolism unpredictably",
     [], "Manual"),
 
    ("warfarin", "levothyroxine", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "Thyroid hormone increases catabolism of clotting factors",
     [], "Manual"),
 
    ("warfarin", "amiodarone", "HIGH",
     "زيادة كبيرة جداً في تأثير مميع الدم",
     "Major increase in anticoagulant effect",
     "Strong CYP2C9 inhibition by amiodarone",
     [], "Manual"),
 
    ("warfarin", "clopidogrel", "HIGH",
     "زيادة كبيرة في خطر النزيف",
     "Increased bleeding risk",
     "Additive anticoagulant and antiplatelet effects",
     [], "Manual"),
 
    # ===== إيبوبروفين =====
    ("ibuprofen", "warfarin", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "NSAIDs displace warfarin from protein binding",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "lisinopril", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية أدوية الضغط",
     "NSAIDs reduce ACE inhibitor effectiveness",
     "NSAIDs cause sodium retention and vasoconstriction",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "losartan", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية أدوية الضغط",
     "NSAIDs reduce ARB effectiveness",
     "NSAIDs cause sodium retention and vasoconstriction",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "metformin", "MODERATE",
     "مضادات الالتهاب قد تضر الكلى مما يؤثر على الميتفورمين",
     "NSAIDs may worsen kidney function affecting metformin",
     "Reduced renal clearance of metformin",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "lithium", "HIGH",
     "الإيبوبروفين يرفع مستويات الليثيوم في الدم",
     "Ibuprofen increases lithium levels",
     "NSAIDs reduce renal clearance of lithium",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "methotrexate", "HIGH",
     "زيادة سمية الميثوتريكسات",
     "Increased methotrexate toxicity",
     "NSAIDs reduce renal clearance of methotrexate",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "prednisolone", "HIGH",
     "زيادة خطر نزيف المعدة",
     "Increased GI bleeding risk",
     "Additive GI irritation",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "furosemide", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية مدر البول",
     "NSAIDs reduce diuretic effectiveness",
     "NSAIDs cause sodium retention opposing diuresis",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "bisoprolol", "MODERATE",
     "مضادات الالتهاب تقلل من تأثير دواء الضغط",
     "NSAIDs reduce antihypertensive effect",
     "NSAIDs cause sodium retention and vasoconstriction",
     ["paracetamol"], "Manual"),
 
    ("ibuprofen", "alcohol", "HIGH",
     "زيادة خطر نزيف المعدة",
     "Increased GI bleeding risk",
     "Additive gastric irritation",
     ["paracetamol"], "Manual"),
 
    # ===== ميتفورمين =====
    ("metformin", "alcohol", "HIGH",
     "زيادة خطر تحمض الدم باللاكتات — خطير",
     "Increased risk of lactic acidosis",
     "Alcohol impairs hepatic lactate clearance",
     [], "Manual"),
 
    ("metformin", "furosemide", "MODERATE",
     "الفيروسيمايد قد يرفع مستويات الميتفورمين",
     "Furosemide may increase metformin levels",
     "Furosemide reduces renal clearance of metformin",
     [], "Manual"),
 
    ("metformin", "ciprofloxacin", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Fluoroquinolones stimulate insulin secretion",
     [], "Manual"),
 
    ("metformin", "glimepiride", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Additive blood glucose lowering effect",
     [], "Manual"),
 
    ("metformin", "insulin", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Additive blood glucose lowering effect",
     [], "Manual"),
 
    # ===== بيسوبرولول =====
    ("bisoprolol", "verapamil", "HIGH",
     "خطر تباطؤ شديد في ضربات القلب وتوقف في التوصيل الكهربائي",
     "Risk of severe bradycardia and heart block",
     "Additive negative chronotropic and dromotropic effects",
     [], "Manual"),
 
    ("bisoprolol", "diltiazem", "HIGH",
     "خطر تباطؤ ضربات القلب وتوقف في التوصيل",
     "Risk of bradycardia and heart block",
     "Additive negative chronotropic effects",
     [], "Manual"),
 
    ("bisoprolol", "amiodarone", "MODERATE",
     "خطر تباطؤ ضربات القلب",
     "Risk of bradycardia",
     "Additive negative chronotropic effects",
     [], "Manual"),
 
    ("bisoprolol", "digoxin", "MODERATE",
     "تأثير مضاعف في إبطاء ضربات القلب",
     "Additive bradycardia effect",
     "Both drugs slow AV conduction",
     [], "Manual"),
 
    ("bisoprolol", "insulin", "MODERATE",
     "حاصرات بيتا تخفي أعراض انخفاض السكر",
     "Beta blockers mask hypoglycemia symptoms",
     "Beta-blockade masks tachycardia and tremor of hypoglycemia",
     [], "Manual"),
 
    ("bisoprolol", "glimepiride", "MODERATE",
     "حاصرات بيتا تخفي أعراض انخفاض السكر",
     "Beta blockers mask hypoglycemia symptoms",
     "Beta-blockade masks tachycardia and tremor of hypoglycemia",
     [], "Manual"),
 
    ("bisoprolol", "ibuprofen", "MODERATE",
     "مضادات الالتهاب تقلل من تأثير دواء الضغط",
     "NSAIDs reduce antihypertensive effect",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("bisoprolol", "amlodipine", "MODERATE",
     "تأثير مضاعف في خفض الضغط",
     "Additive hypotensive effect",
     "Additive antihypertensive mechanisms",
     [], "Manual"),
 
    ("bisoprolol", "fluoxetine", "MODERATE",
     "الفلوكستين يرفع مستويات البيسوبرولول في الدم",
     "Fluoxetine increases bisoprolol levels",
     "CYP2D6 inhibition by fluoxetine",
     [], "Manual"),
 
    # ===== أملوديبين =====
    ("amlodipine", "simvastatin", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Amlodipine inhibits CYP3A4 metabolism of simvastatin",
     ["rosuvastatin", "pravastatin"], "Manual"),
 
    ("amlodipine", "cyclosporine", "MODERATE",
     "الأملوديبين يرفع مستويات السيكلوسبورين",
     "Amlodipine increases cyclosporine levels",
     "CYP3A4 competition",
     [], "Manual"),
 
    ("amlodipine", "rifampicin", "MODERATE",
     "الريفامبيسين يقلل من تأثير الأملوديبين",
     "Rifampicin reduces amlodipine levels",
     "CYP3A4 induction by rifampicin",
     [], "Manual"),
 
    ("amlodipine", "clarithromycin", "MODERATE",
     "زيادة مستويات الأملوديبين في الدم",
     "Increased amlodipine levels",
     "CYP3A4 inhibition by clarithromycin",
     [], "Manual"),
 
    # ===== لوسارتان =====
    ("losartan", "spironolactone", "HIGH",
     "خطر ارتفاع البوتاسيوم في الدم — خطير",
     "Risk of hyperkalemia",
     "Both drugs increase serum potassium",
     [], "Manual"),
 
    ("losartan", "ibuprofen", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية دواء الضغط",
     "NSAIDs reduce ARB effectiveness",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("losartan", "lithium", "MODERATE",
     "اللوسارتان يرفع مستويات الليثيوم",
     "Losartan increases lithium levels",
     "Reduced renal clearance of lithium",
     [], "Manual"),
 
    ("losartan", "lisinopril", "HIGH",
     "زيادة خطر مشاكل الكلى وارتفاع البوتاسيوم",
     "Increased risk of kidney problems and hyperkalemia",
     "Dual RAAS blockade increases renal impairment risk",
     [], "Manual"),
 
    # ===== ليزينوبريل =====
    ("lisinopril", "spironolactone", "HIGH",
     "خطر ارتفاع البوتاسيوم في الدم",
     "Risk of hyperkalemia",
     "Both drugs increase serum potassium",
     [], "Manual"),
 
    ("lisinopril", "ibuprofen", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية دواء الضغط",
     "NSAIDs reduce ACE inhibitor effect",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("lisinopril", "lithium", "MODERATE",
     "الليزينوبريل يرفع مستويات الليثيوم",
     "Lisinopril increases lithium levels",
     "ACE inhibitors reduce renal clearance of lithium",
     [], "Manual"),
 
    ("lisinopril", "allopurinol", "MODERATE",
     "زيادة خطر الحساسية",
     "Increased risk of allergic reaction",
     "Mechanism not fully established",
     [], "Manual"),
 
    ("lisinopril", "losartan", "HIGH",
     "الحصار المزدوج للـ RAAS يزيد من خطر الكلى",
     "Dual blockade increases kidney risk",
     "Dual RAAS blockade increases renal impairment risk",
     [], "Manual"),
 
    # ===== روسوفاستاتين =====
    ("rosuvastatin", "cyclosporine", "HIGH",
     "زيادة كبيرة في مستويات الروسوفاستاتين — خطر سمية العضلات",
     "Major increase in rosuvastatin levels",
     "Cyclosporine inhibits OATP1B1 transporter",
     ["pravastatin"], "Manual"),
 
    ("rosuvastatin", "gemfibrozil", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "Gemfibrozil inhibits OATP1B1 and CYP2C8",
     ["pravastatin"], "Manual"),
 
    ("rosuvastatin", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("rosuvastatin", "amiodarone", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Amiodarone inhibits OATP1B1",
     [], "Manual"),
 
    ("rosuvastatin", "colchicine", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Additive myopathy risk",
     [], "Manual"),
 
    # ===== أتورفاستاتين =====
    ("atorvastatin", "cyclosporine", "HIGH",
     "زيادة كبيرة في مستويات الأتورفاستاتين",
     "Major increase in atorvastatin levels",
     "Cyclosporine inhibits OATP1B1 and CYP3A4",
     ["pravastatin"], "Manual"),
 
    ("atorvastatin", "gemfibrozil", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "Additive myopathy risk",
     ["pravastatin"], "Manual"),
 
    ("atorvastatin", "clarithromycin", "MODERATE",
     "زيادة مستويات الأتورفاستاتين في الدم",
     "Increased atorvastatin levels",
     "CYP3A4 inhibition by clarithromycin",
     ["pravastatin"], "Manual"),
 
    ("atorvastatin", "amiodarone", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Additive myopathy risk",
     [], "Manual"),
 
    ("atorvastatin", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("atorvastatin", "colchicine", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Additive myopathy risk",
     [], "Manual"),
 
    ("atorvastatin", "digoxin", "MODERATE",
     "الأتورفاستاتين يرفع مستويات الديجوكسين",
     "Atorvastatin increases digoxin levels",
     "P-glycoprotein competition",
     [], "Manual"),
 
    # ===== أوميبرازول =====
    ("omeprazole", "clopidogrel", "HIGH",
     "الأوميبرازول يقلل من فاعلية الكلوبيدوجريل بشكل كبير",
     "Omeprazole significantly reduces clopidogrel effectiveness",
     "CYP2C19 inhibition reduces clopidogrel activation",
     ["pantoprazole", "rabeprazole"], "Manual"),
 
    ("omeprazole", "methotrexate", "MODERATE",
     "الأوميبرازول يرفع مستويات الميثوتريكسات",
     "Omeprazole increases methotrexate levels",
     "Reduced renal tubular secretion of methotrexate",
     ["pantoprazole"], "Manual"),
 
    ("omeprazole", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "CYP2C19 inhibition increases warfarin levels",
     ["pantoprazole"], "Manual"),
 
    ("omeprazole", "digoxin", "MODERATE",
     "الأوميبرازول يزيد من امتصاص الديجوكسين",
     "Omeprazole increases digoxin absorption",
     "Increased gastric pH increases digoxin absorption",
     [], "Manual"),
 
    ("omeprazole", "iron", "LOW",
     "الأوميبرازول يقلل من امتصاص الحديد",
     "Omeprazole reduces iron absorption",
     "Increased gastric pH reduces iron solubility",
     [], "Manual"),
 
    # ===== أموكسيسيلين =====
    ("amoxicillin", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "Antibiotics reduce vitamin K producing gut bacteria",
     [], "Manual"),
 
    ("amoxicillin", "methotrexate", "HIGH",
     "زيادة سمية الميثوتريكسات",
     "Increased methotrexate toxicity",
     "Amoxicillin reduces renal clearance of methotrexate",
     [], "Manual"),
 
    ("amoxicillin", "allopurinol", "MODERATE",
     "زيادة خطر الطفح الجلدي",
     "Increased risk of skin rash",
     "Mechanism not fully established",
     [], "Manual"),
 
    ("amoxicillin", "tetracycline", "MODERATE",
     "التتراسيكلين قد يقلل من فاعلية الأموكسيسيلين",
     "Tetracycline may reduce amoxicillin effectiveness",
     "Bacteriostatic drug may antagonize bactericidal effect",
     [], "Manual"),
 
    # ===== سيبروفلوكساسين =====
    ("ciprofloxacin", "warfarin", "HIGH",
     "يزيد من تأثير مميع الدم بشكل ملحوظ",
     "Significantly increases anticoagulant effect",
     "CYP1A2 and CYP2C9 inhibition",
     [], "Manual"),
 
    ("ciprofloxacin", "theophylline", "HIGH",
     "السيبروفلوكساسين يضاعف مستويات الثيوفيلين في الدم",
     "Ciprofloxacin doubles theophylline levels",
     "CYP1A2 inhibition by ciprofloxacin",
     [], "Manual"),
 
    ("ciprofloxacin", "antacids", "HIGH",
     "مضادات الحموضة تقلل من امتصاص السيبرو بنسبة 90%",
     "Antacids reduce ciprofloxacin absorption by 90%",
     "Chelation with divalent cations",
     [], "Manual"),
 
    ("ciprofloxacin", "iron", "HIGH",
     "الحديد يقلل من امتصاص السيبروفلوكساسين",
     "Iron reduces ciprofloxacin absorption",
     "Chelation with iron ions",
     [], "Manual"),
 
    ("ciprofloxacin", "tizanidine", "HIGH",
     "زيادة كبيرة في مستويات التيزانيدين — خطير",
     "Major increase in tizanidine levels",
     "CYP1A2 inhibition by ciprofloxacin",
     [], "Manual"),
 
    ("ciprofloxacin", "metformin", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Fluoroquinolones stimulate insulin secretion",
     [], "Manual"),
 
    ("ciprofloxacin", "metronidazole", "MODERATE",
     "زيادة الآثار الجانبية على الجهاز العصبي",
     "Increased CNS side effects",
     "Additive CNS effects",
     [], "Manual"),
 
    # ===== أزيثروميسين =====
    ("azithromycin", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "Possible CYP2C9 inhibition",
     [], "Manual"),
 
    ("azithromycin", "digoxin", "MODERATE",
     "الأزيثروميسين يرفع مستويات الديجوكسين",
     "Azithromycin increases digoxin levels",
     "Inhibition of gut bacteria that metabolize digoxin",
     [], "Manual"),
 
    ("azithromycin", "amiodarone", "HIGH",
     "خطر اضطرابات خطيرة في ضربات القلب",
     "Risk of serious cardiac arrhythmia",
     "Both prolong QT interval",
     [], "Manual"),
 
    ("azithromycin", "carbamazepine", "MODERATE",
     "زيادة مستويات الكاربامازيبين في الدم",
     "Increased carbamazepine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    # ===== ميترونيدازول =====
    ("metronidazole", "warfarin", "HIGH",
     "زيادة كبيرة في تأثير مميع الدم",
     "Major increase in anticoagulant effect",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("metronidazole", "alcohol", "HIGH",
     "غثيان شديد وقيء واحمرار الوجه — تأثير ديسولفيرام",
     "Severe nausea, vomiting, flushing",
     "Disulfiram-like reaction — inhibition of aldehyde dehydrogenase",
     [], "Manual"),
 
    ("metronidazole", "lithium", "MODERATE",
     "زيادة سمية الليثيوم",
     "Increased lithium toxicity",
     "Reduced renal clearance of lithium",
     [], "Manual"),
 
    ("metronidazole", "phenytoin", "MODERATE",
     "الميترونيدازول يرفع مستويات الفينيتوين",
     "Metronidazole increases phenytoin levels",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("metronidazole", "disulfiram", "HIGH",
     "تفاعلات نفسية وارتباك",
     "Psychotic reactions and confusion",
     "Additive CNS toxicity",
     [], "Manual"),
 
    # ===== ديجوكسين =====
    ("digoxin", "amiodarone", "HIGH",
     "زيادة كبيرة في مستويات الديجوكسين — خطر التسمم",
     "Major increase in digoxin toxicity",
     "Amiodarone inhibits P-glycoprotein and renal clearance",
     [], "Manual"),
 
    ("digoxin", "verapamil", "HIGH",
     "الفيراباميل يضاعف مستويات الديجوكسين",
     "Verapamil doubles digoxin levels",
     "Verapamil inhibits P-glycoprotein",
     [], "Manual"),
 
    ("digoxin", "spironolactone", "MODERATE",
     "السبيرونولاكتون قد يرفع مستويات الديجوكسين",
     "Spironolactone may increase digoxin levels",
     "Competition for renal tubular secretion",
     [], "Manual"),
 
    ("digoxin", "bisoprolol", "MODERATE",
     "تأثير مضاعف في إبطاء ضربات القلب",
     "Additive bradycardia",
     "Both slow AV conduction",
     [], "Manual"),
 
    ("digoxin", "clarithromycin", "HIGH",
     "الكلاريثروميسين يرفع مستويات الديجوكسين بشكل خطير",
     "Clarithromycin increases digoxin levels",
     "Inhibition of gut bacteria metabolizing digoxin + P-gp inhibition",
     [], "Manual"),
 
    ("digoxin", "furosemide", "MODERATE",
     "نقص البوتاسيوم من الفيروسيمايد يزيد سمية الديجوكسين",
     "Hypokalemia from furosemide increases digoxin toxicity",
     "Hypokalemia increases digoxin binding to Na/K ATPase",
     [], "Manual"),
 
    ("digoxin", "antacids", "MODERATE",
     "مضادات الحموضة تقلل من امتصاص الديجوكسين",
     "Antacids reduce digoxin absorption",
     "Adsorption of digoxin to antacid",
     [], "Manual"),
 
    # ===== أميودارون =====
    ("amiodarone", "warfarin", "HIGH",
     "زيادة كبيرة جداً في تأثير مميع الدم",
     "Major increase in anticoagulant effect",
     "Strong CYP2C9 inhibition",
     [], "Manual"),
 
    ("amiodarone", "digoxin", "HIGH",
     "زيادة كبيرة في مستويات الديجوكسين — خطر التسمم",
     "Major increase in digoxin toxicity",
     "P-glycoprotein inhibition by amiodarone",
     [], "Manual"),
 
    ("amiodarone", "simvastatin", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "CYP3A4 inhibition by amiodarone",
     ["rosuvastatin", "pravastatin"], "Manual"),
 
    ("amiodarone", "bisoprolol", "MODERATE",
     "خطر تباطؤ ضربات القلب",
     "Risk of bradycardia",
     "Additive negative chronotropic effects",
     [], "Manual"),
 
    ("amiodarone", "azithromycin", "HIGH",
     "خطر اضطرابات خطيرة في ضربات القلب",
     "Risk of serious cardiac arrhythmia",
     "Both prolong QT interval",
     [], "Manual"),
 
    ("amiodarone", "rosuvastatin", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "OATP1B1 inhibition by amiodarone",
     ["pravastatin"], "Manual"),
 
    # ===== فيروسيمايد =====
    ("furosemide", "ibuprofen", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية مدر البول",
     "NSAIDs reduce diuretic effectiveness",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("furosemide", "digoxin", "MODERATE",
     "نقص البوتاسيوم يزيد من سمية الديجوكسين",
     "Hypokalemia increases digoxin toxicity",
     "Furosemide-induced hypokalemia sensitizes heart to digoxin",
     [], "Manual"),
 
    ("furosemide", "lithium", "HIGH",
     "الفيروسيمايد يرفع مستويات الليثيوم بشكل خطير",
     "Furosemide increases lithium levels",
     "Volume depletion increases proximal tubular reabsorption of lithium",
     [], "Manual"),
 
    ("furosemide", "gentamicin", "HIGH",
     "زيادة سمية الكلى والأذن",
     "Additive nephrotoxicity and ototoxicity",
     "Additive toxic effects on renal tubules and cochlea",
     [], "Manual"),
 
    ("furosemide", "metformin", "MODERATE",
     "الفيروسيمايد قد يرفع مستويات الميتفورمين",
     "Furosemide may increase metformin levels",
     "Competition for renal tubular secretion",
     [], "Manual"),
 
    # ===== سبيرونولاكتون =====
    ("spironolactone", "lisinopril", "HIGH",
     "خطر ارتفاع البوتاسيوم في الدم — خطير",
     "Risk of hyperkalemia",
     "Both drugs increase serum potassium",
     [], "Manual"),
 
    ("spironolactone", "losartan", "HIGH",
     "خطر ارتفاع البوتاسيوم في الدم",
     "Risk of hyperkalemia",
     "Both drugs increase serum potassium",
     [], "Manual"),
 
    ("spironolactone", "ibuprofen", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية مدر البول",
     "NSAIDs reduce diuretic effectiveness",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("spironolactone", "digoxin", "MODERATE",
     "قد يرفع مستويات الديجوكسين",
     "May increase digoxin levels",
     "Competition for renal tubular secretion",
     [], "Manual"),
 
    ("spironolactone", "lithium", "MODERATE",
     "تقليل من إزالة الليثيوم",
     "Reduced lithium clearance",
     "Reduced renal clearance of lithium",
     [], "Manual"),
 
    # ===== بريدنيزولون =====
    ("prednisolone", "ibuprofen", "HIGH",
     "زيادة خطر نزيف المعدة",
     "Increased GI bleeding risk",
     "Additive GI irritation",
     ["paracetamol"], "Manual"),
 
    ("prednisolone", "aspirin", "HIGH",
     "زيادة خطر نزيف المعدة",
     "Increased GI bleeding risk",
     "Additive GI irritation",
     ["paracetamol"], "Manual"),
 
    ("prednisolone", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "Uncertain mechanism",
     [], "Manual"),
 
    ("prednisolone", "insulin", "MODERATE",
     "الكورتيزونات ترفع مستوى السكر",
     "Corticosteroids increase blood glucose",
     "Glucocorticoids cause insulin resistance and gluconeogenesis",
     [], "Manual"),
 
    ("prednisolone", "metformin", "MODERATE",
     "الكورتيزونات ترفع مستوى السكر",
     "Corticosteroids increase blood glucose",
     "Glucocorticoids cause insulin resistance",
     [], "Manual"),
 
    ("prednisolone", "ketoconazole", "MODERATE",
     "الكيتوكونازول يرفع مستويات البريدنيزولون",
     "Ketoconazole increases prednisolone levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("prednisolone", "rifampicin", "MODERATE",
     "الريفامبيسين يقلل من تأثير البريدنيزولون",
     "Rifampicin reduces prednisolone effect",
     "CYP3A4 induction by rifampicin",
     [], "Manual"),
 
    ("prednisolone", "furosemide", "MODERATE",
     "تأثير مضاعف في فقد البوتاسيوم",
     "Additive potassium loss",
     "Both drugs cause hypokalemia",
     [], "Manual"),
 
    ("prednisolone", "digoxin", "MODERATE",
     "نقص البوتاسيوم يزيد من سمية الديجوكسين",
     "Hypokalemia increases digoxin toxicity",
     "Prednisolone-induced hypokalemia sensitizes heart to digoxin",
     [], "Manual"),
 
    # ===== ليفوثيروكسين =====
    ("levothyroxine", "antacids", "MODERATE",
     "مضادات الحموضة تقلل من امتصاص هرمون الغدة",
     "Antacids reduce levothyroxine absorption",
     "Chelation and adsorption",
     [], "Manual"),
 
    ("levothyroxine", "calcium", "MODERATE",
     "الكالسيوم يقلل من امتصاص هرمون الغدة بنسبة 40%",
     "Calcium reduces levothyroxine absorption by 40%",
     "Calcium forms insoluble complex with levothyroxine",
     [], "Manual"),
 
    ("levothyroxine", "iron", "MODERATE",
     "الحديد يقلل من امتصاص هرمون الغدة",
     "Iron reduces levothyroxine absorption",
     "Iron forms insoluble complex with levothyroxine",
     [], "Manual"),
 
    ("levothyroxine", "warfarin", "MODERATE",
     "هرمون الغدة يزيد من تأثير مميع الدم",
     "Levothyroxine increases anticoagulant effect",
     "Thyroid hormone increases catabolism of clotting factors",
     [], "Manual"),
 
    ("levothyroxine", "omeprazole", "LOW",
     "قد يقلل من امتصاص هرمون الغدة",
     "May reduce levothyroxine absorption",
     "Increased gastric pH reduces levothyroxine dissolution",
     [], "Manual"),
 
    ("levothyroxine", "digoxin", "MODERATE",
     "هرمون الغدة يقلل من تأثير الديجوكسين",
     "Levothyroxine reduces digoxin effect",
     "Thyroid hormone increases renal clearance of digoxin",
     [], "Manual"),
 
    # ===== كلوبيدوجريل =====
    ("clopidogrel", "omeprazole", "HIGH",
     "الأوميبرازول يقلل من فاعلية الكلوبيدوجريل بشكل كبير",
     "Omeprazole significantly reduces clopidogrel effectiveness",
     "CYP2C19 inhibition prevents clopidogrel activation",
     ["pantoprazole", "rabeprazole"], "Manual"),
 
    ("clopidogrel", "aspirin", "MODERATE",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Dual antiplatelet effect",
     [], "Manual"),
 
    ("clopidogrel", "warfarin", "HIGH",
     "خطر نزيف كبير",
     "Major bleeding risk",
     "Additive antiplatelet and anticoagulant effects",
     [], "Manual"),
 
    ("clopidogrel", "ibuprofen", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive antiplatelet effects",
     ["paracetamol"], "Manual"),
 
    ("clopidogrel", "fluoxetine", "MODERATE",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "SSRIs inhibit platelet aggregation",
     [], "Manual"),
 
    ("clopidogrel", "rosuvastatin", "MODERATE",
     "زيادة في المستقلب الفعال للكلوبيدوجريل",
     "Increased clopidogrel active metabolite",
     "OATP1B1 competition",
     [], "Manual"),
 
    # ===== ليثيوم =====
    ("lithium", "ibuprofen", "HIGH",
     "مضادات الالتهاب ترفع مستويات الليثيوم في الدم",
     "NSAIDs increase lithium levels",
     "NSAIDs reduce renal clearance of lithium",
     ["paracetamol"], "Manual"),
 
    ("lithium", "diclofenac", "HIGH",
     "مضادات الالتهاب ترفع مستويات الليثيوم",
     "NSAIDs increase lithium levels",
     "NSAIDs reduce renal clearance of lithium",
     ["paracetamol"], "Manual"),
 
    ("lithium", "lisinopril", "HIGH",
     "مثبطات الـ ACE ترفع مستويات الليثيوم",
     "ACE inhibitors increase lithium levels",
     "ACE inhibitors reduce renal clearance of lithium",
     [], "Manual"),
 
    ("lithium", "furosemide", "HIGH",
     "مدرات البول ترفع مستويات الليثيوم بشكل خطير",
     "Diuretics increase lithium levels",
     "Volume depletion increases lithium reabsorption",
     [], "Manual"),
 
    ("lithium", "metronidazole", "MODERATE",
     "زيادة سمية الليثيوم",
     "Increased lithium toxicity",
     "Reduced renal clearance",
     [], "Manual"),
 
    ("lithium", "carbamazepine", "MODERATE",
     "زيادة سمية الجهاز العصبي",
     "Additive neurotoxicity",
     "Additive CNS toxicity",
     [], "Manual"),
 
    # ===== كاربامازيبين =====
    ("carbamazepine", "warfarin", "MODERATE",
     "الكاربامازيبين يقلل من فاعلية الوارفارين",
     "Carbamazepine reduces warfarin effectiveness",
     "CYP2C9 induction",
     [], "Manual"),
 
    ("carbamazepine", "azithromycin", "MODERATE",
     "زيادة مستويات الكاربامازيبين",
     "Increased carbamazepine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("carbamazepine", "clarithromycin", "HIGH",
     "الكلاريثروميسين يضاعف مستويات الكاربامازيبين",
     "Clarithromycin doubles carbamazepine levels",
     "CYP3A4 inhibition by clarithromycin",
     [], "Manual"),
 
    ("carbamazepine", "lithium", "MODERATE",
     "زيادة سمية الجهاز العصبي",
     "Additive neurotoxicity",
     "Additive CNS toxicity",
     [], "Manual"),
 
    ("carbamazepine", "valproate", "MODERATE",
     "الكاربامازيبين يقلل من مستويات الفالبروات",
     "Carbamazepine reduces valproate levels",
     "CYP2C9 induction reduces valproate levels",
     [], "Manual"),
 
    ("carbamazepine", "theophylline", "MODERATE",
     "الكاربامازيبين يقلل من مستويات الثيوفيلين",
     "Carbamazepine reduces theophylline levels",
     "CYP1A2 induction",
     [], "Manual"),
 
    # ===== الكحول =====
    ("alcohol", "metronidazole", "HIGH",
     "غثيان شديد وقيء واحمرار — تأثير ديسولفيرام",
     "Severe reaction: nausea, vomiting, flushing",
     "Disulfiram-like reaction",
     [], "Manual"),
 
    ("alcohol", "metformin", "HIGH",
     "زيادة خطر تحمض الدم باللاكتات",
     "Increased lactic acidosis risk",
     "Alcohol impairs hepatic lactate clearance",
     [], "Manual"),
 
    ("alcohol", "warfarin", "HIGH",
     "تأثير غير متوقع على مميع الدم",
     "Unpredictable effect on anticoagulation",
     "Alcohol affects warfarin metabolism unpredictably",
     [], "Manual"),
 
    ("alcohol", "paracetamol", "HIGH",
     "خطر كبير على الكبد",
     "Increased liver toxicity risk",
     "Alcohol induces CYP2E1 producing toxic paracetamol metabolite",
     [], "Manual"),
 
    ("alcohol", "ibuprofen", "HIGH",
     "زيادة نزيف المعدة",
     "Increased GI bleeding",
     "Additive gastric irritation",
     ["paracetamol"], "Manual"),
 
    ("alcohol", "diazepam", "HIGH",
     "اكتئاب شديد في الجهاز العصبي",
     "Severe CNS depression",
     "Additive CNS depressant effects",
     [], "Manual"),
 
    ("alcohol", "alprazolam", "HIGH",
     "اكتئاب شديد في الجهاز العصبي",
     "Severe CNS depression",
     "Additive CNS depressant effects",
     [], "Manual"),
 
    ("alcohol", "insulin", "HIGH",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Alcohol inhibits gluconeogenesis",
     [], "Manual"),
 
    ("alcohol", "glimepiride", "HIGH",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Alcohol inhibits gluconeogenesis and enhances drug effect",
     [], "Manual"),
 
    # ===== إنسولين =====
    ("insulin", "bisoprolol", "MODERATE",
     "حاصرات بيتا تخفي أعراض انخفاض السكر",
     "Beta blockers mask hypoglycemia symptoms",
     "Beta-blockade masks adrenergic signs of hypoglycemia",
     [], "Manual"),
 
    ("insulin", "atenolol", "MODERATE",
     "حاصرات بيتا تخفي أعراض انخفاض السكر",
     "Beta blockers mask hypoglycemia symptoms",
     "Beta-blockade masks adrenergic signs of hypoglycemia",
     [], "Manual"),
 
    ("insulin", "prednisolone", "MODERATE",
     "الكورتيزونات ترفع مستوى السكر",
     "Corticosteroids increase blood glucose",
     "Glucocorticoids cause insulin resistance",
     [], "Manual"),
 
    ("insulin", "furosemide", "MODERATE",
     "مدرات البول قد تقلل من تأثير الإنسولين",
     "Diuretics may reduce insulin effect",
     "Hypokalemia impairs insulin secretion",
     [], "Manual"),
 
    ("insulin", "ciprofloxacin", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Increased hypoglycemia risk",
     "Fluoroquinolones stimulate insulin secretion",
     [], "Manual"),
 
    # ===== جليميبيريد =====
    ("glimepiride", "fluconazole", "HIGH",
     "الفلوكونازول يرفع مستويات الجليميبيريد — خطر انخفاض السكر",
     "Fluconazole increases glimepiride levels",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("glimepiride", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("glimepiride", "aspirin", "MODERATE",
     "الأسبرين قد يزيد من تأثير خفض السكر",
     "Aspirin may enhance hypoglycemic effect",
     "Salicylates have intrinsic hypoglycemic effect",
     [], "Manual"),
 
    ("glimepiride", "metformin", "MODERATE",
     "زيادة خطر انخفاض السكر",
     "Additive hypoglycemia risk",
     "Additive blood glucose lowering effect",
     [], "Manual"),
 
    ("glimepiride", "bisoprolol", "MODERATE",
     "حاصرات بيتا تخفي أعراض انخفاض السكر",
     "Beta blockers mask hypoglycemia",
     "Beta-blockade masks adrenergic signs of hypoglycemia",
     [], "Manual"),
 
    # ===== باراسيتامول =====
    ("paracetamol", "warfarin", "MODERATE",
     "الاستخدام المنتظم يزيد من تأثير مميع الدم",
     "Regular use increases anticoagulant effect",
     "Paracetamol metabolite inhibits warfarin metabolism",
     [], "Manual"),
 
    ("paracetamol", "alcohol", "HIGH",
     "خطر كبير على الكبد",
     "Major liver toxicity risk",
     "Alcohol induces CYP2E1 producing toxic paracetamol metabolite",
     [], "Manual"),
 
    ("paracetamol", "isoniazid", "HIGH",
     "زيادة سمية الكبد",
     "Increased liver toxicity",
     "Isoniazid induces CYP2E1 increasing toxic metabolite of paracetamol",
     [], "Manual"),
 
    ("paracetamol", "carbamazepine", "MODERATE",
     "الكاربامازيبين يقلل من تأثير الباراسيتامول",
     "Carbamazepine reduces paracetamol effect",
     "CYP enzyme induction increases paracetamol metabolism",
     [], "Manual"),
 
    # ===== ديكلوفيناك =====
    ("diclofenac", "warfarin", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "NSAIDs displace warfarin from protein binding",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "heparin", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive anticoagulant and antiplatelet effects",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "lithium", "HIGH",
     "الديكلوفيناك يرفع مستويات الليثيوم",
     "Diclofenac increases lithium levels",
     "NSAIDs reduce renal clearance of lithium",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "methotrexate", "HIGH",
     "زيادة سمية الميثوتريكسات",
     "Increased methotrexate toxicity",
     "NSAIDs reduce renal clearance of methotrexate",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "cyclosporine", "HIGH",
     "زيادة سمية الكلى",
     "Increased nephrotoxicity",
     "Additive nephrotoxic effects",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "lisinopril", "MODERATE",
     "مضادات الالتهاب تقلل من فاعلية دواء الضغط",
     "NSAIDs reduce ACE inhibitor effect",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    ("diclofenac", "bisoprolol", "MODERATE",
     "مضادات الالتهاب تقلل من تأثير دواء الضغط",
     "NSAIDs reduce antihypertensive effect",
     "NSAIDs cause sodium retention",
     ["paracetamol"], "Manual"),
 
    # ===== فلوكونازول =====
    ("fluconazole", "warfarin", "HIGH",
     "الفلوكونازول يضاعف تأثير الوارفارين",
     "Fluconazole doubles warfarin effect",
     "Strong CYP2C9 inhibition",
     [], "Manual"),
 
    ("fluconazole", "phenytoin", "HIGH",
     "الفلوكونازول يرفع مستويات الفينيتوين",
     "Fluconazole increases phenytoin levels",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("fluconazole", "glimepiride", "HIGH",
     "الفلوكونازول يرفع مستويات الجليميبيريد — خطر انخفاض السكر",
     "Fluconazole increases glimepiride levels",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("fluconazole", "cyclosporine", "HIGH",
     "الفلوكونازول يرفع مستويات السيكلوسبورين",
     "Fluconazole increases cyclosporine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("fluconazole", "simvastatin", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "CYP3A4 inhibition increases simvastatin levels",
     ["pravastatin", "rosuvastatin"], "Manual"),
 
    ("fluconazole", "midazolam", "HIGH",
     "الفلوكونازول يرفع مستويات الميدازولام بشكل خطير",
     "Fluconazole increases midazolam levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    # ===== ثيوفيلين =====
    ("theophylline", "ciprofloxacin", "HIGH",
     "السيبرو يضاعف مستويات الثيوفيلين في الدم",
     "Ciprofloxacin doubles theophylline levels",
     "CYP1A2 inhibition by ciprofloxacin",
     [], "Manual"),
 
    ("theophylline", "azithromycin", "MODERATE",
     "زيادة مستويات الثيوفيلين في الدم",
     "Increased theophylline levels",
     "CYP1A2 inhibition",
     [], "Manual"),
 
    ("theophylline", "carbamazepine", "MODERATE",
     "الكاربامازيبين يقلل من مستويات الثيوفيلين",
     "Carbamazepine reduces theophylline levels",
     "CYP1A2 induction",
     [], "Manual"),
 
    ("theophylline", "cimetidine", "HIGH",
     "السيميتيدين يضاعف مستويات الثيوفيلين",
     "Cimetidine doubles theophylline levels",
     "CYP1A2 and CYP3A4 inhibition",
     [], "Manual"),
 
    ("theophylline", "lithium", "MODERATE",
     "الثيوفيلين يقلل من مستويات الليثيوم",
     "Theophylline reduces lithium levels",
     "Increased renal clearance of lithium",
     [], "Manual"),
 
    # ===== سيكلوسبورين =====
    ("cyclosporine", "ibuprofen", "HIGH",
     "زيادة سمية الكلى",
     "Increased nephrotoxicity",
     "Additive nephrotoxic effects",
     ["paracetamol"], "Manual"),
 
    ("cyclosporine", "fluconazole", "HIGH",
     "الفلوكونازول يرفع مستويات السيكلوسبورين",
     "Increased cyclosporine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("cyclosporine", "clarithromycin", "HIGH",
     "الكلاريثروميسين يرفع مستويات السيكلوسبورين",
     "Increased cyclosporine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("cyclosporine", "rifampicin", "HIGH",
     "الريفامبيسين يقلل من مستويات السيكلوسبورين بشكل خطير",
     "Rifampicin drastically reduces cyclosporine levels",
     "Strong CYP3A4 induction",
     [], "Manual"),
 
    ("cyclosporine", "amlodipine", "MODERATE",
     "زيادة مستويات السيكلوسبورين",
     "Increased cyclosporine levels",
     "P-glycoprotein inhibition",
     [], "Manual"),
 
    ("cyclosporine", "atorvastatin", "HIGH",
     "زيادة كبيرة في مستويات الأتورفاستاتين",
     "Increased atorvastatin levels",
     "OATP1B1 and CYP3A4 inhibition",
     ["pravastatin"], "Manual"),
 
    ("cyclosporine", "simvastatin", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "OATP1B1 and CYP3A4 inhibition",
     ["pravastatin"], "Manual"),
 
    # ===== مضادات حيوية فيما بينها =====
    ("ciprofloxacin", "metronidazole", "MODERATE",
     "زيادة الآثار الجانبية على الجهاز العصبي",
     "Increased CNS side effects",
     "Additive CNS effects",
     [], "Manual"),
 
    ("doxycycline", "antacids", "MODERATE",
     "مضادات الحموضة تقلل من امتصاص الدوكسيسيكلين",
     "Antacids reduce doxycycline absorption",
     "Chelation with divalent cations",
     [], "Manual"),
 
    ("doxycycline", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "Antibiotics reduce vitamin K producing gut bacteria",
     [], "Manual"),
 
    ("doxycycline", "iron", "MODERATE",
     "الحديد يقلل من امتصاص الدوكسيسيكلين",
     "Iron reduces doxycycline absorption",
     "Chelation with iron",
     [], "Manual"),
 
    ("doxycycline", "rifampicin", "MODERATE",
     "الريفامبيسين يقلل من مستويات الدوكسيسيكلين",
     "Rifampicin reduces doxycycline levels",
     "CYP3A4 induction",
     [], "Manual"),
 
    ("tetracycline", "antacids", "HIGH",
     "مضادات الحموضة تقلل من امتصاص التتراسيكلين بنسبة 90%",
     "Antacids reduce tetracycline absorption by 90%",
     "Chelation with divalent cations",
     [], "Manual"),
 
    ("tetracycline", "iron", "HIGH",
     "الحديد يقلل من امتصاص التتراسيكلين بشكل كبير",
     "Iron reduces tetracycline absorption",
     "Chelation with iron",
     [], "Manual"),
 
    ("tetracycline", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "Antibiotics reduce vitamin K producing gut bacteria",
     [], "Manual"),
 
    ("clarithromycin", "carbamazepine", "HIGH",
     "الكلاريثروميسين يضاعف مستويات الكاربامازيبين",
     "Clarithromycin doubles carbamazepine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("clarithromycin", "digoxin", "HIGH",
     "الكلاريثروميسين يرفع مستويات الديجوكسين بشكل خطير",
     "Clarithromycin increases digoxin levels",
     "P-glycoprotein inhibition + gut bacteria inhibition",
     [], "Manual"),
 
    ("clarithromycin", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("clarithromycin", "simvastatin", "HIGH",
     "زيادة كبيرة في خطر ألم وتلف العضلات",
     "Major increased risk of myopathy",
     "CYP3A4 inhibition increases simvastatin levels",
     ["pravastatin", "rosuvastatin"], "Manual"),
 
    ("clarithromycin", "cyclosporine", "HIGH",
     "زيادة مستويات السيكلوسبورين",
     "Increased cyclosporine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("levofloxacin", "antacids", "HIGH",
     "مضادات الحموضة تقلل من امتصاص الليفوفلوكساسين",
     "Antacids reduce levofloxacin absorption",
     "Chelation with divalent cations",
     [], "Manual"),
 
    ("levofloxacin", "warfarin", "HIGH",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("levofloxacin", "iron", "HIGH",
     "الحديد يقلل من امتصاص الليفوفلوكساسين",
     "Iron reduces levofloxacin absorption",
     "Chelation with iron",
     [], "Manual"),
 
    ("levofloxacin", "amiodarone", "HIGH",
     "خطر اضطرابات خطيرة في ضربات القلب",
     "Risk of cardiac arrhythmia",
     "Both prolong QT interval",
     [], "Manual"),
 
    # ===== بنزوديازيبينات =====
    ("diazepam", "alcohol", "HIGH",
     "اكتئاب شديد في الجهاز العصبي والتنفسي",
     "Severe CNS and respiratory depression",
     "Additive CNS depressant effects",
     [], "Manual"),
 
    ("diazepam", "omeprazole", "MODERATE",
     "الأوميبرازول يرفع مستويات الديازيبام",
     "Omeprazole increases diazepam levels",
     "CYP2C19 inhibition",
     [], "Manual"),
 
    ("diazepam", "fluconazole", "MODERATE",
     "زيادة مستويات الديازيبام",
     "Increased diazepam levels",
     "CYP2C19 inhibition",
     [], "Manual"),
 
    ("alprazolam", "alcohol", "HIGH",
     "اكتئاب شديد في الجهاز العصبي",
     "Severe CNS depression",
     "Additive CNS depressant effects",
     [], "Manual"),
 
    ("alprazolam", "fluconazole", "MODERATE",
     "زيادة مستويات الألبرازولام",
     "Increased alprazolam levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("alprazolam", "clarithromycin", "MODERATE",
     "زيادة مستويات الألبرازولام",
     "Increased alprazolam levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    # ===== مضادات الاكتئاب =====
    ("fluoxetine", "tramadol", "HIGH",
     "خطر متلازمة السيروتونين — خطير",
     "Risk of serotonin syndrome",
     "Additive serotonergic effects",
     [], "Manual"),
 
    ("fluoxetine", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 inhibition by fluoxetine",
     [], "Manual"),
 
    ("fluoxetine", "bisoprolol", "MODERATE",
     "الفلوكستين يرفع مستويات البيسوبرولول",
     "Increased bisoprolol levels",
     "CYP2D6 inhibition",
     [], "Manual"),
 
    ("fluoxetine", "carbamazepine", "MODERATE",
     "الفلوكستين يرفع مستويات الكاربامازيبين",
     "Fluoxetine increases carbamazepine levels",
     "CYP3A4 inhibition",
     [], "Manual"),
 
    ("sertraline", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "SSRIs inhibit platelet aggregation",
     [], "Manual"),
 
    ("sertraline", "tramadol", "HIGH",
     "خطر متلازمة السيروتونين",
     "Risk of serotonin syndrome",
     "Additive serotonergic effects",
     [], "Manual"),
 
    # ===== ريفامبيسين =====
    ("rifampicin", "warfarin", "HIGH",
     "الريفامبيسين يقلل من تأثير الوارفارين بشكل كبير جداً",
     "Rifampicin dramatically reduces warfarin effect",
     "Strong CYP2C9 and CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "cyclosporine", "HIGH",
     "الريفامبيسين يقلل من مستويات السيكلوسبورين بشكل خطير",
     "Rifampicin drastically reduces cyclosporine levels",
     "Strong CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "prednisolone", "MODERATE",
     "الريفامبيسين يقلل من تأثير البريدنيزولون",
     "Rifampicin reduces prednisolone effect",
     "CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "bisoprolol", "MODERATE",
     "الريفامبيسين يقلل من مستويات البيسوبرولول",
     "Rifampicin reduces bisoprolol levels",
     "CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "amlodipine", "MODERATE",
     "الريفامبيسين يقلل من تأثير الأملوديبين",
     "Rifampicin reduces amlodipine levels",
     "CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "levothyroxine", "MODERATE",
     "الريفامبيسين يقلل من تأثير هرمون الغدة",
     "Rifampicin reduces levothyroxine effect",
     "Increased metabolism of levothyroxine",
     [], "Manual"),
 
    ("rifampicin", "doxycycline", "MODERATE",
     "الريفامبيسين يقلل من مستويات الدوكسيسيكلين",
     "Rifampicin reduces doxycycline levels",
     "CYP3A4 induction",
     [], "Manual"),
 
    ("rifampicin", "fluconazole", "MODERATE",
     "الريفامبيسين يقلل من تأثير الفلوكونازول",
     "Rifampicin reduces fluconazole effect",
     "CYP3A4 induction",
     [], "Manual"),
 
    # ===== كوليشيسين =====
    ("colchicine", "clarithromycin", "HIGH",
     "زيادة كبيرة في سمية الكولشيسين — خطير جداً",
     "Major increase in colchicine toxicity",
     "P-glycoprotein and CYP3A4 inhibition",
     [], "Manual"),
 
    ("colchicine", "cyclosporine", "HIGH",
     "زيادة سمية الكولشيسين",
     "Increased colchicine toxicity",
     "P-glycoprotein inhibition",
     [], "Manual"),
 
    ("colchicine", "atorvastatin", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased myopathy risk",
     "Additive myopathy risk",
     [], "Manual"),
 
    ("colchicine", "rosuvastatin", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased myopathy risk",
     "Additive myopathy risk",
     [], "Manual"),
 
    # ===== ألوبيورينول =====
    ("allopurinol", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 inhibition",
     [], "Manual"),
 
    ("allopurinol", "azathioprine", "HIGH",
     "زيادة كبيرة في سمية الأزاثيوبرين — خطير",
     "Major increase in azathioprine toxicity",
     "Allopurinol inhibits xanthine oxidase that metabolizes azathioprine",
     [], "Manual"),
 
    ("allopurinol", "amoxicillin", "MODERATE",
     "زيادة خطر الطفح الجلدي",
     "Increased risk of skin rash",
     "Mechanism not fully established",
     [], "Manual"),
 
    ("allopurinol", "lisinopril", "MODERATE",
     "زيادة خطر الحساسية",
     "Increased risk of allergic reaction",
     "Mechanism not fully established",
     [], "Manual"),
 
    ("allopurinol", "theophylline", "MODERATE",
     "الألوبيورينول يرفع مستويات الثيوفيلين",
     "Allopurinol increases theophylline levels",
     "Xanthine oxidase inhibition reduces theophylline catabolism",
     [], "Manual"),
 
    # ===== ترامادول =====
    ("tramadol", "fluoxetine", "HIGH",
     "خطر متلازمة السيروتونين — خطير",
     "Risk of serotonin syndrome",
     "Additive serotonergic effects",
     [], "Manual"),
 
    ("tramadol", "sertraline", "HIGH",
     "خطر متلازمة السيروتونين",
     "Risk of serotonin syndrome",
     "Additive serotonergic effects",
     [], "Manual"),
 
    ("tramadol", "carbamazepine", "MODERATE",
     "الكاربامازيبين يقلل من تأثير الترامادول",
     "Carbamazepine reduces tramadol effect",
     "CYP3A4 induction reduces tramadol levels",
     [], "Manual"),
 
    ("tramadol", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "Possible CYP2C9 competition",
     [], "Manual"),
 
    ("tramadol", "alcohol", "HIGH",
     "زيادة اكتئاب الجهاز العصبي",
     "Increased CNS depression",
     "Additive CNS depressant effects",
     [], "Manual"),
 
    # ===== إنوكسابارين =====
    ("enoxaparin", "aspirin", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive antiplatelet and anticoagulant effects",
     [], "Manual"),
 
    ("enoxaparin", "warfarin", "HIGH",
     "تأثير مضاعف لمميع الدم",
     "Additive anticoagulant effect",
     "Additive anticoagulant effects",
     [], "Manual"),
 
    ("enoxaparin", "ibuprofen", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "NSAIDs inhibit platelet aggregation",
     ["paracetamol"], "Manual"),
 
    ("enoxaparin", "clopidogrel", "HIGH",
     "زيادة خطر النزيف",
     "Increased bleeding risk",
     "Additive antiplatelet and anticoagulant effects",
     [], "Manual"),
 
    # ===== ميثوتريكسات =====
    ("methotrexate", "aspirin", "HIGH",
     "الأسبرين يزيد من سمية الميثوتريكسات",
     "Aspirin increases methotrexate toxicity",
     "NSAIDs reduce renal clearance of methotrexate",
     ["paracetamol"], "Manual"),
 
    ("methotrexate", "ibuprofen", "HIGH",
     "زيادة سمية الميثوتريكسات",
     "Increased methotrexate toxicity",
     "NSAIDs reduce renal clearance of methotrexate",
     ["paracetamol"], "Manual"),
 
    ("methotrexate", "amoxicillin", "HIGH",
     "الأموكسيسيلين يرفع مستويات الميثوتريكسات",
     "Amoxicillin increases methotrexate levels",
     "Competition for renal tubular secretion",
     [], "Manual"),
 
    ("methotrexate", "omeprazole", "MODERATE",
     "الأوميبرازول يرفع مستويات الميثوتريكسات",
     "Omeprazole increases methotrexate levels",
     "Reduced renal tubular secretion",
     ["pantoprazole"], "Manual"),
 
    ("methotrexate", "trimethoprim", "HIGH",
     "تضاعف في منع حمض الفوليك — خطير",
     "Additive folate antagonism",
     "Both drugs inhibit dihydrofolate reductase",
     [], "Manual"),
 
    # ===== فالبروات =====
    ("valproate", "carbamazepine", "MODERATE",
     "الكاربامازيبين يقلل من مستويات الفالبروات",
     "Carbamazepine reduces valproate levels",
     "CYP2C9 induction",
     [], "Manual"),
 
    ("valproate", "aspirin", "MODERATE",
     "الأسبرين يرفع مستويات الفالبروات",
     "Aspirin increases valproate levels",
     "Aspirin displaces valproate from protein binding",
     [], "Manual"),
 
    ("valproate", "warfarin", "MODERATE",
     "قد يزيد من تأثير مميع الدم",
     "May increase anticoagulant effect",
     "Valproate displaces warfarin from protein binding",
     [], "Manual"),
 
    ("valproate", "lamotrigine", "HIGH",
     "الفالبروات يضاعف مستويات اللاموتريجين",
     "Valproate doubles lamotrigine levels",
     "Inhibition of glucuronidation of lamotrigine",
     [], "Manual"),
 
    # ===== جنتاميسين =====
    ("gentamicin", "furosemide", "HIGH",
     "زيادة سمية الكلى والأذن",
     "Additive nephrotoxicity and ototoxicity",
     "Additive toxic effects on renal tubules and cochlea",
     [], "Manual"),
 
    ("gentamicin", "cisplatin", "HIGH",
     "زيادة سمية الكلى",
     "Additive nephrotoxicity",
     "Additive nephrotoxic effects",
     [], "Manual"),
 
    ("gentamicin", "cyclosporine", "HIGH",
     "زيادة سمية الكلى",
     "Additive nephrotoxicity",
     "Additive nephrotoxic effects",
     [], "Manual"),
 
    ("gentamicin", "ibuprofen", "MODERATE",
     "زيادة سمية كلى الجنتاميسين",
     "Increased gentamicin nephrotoxicity",
     "NSAIDs reduce renal perfusion",
     ["paracetamol"], "Manual"),
 
    ("gentamicin", "vancomycin", "HIGH",
     "زيادة سمية الكلى",
     "Additive nephrotoxicity",
     "Additive nephrotoxic effects",
     [], "Manual"),
 
    # ===== ستاتينات فيما بينها =====
    ("simvastatin", "amiodarone", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "Amiodarone inhibits CYP3A4",
     ["rosuvastatin", "pravastatin"], "Manual"),
 
    ("simvastatin", "clarithromycin", "HIGH",
     "زيادة كبيرة في خطر ألم وتلف العضلات",
     "Major increased risk of myopathy",
     "CYP3A4 inhibition",
     ["pravastatin", "rosuvastatin"], "Manual"),
 
    ("simvastatin", "cyclosporine", "HIGH",
     "زيادة خطر ألم وتلف العضلات",
     "Increased risk of myopathy",
     "OATP1B1 and CYP3A4 inhibition",
     ["pravastatin"], "Manual"),
 
    ("simvastatin", "warfarin", "MODERATE",
     "زيادة تأثير مميع الدم",
     "Increased anticoagulant effect",
     "CYP2C9 competition",
     [], "Manual"),
 
    ("pravastatin", "cyclosporine", "HIGH",
     "زيادة مستويات البرافاستاتين",
     "Increased pravastatin levels",
     "OATP1B1 inhibition",
     [], "Manual"),
 
    ("pravastatin", "gemfibrozil", "MODERATE",
     "زيادة خطر ألم العضلات",
     "Increased risk of myopathy",
     "Additive myopathy risk",
     [], "Manual"),
]
 
 
def add_interactions():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
 
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    errors = 0
    today = "2025-01-01"  # last_reviewed default
 
    for row in interactions:
        drug1, drug2, severity, desc_ar, desc_en, mechanism, alternatives, source = row
        interaction_id = str(uuid.uuid4())
        try:
            cursor.execute("""
                INSERT INTO "DrugInteractions"
                    ("Id", "Drug1Ingredient", "Drug2Ingredient", "Severity", "DescriptionAr", "DescriptionEn", "Mechanism", "Alternatives", "Source","LastReviewed")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                interaction_id,
                drug1, drug2, severity,
                desc_ar, desc_en, mechanism,
                json.dumps(alternatives),
                source, today
            ))
 
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
 
        except Exception as e:
            print(f"❌ Error inserting '{drug1}' + '{drug2}': {e}")
            errors += 1
 
    conn.commit()
    cursor.close()
    conn.close()
 
    print(f"\n✅ Done!")
    print(f"   Inserted : {inserted}")
    print(f"   Skipped  : {skipped}")
    print(f"   Errors   : {errors}")
    print(f"   Total    : {len(interactions)}")
 
 
if __name__ == "__main__":
    add_interactions()