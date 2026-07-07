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


async def add_new_vpn_client(tg_id: int, db_id: int, days: int = 3) -> str | None:
    client_email = f'tg_{tg_id}'

    current_time_ms = int(time.time() * 1000)
    days_in_ms = days * 24 * 60 * 60 * 1000
    buffer_hours_in_ms = 4 * 60 * 60 * 1000  # запас 4 часа

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # -----------------------------------------------------------------
            # ШАГ 1: Запрашиваем конкретного клиента по Email через ОФИЦИАЛЬНЫЙ API
            # -----------------------------------------------------------------
            get_client_url = f"{BASE_URL}/panel/api/clients/get/{client_email}"
            print(f"📡 Проверяем клиента {client_email} через официальный API...")

            existing_client = None
            async with session.get(get_client_url) as get_response:
                if get_response.status == 200:
                    get_data = await get_response.json()
                    # Если клиент найден, панель возвращает его в поле "obj"
                    if get_data.get("success") is True and get_data.get("obj"):
                        existing_client = get_data["obj"]
                else:
                    print(f"ℹ️ Клиент не найден (статус {get_response.status}), будем создавать нового.")

            # -----------------------------------------------------------------
            # ШАГ 2: Если клиент СУЩЕСТВУЕТ -> ОБНОВЛЯЕМ (Продлеваем подписку)
            # -----------------------------------------------------------------
            if existing_client:
                print(f"ℹ️ Клиент {client_email} существует. Переходим к продлению подписки...")

                client_uuid = existing_client.get("id")
                sub_id = existing_client.get("subId")
                if not sub_id or sub_id == "none":
                    # Генерируем уникальный ID, если его нет
                    sub_id = str(uuid.uuid4())[:8]
                old_expiry = existing_client.get("expiryTime", 0)

                # Умный расчет времени окончания
                # Умный расчет времени окончания (твою логику не трогаем, она супер)
                if old_expiry > current_time_ms:
                    expiry_timestamp = old_expiry + days_in_ms
                else:
                    expiry_timestamp = current_time_ms + days_in_ms + buffer_hours_in_ms

                # ✅ ПРАВИЛЬНЫЙ PAYLOAD: все поля идут на верхнем уровне, без оберток!
                payload = {
                    "id": client_uuid,
                    "flow": "xtls-rprx-vision",
                    "email": client_email,
                    "limitIp": 2,
                    "totalGB": 0,
                    "expiryTime": int(expiry_timestamp),  # Защита от точек в минутах
                    "enable": True,
                    "tgId": int(tg_id),
                    "subId": sub_id,
                    "comment": "",
                    "group": "",
                    "reset": 0,
                    "security": "auto"
                }

                # URL строго по твоей документации
                update_url = f"{BASE_URL}/panel/api/clients/update/{client_email}"
                print(f"📡 Отправляем запрос на обновление клиента {client_email}...")

                async with session.post(update_url, json=payload) as put_response:
                    if put_response.status == 200:
                        data = await put_response.json()
                        if data.get("success") is True:
                            print(f"🎉 Успех! Официальный API обновил подписку для {client_email}.")
                            return f"{SUB_BASE_URL}/{sub_id}"
                        else:
                            print(f"❌ Ошибка обновления: {data.get('msg')}")
                            return None
                    else:
                        print(f"❌ Сервер ответил статусом: {put_response.status}")
                        return None


            # -----------------------------------------------------------------
            # ШАГ 3: Если клиента НЕТ -> СОЗДАЕМ НОВОГО
            # -----------------------------------------------------------------
            else:
                print(f"ℹ️ Клиента {client_email} нет в панели. Создаем с нуля...")

                client_uuid = str(uuid.uuid4())
                sub_id = str(uuid.uuid4()).replace("-", "")[:16]
                expiry_timestamp = int(current_time_ms + days_in_ms + buffer_hours_in_ms)

                payload = {
                    "client": {
                        "id": client_uuid,
                        "flow": "xtls-rprx-vision",
                        "email": client_email,
                        "limitIp": 2,
                        "totalGB": 0,
                        "expiryTime": expiry_timestamp,
                        "enable": True,
                        "tgId": int(tg_id),
                        "subId": sub_id,
                        "comment": "",
                        "group": "",
                        "reset": 0,
                        "security": "auto"
                    },
                    "inboundIds": [1]
                }

                add_url = f"{BASE_URL}/panel/api/clients/add"
                async with session.post(add_url, json=payload) as post_response:
                    if post_response.status == 200:
                        data = await post_response.json()
                        if data.get("success") is True:
                            print("🎉 Успех! Официальный API создал нового клиента.")
                            return f"{SUB_BASE_URL}/{sub_id}"
                        else:
                            print(f"❌ Ошибка добавления: {data.get('msg')}")
                            return None
                    else:
                        print(f"❌ Сервер ответил статусом: {post_response.status}")
                        return None

        except Exception as e:
            print(f"💥 Критическая ошибка в add_new_vpn_client: {e}")
            return None