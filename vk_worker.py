import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

logger = logging.getLogger(__name__)

def send_to_vk_groups(message_text, photo_paths):
    groups_raw = os.getenv("GROUP_IDS", "")
    group_ids = [int(gid.strip()) for gid in groups_raw.split(",") if gid.strip()]
    login = os.getenv("VK_LOGIN")
    password = os.getenv("VK_PASSWORD")

    if not login or not password:
        err_msg = "Отсутствуют VK_LOGIN или VK_PASSWORD в переменных окружения"
        logger.error(err_msg)
        return f"❌ Ошибка: {err_msg}"
    if not group_ids:
        err_msg = "Отсутствует GROUP_IDS"
        logger.error(err_msg)
        return f"❌ Ошибка: {err_msg}"

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
        
        # Ожидаем появления поля для логина (максимум 10 секунд)
        wait = WebDriverWait(driver, 10)
        
        # Пробуем найти поле ввода логина разными способами
        try:
            login_input = wait.until(EC.presence_of_element_located((By.NAME, "login")))
        except:
            # Если не нашли по name, ищем по другим селекторам
            login_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
        
        login_input.send_keys(login)
        
        # Поле для пароля
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        
        # Кнопка входа
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        for gid in group_ids:
            try:
                group_id_clean = str(gid).replace("-", "")
                logger.info(f"Переход в группу {gid}")
                driver.get(f"https://vk.com/club{group_id_clean}")
                time.sleep(5)

                # Открытие формы предложки
                try:
                    driver.find_element(By.XPATH, "//button[contains(@class, 'suggest')]").click()
                except:
                    driver.find_element(By.XPATH, "//div[contains(@class, 'post_field')]").click()
                time.sleep(2)

                # Загрузка фото
                for path in photo_paths:
                    driver.find_element(By.XPATH, "//input[@type='file']").send_keys(os.path.abspath(path))
                    time.sleep(2)

                # Ввод текста
                textarea = driver.find_element(By.XPATH, "//div[@role='textbox']")
                textarea.click()
                textarea.send_keys(message_text)

                # Отправка
                driver.find_element(By.XPATH, "//button[contains(@class, 'submit')]").click()
                time.sleep(5)
                results.append(f"✅ Группа {gid}: пост отправлен.")
                logger.info(f"Успешно отправлено в группу {gid}")
            except Exception as e:
                err = str(e)[:150]
                results.append(f"❌ Группа {gid}: ошибка — {err}")
                logger.error(f"Ошибка при отправке в группу {gid}: {err}")
            time.sleep(30)

        return "\n".join(results)
    except Exception as e:
        err = str(e)[:200]
        logger.error(f"Критическая ошибка: {err}")
        return f"🔥 Критическая ошибка ВК: {err}"
    finally:
        if driver:
            driver.quit()
            logger.info("Браузер закрыт")
