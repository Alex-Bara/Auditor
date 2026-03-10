from fpdf import FPDF
import os

def generate_error_pdf(pdf, message):
    pdf.cell(200, 10, txt=message, ln=True)
    return pdf.output()

def create_claim_pdf(seller_info, audit_results):
    pdf = FPDF()
    pdf.add_page()
    
    # ВАЖНО: Нужно подгрузить шрифт с поддержкой кириллицы (например, DejaVuSans)
    # Загрузи файл шрифта .ttf в папку backend
    # Путь к шрифту (он должен лежать в той же папке на сервере)
    font_path = os.path.join(os.path.dirname(__file__), "Roboto_Condensed-Regular.ttf")
    if os.path.exists(font_path):
        pdf.add_font('Roboto_Condensed-Regular', "", font_path)
        pdf.set_font("Roboto_Condensed-Regular", size=14)
    else:
        pdf.set_font("Arial", size=12)
        return generate_error_pdf(pdf, "Font file missing! Check backend folder.")
    
   # 1. Шапка (справа)
    pdf.set_x(120)
    pdf.multi_cell(80, 5, txt=f"Кому: ООО «Вайлдберриз»\nОт: {seller_info['seller-name']}\nИНН: {seller_info['seller-inn']}\nАдрес: {seller_info['seller-address']}", align='L')
    pdf.ln(20)
    # 2. Заголовок
    pdf.set_font("Roboto_Condensed-Regular", size=14)
    pdf.cell(0, 10, txt="ДОСУДЕБНАЯ ПРЕТЕНЗИЯ", ln=True, align='C')
    pdf.ln(10)
    # 3. Текст
    pdf.set_font("Roboto_Condensed-Regular", size=11)
    text = (
        f"Между мной и ООО «Вайлдберриз» заключен Договор о реализации товара на маркетплейсе. "
        f"В ходе проведения сверки взаиморасчетов за период проведения аудита были выявлены расхождения "
        f"на общую сумму {audit_results['total']} руб."
    )
    pdf.multi_cell(0, 7, txt=text)
    pdf.ln(5)
    
    pdf.multi_cell(0, 7, txt="Основания требований: несоответствие фактически начисленных удержаний "
                             "данным первичной документации и отчетам о реализации.")
    pdf.ln(10)
    # 4. Таблица или список нарушений
    pdf.set_font("Roboto_Condensed-Regular", size=10)
    for item in audit_results['items']:
        pdf.cell(0, 8, txt=f"- {item['reason']}: {item['amount']} руб. (ID операции: {item['id']})", ln=True)
    
    pdf.multi_cell(0, 7, txt=f"Денежные средства прошу перечислить по следующим реквизитам:\n"
                         f"Р/с: {seller_info['seller-account']}\nБИК: {seller_info['seller-bik']}")

    pdf.ln(15)
    pdf.multi_cell(0, 7, txt="На основании вышеизложенного, требую выплатить указанную сумму в течение 10 (десяти) "
                             "календарных дней. В противном случае я буду вынужден обратиться в Арбитражный суд.")
    
    # Возвращаем байты файла
    return pdf.output()
