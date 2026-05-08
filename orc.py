import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import easyocr

reader = easyocr.Reader(['ar', 'en'])

def ocr_image(image_path):
    results = reader.readtext(image_path)
    text = " ".join([r[1] for r in results])
    return text

# تجربة
result = ocr_image("test.jpg")
print(result)