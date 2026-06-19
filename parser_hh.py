import requests
import time

def get_city_id(city_name):
    """Получает ID города через API hh.ru"""
    try:
        url = "https://api.hh.ru/areas"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        def find_city(areas, name):
            for area in areas:
                if area["name"].lower() == name.lower():
                    return area["id"]
                if "areas" in area:
                    result = find_city(area["areas"], name)
                    if result:
                        return result
            return None
        
        result = find_city(data, city_name)
        return result if result else 1
    except Exception as e:
        print(f"Ошибка получения ID города: {e}")
        return 1

def search_vacancies(
    query,
    city="Москва",
    salary_from=0,
    employment="any",    # full, part, internship, any
    schedule="any",      # remote, flexible, shift, any
    experience="any"     # noExperience, between1And3, between3And6, any
):
    """Поиск вакансий с фильтрами"""
    area_id = get_city_id(city)
    
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": query,
        "area": area_id,
        "salary": salary_from if salary_from > 0 else None,
        "only_with_salary": False,
        "per_page": 20,
        "order_by": "publication_time"
    }
    
    # Добавляем фильтры, если они не "any"
    if employment != "any":
        params["employment"] = employment
    
    if schedule != "any":
        params["schedule"] = schedule
    
    if experience != "any":
        params["experience"] = experience
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        vacancies = []
        for item in data.get("items", []):
            vacancy = {
                "id": item["id"],
                "title": item["name"],
                "company": item["employer"]["name"] if item.get("employer") else "Не указано",
                "salary": format_salary(item.get("salary")),
                "url": item["alternate_url"],
                "description": item.get("snippet", {}).get("responsibility", "")[:200],
                "published_at": item["published_at"]
            }
            vacancies.append(vacancy)
        
        time.sleep(0.5)
        return vacancies
    
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

def format_salary(salary_data):
    if not salary_data:
        return "Зарплата не указана"
    
    from_val = salary_data.get("from")
    to_val = salary_data.get("to")
    currency = salary_data.get("currency", "руб.")
    
    if from_val and to_val:
        return f"{from_val} - {to_val} {currency}"
    elif from_val:
        return f"от {from_val} {currency}"
    elif to_val:
        return f"до {to_val} {currency}"
    return "Зарплата не указана"