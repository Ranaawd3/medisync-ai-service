import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
 
import io
import time
import uuid
import re
import json
import shutil
 
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import psycopg2
import psycopg2.pool
import easyocr
from rapidfuzz import process
 
app = FastAPI()
 
# =====================================================
# إعدادات — كل الـ secrets من environment variables
# =====================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY environment variable is not set!")
 
groq_client = Groq(api_key=GROQ_API_KEY)
 
# =====================================================
# DB CONFIG
# لو على Railway: استخدم DATABASE_URL
# لو محلي: استخدم المتغيرات دول
# =====================================================
DATABASE_URL = os.getenv("DATABASE_URL")
 
if DATABASE_URL:
    # Railway / Production
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DB_CONFIG = {
        "host":     url.hostname,
        "database": url.path[1:],
        "user":     url.username,
        "password": url.password,
        "port":     url.port or 5432
    }
else:
    # Local development
    DB_CONFIG = {
        "host":     os.getenv("DB_HOST",     "127.0.0.1"),
        "database": os.getenv("DB_NAME",     "medisync_db"),
        "user":     os.getenv("DB_USER",     "postgres"),
        "password": os.getenv("DB_PASSWORD", "123456789"),
        "port":     os.getenv("DB_PORT",     "5432")
    }
 
# =====================================================
# Connection Pool — أحسن من فتح connection مع كل request
# =====================================================
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
except Exception as e:
    print(f"⚠️  DB Pool init failed: {e} — سيتم المحاولة عند أول request")
    connection_pool = None

# =====================================================
# Google Cloud Vision Setup
# =====================================================
vision_client = None
 
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if GOOGLE_CREDENTIALS_JSON:
    try:
        from google.cloud import vision as gvision
        from google.oauth2 import service_account
 
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        vision_client = gvision.ImageAnnotatorClient(credentials=credentials)
        print("✅ Google Cloud Vision loaded")
    except Exception as e:
        print(f"⚠️  Google Vision init failed: {e} — سيتم استخدام EasyOCR")
        vision_client = None
else:
    print("⚠️  GOOGLE_APPLICATION_CREDENTIALS_JSON not set — using EasyOCR")
 
# =====================================================
# EasyOCR Reader — بيتحمل مرة واحدة عند البدء
# =====================================================
print("⏳ Loading EasyOCR model...")
# ✅ بيتحمل بس لو مفيش Google Vision
USE_EASYOCR = os.getenv("USE_EASYOCR", "false").lower() == "true"

reader = None
if USE_EASYOCR:
    print("⏳ Loading EasyOCR model...")
    reader = easyocr.Reader(['ar', 'en'], gpu=False)
    print("✅ EasyOCR loaded")
else:
    print("ℹ️  EasyOCR disabled — using Google Vision only")
print("✅ EasyOCR model loaded")

# =====================================================
# SYSTEM PROMPTS
# =====================================================
SYSTEM_PROMPT = """
You are a pharmaceutical data extractor specialized in Egyptian and Arab prescriptions.
 
IMPORTANT RULES:
- Output MUST be ONLY valid JSON array
- Do NOT include any text, explanation, or markdown
- DO NOT use any language except English inside JSON values
- If no medications found return []
 
TASK:
Extract ALL medications from the text.
 
For each medication return:
{
  "brandName": "original name as written",
  "genericName": "English generic name (Capitalized)",
  "activeIngredient": "english lowercase generic name",
  "dosageValue": number or null,
  "dosageUnit": "mg | ml | IU | mcg | null",
  "form": "tablet | capsule | syrup | injection | drops | ointment | unknown",
  "timesPerDay": number or null,
  "scheduleType": "empty_stomach | with_food | after_food | before_sleep | unknown",
  "durationDays": number or null,
  "instructions": "short notes or empty string",
  "confidencePerField": {
    "brandName": 0-100,
    "dosage": 0-100,
    "timesPerDay": 0-100
  }
}
 
Arabic drug name mapping (IMPORTANT — use these exact generics):
- بروفين / Brufen / ادفيل = ibuprofen
- بنادول / Panadol / تايلينول = paracetamol
- أسبرين = aspirin
- كونكور / Concor = bisoprolol
- ديابيكون / انتوبرال / جلوكوفاج = metformin
- كوزار / Cozaar = losartan
- كريستور / Crestor = rosuvastatin
- نورفاسك / Norvasc = amlodipine
- زيثروماكس / Zithromax = azithromycin
- أموكسيل / Amoxil / فلوموكس = amoxicillin
- فلاجيل / Flagyl = metronidazole
- سيبروسين / Ciprocin = ciprofloxacin
- فينتولين / Ventolin = salbutamol
- لازيكس / Lasix = furosemide
- أوميز / Omez / لوسيك = omeprazole
 
Return ONLY JSON array.
"""
 
TRANSLATE_PROMPT = """
You are a pharmaceutical translation engine.
 
INPUT: drug name in Arabic or English
 
OUTPUT RULES:
- Return ONLY JSON
- No explanation, no markdown
- Always lowercase generic name
 
FORMAT:
{"generic": "metformin", "confidence": 0.95}
 
KNOWN MAPPINGS:
- بروفين / Brufen = ibuprofen
- بنادول / Panadol = paracetamol
- أسبرين = aspirin
- كونكور / Concor = bisoprolol
- ديابيكون / انتوبرال / جلوكوفاج = metformin
- كوزار / Cozaar = losartan
- كريستور / Crestor = rosuvastatin
- نورفاسك / Norvasc = amlodipine
- زيثروماكس / Zithromax = azithromycin
- أموكسيل / Amoxil = amoxicillin
- فلاجيل / Flagyl = metronidazole
- فينتولين / Ventolin = salbutamol
- لازيكس / Lasix = furosemide
- أوميز / Omez = omeprazole
"""
 
 
# =====================================================
# HELPERS
# =====================================================
def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF]', '', text)
    return text
 
 
def get_conn():
    """Get a DB connection from pool or create new one."""
    global connection_pool
    try:
        if connection_pool:
            return connection_pool.getconn()
    except Exception:
        pass
    # Fallback: direct connection
    return psycopg2.connect(**DB_CONFIG)
 
 
def release_conn(conn):
    """Return connection to pool."""
    global connection_pool
    try:
        if connection_pool:
            connection_pool.putconn(conn)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
 
 
def safe_json_parse(text: str):
    """Parse JSON safely — handle markdown fences."""
    text = re.sub(r'```json|```', '', text).strip()
    return json.loads(text)
 
 
def get_generic_from_db(drug_name: str):
    """
    بحث في drug_name_mappings بـ local_name.
    Schema: local_name, generic_name, active_ingredient, country, source
    """
    normalized = normalize(drug_name)
    conn = get_conn()
    try:
        cur = conn.cursor()
        # بحث في drug_name_mappings (الـ Schema المتفق عليه)
        cur.execute("""
            SELECT active_ingredient
            FROM drug_name_mappings
            WHERE LOWER(REGEXP_REPLACE(local_name, '[^a-zA-Z0-9\u0600-\u06FF]', '', 'g')) = %s
            LIMIT 1
        """, (normalized,))
        result = cur.fetchone()
        if result:
            return result[0]
 
        # بحث في drug_dictionary (fallback)
        cur.execute("""
            SELECT generic_name
            FROM drug_dictionary
            WHERE normalized_name = %s
            LIMIT 1
        """, (normalized,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"⚠️  DB lookup error for '{drug_name}': {e}")
        return None
    finally:
        release_conn(conn)
 
 
def dict_insert(brand: str, generic: str, source: str, confidence: float):
    """حفظ دواء جديد في drug_dictionary."""
    normalized = normalize(brand)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO drug_dictionary
                (brand_name, generic_name, normalized_name, source, confidence)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (brand, generic, normalized, source, confidence))
        conn.commit()
    except Exception as e:
        print(f"⚠️  dict_insert error: {e}")
        conn.rollback()
    finally:
        release_conn(conn)
 
 
def get_all_local_names():
    """جيب كل الأسماء من drug_name_mappings وdrug_dictionary."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT local_name FROM drug_name_mappings
            UNION
            SELECT brand_name FROM drug_dictionary
        """)
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"⚠️  get_all_local_names error: {e}")
        return []
    finally:
        release_conn(conn)
 
 
def translate_drug(name: str) -> str:
    """
    ترجمة اسم الدواء لـ generic name.
    الترتيب: DB → Fuzzy Match → AI → fallback (الاسم نفسه)
    """
    if not name or not name.strip():
        return name
 
    # 1. من قاعدة البيانات أولاً
    generic = get_generic_from_db(name)
    if generic:
        return generic
 
    # 2. Fuzzy match
    brands = get_all_local_names()
    if brands:
        match = process.extractOne(name, brands)
        if match and match[1] > 85:
            generic = get_generic_from_db(match[0])
            if generic:
                dict_insert(name, generic, "fuzzy", round(match[1] / 100, 2))
                return generic
 
    # 3. AI (Groq)
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=100,
            messages=[
                {"role": "system", "content": TRANSLATE_PROMPT},
                {"role": "user", "content": name}
            ]
        )
        result = safe_json_parse(response.choices[0].message.content)
        generic = result.get("generic", "").strip().lower()
        confidence = float(result.get("confidence", 0.7))
        if generic:
            dict_insert(name, generic, "ai", confidence)
            return generic
    except Exception as e:
        print(f"⚠️  AI translate error for '{name}': {e}")
 
    # 4. Fallback — إرجاع الاسم كما هو
    return name.lower().strip()
 
 
def check_interaction_in_db(drug1: str, drug2: str):
    """
    بحث عن تفاعل بين دوائين في drug_interactions.
    Schema المتفق عليه:
    drug1_ingredient, drug2_ingredient, severity,
    description_ar, description_en, mechanism, alternatives, source, last_reviewed
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT drug1_ingredient, drug2_ingredient,
                   severity, description_ar, description_en,
                   mechanism, alternatives, source, last_reviewed
            FROM drug_interactions
            WHERE (LOWER(drug1_ingredient) = LOWER(%s) AND LOWER(drug2_ingredient) = LOWER(%s))
               OR (LOWER(drug1_ingredient) = LOWER(%s) AND LOWER(drug2_ingredient) = LOWER(%s))
            LIMIT 1
        """, (drug1, drug2, drug2, drug1))
        return cur.fetchone()
    except Exception as e:
        print(f"⚠️  check_interaction error: {e}")
        return None
    finally:
        release_conn(conn)
 
 
def format_interaction(result) -> dict:
    """تحويل نتيجة DB لـ dict منظم."""
    alternatives = result[6]
    if isinstance(alternatives, str):
        try:
            alternatives = json.loads(alternatives)
        except Exception:
            alternatives = []
    return {
        "drug1_ingredient": result[0],
        "drug2_ingredient": result[1],
        "severity":         result[2],
        "description_ar":   result[3],
        "description_en":   result[4],
        "mechanism":        result[5],
        "alternatives":     alternatives or [],
        "source":           result[7],
        "last_reviewed":    str(result[8]) if result[8] else None
    }
 
# =====================================================
# OCR FUNCTIONS
# =====================================================
def ocr_with_google(image_path: str) -> tuple[str, float]:
    """
    OCR بـ Google Cloud Vision
    دقة عربي: 92-97% | سرعة: 0.5-1 ثانية
    Returns: (raw_text, avg_confidence)
    """
    if not vision_client:
        return "", 0.0
 
    from google.cloud import vision as gvision
 
    with open(image_path, "rb") as f:
        content = f.read()
 
    image = gvision.Image(content=content)
 
    # language_hints بتحسن دقة النص المختلط عربي + إنجليزي
    image_context = gvision.ImageContext(
        language_hints=["ar", "en"]
    )
 
    response = vision_client.document_text_detection(
        image=image,
        image_context=image_context
    )
 
    if response.error.message:
        raise Exception(f"Google Vision API error: {response.error.message}")
 
    full_text = response.full_text_annotation.text
 
    if not full_text or not full_text.strip():
        return "", 0.0
 
    # confidence من الـ blocks — Google بيديك 0.0 → 1.0
    confidences = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            if block.confidence > 0:
                confidences.append(block.confidence)
 
    avg_confidence = round(
        sum(confidences) / len(confidences) * 100, 1
    ) if confidences else 85.0
 
    return full_text.strip(), avg_confidence
 
 
def ocr_with_easyocr(image_path: str) -> tuple[str, float]:
    if not reader:
        return "", 0.0
    """
    OCR بـ EasyOCR
    دقة عربي: 60-75% | Fallback لو Google Vision مش شغال
    Returns: (raw_text, avg_confidence)
    """
    results = reader.readtext(image_path)
 
    if not results:
        return "", 0.0
 
    raw_text = " ".join([r[1] for r in results])
    confidences = [float(r[2]) for r in results]
    avg_confidence = round(
        sum(confidences) / len(confidences) * 100, 1
    )
 
    return raw_text.strip(), avg_confidence
 
 
def perform_ocr(image_path: str) -> tuple[str, float]:
    """
    الـ OCR الرئيسي:
    1. يجرب Google Cloud Vision أولاً (أدق)
    2. لو فشل أو مش موجود → EasyOCR تلقائياً
    Returns: (raw_text, avg_confidence)
    """
    if vision_client:
        try:
            text, confidence = ocr_with_google(image_path)
            if text:
                print("✅ OCR: Google Vision succeeded")
                return text, confidence
            else:
                print("⚠️  Google Vision returned empty — falling back to EasyOCR")
        except Exception as e:
            print(f"⚠️  Google Vision failed: {e} — falling back to EasyOCR")
 
    print("⚠️  OCR: Using EasyOCR")
    return ocr_with_easyocr(image_path)
 
# =====================================================
# Endpoint 1: OCR فقط
# POST /ocr
# Input:  multipart/form-data — صورة روشتة
# Output: OCR Response Contract المتفق عليه
# =====================================================
@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    start_time = time.time()
 
    # حفظ الصورة بـ uuid فريد لتجنب التعارض عند التزامن
    temp_path = f"/tmp/ocr_{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
 
        raw_text, avg_confidence = perform_ocr(temp_path)
 
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
 
    if not raw_text.strip():
        return {
            "scanId": str(uuid.uuid4()),
            "confidence": 0.0,
            "status": "failed",
            "requiresManualReview": True,
            "rawText": "",
            "processingTimeMs": int((time.time() - start_time) * 1000),
            "extractedMedications": []
        }
 
    # AI Extraction
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ]
        )
        medications = safe_json_parse(response.choices[0].message.content)
        if not isinstance(medications, list):
            medications = []
    except Exception as e:
        print(f"⚠️  AI extraction error: {e}")
        medications = []
 
    processing_time = int((time.time() - start_time) * 1000)
 
    # Response Contract المتفق عليه بالظبط
    return {
        "scanId":               str(uuid.uuid4()),
        "confidence":           avg_confidence,
        "status":               "success" if avg_confidence >= 70 else "low_confidence",
        "requiresManualReview": avg_confidence < 70,
        "rawText":              raw_text,
        "processingTimeMs":     processing_time,
        "extractedMedications": medications
    }
 
 
# =====================================================
# Endpoint 2: Drug Interaction — دوائين
# POST /drug-interaction
# Input:  {"ingredient1": "...", "ingredient2": "..."}
# Output: interaction details بـ Schema المتفق عليه
# =====================================================
class InteractionRequest(BaseModel):
    ingredient1: str
    ingredient2: str
 
 
@app.post("/drug-interaction")
async def drug_interaction(req: InteractionRequest):
    drug1 = translate_drug(req.ingredient1)
    drug2 = translate_drug(req.ingredient2)
 
    result = check_interaction_in_db(drug1, drug2)
 
    if result:
        return {
            "success":           True,
            "interaction_found": True,
            "queried_drug1":     drug1,
            "queried_drug2":     drug2,
            **format_interaction(result)
        }
    else:
        return {
            "success":           True,
            "interaction_found": False,
            "queried_drug1":     drug1,
            "queried_drug2":     drug2
        }
 
 
# =====================================================
# Endpoint 3: OCR + Drug Interaction في خطوة واحدة
# POST /scan-and-check
# =====================================================
@app.post("/scan-and-check")
async def scan_and_check(file: UploadFile = File(...)):
    start_time = time.time()
 
    temp_path = f"/tmp/scan_{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
 
        raw_text, avg_confidence = perform_ocr(temp_path)
 
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
 
    # AI Extraction
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ]
        )
        medications = safe_json_parse(response.choices[0].message.content)
        if not isinstance(medications, list):
            medications = []
    except Exception as e:
        print(f"⚠️  AI extraction error: {e}")
        medications = []
 
    processing_time = int((time.time() - start_time) * 1000)
 
    # Drug Interaction Check
    drug_names = [
        translate_drug(m.get("activeIngredient", ""))
        for m in medications
        if m.get("activeIngredient", "").strip()
    ]
 
    interactions = []
    for i in range(len(drug_names)):
        for j in range(i + 1, len(drug_names)):
            result = check_interaction_in_db(drug_names[i], drug_names[j])
            if result:
                interactions.append(format_interaction(result))
 
    return {
        "scanId":               str(uuid.uuid4()),
        "confidence":           avg_confidence,
        "status":               "success" if avg_confidence >= 70 else "low_confidence",
        "requiresManualReview": avg_confidence < 70,
        "rawText":              raw_text,
        "processingTimeMs":     processing_time,
        "extractedMedications": medications,
        "interactions":         interactions
    }
 
 
# =====================================================
# Endpoint 4: كل تفاعلات دواء معين
# GET /drug-info/{drug_name}
# =====================================================
@app.get("/drug-info/{drug_name}")
async def drug_info(drug_name: str):
    generic_name = translate_drug(drug_name)
 
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT drug1_ingredient, drug2_ingredient,
                   severity, description_ar, description_en,
                   mechanism, alternatives, source, last_reviewed
            FROM drug_interactions
            WHERE LOWER(drug1_ingredient) = LOWER(%s)
               OR LOWER(drug2_ingredient) = LOWER(%s)
            LIMIT 50
        """, (generic_name, generic_name))
        results = cur.fetchall()
    except Exception as e:
        print(f"⚠️  drug_info error: {e}")
        results = []
    finally:
        release_conn(conn)
 
    interactions = [format_interaction(r) for r in results]
 
    return {
        "success":            True,
        "original_name":      drug_name,
        "generic_name":       generic_name,
        "total_interactions": len(interactions),
        "interactions":       interactions
    }
 
 
# =====================================================
# Endpoint 5: Chatbot
# POST /chatbot
# =====================================================
class ChatRequest(BaseModel):
    message: str
 
 
@app.post("/chatbot")
async def chatbot(req: ChatRequest):
    # 1. استخرج الأدوية من السؤال
    try:
        extract_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[
                {"role": "system", "content": """
Extract drug names from the question and return ONLY JSON:
{"drugs": ["drug1", "drug2"]}
- Convert to English generic names lowercase
- Arabic: بروفين=ibuprofen, كونكور=bisoprolol, بنادول=paracetamol, فلاجيل=metronidazole
- Return ONLY JSON, no markdown, no explanation
"""},
                {"role": "user", "content": req.message}
            ]
        )
        drugs_data = safe_json_parse(extract_response.choices[0].message.content)
        drugs = drugs_data.get("drugs", [])
    except Exception as e:
        print(f"⚠️  Drug extraction error: {e}")
        drugs = []
 
    # 2. ابحث عن التفاعلات في الـ DB
    interactions = []
    if len(drugs) >= 2:
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                d1 = translate_drug(drugs[i])
                d2 = translate_drug(drugs[j])
                result = check_interaction_in_db(d1, d2)
                if result:
                    interactions.append(format_interaction(result))
 
    # 3. رد بالعربي
    if interactions:
        context = "معلومات التفاعلات من قاعدة البيانات:\n"
        for inter in interactions:
            context += (
                f"- {inter['drug1_ingredient']} + {inter['drug2_ingredient']}: "
                f"{inter['description_ar']} (خطورة: {inter['severity']})\n"
            )
    else:
        context = "لم يتم العثور على تفاعلات في قاعدة البيانات."
 
    try:
        chat_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": f"""
أنت صيدلاني مصري متخصص ومساعد طبي موثوق.
أجب على أسئلة المرضى بالعربي بشكل واضح ومبسط.
استخدم المعلومات من قاعدة البيانات إذا توفرت.
دائماً انصح بمراجعة الطبيب أو الصيدلاني للتأكيد.
 
{context}
"""},
                {"role": "user", "content": req.message}
            ]
        )
        answer = chat_response.choices[0].message.content
    except Exception as e:
        print(f"⚠️  Chatbot response error: {e}")
        answer = "عذراً، حدث خطأ في معالجة سؤالك. يرجى المحاولة مرة أخرى."
 
    return {
        "success":            True,
        "question":           req.message,
        "drugs_detected":     drugs,
        "interactions_found": interactions,
        "answer":             answer
    }
 
 
# =====================================================
# Health Check
# =====================================================
@app.get("/health")
async def health_check():
    ocr_engine = "Google Cloud Vision" if vision_client else "EasyOCR"
    return {"status": "ok", "service": "MediSync AI FastAPI"}
 
 
# =====================================================
# Run
# =====================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)