from drive_csv_loader import drive_mount_ops
from bq_load import bq_upload_ops
from update_datastore import update_datastore_ops
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bq_loader.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def main():
    ## ----- load csv ----- ##
    out_file_name = None
    try:
        out_file_name = drive_mount_ops()
        logger.info(f"Successfully download today's file: {out_file_name}")
    except Exception as e:
        logger.error(f"An error has occured during downloading csv from drive: {e}")

    if out_file_name:
        bq_control = False
        ## ----- upload to bq ----- ##
        try:
            bq_upload_ops(out_file_name)
            logger.info(f"Successfully upload file to BQ")
            bq_control = True
        except Exception as e:
            logger.error(f"Error uploading to BQ: {e}")

        ## ----- update data store ----- ##
        if bq_control:
            try:
                await update_datastore_ops()
                logger.info(
                    f"Updating the data store, waiting for operation to complete..."
                )
            except Exception as e:
                logger.error(f"Error updating the data store: {e}")


if __name__ == "__main__":
    asyncio.run(main())
