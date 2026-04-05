import streamlit as st
import requests
import pandas as pd
import time
from fields import AVAILABLE_FIELDS, extract_vacancy_data

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

# --- БОКОВАЯ ПАНЕЛЬ: ФИЛЬТРЫ API ---
st.sidebar.header("🎯 Фильтры поиска")

exp_dict = {"Неважно": None, "Нет опыта": "noExperience", "От 1 до 3 лет": "between1And3", "От 3 до 6 лет": "between3And6", "Более 6 лет": "moreThan6"}
schedule_dict = {"Неважно": None, "Полный день": "fullDay", "Удаленная работа": "remote", "Гибкий график": "flexible", "Сменный график": "shift", "Вахтовый метод": "flyInFlyOut"}

filter_salary_only = st.sidebar.checkbox("Только с указанной зарплатой")
filter_salary_amt = st.sidebar.number_input("Уровень дохода от (руб)", min_value=0, step=10000, value=0)
filter_exp = st.sidebar.selectbox("Опыт работы", list(exp_dict.keys()))
filter_schedule = st.sidebar.selectbox("График работы", list(schedule_dict.keys()))

# --- ОСНОВНОЙ ЭКРАН ---
st.title("🔍 Универсальный парсер вакансий")
st.markdown("Настройте параметры поиска и выберите необходимые поля для формирования базы.")

col1, col2 = st.columns([2, 1])
with col1:
    search_text = st.text_input("🔑 Ключевые слова", value="менеджер по продажам")
with col2:
    user_email = st.text_input("📧 Ваш Email (для API)", placeholder="example@mail.ru")

regions_dict = get_russian_regions()
selected_regions = st.multiselect(
    "🌍 Регионы поиска",
    options=list(regions_dict.keys()),
    default=["Москва"]
)

with st.expander("⚙️ Настройка выгрузки и дубликатов", expanded=True):
    remove_duplicates = st.checkbox("Удалять дубликаты (оставлять только одну запись на каждую уникальную компанию)", value=True)
    
    selected_display_names = st.multiselect(
        "Выберите поля, которые попадут в итоговую таблицу:",
        options=list(AVAILABLE_FIELDS.keys()),

        default=["Компания", "Вакансия", "Регион", "Город", "Зарплата ОТ", "Ссылка на вакансию"] 
    )

if st.button("🚀 Начать сбор данных", type="primary"):
    if not search_text or not selected_regions or not user_email or not selected_display_names:
        st.warning("Заполните все обязательные поля и выберите хотя бы одну колонку для вывода.")
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
                params = {
                    "text": search_text,
                    "area": area_id,
                    "per_page": 100, 
                    "page": page
                }
                
                if filter_salary_only: params["only_with_salary"] = True
                if filter_salary_amt > 0: params["salary"] = filter_salary_amt
                if exp_dict[filter_exp]: params["experience"] = exp_dict[filter_exp]
                if schedule_dict[filter_schedule]: params["schedule"] = schedule_dict[filter_schedule]

                response = requests.get("https://api.hh.ru/vacancies", params=params, headers=headers)
                
                if response.status_code != 200:
                    break 
                    
                data = response.json()
                if page == 0 and data.get("found", 0) > 2000:
                    with warnings_container:
                        st.warning(f"⚠️ {region_name}: Найдено {data['found']}. Будет собрано только первые 2000 из-за лимита HH.")

                items = data.get("items", [])
                if not items: break 
                
                for item in items:
                    # ПЕРЕДАЕМ ИМЯ РЕГИОНА ВТОРЫМ АРГУМЕНТОМ!
                    extracted_data = extract_vacancy_data(item, region_name)
                    
                    filtered_entry = {}
                    for display_name in selected_display_names:
                        internal_key = AVAILABLE_FIELDS[display_name]
                        raw_value = str(extracted_data.get(internal_key, ""))
                        clean_value = raw_value.replace("<highlighttext>", "").replace("</highlighttext>", "")
                        filtered_entry[display_name] = clean_value
                        
                    all_vacancies.append(filtered_entry)
                
                if page >= data.get("pages", 1) - 1: break
                page += 1
                time.sleep(0.4)
            
            progress_bar.progress((i + 1) / len(selected_regions))

        status_text.text("✅ Готово!")

        if all_vacancies:
            df = pd.DataFrame(all_vacancies)
            
            # НОВАЯ ЛОГИКА: Проверяем галочку перед удалением
            if remove_duplicates and "Компания" in df.columns:
                df = df.drop_duplicates(subset=["Компания"])
            
            st.success(f"Собрано строк: {len(df)}")
            st.dataframe(df.head(20)) 
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Скачать CSV", data=csv, file_name='export_hh.csv', mime='text/csv')