ROLE_TAGS = {
    "medical",      # медицина
    "engineering",  # инженерия / техника
    "science",      # наука / исследования
    "survival",     # выживание / охота / сельское хозяйство
    "social",       # коммуникация / психология / лидерство
    "military",     # оружие / охрана / тактика
    "craft",        # ремесло / строительство
    "scout",        # разведка / наблюдение / связь
    "magic",        # магия / оккультизм / сверхъестественное
}

GENDER_TAGS = {"male", "female", "neutral"}

profession = [
    {"id": "Surgeon",  "title": "Хирург",  "gender": "neutral", "tags": ["medical"]},
    {"id": "Male nurse", "title": "Медбрат", "gender": "male",   "tags": ["medical"]},
    {"id": "Military doctor", "title": "Военный врач", "gender": "neutral", "tags": ["medical", "military"]},
    {"id": "Ophthalmologist", "title": "Офтальмолог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Nurse", "title": "Медсестра", "gender": "female", "tags": ["medical"]},
    {"id": "Paramedic", "title": "Фельдшер", "gender": "neutral", "tags": ["medical"]},
    {"id": "Gynecologist", "title": "Гинеколог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Nutritionist", "title": "Диетолог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Pediatrician", "title": "Педиатр", "gender": "neutral", "tags": ["medical"]},
    {"id": "Urologist", "title": "Уролог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Dentist", "title": "Зубной врач", "gender": "neutral", "tags": ["medical"]},
    {"id": "Pharmacist", "title": "Фармацевт", "gender": "neutral", "tags": ["medical"]},
    {"id": "Psychiatrist", "title": "Психиатр", "gender": "neutral", "tags": ["medical"]},
    {"id": "Dermatovenereologist", "title": "Дерматовенеролог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Bioengineer", "title": "Биоинженер", "gender": "neutral", "tags": ["medical"]},
    {"id": "Folk Healer", "title": "Знахарь", "gender": "neutral", "tags": ["medical", "magic"]},
    {"id": "Ship's doctor", "title": "Корабельный врач", "gender": "neutral", "tags": ["medical"]},
    {"id": "Gastroenterologist", "title": "Гастроэнтеролог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Virologist", "title": "Вирусолог", "gender": "neutral", "tags": ["medical"]},
    {"id": "Vet", "title": "Ветеринар", "gender": "neutral", "tags": ["medical", "survival"]},
    {"id": "Infectious disease specialist", "title": "Инфекционист", "gender": "neutral", "tags": ["medical"]},
    {"id": "Pathologist", "title": "Патологоанатом", "gender": "neutral", "tags": ["medical"]},
    {"id": "Electrical specialist", "title": "Специалист по электрике", "gender": "neutral", "tags": ["engineering"]},
    {"id": "Mechanical Engineer", "title": "Инженер-механик", "gender": "neutral", "tags": ["engineering"]},
    {"id": "Chemist", "title": "Химик", "gender": "neutral", "tags": ["engineering"]},
]
