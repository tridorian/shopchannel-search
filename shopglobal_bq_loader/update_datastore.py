from google.oauth2 import service_account
from google.cloud import discoveryengine
from google.cloud.discoveryengine import BigQuerySource

CREDENTIALS_FILE = "gcp_master_key.json"
DATA_STORE_ID = "shopchannel-products_1750769018113"
DATA_STORE = "shopchannel-products"
GOOGLE_PROJECT_ID = "prd-search-shg-api"
GOOGLE_LOCATION = "global"
RESOURCE_NAME = f"projects/{GOOGLE_PROJECT_ID}/locations/{GOOGLE_LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}"

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


DATASET_ID = "shopchannel"
TABLE_ID = "products"

BQ_SOURCE = BigQuerySource(
    project_id=GOOGLE_PROJECT_ID,
    dataset_id=DATASET_ID,
    table_id=TABLE_ID,
    data_schema="custom",
)
PARENT = f"projects/{GOOGLE_PROJECT_ID}/locations/{GOOGLE_LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/branches/default_branch"


async def update_datastore_ops():
    doc_client = discoveryengine.DocumentServiceAsyncClient(credentials=credentials)

    # Initialize request argument(s)
    request = discoveryengine.ImportDocumentsRequest(
        parent=PARENT,
        bigquery_source=BQ_SOURCE,
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
        auto_generate_ids=True,
    )

    # Make the request
    operation = await doc_client.import_documents(request=request)

    # print("Waiting for operation to complete...")

    # response = (await operation).result()

    # Handle the response
    # return response
