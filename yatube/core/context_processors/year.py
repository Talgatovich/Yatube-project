from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    current_date = datetime.now().year
    return {
        'year': current_date
    }
