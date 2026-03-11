from fpdf import FPDF
import os
from datetime import datetime

MARKETPLACE_DETAILS = {
    "wb": {
        "full_name": "Общество с ограниченной ответственностью «Вайлдберриз»",
        "inn": "7721546864",
        "address": "142181, Московская область, г. Подольск, деревня Коледино, тер. Индустриальный Парк Коледино, д. 6, стр. 1"
    },
    "ozon": {
        "full_name": "Общество с ограниченной ответственностью «Интернет Решения»",
        "inn": "7704217370",
        "address": "123112, г. Москва, Пресненская наб., д. 10, блок С, комплекс «Башня на Набережной»"
    }
}


class ClaimPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Roboto", size=8)
        self.set_text_color(128)
        self.cell(0, 10, f"Сформировано автоматически сервисом Audit-App. Страница {self.page_no()}", align="C")


def create_claim_pdf(audit_results, seller_info, marketplace_type="wb"):
    pdf = ClaimPDF()
    pdf.add_page()

    # Подгрузка шрифтов
    base_path = os.path.dirname(__file__)
    reg_font = os.path.join(base_path, "Roboto-Regular.ttf")
    bold_font = os.path.join(base_path, "Roboto-Bold.ttf")

    if os.path.exists(reg_font) and os.path.exists(bold_font):
        pdf.add_font("Roboto", "", reg_font)
        pdf.add_font("Roboto", "B", bold_font)
        font_name = "Roboto"
    else:
        # Фолбэк на Arial, если файлы не найдены (но кириллица может поплыть)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "ОШИБКА: Файлы шрифтов Roboto не найдены в директории backend!", ln=True)
        return pdf.output()

    mp = MARKETPLACE_DETAILS.get(marketplace_type, MARKETPLACE_DETAILS["wb"])

    # 1. ЮРИДИЧЕСКАЯ ШАПКА (выравнивание вправо)
    pdf.set_font(font_name, size=10)
    pdf.set_x(110)
    header_text = (
        f"Кому: Ген. директору {mp['full_name']}\n"
        f"ИНН: {mp['inn']}\n"
        f"Адрес: {mp['address']}\n\n"
        f"От: {seller_info['name']}\n"
        f"ИНН: {seller_info['inn']}\n"
        f"Адрес: {seller_info['address']}"
    )
    pdf.multi_cell(90, 5, txt=header_text, align='L')
    pdf.ln(10)

    # 2. ЗАГОЛОВОК
    pdf.set_font(font_name, "B", size=16)
    pdf.cell(0, 15, txt="ДОСУДЕБНАЯ ПРЕТЕНЗИЯ", ln=True, align='C')
    pdf.ln(5)

    # 3. ОСНОВНОЙ ТЕКСТ С СЫЛКАМИ НА ЗАКОНЫ
    pdf.set_font(font_name, size=11)
    date_now = datetime.now().strftime("%d.%m.%Y")
    intro_text = (
        f"Между нами и {mp['full_name']} заключен договор (Оферта) о реализации товаров. "
        f"По результатам финансового аудита за отчетный период выявлены нарушения условий договора, "
        f"приведшие к необоснованному удержанию денежных средств.\n\n"
        f"Согласно ст. 309, 310 ГК РФ, обязательства должны исполняться надлежащим образом. "
        f"В соответствии со ст. 783 ГК РФ и нормами о договоре возмездного оказания услуг (ст. 779 ГК РФ), "
        f"требуем устранить нарушения и произвести выплату в размере {audit_results['total']} руб."
    )
    pdf.multi_cell(0, 6, txt=intro_text)
    pdf.ln(5)

    # 4. ТАБЛИЦА НАРУШЕНИЙ
    pdf.set_font(font_name, "B", size=10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 10, "Основание (Детали нарушения)", 1, 0, "C", True)
    pdf.cell(40, 10, "ID Операции", 1, 0, "C", True)
    pdf.cell(40, 10, "Сумма (руб.)", 1, 1, "C", True)

    pdf.set_font(font_name, size=9)
    for item in audit_results['items']:
        # Обрезаем текст, чтобы не ломал таблицу
        reason = (item['reason'][:55] + '..') if len(item['reason']) > 55 else item['reason']
        pdf.cell(110, 8, reason, 1)
        pdf.cell(40, 8, str(item['id']), 1, 0, "C")
        pdf.cell(40, 8, f"{item['amount']}", 1, 1, "R")

    pdf.set_font(font_name, "B", size=11)
    pdf.cell(150, 10, "ИТОГО К ВОЗВРАТУ:", 0, 0, "R")
    pdf.cell(40, 10, f"{audit_results['total']} руб.", 0, 1, "R")
    pdf.ln(5)

    # 5. РЕКВИЗИТЫ И СРОКИ
    pdf.set_font(font_name, size=11)
    footer_legal = (
        f"Денежные средства просим перечислить по реквизитам:\n"
        f"Р/с: {seller_info['account']}\nБИК: {seller_info['bik']}\n\n"
        f"Срок ответа на претензию — 10 рабочих дней. В случае отказа в удовлетворении требований, "
        f"мы будем вынуждены обратиться в Арбитражный суд для принудительного взыскания суммы долга, "
        f"процентов за пользование чужими денежными средствами (ст. 395 ГК РФ) и судебных издержек."
    )
    pdf.multi_cell(0, 6, txt=footer_legal)

    # 6. ПОДПИСЬ И ПЕЧАТЬ
    pdf.ln(10)
    pdf.cell(100, 10, f"Дата: {date_now}", ln=0)
    pdf.cell(0, 10, "Подпись: ________________ / (ФИО)", ln=1, align="R")

    # СИНЯЯ ПЕЧАТЬ (Электронная подпись)
    pdf.set_draw_color(0, 51, 153)
    pdf.set_text_color(0, 51, 153)
    pdf.set_line_width(0.5)
    pdf.rect(140, 245, 55, 25)
    pdf.set_font(font_name, "B", 7)
    pdf.set_xy(142, 247)
    pdf.multi_cell(51, 4, "ДОКУМЕНТ ПОДПИСАН\nУСИЛЕННОЙ КВАЛИФИЦИРОВАННОЙ\nЭЛЕКТРОННОЙ ПОДПИСЬЮ\nID: AUDIT-CLAIM-8821",
                   align="C")

    return pdf.output()