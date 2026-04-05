import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="Парсер вакансий HH.ru", page_icon="🔍", layout="centered")

@st.cache_data(ttl=86400)
def get_russian_regions():
    try:
        response = requests.get("https://api.hh.ru/areas/113")
        response.raise_for_status()
        areas = response.json().get('areas', [])
        regions_dict = {area['name']: area['id'] for area in areas}
        return dict(sorted(regions_dict.items()))
    except Exception:
        return {"Москва": 1, "Санкт-Петербург": 2}

st.title("🔍 Универсальный парсер вакансий")
st.markdown("Настройте параметры поиска и выберите необходимые поля для формирования базы.")

# 1. Основные настройки
col1, col2 = st.columns(2)
with col1:
    search_text = st.text_input("🔑 Ключевые слова", value="менеджер по продажам")
with col2:
    user_email = st.text_input("📧 Ваш Email (для API)", placeholder="example@mail.ru")

# 2. Выбор регионов
regions_dict = get_russian_regions()
selected_regions = st.multiselect(
    "🌍 Регионы поиска",
    options=list(regions_dict.keys()),
    default=["Москва"]
)

# 3. Выбор полей для вывода (Новое!)
available_fields = {
    "Компания": "employer_name",
    "Вакансия": "vacancy_name",
    "Город": "city",
    "Зарплата ОТ": "salary_from",
    "Зарплата ДО": "salary_to",
    "Требования": "snippet_requirement",
    "Ссылка на вакансию": "vacancy_url",
    "Ссылка на компанию": "employer_url"
}

selected_display_names = st.multiselect(
    "📊 Выберите поля для таблицы и CSV",
    options=list(available_fields.keys()),
    default=["Компания", "Вакансия", "Город", "Ссылка на вакансию"]
)

if st.button("🚀 Начать сбор данных", type="primary"):
    if not search_text or not selected_regions or not user_email or not selected_display_names:
        st.warning("Заполните все поля, выберите регионы и хотя бы одно поле для вывода.")
    elif "@" not in user_email:
        st.error("Введите корректный Email.")
    else:
        all_vacancies = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        warnings_container = st.container()

        headers = {"User-Agent": f"HHParserApp/1.0 ({user_email})"}

        for i, region_name in enumerate(selected_regions):
            area_id = regions_dict[region_name]
            status_text.text(f"⏳ Обработка региона: {region_name}...")
            
            page = 0
            while page < 20:
                params = {"text": search_text, "area": area_id, "per_page": 100, "page": page}
                response = requests.get("https://api.hh.ru/vacancies", params=params, headers=headers)
                
                if response.status_code != 200:
                    break 
                    
                data = response.json()
                if page == 0 and data.get("found", 0) > 2000:
                    with warnings_container:
                        st.warning(f"⚠️ {region_name}: Найдено {data['found']}. Будет собрано только первые 2000.")

                items = data.get("items", [])
                if not items: break 
                
                for item in items:
                    emp = item.get("employer", {})
                    sal = item.get("salary") or {}
                    snip = item.get("snippet") or {}
                    
                    # Собираем полный объект данных
                    full_entry = {
                        "Компания": emp.get("name"),
                        "Вакансия": item.get("name"),
                        "Город": item.get("area", {}).get("name"),
                        "Зарплата ОТ": sal.get("from"),
                        "Зарплата ДО": sal.get("to"),
                        "Требования": snip.get("requirement"),
                        "Ссылка на вакансию": item.get("alternate_url"),
                        "Ссылка на компанию": emp.get("alternate_url")
                    }
                    # Фильтруем только выбранные пользователем поля
                    filtered_entry = {k: full_entry[k] for k in selected_display_names}
                    all_vacancies.append(filtered_entry)
                
                if page >= data.get("pages", 1) - 1: break
                page += 1
                time.sleep(0.4)
            
            progress_bar.progress((i + 1) / len(selected_regions))

        status_text.text("✅ Готово!")

        if all_vacancies:
            df = pd.DataFrame(all_vacancies)
            # Очистка дублей по первой колонке (обычно Компания)
            if "Компания" in df.columns:
                df = df.drop_duplicates(subset=["Компания"])
            
            st.write(f"Собрано записей: {len(df)}")
            st.dataframe(df.head(20)) 
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Скачать CSV", data=csv, file_name='export_hh.csv', mime='text/csv')