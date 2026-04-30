import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

logger = logging.getLogger(__name__)

def send_to_vk_groups(message_text, photo_paths):
    """
    Отправляет пост во все группы из переменной GROUP_IDS.
    Использует логин/пароль из VK_LOGIN / VK_PASSWORD.
    """
    groups_raw = os.getenv("GROUP_IDS", "")
    group_ids = [int(gid.strip()) for gid in groups_raw.split(",") if gid.strip()]
    login = os.getenv("VK_LOGIN")
    password = os.getenv("VK_PASSWORD")

    # Проверка ошибок на старте
    if not login or not password:
        err_msg = "Отсутствуют VK_LOGIN или VK_PASSWORD в переменных окружения"
        logger.error(err_msg)
        return f"❌ Ошибка: {err_msg}"
    if not group_ids:
        err_msg = "Отсутствует GROUP_IDS"
        logger.error(err_msg)
        return f"❌ Ошибка: {err_msg}"
    if not photo_paths:
        logger.warning("Список photo_paths пуст, будет отправлен только текст")

    # Настройка браузера (headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = None
    results = []
    try:
        logger.info("Запуск браузера...")
        driver = uc.Chrome(options=chrome_options, version_main=147)
        driver.get("https://vk.com")
        time.sleep(3)

        # Авторизация
        logger.info("Авторизация в ВК...")
        driver.find_element(By.NAME, "login").send_keys(login)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        # Основной цикл по группам
        for gid in group_ids:
            try:
                group_id_clean = str(gid).replace("-", "")
                logger.info(f"Переход в группу {gid} (club{group_id_clean})")
                driver.get(f"https://vk.com/club{group_id_clean}")
                time.sleep(5)

                # Открытие формы предложки
                try:
                    driver.find_element(By.XPATH, "//button[contains(@class, 'suggest')]").click()
                    logger.info("Нажата кнопка 'Предложить новость'")
                except:
                    driver.find_element(By.XPATH, "//div[contains(@class, 'post_field')]").click()
                    logger.info("Нажато поле для поста")
                time.sleep(2)

                # Загрузка фото
                for path in photo_paths:
                    abs_path = os.path.abspath(path)
                    driver.find_element(By.XPATH, "//input[@type='file']").send_keys(abs_path)
                    logger.info(f"Загружено фото: {abs_path}")
                    time.sleep(2)

                # Ввод текста
                textarea = driver.find_element(By.XPATH, "//div[@role='textbox']")
                textarea.click()
                textarea.send_keys(message_text)
                logger.info("Текст объявления введён")

                # Отправка
                driver.find_element(By.XPATH, "//button[contains(@class, 'submit')]").click()
                time.sleep(5)
                results.append(f"✅ Группа {gid}: пост отправлен (на модерацию/опубликован).")
                logger.info(f"Успешно отправлено в группу {gid}")
            except Exception as e:
                err = str(e)[:150]
                results.append(f"❌ Группа {gid}: ошибка — {err}")
                logger.error(f"Ошибка при отправке в группу {gid}: {err}")

            time.sleep(30)  # пауза между группами

        return "\n".join(results)

    except Exception as e:
        err = str(e)[:200]
        logger.error(f"Критическая ошибка в send_to_vk_groups: {err}")
        return f"🔥 Критическая ошибка ВК: {err}"
    finally:
        if driver:
            driver.quit()
            logger.info("Браузер закрыт")
