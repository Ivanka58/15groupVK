import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

def send_to_vk_groups(message_text, photo_paths):
    groups_raw = os.getenv("GROUP_IDS", "")
    group_ids = [int(gid.strip()) for gid in groups_raw.split(",") if gid.strip()]
    login = os.getenv("VK_LOGIN")
    password = os.getenv("VK_PASSWORD")

    if not login or not password:
        err_msg = "Отсутствуют VK_LOGIN или VK_PASSWORD"
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
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = None
    results = []
    try:
        logger.info("Запуск ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get("https://vk.com")
        wait = WebDriverWait(driver, 10)
        
        # Ввод логина
        login_input = wait.until(EC.presence_of_element_located((By.NAME, "login")))
        login_input.send_keys(login)
        
        # Ввод пароля
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

                # Открытие формы поста
                try:
                    driver.find_element(By.XPATH, "//button[contains(@class, 'suggest')]").click()
                except:
                    driver.find_element(By.XPATH, "//div[contains(@class, 'post_field')]").click()
                time.sleep(2)

                # Загрузка фото
                for path in photo_paths:
                    file_input = driver.find_element(By.XPATH, "//input[@type='file']")
                    file_input.send_keys(os.path.abspath(path))
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
                logger.error(f"Ошибка в группе {gid}: {err}")
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
