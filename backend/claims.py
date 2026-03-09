from fpdf import FPDF
import os

def generate_error_pdf(pdf, message):
    pdf.cell(200, 10, txt=message, ln=True)
    return pdf.output()

def create_claim_pdf(user_data, audit_results):
    pdf = FPDF()
    pdf.add_page()
    
    # ВАЖНО: Нужно подгрузить шрифт с поддержкой кириллицы (например, DejaVuSans)
    # Загрузи файл шрифта .ttf в папку backend
    # Путь к шрифту (он должен лежать в той же папке на сервере)
    font_path = os.path.join(os.path.dirname(__file__), "Roboto_Condensed-Regular.ttf")
    if os.path.exists(font_path):
        pdf.add_font('Roboto_Condensed-Regular', '', font_path)
        pdf.set_font("Roboto_Condensed-Regular", 14)
    else:
        pdf.set_font("Arial", size=12)
        return generate_error_pdf(pdf, "Font file missing! Check backend folder.")
    
    pdf.cell(200, 10, txt="ПРЕТЕНЗИЯ К МАРКЕТПЛЕЙСУ", ln=True, align='C')
    pdf.ln(10)
    
    pdf.cell(200, 10, txt=f"Сумма требований: {audit_results['total']} руб.", ln=True)
    pdf.ln(5)
    
    pdf.multi_cell(0, 10, txt="В ходе автоматизированной сверки были выявлены следующие расхождения:")
    
    for item in audit_results['items']:
        pdf.cell(0, 10, txt=f"- {item['reason']}: {item['amount']} руб. (Заказ {item['id']})", ln=True)
    
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt="Требую произвести корректировку взаиморасчетов в течение 10 рабочих дней.")
    
    # Возвращаем байты файла
    return pdf.output()
