from fpdf import FPDF

def create_claim_pdf(user_data, audit_results):
    pdf = FPDF()
    pdf.add_page()
    
    # ВАЖНО: Нужно подгрузить шрифт с поддержкой кириллицы (например, DejaVuSans)
    # Загрузи файл шрифта .ttf в папку backend
    pdf.add_font('Roboto_Condensed-Regular', '', 'Roboto_Condensed-Regular.ttf', uni=True)
    
    pdf.set_font("Roboto_Condensed-Regular.ttf", size=14) # Пока стандартный для структуры
    
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
