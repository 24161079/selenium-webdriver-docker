import time
from typing import Dict, List

from selenium.webdriver.common.by import By

from ..app_types import ComboBoxIds
from ..constants import TIMEOUTS, msg_not_found, msg_select_error, msg_selected


class ComboBoxHelper:
    def __init__(self, driver):
        self.driver = driver

    def get_items(self, combo_id: str) -> List[Dict[str, str]]:
        script = """
        const id = arguments[0];
        const listItems = document.querySelectorAll(`#${id} .rcbSlide .rcbList li`);
        return Array.from(listItems).map((li, idx) => ({
          index: idx,
          text: li.textContent ? li.textContent.trim() : '',
          className: li.className || ''
        }));
        """
        items = self.driver.execute_script(script, combo_id)
        print(f"      Retrieved {len(items)} items from {combo_id}: {items[:3]}")
        return items

    def select_item(self, combo_id: str, item_text: str) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR, f"#{combo_id}_Arrow").click()
            time.sleep(TIMEOUTS["click_arrow"])

            clicked = self.driver.execute_script(
                """
                const id = arguments[0];
                const text = arguments[1];
                const items = Array.from(document.querySelectorAll(`#${id}_DropDown .rcbList li`));
                for (const item of items) {
                  if ((item.textContent || '').trim() === text) {
                    item.click();
                    return true;
                  }
                }
                return false;
                """,
                combo_id,
                item_text,
            )

            if clicked:
                print(msg_selected(item_text))
                time.sleep(TIMEOUTS["after_network_idle"])
                return True

            print(msg_not_found(item_text))
            return False
        except Exception as exc:
            print(msg_select_error(item_text, str(exc)))
            return False

    @staticmethod
    def find_combo_box_ids(combo_box_info: List[Dict], patterns: Dict[str, str]) -> ComboBoxIds:
        ids = ComboBoxIds()
        for combo in combo_box_info:
            combo_id = combo.get("id", "")
            if patterns["grade"] in combo_id and ids.grade is None:
                ids.grade = combo_id
            if patterns["class_room"] in combo_id and ids.class_room is None:
                ids.class_room = combo_id
            if patterns["subject"] in combo_id and ids.subject is None:
                ids.subject = combo_id
        return ids
