from config import config
import gspread
import re
import logging
from datetime import date

logger = logging.getLogger(__name__)


class GSheet:
    def __init__(self, token: dict = config.ROTA_SERVICE_ACCOUNT):
        rota_sheet = getattr(config, "ROTA_SHEET", "ROTA")
        assignment_wsheet = getattr(config, "ASSIGNMENT_WSHEET", "Assignments")

        account = gspread.service_account_from_dict(token)
        self._rota_sheet = account.open(rota_sheet)
        self._assignment_wsheet = self._rota_sheet.worksheet(assignment_wsheet)

    def add_release(
        self,
        rel_ver: str,
        s_date: date = None,
        e_date: date = None,
        pm: str = None,
        qe1: str = None,
        qe2: str = None,
    ) -> None:
        passed_args = {**locals()}
        release_regex = re.compile(r"^\d\.\d{1,3}\.\d{1,3}$")
        if not release_regex.match(rel_ver):
            logger.debug(f"{rel_ver} seems to be wrongly formatted")
            raise ValueError(
                f"{rel_ver} does not seem to match the expected format `\\d\\.\\d{1, 3}\\.\\d{1, 3}`"
            )

        row_to_append = [rel_ver, s_date, e_date, pm, qe1, qe2]

        if not row_to_append:
            logging.error(f"No row to be updated: {passed_args}")
            raise ValueError("No arguments to be added.")

        self._assignment_wsheet.append_row(
            row_to_append, value_input_option="USER_ENTERED"
        )  # use `input_option` so that Appscript gets triggered

    def fetch_data_by_release(self, rel_ver: str) -> list:
        release_regex = re.compile(r"^\d\.\d{1,3}\.\d{1,3}$")
        if not release_regex.match(rel_ver):
            logger.debug(f"{rel_ver} seems to be wrongly formatted")
            raise ValueError(
                f"{rel_ver} does not seem to match the expected format `\\d\\.\\d{1, 3}\\.\\d{1, 3}`"
            )

        values = self._assignment_wsheet.get_values("A:G")  # only get relevant columns

        return_val = None
        for v in values:
            if v[0] == rel_ver:
                return_val = v
                break

        return return_val

    def fetch_data_by_time(self, time_period: str) -> list:
        time_period = time_period.title()  # Google Sheet has title case
        if time_period not in ("This Week", "Next Week"):
            logger.error(f"Incorrect time period: {time_period}")
            raise ValueError(f"Invalid `time_period`: {time_period}")

        values = self._assignment_wsheet.get_values("A:G")  # only get relevant columns

        return [v for v in values if v[6] == time_period]

    def replace_user_for_release(
        self, rel_ver: str, column: str, user: str = None
    ) -> None:
        column = column.lower()
        release_regex = re.compile(r"^\d\.\d{1,3}\.\d{1,3}$")
        if not release_regex.match(rel_ver):
            logger.debug(f"{rel_ver} seems to be wrongly formatted")
            raise ValueError(
                f"{rel_ver} does not seem to match the expected format `\\d\\.\\d{1, 3}\\.\\d{1, 3}`"
            )

        if column not in ("pm", "qe1", "qe2"):
            logger.error(f"Invalid value for replace column: {column}")
            raise ValueError(f"Invalid value for replace column: {column}")

        column_letter_mapping = {"pm": "D", "qe1": "E", "qe2": "F"}

        column_a1 = column_letter_mapping[column]

        values = self._assignment_wsheet.get_values("A:G")  # only get relevant columns

        row_idx = -1
        for idx, v in enumerate(values):
            if v[0] == rel_ver:
                row_idx = idx
                break

        if row_idx == -1:
            logging.debug(f"Release {rel_ver} not found")
            raise ValueError(f"Release {rel_ver} not found")

        cell_a1 = f"{column_a1}{row_idx + 1}"
        if not user:
            logger.debug(f"Cleared cell: {cell_a1}")
            self._assignment_wsheet.batch_clear([cell_a1])
        else:
            self._assignment_wsheet.update_acell(cell_a1, user)


try:
    gsheet = GSheet()
except Exception as ex:
    gsheet =  None
    logging.info(f"Error in call to Gsheet : {repr(ex)}")
