import vk_api
import os
import time
import logging

logger = logging.getLogger(__name__)

def send_to_vk_groups(message_text, photo_paths):
    """
    Отправляет пост во все группы из GROUP_IDS.
    Требуется только VK_TOKEN (пользовательский, полученный через OAuth).
    """
    token = os.getenv("VK_TOKEN")
    groups_raw = os.getenv("GROUP_IDS", "")
    group_ids = [int(gid.strip()) for gid in groups_raw.split(",") if gid.strip()]

    if not token:
        return "❌ Ошибка: VK_TOKEN не задан"
    if not group_ids:
        return "❌ Ошибка: GROUP_IDS не задан"

    try:
        vk_session = vk_api.VkApi(token=token)
        vk = vk_session.get_api()
        upload = vk_api.VkUpload(vk_session)

        # Загружаем фото
        attachments = []
        for path in photo_paths:
            photo = upload.photo_wall(path)[0]
            attachments.append(f"photo{photo['owner_id']}_{photo['id']}")
        attachments_str = ",".join(attachments)

        results = []
        for gid in group_ids:
            try:
                vk.wall.post(owner_id=gid, message=message_text, attachments=attachments_str)
                results.append(f"✅ Группа {gid}: пост опубликован.")
                logger.info(f"Пост в {gid} отправлен")
            except vk_api.exceptions.ApiError as e:
                err = str(e)
                results.append(f"❌ Группа {gid}: ошибка API — {err[:100]}")
                logger.error(f"Ошибка в группе {gid}: {err}")
            time.sleep(2)   # пауза, чтобы не спамить

        return "\n".join(results)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return f"🔥 Критическая ошибка: {e}"
