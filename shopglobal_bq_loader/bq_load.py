"""
Main module for BigQuery data loading operations.
"""

from google.cloud import bigquery
from google.oauth2 import service_account
from typing import Optional, List, Dict, Any
import pandas as pd
import os
from tqdm import tqdm
import logging
from datetime import datetime
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bq_loader.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Environment variables
GCP_KEY_PATH = "gcp_master_key.json"
PROJECT_ID = "prd-search-shg-api"
CSV_FILE = "product_data_2025-07-17.csv"
DATASET_ID = "shopchannel"
RAW_TABLE_ID = "products_raw"
FILTERED_TABLE_ID = "products"
BATCH_SIZE = 10000


class BigQueryLoader:
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize the BigQuery loader.
        """
        credentials = service_account.Credentials.from_service_account_file(
            GCP_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        # If project_id is not provided, use the one from credentials
        if project_id is None:
            project_id = credentials.project_id

        self.client = bigquery.Client(
            credentials=credentials,
            project=project_id,
        )
        self.project_id = project_id

    def test_connection(self) -> bool:
        """
        Test the connection to BigQuery.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            # List datasets to test connection
            list(self.client.list_datasets(max_results=1))
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _process_batch(
        self,
        df_batch: pd.DataFrame,
        full_table_id: str,
        job_config: bigquery.LoadJobConfig,
        batch_num: int,
        total_batches: int,
    ) -> bool:
        """
        Process a single batch of data.

        Args:
            df_batch: DataFrame containing the batch data
            full_table_id: Full BigQuery table ID
            job_config: BigQuery job configuration
            batch_num: Current batch number
            total_batches: Total number of batches

        Returns:
            bool: True if batch was processed successfully
        """
        try:
            # Rename 'id' column to 'record_id' if it exists
            if "id" in df_batch.columns:
                df_batch = df_batch.rename(columns={"id": "record_id"})

            job = self.client.load_table_from_dataframe(
                df_batch, full_table_id, job_config=job_config
            )
            job.result()
            logger.info(f"Batch {batch_num}/{total_batches} uploaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error uploading batch {batch_num}/{total_batches}: {str(e)}")
            return False

    def _read_csv_safely(
        self, file_path: str, encoding: str = "utf-8"
    ) -> List[Dict[str, Any]]:
        """
        Safely read CSV file handling inconsistent columns.

        Args:
            file_path: Path to the CSV file
            encoding: File encoding

        Returns:
            List of dictionaries containing the data
        """
        data = []
        expected_columns = None

        with open(file_path, "r", encoding=encoding) as f:
            csv_reader = csv.reader(f)
            headers = next(csv_reader)  # Get headers
            # Rename 'id' column to 'record_id'
            headers = ["record_id" if h == "id" else h for h in headers]
            expected_columns = len(headers)

            for row_num, row in enumerate(
                csv_reader, start=2
            ):  # start=2 because we already read header
                try:
                    if len(row) != expected_columns:
                        logger.warning(
                            f"Line {row_num}: Expected {expected_columns} columns, got {len(row)}. Truncating/expanding row."
                        )
                        # Truncate or expand row to match expected columns
                        if len(row) > expected_columns:
                            row = row[:expected_columns]
                        else:
                            row.extend([""] * (expected_columns - len(row)))

                    # Convert row to dictionary
                    row_dict = dict(zip(headers, row))
                    data.append(row_dict)
                except Exception as e:
                    logger.error(f"Error processing line {row_num}: {str(e)}")
                    continue

        return data

    def load_csv_to_bigquery(
        self,
        csv_file_path: str,
        dataset_id: str,
        table_id: str,
        *,
        write_disposition: str = "WRITE_TRUNCATE",
        autodetect_schema: bool = False,
        encoding: str = "utf-8",
        batch_size: int = 10000,
        error_file: str = "error_rows.csv",
        test_mode: bool = False,
        test_rows: int = 100,
    ) -> None:
        """
        Load data from a CSV file into a BigQuery table.

        Args:
            csv_file_path: Path to the CSV file
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            write_disposition: What to do if table exists ('WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY')
            autodetect_schema: Whether to automatically detect the schema
            encoding: File encoding (default: utf-8)
            batch_size: Number of rows to process in each batch
            error_file: Path to save rows that failed to process
            test_mode: If True, only process the first test_rows rows
            test_rows: Number of rows to process in test mode

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            Exception: For other errors during upload
        """
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        # Define schema
        schema = [
            bigquery.SchemaField("record_id", "STRING"),
            bigquery.SchemaField("product_number", "STRING"),
            bigquery.SchemaField("product_name", "STRING"),
            bigquery.SchemaField("is_published", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("sale_start_date", "STRING"),
            bigquery.SchemaField("sale_end_date", "STRING"),
            bigquery.SchemaField("stock", "STRING"),
            bigquery.SchemaField("sale_price", "STRING"),
            bigquery.SchemaField("regular_price", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("brands", "STRING"),
            bigquery.SchemaField("image_uri", "STRING"),
            bigquery.SchemaField("custom_uri", "STRING"),
            bigquery.SchemaField("is_product_variation", "STRING"),
        ]

        # Configure the job
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            schema=schema,
            source_format=bigquery.SourceFormat.CSV,
            allow_quoted_newlines=True,  # Allow newlines in quoted fields
            encoding="UTF-8",
        )

        # Construct full table ID
        full_table_id = f"{self.project_id}.{dataset_id}.{table_id}"

        # Initialize error tracking
        error_rows: List[Dict[str, Any]] = []
        total_rows_processed = 0
        successful_rows = 0

        try:
            # Read the CSV file directly into a DataFrame
            logger.info(f"Starting to process file: {csv_file_path}")
            df = pd.read_csv(
                csv_file_path,
                dtype=str,
                quoting=csv.QUOTE_ALL,  # Quote all fields
                escapechar="\\",  # Use backslash as escape character
                doublequote=True,  # Allow double quotes
                encoding=encoding,
                on_bad_lines="warn",  # Warn about bad lines instead of failing
                lineterminator="\n",  # Explicitly set line terminator
            )

            # Clean column names (remove any trailing whitespace or special characters)
            df.columns = df.columns.str.strip().str.replace("\r", "")

            # Log the initial shape and column names
            logger.info(f"Initial DataFrame shape: {df.shape}")
            logger.info(f"Initial columns: {df.columns.tolist()}")

            # Map Thai column names to English
            column_mapping = {
                "ID": "record_id",
                "รหัสสินค้า": "product_number",
                "ชื่อ": "product_name",
                "เผยแพร่แล้ว": "is_published",
                "คำอธิบาย": "description",
                "วันเริ่มต้นลดราคา": "sale_start_date",
                "วันสิ้นสุดการลดราคา": "sale_end_date",
                "คลังสินค้า": "stock",
                "ราคาที่ลด": "sale_price",
                "ราคาปกติ": "regular_price",
                "หมวดหมู่": "category",
                "Brands": "brands",
                "ไฟล์รูปภาพ": "image_uri",
                "Custom URI": "custom_uri",
            }
            # Verify all columns exist before renaming
            missing_columns = [
                col for col in column_mapping.keys() if col not in df.columns
            ]
            if missing_columns:
                logger.error(f"Missing columns in CSV: {missing_columns}")
                raise ValueError(f"Missing columns in CSV: {missing_columns}")

            # Drop all columns that are not in column_mapping
            columns_to_keep = list(column_mapping.keys())
            df = df[columns_to_keep]
            logger.info(f"Columns after filtering: {list(df.columns)}")

            # Rename columns
            df = df.rename(columns=column_mapping)

            # Verify all expected columns exist after renaming
            expected_columns = set(column_mapping.values())
            actual_columns = set(df.columns)
            if expected_columns != actual_columns:
                logger.error(
                    f"Column mismatch after renaming. Expected: {expected_columns}, Got: {actual_columns}"
                )
                raise ValueError("Column mismatch after renaming")

            # Log the shape after renaming
            logger.info(f"DataFrame shape after renaming: {df.shape}")

            # Data quality checks
            logger.info("\nPerforming data quality checks...")

            # Trim record_ids and add is_product_variation column
            logger.info("Processing record_ids and adding variation flag...")
            df["record_id"] = df["record_id"].str.strip()

            # Check for empty record_ids
            empty_ids = df["record_id"].isna().sum()
            logger.info(f"Number of empty record_ids: {empty_ids}")

            # Check for duplicates
            duplicates = df["record_id"].duplicated().sum()
            if duplicates > 0:
                logger.warning(
                    f"Found {duplicates} duplicate record_ids. Keeping the latest version."
                )
                duplicate_ids = df[df["record_id"].duplicated(keep=False)][
                    "record_id"
                ].unique()
                logger.warning(f"First few duplicate record_ids: {duplicate_ids[:5]}")

                # Show example of duplicates
                for dup_id in duplicate_ids[:3]:
                    dup_rows = df[df["record_id"] == dup_id]
                    logger.warning(f"\nDuplicate records for ID {dup_id}:")
                    for _, row in dup_rows.iterrows():
                        logger.warning(f"  - Product: {row['product_name'][:50]}...")

            # Remove duplicates, keeping the last occurrence
            df = df.drop_duplicates(subset=["record_id"], keep="last")
            logger.info(f"DataFrame shape after removing duplicates: {df.shape}")

            # Check unique record_ids
            unique_ids = df["record_id"].nunique()
            logger.info(f"Number of unique record_ids: {unique_ids}")

            # Get record_id statistics
            id_stats = df["record_id"].describe()
            logger.info(f"\nRecord ID statistics:\n{id_stats}")

            # Analyze product numbers
            logger.info("\nAnalyzing product numbers...")
            # Check for empty product numbers
            empty_product_numbers = df["product_number"].isna().sum()
            logger.info(f"Number of empty product numbers: {empty_product_numbers}")

            # Check for duplicate product numbers
            duplicate_products = df["product_number"].duplicated().sum()
            logger.info(f"Number of duplicate product numbers: {duplicate_products}")

            if duplicate_products > 0:
                duplicate_product_examples = (
                    df[df["product_number"].duplicated(keep=False)]
                    .groupby("product_number")
                    .size()
                )
                logger.info(
                    f"Product numbers with duplicates (first 5):\n{duplicate_product_examples.head()}"
                )

            # Compare record_ids with product numbers
            logger.info("\nComparing record_ids with product numbers...")
            product_number_to_record_ids = df.groupby("product_number")[
                "record_id"
            ].nunique()
            multiple_record_ids = product_number_to_record_ids[
                product_number_to_record_ids > 1
            ]
            logger.info(
                f"Number of product numbers with multiple record_ids: {len(multiple_record_ids)}"
            )
            if len(multiple_record_ids) > 0:
                logger.info(
                    f"First few product numbers with multiple record_ids:\n{multiple_record_ids.head()}"
                )

            # Drop rows with empty record_id
            df = df.dropna(subset=["record_id"])
            logger.info(f"DataFrame shape after dropping empty record_id: {df.shape}")

            # Clean the data
            for col in df.columns:
                if col != "is_product_variation":  # Skip the new column
                    if col == "stock":
                        df[col] = df[col].fillna("0")
                    else:
                        df[col] = df[col].fillna("")  # Replace NaN with empty string
                    df[col] = df[col].astype(str)  # Convert all columns to string

                    # Special handling for description column
                    if col == "description":

                        def clean_description(text):
                            # First, normalize all newlines to \n
                            text = text.replace("\r\n", "\n").replace("\r", "\n")

                            # Handle the case where \n is written as literal characters
                            text = text.replace(
                                "\\\\n", "<br/>"
                            )  # Handle escaped backslash
                            text = text.replace("\\n", "<br/>")  # Handle regular \n

                            # Replace any remaining actual newlines with <br/>
                            text = text.replace("\n", "<br/>")

                            # Clean up any remaining 'n' characters that might appear after <br/>
                            text = text.replace("<br/>n", "<br/>")

                            return text

                        df[col] = df[col].apply(clean_description)
                    else:
                        # For other columns, just clean up newlines
                        df[col] = df[col].apply(
                            lambda x: x.replace("\r\n", " ")
                            .replace("\n", " ")
                            .replace("\r", " ")
                        )

            # Log sample of first row
            logger.info("\nSample of first row:")
            first_row = df.iloc[0].to_dict()
            for key, value in first_row.items():
                logger.info(
                    f"{key}: {value[:100]}..."
                )  # Show first 100 chars of each field

            # If in test mode, limit the data
            if test_mode:
                df = df.head(test_rows)
                logger.info(f"Test mode: Processing first {test_rows} rows")

            logger.info("Populate main products stock and regular_price...")

            # some product number contain "+"
            df["product_number"] = df["product_number"].apply(
                lambda x: x.replace("+", "-")
            )
            # some product number contain " "
            df["product_number"] = df["product_number"].apply(
                lambda x: x.replace(" ", "-")
            )
            # some product number contain " "
            df["product_number"] = df["product_number"].apply(
                lambda x: x.replace("*", "-")
            )
            # add product_variation
            df["is_product_variation"] = (
                df["product_number"].str.contains("-").map({True: "1", False: "0"})
            )
            main_product_numbers = set(
                [num for num in df["product_number"] if "-" not in num and num != ""]
            )
            for main_number in tqdm(main_product_numbers):
                subproduct_df = df[
                    df["product_number"].apply(
                        lambda x: x.startswith(f"{main_number}-")
                    )
                ]
                if len(subproduct_df) > 0:
                    stock_sum = str(subproduct_df["stock"].astype(int).sum().item())
                    regular_price = list(subproduct_df["regular_price"])[-1]
                    df.loc[df["product_number"] == main_number, ["stock"]] = stock_sum
                    df.loc[df["product_number"] == main_number, ["regular_price"]] = (
                        regular_price
                    )

            # Process data in batches
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i : i + batch_size].copy()
                batch_num = (i // batch_size) + 1
                total_batches = (len(df) + batch_size - 1) // batch_size

                # Use WRITE_TRUNCATE for the first batch, WRITE_APPEND for the rest
                if batch_num == 1:
                    batch_write_disposition = write_disposition
                else:
                    batch_write_disposition = "WRITE_APPEND"
                batch_job_config = bigquery.LoadJobConfig(
                    write_disposition=batch_write_disposition,
                    schema=schema,
                    source_format=bigquery.SourceFormat.CSV,
                    allow_quoted_newlines=True,
                    encoding="UTF-8",
                )

                try:
                    # Log batch information
                    logger.info(f"\nProcessing batch {batch_num}/{total_batches}")
                    logger.info(f"Batch size: {len(batch_df)} rows")
                    logger.info(
                        f"First record_id in batch: {batch_df['record_id'].iloc[0]}"
                    )

                    # Try to upload the entire batch at once
                    job = self.client.load_table_from_dataframe(
                        batch_df, full_table_id, job_config=batch_job_config
                    )
                    job.result()
                    logger.info(
                        f"Batch {batch_num}/{total_batches} uploaded successfully"
                    )
                    successful_rows += len(batch_df)
                except Exception as e:
                    logger.error(
                        f"Error uploading batch {batch_num}/{total_batches}: {str(e)}"
                    )
                    # If batch upload fails and we're in test mode, terminate
                    if test_mode:
                        raise Exception(
                            "Test mode: Error encountered, terminating process"
                        )

                    # If not in test mode, try row by row
                    for idx, row in tqdm(
                        batch_df.iterrows(),
                        total=len(batch_df),
                        desc=f"Processing batch {batch_num}/{total_batches} row by row",
                        unit="rows",
                    ):
                        try:
                            row_df = pd.DataFrame([row])
                            if self._process_batch(
                                row_df,
                                full_table_id,
                                batch_job_config,
                                batch_num,
                                total_batches,
                            ):
                                successful_rows += 1
                            else:
                                error_rows.append(
                                    {
                                        "row_index": idx + i,
                                        "batch_number": batch_num,
                                        "error_timestamp": datetime.now().isoformat(),
                                        "row_data": row.to_dict(),
                                    }
                                )
                        except Exception as e:
                            logger.error(
                                f"Error processing row {idx + i} in batch {batch_num}: {str(e)}"
                            )
                            error_rows.append(
                                {
                                    "row_index": idx + i,
                                    "batch_number": batch_num,
                                    "error_timestamp": datetime.now().isoformat(),
                                    "row_data": row.to_dict(),
                                }
                            )

                total_rows_processed += len(batch_df)

            # Save error rows to CSV if any errors occurred
            if error_rows:
                error_df = pd.DataFrame(error_rows)
                error_df.to_csv(error_file, index=False)
                logger.warning(f"Saved {len(error_rows)} error rows to {error_file}")

            # Print summary
            logger.info(
                f"""
            Upload Summary:
            - Total rows processed: {total_rows_processed}
            - Successful rows: {successful_rows}
            - Failed rows: {len(error_rows)}
            - Error log file: {error_file}
            """
            )

        except Exception as e:
            logger.error(f"Fatal error during upload: {str(e)}")
            raise


def bq_upload_ops(file_name):
    """Main entry point for the application."""
    # Initialize loader with specific project ID
    loader = BigQueryLoader(project_id=PROJECT_ID)

    if loader.test_connection():
        logger.info("Successfully connected to BigQuery!")

        try:
            # First run in test mode
            logger.info("Starting test run with first 100 rows...")
            loader.load_csv_to_bigquery(
                csv_file_path=file_name,
                dataset_id=DATASET_ID,
                table_id=RAW_TABLE_ID,
                batch_size=BATCH_SIZE,
                test_mode=True,
                test_rows=100,
            )

            # If test run successful, proceed with full load
            logger.info("Test run successful! Proceeding with full data load...")
            loader.load_csv_to_bigquery(
                csv_file_path=file_name,
                dataset_id=DATASET_ID,
                table_id=RAW_TABLE_ID,
                batch_size=BATCH_SIZE,
                test_mode=False,
            )

            # After loading raw data, create filtered table
            logger.info("Creating filtered products table...")
            client = loader.client

            # Create filtered table query
            query = f"""
            CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.{FILTERED_TABLE_ID}` AS
            SELECT 
                record_id,
                product_number,
                product_name,
                is_published,
                description,
                sale_start_date,
                sale_end_date,
                stock,
                sale_price,
                regular_price,
                category,
                brands,
                -- Take only the first image URL
                CASE 
                    WHEN image_uri IS NOT NULL AND image_uri != '' 
                    THEN SPLIT(image_uri, ',')[OFFSET(0)]
                    ELSE NULL
                END as image_uri,
                -- Create full URL for custom_uri
                CASE 
                    WHEN custom_uri IS NOT NULL AND custom_uri != ''
                    THEN CONCAT('https://www.shopch.in.th/', TRIM(custom_uri))
                    ELSE NULL
                END as custom_uri,
                is_product_variation,
                -- Add is_available column as INT64
                CASE 
                    WHEN SAFE_CAST(stock AS INT64) > 0 
                    AND SAFE_CAST(regular_price AS FLOAT64) > 0 
                    THEN 1
                    ELSE 0
                END as is_available
            FROM `{PROJECT_ID}.{DATASET_ID}.{RAW_TABLE_ID}`
            WHERE product_number IS NOT NULL 
            AND product_number != ''
            AND is_product_variation = '0'
            AND is_published = '1'
            """

            # Run the query
            query_job = client.query(query)
            query_job.result()  # Wait for the query to complete

            # Get row counts for both tables
            raw_count_query = f"SELECT COUNT(*) as count FROM `{PROJECT_ID}.{DATASET_ID}.{RAW_TABLE_ID}`"
            filtered_count_query = f"SELECT COUNT(*) as count FROM `{PROJECT_ID}.{DATASET_ID}.{FILTERED_TABLE_ID}`"

            raw_count = next(client.query(raw_count_query).result()).count
            filtered_count = next(client.query(filtered_count_query).result()).count

            logger.info(
                f"""
            Table Creation Summary:
            - Raw table ({RAW_TABLE_ID}): {raw_count} rows
            - Filtered table ({FILTERED_TABLE_ID}): {filtered_count} rows
            - Filtered out: {raw_count - filtered_count} rows
            """
            )

        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
    else:
        logger.error("Failed to connect to BigQuery. Please check your credentials.")


# if __name__ == "__main__":
#     main()
