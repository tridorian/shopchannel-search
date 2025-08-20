from pydrive2.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.drive import GoogleDrive
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bq_loader.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authen_to_drive():
    gauth = GoogleAuth()

    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "gcp_master_key.json",
        SCOPES,
    )
    drive = GoogleDrive(gauth)

    return drive


def mount_drive(drive):
    query = "'{}' in parents and trashed=false"
    query = query.format("1Sp0-rahtGZN0ewI4ae6FsnAJK7xC096l")
    file_list = drive.ListFile({"q": query}).GetList()

    return file_list


def _fix_month_abbrv(txt):
    txt = txt.strip()
    txt = txt.replace("june", "jun")
    txt = txt.replace("july", "jul")
    return txt


def get_today_csv_folder_id(file_list):
    date_id_map = dict()

    for f in file_list:
        file_id = os.path.basename(
            dict(f)["parents"][0]["selfLink"].split("/parents")[0]
        )
        date = (
            datetime.strptime(_fix_month_abbrv(dict(f)["title"]), "%d %b")
            .replace(year=datetime.now().year)
            .date()
        )

        date_id_map[date] = file_id

    today_date = datetime.today().date()

    # today_date = (datetime.today() - timedelta(days=1)).date()
    # print(date_id_map)
    # print(today_date)
    if today_date not in date_id_map:
        return None, None

    return date_id_map[today_date], date_id_map


def download_today_csv(csv_folder_id, drive):
    query = "'{}' in parents and trashed=false"
    query = query.format(csv_folder_id)
    file_list = drive.ListFile({"q": query}).GetList()
    csv_id = dict(file_list[0])["id"]

    out_file_name = f"product_data_{datetime.today().date()}.csv"

    f = drive.CreateFile({"id": csv_id})

    f.GetContentFile(out_file_name)

    return out_file_name


def drive_mount_ops():
    drive = authen_to_drive()
    logger.info("Drive mounted successfully")
    file_list = mount_drive(drive)
    csv_folder_id, date_map = get_today_csv_folder_id(file_list)

    if csv_folder_id:
        out_file_name = download_today_csv(csv_folder_id, drive)
        return out_file_name
    else:
        return None
