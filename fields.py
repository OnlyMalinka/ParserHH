# Словарь для отображения в интерфейсе -> внутренние ключи
AVAILABLE_FIELDS = {
    "Компания": "employer_name",
    "Вакансия": "vacancy_name",
    "Город": "city",
    "Опыт работы": "experience",
    "График работы": "schedule",
    "Тип занятости": "employment",
    "Зарплата ОТ": "salary_from",
    "Зарплата ДО": "salary_to",
    "Валюта": "salary_currency",
    "Требования": "snippet_requirement",
    "Обязанности": "snippet_responsibility",
    "Ссылка на вакансию": "vacancy_url",
    "Ссылка на компанию": "employer_url",
    "Дата публикации": "published_at"
}

def extract_vacancy_data(item):
    """Безопасно извлекает данные из одного элемента вакансии"""
    emp = item.get("employer", {})
    sal = item.get("salary") or {}
    snip = item.get("snippet") or {}
    exp = item.get("experience") or {}
    sched = item.get("schedule") or {}
    empl = item.get("employment") or {}
    area = item.get("area") or {}

    return {
        "employer_name": emp.get("name", "Не указано"),
        "vacancy_name": item.get("name", "Не указано"),
        "city": area.get("name", "Не указано"),
        "experience": exp.get("name", "Не указано"),
        "schedule": sched.get("name", "Не указано"),
        "employment": empl.get("name", "Не указано"),
        "salary_from": sal.get("from", ""),
        "salary_to": sal.get("to", ""),
        "salary_currency": sal.get("currency", ""),
        "snippet_requirement": snip.get("requirement", ""),
        "snippet_responsibility": snip.get("responsibility", ""),
        "vacancy_url": item.get("alternate_url", ""),
        "employer_url": emp.get("alternate_url", ""),
        "published_at": item.get("published_at", "")
    }