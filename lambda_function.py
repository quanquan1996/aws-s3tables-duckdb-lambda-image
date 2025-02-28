from pyiceberg.catalog.glue import GlueCatalog
import boto3
import io
import duckdb
import urllib.parse
import pyarrow as pa
import pyarrow.parquet as pq

def parse_s3_uri(s3_uri):
    """解析 S3 URI 为 bucket 和 key"""
    parsed = urllib.parse.urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    return bucket, key

def query_s3_parquet_with_pyarrow(s3_uris, sql_query,table_name_with_db):
    """
    从 S3 下载 Parquet 文件到内存，使用 PyArrow 读取，然后用 DuckDB 查询
    """
    s3_client = boto3.client('s3')
    tables = []

    # 下载并解析所有文件
    for uri in s3_uris:
        bucket, key = parse_s3_uri(uri)
        buffer = io.BytesIO()
        s3_client.download_fileobj(bucket, key, buffer)
        buffer.seek(0)

        # 使用 PyArrow 读取 Parquet 文件
        table = pq.read_table(buffer)
        tables.append(table)

    # 合并所有表
    if tables:
        combined_table = pa.concat_tables(tables)

        # 创建 DuckDB 连接并注册 PyArrow 表
        con = duckdb.connect(database=':memory:')
        con.register('all_data', combined_table)

        # 执行查询
        modified_query = sql_query.replace(table_name_with_db, "all_data")
        result = con.execute(modified_query).fetchall()
        #print(result)
        return result
    else:
        return None
def load_and_query_iceberg_table(region, catalog_id, db_name, table_name, query):
    """
    加载Iceberg表并执行查询。

    Args:
        region (str): AWS区域。
        catalog_id (str): Glue Catalog ID。
        db_name (str): 数据库名称。
        table_name (str): 表名称。
        query (str): 要执行的SQL查询。

    Returns:
        list: 查询结果列表，每项为一行数据。
    """

    catalog = GlueCatalog(
        name="glue_catalog",
        **{
            "glue.region": region,
            "glue.id": catalog_id,
        }
    )
    table_name_with_db = f"{db_name}.{table_name}"
    table = catalog.load_table(table_name_with_db)
    files = [task.file.file_path for task in table.scan().plan_files()]
    return query_s3_parquet_with_pyarrow(files, query,table_name_with_db)


def handler(event, context):
    region = event.get("region")
    catalog_id = event.get("catalog_id")
    db_name = event.get("db_name")
    table_name = event.get("table_name")
    query = event.get("query")

    results = load_and_query_iceberg_table(region, catalog_id, db_name, table_name, query)

    return {
        "statusCode": 200,
        "body": results
    }
