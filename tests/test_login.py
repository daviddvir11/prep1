

import logging
import os
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.info("Logging initialized: This should appear in test.log and console.")

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="tests/.env.dev")
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")
if not LOGIN_USERNAME:
    raise ValueError("LOGIN_USERNAME is not set in .env.dev or environment")
if not LOGIN_PASSWORD:
    raise ValueError("LOGIN_PASSWORD is not set in .env.dev or environment")

logging.info("Test script started")
import pytest

# --- Pytest hook to flush/close logging handlers after all tests ---
def pytest_sessionfinish(session, exitstatus):
    for handler in logging.getLogger().handlers:
        handler.flush()
        handler.close()

import pytest
import logging
import time
import tempfile
import requests

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


#new
logging.info("Test script started")

class BasePage:
    def __init__(self, driver: WebDriver):
        self.wait = WebDriverWait(driver, timeout=10)
        self.driver = driver

    def wait_and_find_element(self, locator):
        try:
            element = self.wait.until(EC.visibility_of_element_located(locator))
            logging.info(f"Element is visible: {locator}")
            return element
        except TimeoutException:
            logging.warning(f"Timeout waiting for element: {locator}")
            raise AssertionError(f"Element {locator} not visible within timeout")
        except Exception as e:
            logging.error(f"Unexpected error while waiting for element {locator}: {e}")
            raise

    def wait_for_clickable_element(self, locator):
        try:
            element = self.wait.until(EC.element_to_be_clickable(locator))
            logging.info(f"Element is clickable: {locator}")
            return element
        except TimeoutException:
            logging.warning(f"Timeout: Element not clickable: {locator}")
            raise AssertionError(f"Element {locator} was not clickable within timeout")
        except Exception as e:
            logging.error(f"Unexpected error while waiting for clickable element {locator}: {e}")
            raise

    def scroll_into_element(self, locator ):
        try:
            element = self.wait_and_find_element(locator)
            if element and element.is_displayed():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", element)
                logging.info(f"Scrolled into element: {locator}")
                if element.is_displayed():
                    return element
                else:
                    raise AssertionError(f"Element {locator} not visible after scroll")
            else:
                raise AssertionError(f"Element {locator} not found or not displayed before scroll")
        except Exception as e:
            logging.error(f"Error while scrolling to element {locator}: {e}")
            raise

class LoginPage_Locators:
    username = (By.ID, 'username')
    password = (By.ID, 'password')
    login_btn = (By.ID, 'loginBtn')

class DashboardPage_Locators:
    welcome_text = (By.XPATH, "//h1[contains(text(), 'Welcome')]")
    logged_in_btn = (By.ID, 'loggedInBtn')

class LoginPage(BasePage):
    def enter_username(self, username: str):
        username_field = self.wait_and_find_element(LoginPage_Locators.username)
        username_field.clear()
        username_field.send_keys(username)
        logging.info("Entered username: [HIDDEN]")

    def enter_password(self, password: str):
        password_field = self.wait_and_find_element(LoginPage_Locators.password)
        password_field.clear()
        password_field.send_keys(password)
        logging.info("Entered password: [HIDDEN]")

    def click_login_button(self):
        login_button = self.wait_for_clickable_element(LoginPage_Locators.login_btn)
        login_button.click()
        logging.info("Clicked login button")

class DashboardPage(BasePage):
    def verify_logged_in(self):
        self.wait_and_find_element(DashboardPage_Locators.welcome_text)
        self.wait_and_find_element(DashboardPage_Locators.logged_in_btn)
        logging.info("Verified dashboard page")

@pytest.fixture(scope="class")
def driver(request):
    logging.info("Launching browser...")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # Detect if running inside Docker container
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('RUNNING_IN_DOCKER') == '1'
    if in_docker:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    browser = webdriver.Chrome(service=service, options=options)
    browser.implicitly_wait(10)
    request.cls.driver = browser
    yield browser
    logging.info("Closing browser...")
    browser.quit()
    # Ensure all logging handlers are flushed and closed so test.log is written
    for handler in logging.getLogger().handlers:
        handler.flush()
        handler.close()

@pytest.mark.usefixtures("driver")
class TestLoginPage:
    driver: WebDriver

    def wait_for_app(self, url, timeout=30):
        for _ in range(timeout):
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError(f"App not available at {url}")

    def test_login_page(self):
        # Detect if running inside Docker container
        in_docker = os.path.exists('/.dockerenv') or os.environ.get('RUNNING_IN_DOCKER') == '1'
        if in_docker:
            app_url = "http://host.docker.internal:5000/"
        else:
            app_url = "http://localhost:5000/"
        self.wait_for_app(app_url)
        self.driver.get(app_url)
        login_page = LoginPage(self.driver)
        dashboard_page = DashboardPage(self.driver)
        assert "Login" in self.driver.title or "Dashboard" in self.driver.title
        login_page.enter_username(username=LOGIN_USERNAME)
        login_page.enter_password(password=LOGIN_PASSWORD)
        login_page.click_login_button()
        dashboard_page.verify_logged_in()

# SECURITY NOTE:
# - .env.dev is in .gitignore and should NOT be pushed to GitHub.
# - Never log or expose credentials in code or logs.
# - Review code for secrets before pushing to public repositories.
