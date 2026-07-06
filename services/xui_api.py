import aiohttp
import os
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://gamzivpn-client.mooo.com:39933/y6vfKjjnGmBIbxBUf7'
API_TOKEN = os.getenv('API_TOKEN')
SUB_BASE_URL = 'https://gamzivpn-client.mooo.com:2096/GamziVPN'

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}


async def add_new_vpn_client(tg_id: int, username: str) -> str | None:
    url = f"{BASE_URL}/panel/api/clients/add"

    client_uuid = str(uuid.uuid4())
    sub_id = str(uuid.uuid4()).replace("-", "")[:16]

    # Расчет 3-х дней триала в миллисекундах
    # Вместо ровных 3 дней добавим небольшой хвостик в 4 часа для компенсации часовых поясов
    three_days_in_ms = 3 * 24 * 60 * 60 * 1000
    buffer_hours_in_ms = 4 * 60 * 60 * 1000  # запас 4 часа

    expiry_timestamp = int((time.time() * 1000) + three_days_in_ms + buffer_hours_in_ms)

    # 🎯 Идеальная структура один-в-один как на твоем скриншоте изображение_5.png
    payload = {
        "client": {
            "id": client_uuid,
            "flow": "xtls-rprx-vision",
            "email": username,
            "limitIp": 1,  # Ограничение: 1 устройство (число)
            "totalGB": 0,  # Безлимитный трафик (число)
            "expiryTime": expiry_timestamp,  # Отключение через 3 дня (число)
            "enable": True,
            "tgId": int(tg_id),  # Передаем как число, как в твоем инспекторе
            "subId": sub_id,
            "comment": "",
            "group": "",
            "reset": 0,
            "security": "auto"
        },
        "inboundIds": [1]  # Привязка к Швеции идет наравне с client
    }

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            print(f"📡 Отправляем идеально точный JSON для {username}...")
            async with session.post(url, json=payload) as response:
                print(f"📡 Статус ответа панели: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    if data.get("success") is True:
                        print("🎉 Успех! Панель создала клиента.")
                        return f"{SUB_BASE_URL}/{sub_id}"
                    else:
                        print(f"❌ Панель вернула ошибку: {data.get('msg')}")
                        return None
                else:
                    print(f"❌ Ошибка сервера: {response.status}")
                    return None
        except Exception as e:
            print(f"💥 Критическая ошибка сети: {e}")
            return None